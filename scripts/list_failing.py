"""List OCC-failing graphs on n vertices as "graphNumber graph6" lines.

Graph numbers follow the SSRI convention: geng -c order after keeping non-bipartite graphs with
min degree >= 2 and n+1 <= m <= C(n,2)-9 (the edge-threshold band).

Usage: nauty-geng -cq n | python3 scripts/list_failing.py > data/derived/fail<n>_graphs.txt
"""
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from toric_graphs.graph6 import num_edges, parse_g6  # noqa: E402
from toric_graphs.occ import fails_occ, is_nonbipartite  # noqa: E402

num = 0
for line in sys.stdin:
    g6 = line.strip()
    n, adj = parse_g6(g6)
    m = num_edges(adj)
    if not (n + 1 <= m <= comb(n, 2) - 9) or min(bin(a).count("1") for a in adj) < 2:
        continue
    if not is_nonbipartite(adj, (1 << n) - 1):
        continue
    num += 1
    if fails_occ(n, adj):
        print(num, g6)
