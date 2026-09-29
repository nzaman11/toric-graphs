import shutil
import subprocess

import networkx as nx
import pytest

from toric_graphs.features import compute_features
from toric_graphs.occ import fails_occ_g6

# Two triangles {0,1,2}, {3,4,5} joined by the path 2-6-3 (n=7, m=8): the smallest failing graph.
TWO_TRI_PATH = nx.to_graph6_bytes(nx.Graph([(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5), (2, 6), (6, 3)]),
                                  header=False).decode().strip()


@pytest.fixture(scope="module")
def ttp():
    return compute_features(TWO_TRI_PATH)


def test_basic_and_degree(ttp):
    assert (ttp["n"], ttp["m"], ttp["m_minus_n"]) == (7, 8, 1)
    assert (ttp["deg_count_2"], ttp["deg_count_3"]) == (5, 2)
    # degree-2 runs: {0,1}, {4,5}, {6} -> 3 threads, longest 2-0-1-2 has 3 edges
    assert (ttp["n_threads"], ttp["thread_max_len"]) == (3, 3)


def test_cycles_and_connectivity(ttp):
    assert (ttp["n_triangles"], ttp["cyc_len_3"], ttp["n_even_cycles"]) == (2, 2, 0)
    assert (ttp["girth"], ttp["odd_girth"], ttp["even_girth"]) == (3, 3, None)
    assert (ttp["n_cut_vertices"], ttp["n_bridges"], ttp["n_blocks"]) == (3, 2, 4)
    assert ttp["n_nonbipartite_blocks"] == 2
    assert (ttp["diameter"], ttp["node_connectivity"]) == (4, 1)


def test_parity_and_invariants(ttp):
    assert (ttp["odd_cycle_transversal"], ttp["edge_frustration"]) == (2, 2)
    assert (ttp["independence_number"], ttp["matching_number"]) == (3, 3)
    assert (ttp["chromatic_number"], ttp["treewidth"]) == (3, 2)
    assert ttp["aut_group_size"] == 8  # swap within each triangle (2*2) x reflect (2)
    assert ttp["signless_lap_min"] > 1e-9  # non-bipartite


def test_separated_pairs(ttp):
    assert (ttp["sep_pairs"], ttp["sep_pairs_3_3"], ttp["normalization_gap"]) == (1, 1, 1)
    assert (ttp["sep_dist_min"], ttp["sep_closest_geodesics"], ttp["sep_linkage_max"]) == (2, 1, 1)
    assert ttp["sep_same_block_pairs"] == 0
    assert ttp["sep_walk_degree_max"] == 3 + 2


def test_walk_degree_matches_generator_of_graph_1979():
    # graph 1979: two triangles at distance 3; I_G is principal, generated in degree 6
    f = compute_features("GCOe`W")
    assert (f["sep_pairs"], f["sep_dist_min"], f["sep_walk_degree_max"]) == (1, 3, 6)


def test_occ_graph_has_no_separated_pairs():
    f = compute_features("G??F~{")
    assert f["sep_pairs"] == 0 and f["normalization_gap"] == 0 and f["sep_dist_min"] is None


@pytest.mark.skipif(shutil.which("nauty-geng") is None, reason="nauty geng not installed")
def test_separated_pairs_agree_with_occ_check_n7():
    """Two independent OCC implementations (subset-based vs chordless cycles) must agree."""
    out = subprocess.run(["nauty-geng", "-cq", "-d2", "7"], capture_output=True, text=True, check=True).stdout
    for g6 in out.split():
        assert (compute_features(g6)["sep_pairs"] > 0) == fails_occ_g6(g6), g6


def test_known_invariants_petersen_and_k4():
    p = compute_features(nx.to_graph6_bytes(nx.petersen_graph(), header=False).decode().strip())
    assert (p["girth"], p["aut_group_size"], p["chromatic_number"], p["treewidth"]) == (5, 120, 3, 4)
    assert (p["independence_number"], p["n_spanning_trees"]) == (4, 2000)
    k4 = compute_features(nx.to_graph6_bytes(nx.complete_graph(4), header=False).decode().strip())
    assert (k4["aut_group_size"], k4["treewidth"], k4["n_spanning_trees"], k4["cyc_len_4"]) == (24, 3, 16, 3)
