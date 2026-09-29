import shutil
import subprocess
from collections import Counter
from math import comb

import pytest

from toric_graphs.graph6 import edge_list, num_edges, parse_g6, triangle_count
from toric_graphs.occ import fails_occ, fails_occ_g6, is_nonbipartite, occ_witness


def from_edges(n, edges):
    adj = [0] * n
    for u, v in edges:
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    return n, adj


TRI_A = [(0, 1), (1, 2), (0, 2)]
TRI_B = [(3, 4), (4, 5), (3, 5)]


def test_two_triangles_joined_by_edge_satisfies():
    assert not fails_occ(*from_edges(6, TRI_A + TRI_B + [(2, 3)]))


def test_two_triangles_joined_by_path_fails():
    # smallest failing graph from the edge-threshold construction (n=7, m=8)
    n, adj = from_edges(7, TRI_A + TRI_B + [(2, 6), (6, 3)])
    assert fails_occ(n, adj)
    S, T = occ_witness(n, adj)
    assert {S, T} == {0b000111, 0b111000}


def test_bipartite_graph_satisfies():
    assert not fails_occ(*from_edges(6, [(i, (i + 1) % 6) for i in range(6)]))
    assert not is_nonbipartite(from_edges(4, [(0, 1), (1, 2), (2, 3), (3, 0)])[1], 0b1111)


def test_triangle_and_pentagon_via_bridge_vertex_fails():
    pent = [(3, 4), (4, 5), (5, 6), (6, 7), (7, 3)]
    assert fails_occ(*from_edges(9, TRI_A + pent + [(2, 8), (8, 3)]))


def test_known_graphs_from_navila_data():
    assert fails_occ_g6("GCOe`W")      # graph 1979: CM, Gorenstein, complete intersection
    assert not fails_occ_g6("G??F~{")  # graph 1: all odd cycles share the edge 7-8
    assert not fails_occ_g6("F?B~w")   # "Graph 1" in the SSRI notes


def test_graph6_helpers():
    n, adj = parse_g6("GCOe`W")
    assert (n, num_edges(adj), triangle_count(n, adj)) == (8, 9, 2)
    assert edge_list(n, adj)[0] == (1, 4)


GENG = shutil.which("nauty-geng") or shutil.which("geng")


def geng(*args):
    out = subprocess.run([GENG, "-q", *args], capture_output=True, text=True, check=True).stdout
    return out.split()


@pytest.mark.skipif(GENG is None, reason="nauty geng not installed")
@pytest.mark.parametrize("n", [7, 8])
def test_edge_threshold_theorem(n):
    """Failing graphs exist for exactly n+1 <= m <= C(n,2)-9 (connected, min degree >= 2)."""
    fail = Counter()
    for g6 in geng("-c", "-d2", str(n)):
        n_, adj = parse_g6(g6)
        if fails_occ(n_, adj):
            fail[num_edges(adj)] += 1
    assert set(fail) == set(range(n + 1, comb(n, 2) - 9 + 1))


@pytest.mark.skipif(GENG is None, reason="nauty geng not installed")
def test_n8_failing_count_matches_research_data():
    """161 failing graphs at n=8 = 51 CM + 110 non-CM in Navila's Macaulay2 results."""
    total = sum(1 for g6 in geng("-c", "-d2", "8", "9:19") if fails_occ_g6(g6))
    assert total == 161
