"""Check conjecture C5: a Hamiltonian graph failing OCC is not CM (see conjectures.md).

Read-only: uses the SQLite database for n <= 9 and the n = 10 run files (data/derived/fail10_*);
no Macaulay2. At n = 10 the depth is over ZZ/32003, where depth 10 proves CM over QQ; depth < 10
there is only a screen.

Usage:  python3 scripts/check_hamiltonian.py [--workers 8]
"""
import argparse
import sqlite3
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from toric_graphs.m2parse import h_vector  # noqa: E402

DERIVED = ROOT / "data" / "derived"
DB = ROOT / "data" / "toric_graphs.sqlite"


def is_hamiltonian(g6: str) -> bool:
    """Held-Karp bitmask DP: is there a cycle through every vertex?"""
    G = nx.from_graph6_bytes(g6.encode())
    n = G.number_of_nodes()
    adj = [0] * n
    for i, j in G.edges():
        adj[i] |= 1 << j
        adj[j] |= 1 << i
    reach = [0] * (1 << n)  # reach[S]: end vertices of paths from vertex 0 covering exactly S
    reach[1] = 1
    for S in range(1, 1 << n, 2):
        ends = reach[S]
        while ends:
            v = (ends & -ends).bit_length() - 1
            ends &= ends - 1
            nxt = adj[v] & ~S
            while nxt:
                w = (nxt & -nxt).bit_length() - 1
                nxt &= nxt - 1
                reach[S | (1 << w)] |= 1 << w
    last = reach[(1 << n) - 1]
    return any((last >> v) & 1 and adj[v] & 1 for v in range(n))


def _ham(item: tuple) -> tuple:
    return item[0], is_hamiltonian(item[1])


def small_n(pool: Pool) -> None:
    con = sqlite3.connect(DB)
    rows = con.execute("""select g.n, g.graph_number, g.graph6, r.is_cm from graphs g
                          join m2_results r using (graph6) where g.fails_occ = 1""").fetchall()
    ham = dict(pool.map(_ham, [((n, num), g6) for n, num, g6, _ in rows], chunksize=500))
    tab = Counter((n, ham[(n, num)], bool(cm)) for n, num, _, cm in rows)
    for n in sorted({r[0] for r in rows}):
        print(f"n = {n}: Hamiltonian CM / not CM = {tab[(n, True, True)]} / {tab[(n, True, False)]};"
              f"  not Hamiltonian = {tab[(n, False, True)]} / {tab[(n, False, False)]}")


def n10(pool: Pool) -> None:
    graphs = [(int(a), b) for a, b in
              (ln.split() for ln in (DERIVED / "fail10_graphs.txt").read_text().splitlines())]
    neg = {}
    for ln in (DERIVED / "fail10_hilbert.tsv").read_text().splitlines():
        p = ln.split("\t")
        if len(p) >= 5 and p[0].isdigit():
            neg[int(p[0])] = min(h_vector(p[3])) < 0
    depth = {}
    for ln in (DERIVED / "fail10_depth.txt").read_text().splitlines():
        t = ln.split()
        if len(t) >= 3 and t[0].isdigit() and t[1].lstrip("-").isdigit():
            depth[int(t[0])] = int(t[1])
    ham = dict(pool.imap_unordered(_ham, graphs, chunksize=2000))
    tab, counterexamples = Counter(), []
    for num, _ in graphs:
        if num not in neg:
            status = "no Hilbert series"
        elif neg[num]:
            status = "negative h => not CM (proved)"
        elif num not in depth:
            status = "h >= 0, depth not computed"
        elif depth[num] == 10:
            status = "h >= 0, depth 10 => CM (proved)"
            if ham[num]:
                counterexamples.append(num)
        else:
            status = "h >= 0, depth < 10 over ZZ/p (screen)"
        tab[(ham[num], status)] += 1
    for h in (True, False):
        print(f"n = 10, {'Hamiltonian' if h else 'not Hamiltonian'}:")
        for (hh, status), v in sorted(tab.items()):
            if hh == h:
                print(f"   {status:42s} {v:7d}")
    print(f"C5 counterexamples at n = 10 (Hamiltonian and CM): {len(counterexamples)};"
          f" first: {sorted(counterexamples)[:10]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    with Pool(a.workers) as pool:
        small_n(pool)
        n10(pool)


if __name__ == "__main__":
    main()
