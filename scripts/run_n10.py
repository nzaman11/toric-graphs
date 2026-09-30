"""Test conjecture C2' at n vertices: every OCC-failing graph with nonnegative h-vector is CM.

Steps (each resumable; rerun the same command after an interruption):
  enumerate  list OCC-failing graphs with nauty (parallel slices), then number them in geng order
  hilbert    toric ideal + Hilbert series for every failing graph (batched M2 sessions)
  depth      depth over ZZ/32003 for graphs with h >= 0 (depth = n proves CM over QQ)
  summary    counts and C2' verdict -> data/derived/fail<n>_summary.json
  all        everything, in order

Usage:  python3 scripts/run_n10.py all --n 10 --workers 8
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from toric_graphs.batch import run_batches  # noqa: E402
from toric_graphs.graph6 import num_edges, parse_g6  # noqa: E402
from toric_graphs.m2parse import h_vector  # noqa: E402
from toric_graphs.occ import is_nonbipartite  # noqa: E402

DERIVED = ROOT / "data" / "derived"


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def geng() -> str:
    for name in ("nauty-geng", "geng"):
        if shutil.which(name):
            return name
    sys.exit("nauty geng not found (install the 'nauty' package)")


def paths(n: int) -> dict[str, Path]:
    return {k: DERIVED / f"fail{n}_{k}" for k in
            ("graphs.txt", "hilbert.tsv", "depth.txt", "summary.json", "enum.parts")}


# ---------------------------------------------------------------- enumerate + number

def enumerate_failing(n: int, workers: int, slices: int) -> None:
    p = paths(n)
    if p["graphs.txt"].exists():
        log(f"{p['graphs.txt'].name} exists; skipping enumeration")
        return
    parts = p["enum.parts"]
    parts.mkdir(parents=True, exist_ok=True)
    lo, hi = n + 1, comb(n, 2) - 9

    def slice_job(r: int) -> None:
        logf = parts / f"s{r}.log"
        if logf.exists() and "seen" in logf.read_text():
            return
        cmd = (f"{geng()} -cq -d2 {n} {lo}:{hi} {r}/{slices} | "
               f"{sys.executable} {ROOT / 'scripts' / 'count_failing.py'} > {parts / f's{r}.g6'} 2> {logf}")
        subprocess.run(cmd, shell=True, check=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for k, _ in enumerate(pool.map(slice_job, range(slices)), 1):
            if k % max(1, slices // 20) == 0:
                log(f"enumerate: {k}/{slices} slices done ({(time.time() - t0) / 60:.1f} min)")
    failing = set()
    for f in parts.glob("s*.g6"):
        failing.update(x for x in f.read_text().split() if x)
    log(f"enumerate: {len(failing)} failing graphs; numbering in full geng order (single pass)")

    # graph numbers: position in `geng -c n` order after the SSRI filters (as for n = 8, 9)
    tmp = p["graphs.txt"].with_suffix(".tmp")
    num = found = 0
    proc = subprocess.Popen([geng(), "-cq", str(n)], stdout=subprocess.PIPE, text=True)
    with open(tmp, "w") as out:
        for line in proc.stdout:
            g6 = line.strip()
            nn, adj = parse_g6(g6)
            m = num_edges(adj)
            if not (lo <= m <= hi) or min(bin(a).count("1") for a in adj) < 2:
                continue
            if not is_nonbipartite(adj, (1 << nn) - 1):
                continue
            num += 1
            if g6 in failing:
                out.write(f"{num} {g6}\n")
                found += 1
    proc.wait()
    if found != len(failing):
        sys.exit(f"numbering found {found} of {len(failing)} failing graphs; not writing {p['graphs.txt']}")
    tmp.replace(p["graphs.txt"])
    log(f"enumerate: wrote {p['graphs.txt'].name} ({found} graphs; {num} graphs in the band)")


def read_graphs(n: int) -> list[tuple[int, str]]:
    return [(int(a), b) for a, b in (ln.split() for ln in paths(n)["graphs.txt"].read_text().splitlines())]


# ---------------------------------------------------------------- M2 stages

def hilbert_rows(n: int) -> dict[int, list[str]]:
    rows = {}
    f = paths(n)["hilbert.tsv"]
    if f.exists():
        for ln in f.read_text().splitlines():
            parts = ln.split("\t")
            if parts and parts[0].isdigit():
                rows[int(parts[0])] = parts
    return rows


def take_share(items: list, share: str | None) -> list:
    """share 'k/K' or 'k1,k2/K': keep items whose position i has i % K in {k...} (interleaved, so
    shares are equally hard). E.g. laptop '1,2/3' and droplet '0/3' split the work 2:1."""
    if not share:
        return items
    ks, big_k = share.split("/")
    keep, big_k = {int(k) for k in ks.split(",")}, int(big_k)
    return [it for i, it in enumerate(items) if i % big_k in keep]


def stage_hilbert(n: int, workers: int, batch: int, timeout: float, share: str | None = None) -> None:
    items = take_share(read_graphs(n), share)
    log(f"hilbert: {len(items)} graphs" + (f" (share {share})" if share else ""))
    run_batches(items, ROOT / "m2" / "compute_hilbert.m2", paths(n)["hilbert.tsv"], n,
                workers=workers, batch_size=batch, timeout=timeout, min_fields=5, log=log)


def nonneg_graphs(n: int) -> list[tuple[int, str]]:
    g6 = dict(read_graphs(n))
    return sorted((k, g6[k]) for k, r in hilbert_rows(n).items()
                  if len(r) >= 5 and min(h_vector(r[3])) >= 0)


def stage_depth(n: int, workers: int, batch: int, timeout: float) -> None:
    items = nonneg_graphs(n)
    log(f"depth: {len(items)} graphs with nonnegative h-vector")
    run_batches(items, ROOT / "m2" / "time_depth.m2", paths(n)["depth.txt"], n,
                workers=workers, batch_size=batch, timeout=timeout, min_fields=3, log=log)


# ---------------------------------------------------------------- summary

def summary(n: int) -> dict:
    graphs = read_graphs(n)
    hil = hilbert_rows(n)
    ok = {k: r for k, r in hil.items() if len(r) >= 5}
    neg = {k for k, r in ok.items() if min(h_vector(r[3])) < 0}
    nonneg = set(ok) - neg
    depth = {}
    f = paths(n)["depth.txt"]
    if f.exists():
        for ln in f.read_text().splitlines():
            t = ln.split()
            if len(t) >= 3 and t[0].isdigit() and t[1].lstrip("-").isdigit():
                depth[int(t[0])] = int(t[1])
    cm = {k for k in nonneg if depth.get(k) == n}
    screened = sorted(k for k in nonneg if k in depth and depth[k] < n)  # C2' candidates: confirm over QQ
    s = {
        "n": n, "failing_graphs": len(graphs),
        "hilbert_done": len(ok), "hilbert_failed": sorted(set(hil) - set(ok)),
        "negative_h_not_CM": len(neg), "nonnegative_h": len(nonneg),
        "proven_CM": len(cm), "depth_missing": sorted(nonneg - set(depth)),
        "C2prime_candidates_ZZp_depth_below_n": screened,
        "hilbert_cpu_hours": round(sum(float(r[4]) for r in ok.values()) / 3600, 2),
        "top_h_coefficients_not_CM": dict(Counter(h_vector(ok[k][3])[-1] for k in neg).most_common(8)),
    }
    s["C2prime_holds_so_far"] = not screened and not s["depth_missing"] and not s["hilbert_failed"] \
        and len(ok) == len(graphs)
    paths(n)["summary.json"].write_text(json.dumps(s, indent=1) + "\n")
    log("summary: " + json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in s.items()}))
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["enumerate", "hilbert", "depth", "summary", "all"])
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--slices", type=int, default=400, help="geng res/mod slices for enumeration")
    ap.add_argument("--batch", type=int, default=500, help="graphs per Macaulay2 session")
    ap.add_argument("--timeout", type=float, default=4 * 3600, help="seconds per Macaulay2 session")
    ap.add_argument("--share", default=None,
                    help="k/K: hilbert step only does every K-th graph from position k (split across machines)")
    a = ap.parse_args()
    DERIVED.mkdir(parents=True, exist_ok=True)
    if a.step in ("enumerate", "all"):
        enumerate_failing(a.n, a.workers, a.slices)
    if a.step in ("hilbert", "all"):
        stage_hilbert(a.n, a.workers, a.batch, a.timeout, a.share)
    if a.step in ("depth", "all"):
        stage_depth(a.n, a.workers, max(1, a.batch // 5), a.timeout)
    if a.step in ("summary", "all"):
        summary(a.n)


if __name__ == "__main__":
    main()
