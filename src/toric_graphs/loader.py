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
    if is_cm is None:
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
         (int(is_cm and sym) if sym is not None else (0 if not is_cm else None)),
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
    """Last record per graph from a runner .jsonl file (a retried timeout supersedes the timeout)."""
    recs: dict[int, dict] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:  # last line of a file still being written
                    continue
                if r["status"] == "done" or r["graph_number"] not in recs:
                    recs[r["graph_number"]] = r
    return recs


def load_runs_jsonl(conn: sqlite3.Connection, path: Path, source: str = "runner_n9") -> tuple[int, int]:
    """Runner output. Every graph gets a graphs row; finished ones also get m2_results."""
    done = timeouts = 0
    for r in latest_runs(path).values():
        upsert_graph(conn, r["graph6"], r["graph_number"])
        if r["status"] != "done":
            timeouts += 1
            continue
        upsert_result(conn, r["graph6"], source, depth=r.get("depth"), hilbert_series=r["hilbert_series"],
                      toric_ideal=r["toric_ideal"], gens_minimal=1, is_cm=r["is_cm"], decided_by=r["decided_by"],
                      seconds=(r.get("seconds_ker"), r.get("wall_depth_zzp"), r.get("seconds_hilbert")))
        done += 1
    return done, timeouts


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
