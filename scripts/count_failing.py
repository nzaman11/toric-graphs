"""Filter graph6 lines from stdin to OCC-failing, non-bipartite, leaf-free graphs in the edge band.

Unlike list_failing.py this does not number graphs (numbering needs the full geng order), so it can
run on geng res/mod slices in parallel. Prints failing graph6 strings; a count goes to stderr.

Usage: nauty-geng -cq -d2 10 11:36 0/200 | python3 scripts/count_failing.py > slice.g6
"""
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from toric_graphs.graph6 import num_edges, parse_g6  # noqa: E402
from toric_graphs.occ import fails_occ, is_nonbipartite  # noqa: E402

seen = kept = 0
for line in sys.stdin:
    g6 = line.strip()
    n, adj = parse_g6(g6)
    seen += 1
    m = num_edges(adj)
    if not (n + 1 <= m <= comb(n, 2) - 9) or min(bin(a).count("1") for a in adj) < 2:
        continue
    if is_nonbipartite(adj, (1 << n) - 1) and fails_occ(n, adj):
        kept += 1
        print(g6)
print(f"seen {seen} failing {kept}", file=sys.stderr)
