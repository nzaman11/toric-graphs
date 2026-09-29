"""Load Macaulay2 results into the SQLite database."""

import ast
import json
import sqlite3
from pathlib import Path

from .graph6 import edge_list, num_edges, parse_g6
from .m2parse import binomial_degree, h_vector, hilbert_dim, ideal_generators, read_blocks
from .occ import occ_witness

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"


def _mask_to_vertices(mask: int) -> list[int]:
    return [v + 1 for v in range(mask.bit_length()) if (mask >> v) & 1]


def upsert_graph(conn: sqlite3.Connection, g6: str, graph_number: int | None = None) -> None:
    n, adj = parse_g6(g6)
    w = occ_witness(n, adj)
    conn.execute(
        """INSERT INTO graphs (graph6, n, graph_number, m, edges, fails_occ, occ_witness)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(graph6) DO UPDATE SET graph_number = COALESCE(excluded.graph_number, graph_number)""",
        (g6, n, graph_number, num_edges(adj), json.dumps(edge_list(n, adj)), int(w is not None),
         json.dumps([_mask_to_vertices(w[0]), _mask_to_vertices(w[1])]) if w else None),
    )


def upsert_result(conn: sqlite3.Connection, g6: str, source: str, *, depth: int | None,
                  hilbert_series: str | None, toric_ideal: str | None, gens_minimal: int | None,
                  seconds: tuple[float | None, float | None, float | None] = (None, None, None),
                  is_cm: int | None = None, decided_by: str = "depth_QQ") -> None:
    n, adj = parse_g6(g6)
    m = num_edges(adj)
    if is_cm is None and depth is not None:
        is_cm = int(depth == n)
    h = h_vector(hilbert_series) if hilbert_series else None
    if hilbert_series and hilbert_dim(hilbert_series) != n:
        raise ValueError(f"{g6}: Hilbert series dimension {hilbert_dim(hilbert_series)} != n = {n}")
    sym = int(h == h[::-1]) if h else None
    gens = ideal_generators(toric_ideal) if toric_ideal else None
    degs = sorted(binomial_degree(g) for g in gens) if gens is not None else None
    is_ci = None
    if gens is not None:
        if len(gens) == m - n:
            is_ci = 1
        elif gens_minimal:
            is_ci = 0
    conn.execute(
        """INSERT OR REPLACE INTO m2_results
           (graph6, source, depth, is_cm, decided_by, h_vector, h_symmetric, is_gorenstein, num_gens,
            gen_degrees, gens_minimal, is_ci, toric_ideal, seconds_ker, seconds_depth, seconds_hilbert)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (g6, source, depth, is_cm, decided_by, json.dumps(h) if h else None, sym,
         # Gorenstein = CM + symmetric h (Stanley); unknown when CM is unknown
         (None if is_cm is None else 0 if not is_cm else sym),
         len(gens) if gens is not None else None, json.dumps(degs) if degs is not None else None,
         gens_minimal, is_ci, toric_ideal, *seconds),
    )


def load_ssri_n8(conn: sqlite3.Connection, raw: Path = RAW) -> int:
    """Original SSRI 2026 n = 8 CM graphs: CMgraphs8 + CMHash8Live_full + task3 Hilbert series."""
    numbers = {}
    for line in (raw / "CMgraphs8.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            num, g6, *_ = ast.literal_eval(line)
            numbers[g6] = num
    live = {r["Graph6"]: r for r in read_blocks(raw / "CMHash8Live_full.txt")}
    hilb = {r["Graph6"]: r["ReducedHilbertSeries"] for r in read_blocks(raw / "task3_Hilbert_CM_all8.txt")}
    if not (set(numbers) == set(live) == set(hilb)):
        raise ValueError("SSRI n=8 files disagree on which graphs they contain")
    for g6, num in numbers.items():
        upsert_graph(conn, g6, num)
        upsert_result(conn, g6, "ssri_2026", depth=int(live[g6]["Depth"]), hilbert_series=hilb[g6],
                      toric_ideal=live[g6]["ToricIdeal"], gens_minimal=None)
    return len(numbers)


def latest_runs(path: Path) -> dict[int, dict]:
    """Best record per graph from a runner .jsonl file: a final record (done/unconfirmed) beats a
    timeout/error, and later lines beat earlier ones of the same kind (retries)."""
    from .runner import FINAL, read_records

    recs: dict[int, dict] = {}
    for r in read_records(path):
        old = recs.get(r["graph_number"])
        if old is None or r["status"] in FINAL or old["status"] not in FINAL:
            recs[r["graph_number"]] = r
    return recs


def run_verdict(r: dict) -> tuple[int | None, str | None]:
    """(is_cm, decided_by) from one runner record, using only what is PROVEN.

    depth_ZZp = n proves CM over QQ (depth_ZZp <= depth_QQ <= n for toric rings); a negative
    h-coefficient proves not CM; depth over QQ decides exactly. A ZZ/p depth < n alone is only a
    screen (is_cm None). Also reinterprets records from the first n = 9 run, whose runner still ran
    the (redundant) QQ confirmation and labelled ZZ/p screens 'depth_ZZp'.
    """
    n = r.get("n")
    if r.get("depth_zzp") is not None and r["depth_zzp"] == n:
        return 1, "depth_ZZp_eq_n"
    if r.get("decided_by") == "negative_h":
        return 0, "negative_h"
    if r.get("depth") is not None:
        return int(r["depth"] == n), "depth_QQ"
    if r.get("depth_zzp") is not None:
        return None, "screen_ZZp"
    return None, None


def load_runs_jsonl(conn: sqlite3.Connection, path: Path, source: str = "runner_n9") -> tuple[int, int]:
    """Runner output. Every graph gets a graphs row; graphs with a computed ideal get m2_results.
    Returns (graphs with a proven CM verdict, graphs without one)."""
    decided = undecided = 0
    for r in latest_runs(path).values():
        upsert_graph(conn, r["graph6"], r["graph_number"])
        is_cm, how = run_verdict(r)
        if "hilbert_series" not in r:  # timed out or failed before the ideal stage
            undecided += 1
            continue
        depth_cpu = r.get("seconds_depth_qq", r.get("seconds_depth_zzp"))
        upsert_result(conn, r["graph6"], source, depth=r.get("depth"), hilbert_series=r["hilbert_series"],
                      toric_ideal=r["toric_ideal"], gens_minimal=1, is_cm=is_cm, decided_by=how,
                      seconds=(r.get("seconds_ker"), depth_cpu, r.get("seconds_hilbert")))
        decided += is_cm is not None
        undecided += is_cm is None
    return decided, undecided


def load_m2_results(conn: sqlite3.Connection, path: Path, source: str = "recomputed") -> int:
    """Output of m2/compute_graphs.m2 (generators are trimmed, so minimal)."""
    recs = read_blocks(path)
    for r in recs:
        g6 = r["Graph6"]
        upsert_graph(conn, g6, int(r["GraphNumber"]))
        upsert_result(conn, g6, source, depth=int(r["Depth"]), hilbert_series=r["ReducedHilbertSeries"],
                      toric_ideal=r["ToricIdeal"], gens_minimal=1,
                      seconds=(float(r["SecondsKer"]), float(r["SecondsDepth"]), float(r["SecondsHilbert"])))
    return len(recs)
