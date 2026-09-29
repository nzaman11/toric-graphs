"""Structural graph features. Graph-only: nothing here may use Macaulay2 output.

All exact computations are brute force over vertex subsets, which is fine for n <= 10.
Counts use names that mean the same thing for every n so models can transfer across n.

Groups:
  basic, degree, threads (D), triangles, cycles, connectivity, spectra, symmetry,
  parity (C: distance from bipartite), separated odd-cycle pairs (A) and the
  normalization gap (B), standard invariants (E).
"""

from itertools import combinations

import networkx as nx
import numpy as np

from .graph6 import parse_g6
from .occ import is_nonbipartite

MAX_CYCLE_LEN = 10  # cycle-count columns cyc_len_3 .. cyc_len_10 (fixed schema across n)


def to_nx(n: int, adj: list[int]) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from((u, v) for u in range(n) for v in range(u + 1, n) if (adj[u] >> v) & 1)
    return G


def _popcount(x: int) -> int:
    return bin(x).count("1")


def _mask(vs) -> int:
    out = 0
    for v in vs:
        out |= 1 << v
    return out


# ---------------------------------------------------------------- group D: threads

def threads(n: int, adj: list[int]) -> tuple[int, int]:
    """Maximal runs of degree-2 vertices. Returns (count, longest thread length in edges)."""
    deg2 = [v for v in range(n) if _popcount(adj[v]) == 2]
    H = nx.Graph()
    H.add_nodes_from(deg2)
    H.add_edges_from((u, v) for u, v in combinations(deg2, 2) if (adj[u] >> v) & 1)
    comps = list(nx.connected_components(H))
    return len(comps), max((len(c) + 1 for c in comps), default=0)


# ---------------------------------------------------------------- group C: parity

def odd_cycle_transversal(n: int, adj: list[int]) -> int:
    """Fewest vertices whose deletion leaves a bipartite graph."""
    full = (1 << n) - 1
    for k in range(n + 1):
        for D in combinations(range(n), k):
            if not is_nonbipartite(adj, full & ~_mask(D)):
                return k
    return n


def max_cut(n: int, adj: list[int]) -> int:
    edges = [(u, v) for u in range(n) for v in range(u + 1, n) if (adj[u] >> v) & 1]
    best = 0
    for X in range(1 << (n - 1)):  # fix vertex n-1 on side 0
        best = max(best, sum(((X >> u) ^ (X >> v)) & 1 for u, v in edges))
    return best


# ---------------------------------------------------------------- group E: invariants

def independence_number(n: int, adj: list[int]) -> int:
    best = 0
    for S in range(1 << n):
        k = _popcount(S)
        if k > best and all(not (adj[v] & S) for v in range(n) if (S >> v) & 1):
            best = k
    return best


def chromatic_number(n: int, adj: list[int]) -> int:
    order = sorted(range(n), key=lambda v: -_popcount(adj[v]))

    def colorable(k: int) -> bool:
        color = [-1] * n

        def bt(i: int) -> bool:
            if i == n:
                return True
            v = order[i]
            used = {color[u] for u in range(n) if (adj[v] >> u) & 1 and color[u] >= 0}
            for c in range(k):
                if c not in used:
                    color[v] = c
                    if bt(i + 1):
                        return True
            color[v] = -1
            return False

        return bt(0)

    k = 1 if not any(adj) else 2
    while not colorable(k):
        k += 1
    return k


def treewidth(n: int, adj: list[int]) -> int:
    """Exact treewidth by the O*(2^n) elimination-ordering DP (Bodlaender et al. 2006)."""

    def q(S: int, v: int) -> int:
        # vertices outside S+v reachable from v through S
        seen, stack, out = (1 << v), [v], 0
        while stack:
            u = stack.pop()
            nb = adj[u] & ~seen
            seen |= nb
            while nb:
                low = nb & -nb
                w = low.bit_length() - 1
                nb ^= low
                if (S >> w) & 1:
                    stack.append(w)
                else:
                    out += 1
        return out

    tw = [0] * (1 << n)
    tw[0] = -1
    for S in range(1, 1 << n):
        best = n
        rest = S
        while rest:
            low = rest & -rest
            v = low.bit_length() - 1
            rest ^= low
            best = min(best, max(tw[S ^ low], q(S ^ low, v)))
        tw[S] = best
    return tw[(1 << n) - 1]


# ---------------------------------------------------------------- groups A and B

def _closed_nbhd(adj: list[int], S: int) -> int:
    out, rest = S, S
    while rest:
        low = rest & -rest
        out |= adj[low.bit_length() - 1]
        rest ^= low
    return out


def _set_distance_and_geodesics(G: nx.Graph, A: frozenset, B: frozenset) -> tuple[int, int]:
    """Shortest distance between vertex sets A, B and number of shortest A-B paths."""
    dist = {a: 0 for a in A}
    count = {a: 1 for a in A}
    frontier = list(A)
    while frontier:
        nxt = []
        for u in frontier:
            for w in G[u]:
                if w not in dist:
                    dist[w] = dist[u] + 1
                    count[w] = 0
                    nxt.append(w)
                if dist[w] == dist[u] + 1:
                    count[w] += count[u]
        hits = [b for b in B if b in dist]
        if hits:
            d = min(dist[b] for b in hits)
            return d, sum(count[b] for b in hits if dist[b] == d)
        frontier = nxt
    return -1, 0


def _linkage(G: nx.Graph, A: frozenset, B: frozenset) -> int:
    """Max number of internally vertex-disjoint paths from cycle A to cycle B (Menger)."""
    H = G.copy()
    H.add_edges_from(("s", a) for a in A)
    H.add_edges_from(("t", b) for b in B)
    return nx.node_connectivity(H, "s", "t")


def chordless_odd_cycles(G: nx.Graph) -> list[frozenset]:
    return sorted({frozenset(c) for c in nx.chordless_cycles(G) if len(c) % 2 == 1}, key=sorted)


def separated_pairs(G: nx.Graph, adj: list[int]) -> list[tuple[frozenset, frozenset]]:
    """Pairs of vertex-disjoint chordless odd cycles with no edge between them (OCC violations)."""
    odd = chordless_odd_cycles(G)
    masks = [_mask(c) for c in odd]
    return [(odd[i], odd[j]) for i, j in combinations(range(len(odd)), 2)
            if not (_closed_nbhd(adj, masks[i]) & masks[j])]


def separated_pair_features(G: nx.Graph, n: int, adj: list[int]) -> dict:
    """Group A (how OCC fails) and B (normalization gap), from chordless odd cycles."""
    pairs = separated_pairs(G, adj)
    blocks = [set(b) for b in nx.biconnected_components(G)]
    f = {
        "n_chordless_odd_cycles": len(chordless_odd_cycles(G)),
        "sep_pairs": len(pairs),
        "sep_pairs_3_3": 0, "sep_pairs_3_5": 0, "sep_pairs_other": 0,
        "sep_same_block_pairs": 0,
        "normalization_gap": len({_mask(A) | _mask(B) for A, B in pairs}),
    }
    dists, geos, links, walks, lens = [], [], [], [], []
    for A, B in pairs:
        a, b = sorted((len(A), len(B)))
        key = "sep_pairs_3_3" if (a, b) == (3, 3) else "sep_pairs_3_5" if (a, b) == (3, 5) else "sep_pairs_other"
        f[key] += 1
        f["sep_same_block_pairs"] += any(A <= blk and B <= blk for blk in blocks)
        d, g = _set_distance_and_geodesics(G, A, B)
        dists.append(d)
        geos.append((d, g))
        links.append(_linkage(G, A, B))
        walks.append((a + b) // 2 + d)
        lens.append(a + b)
    if pairs:
        dmin = min(dists)
        f.update({
            "sep_dist_min": dmin, "sep_dist_max": max(dists),
            "sep_closest_geodesics": max(g for d, g in geos if d == dmin),
            "sep_linkage_min": min(links), "sep_linkage_max": max(links),
            "sep_walk_degree_min": min(walks), "sep_walk_degree_max": max(walks),
            "sep_len_sum_min": min(lens), "sep_len_sum_max": max(lens),
        })
    else:
        f.update({k: None for k in ("sep_dist_min", "sep_dist_max", "sep_closest_geodesics",
                                    "sep_linkage_min", "sep_linkage_max", "sep_walk_degree_min",
                                    "sep_walk_degree_max", "sep_len_sum_min", "sep_len_sum_max")})
    return f


# ---------------------------------------------------------------- symmetry

def automorphism_group_size(G: nx.Graph) -> int:
    return sum(1 for _ in nx.algorithms.isomorphism.GraphMatcher(G, G).isomorphisms_iter())


# ---------------------------------------------------------------- all features

def compute_features(g6: str) -> dict:
    n, adj = parse_g6(g6)
    G = to_nx(n, adj)
    m = G.number_of_edges()
    deg = np.array([d for _, d in G.degree()])
    f: dict = {"graph6": g6, "n": n, "m": m, "m_minus_n": m - n, "density": 2 * m / (n * (n - 1))}

    # degree + threads (D)
    f.update({"deg_min": int(deg.min()), "deg_max": int(deg.max()), "deg_mean": float(deg.mean()),
              "deg_std": float(deg.std())})
    for k in (2, 3, 4):
        f[f"deg_count_{k}"] = int((deg == k).sum())
    f["deg_count_5plus"] = int((deg >= 5).sum())
    f["frac_deg_2"] = f["deg_count_2"] / n
    f["n_threads"], f["thread_max_len"] = threads(n, adj)

    # triangles and cycles
    tri = sum(nx.triangles(G).values()) // 3
    f.update({"n_triangles": tri, "avg_clustering": nx.average_clustering(G),
              "transitivity": nx.transitivity(G)})
    lens = [len(c) for c in nx.simple_cycles(G)]
    chordless = [len(c) for c in nx.chordless_cycles(G)]
    for L in range(3, MAX_CYCLE_LEN + 1):
        f[f"cyc_len_{L}"] = lens.count(L)
        f[f"chordless_len_{L}"] = chordless.count(L)
    f["n_odd_cycles"] = sum(1 for L in lens if L % 2)
    f["n_even_cycles"] = sum(1 for L in lens if L % 2 == 0)
    f["n_chordless_even_cycles"] = sum(1 for L in chordless if L % 2 == 0)
    f["girth"] = min(lens) if lens else None
    f["odd_girth"] = min((L for L in lens if L % 2), default=None)
    f["even_girth"] = min((L for L in lens if L % 2 == 0), default=None)

    # connectivity
    blocks = list(nx.biconnected_components(G))
    f.update({
        "node_connectivity": nx.node_connectivity(G), "edge_connectivity": nx.edge_connectivity(G),
        "n_cut_vertices": sum(1 for _ in nx.articulation_points(G)), "n_bridges": sum(1 for _ in nx.bridges(G)),
        "n_blocks": len(blocks),
        "n_nonbipartite_blocks": sum(1 for b in blocks if is_nonbipartite(adj, _mask(b))),
        "diameter": nx.diameter(G), "radius": nx.radius(G),
        "avg_shortest_path": nx.average_shortest_path_length(G),
    })

    # spectra
    A = nx.to_numpy_array(G, nodelist=range(n))
    D = np.diag(A.sum(axis=1))
    ev_a = np.linalg.eigvalsh(A)
    ev_l = np.linalg.eigvalsh(D - A)
    ev_q = np.linalg.eigvalsh(D + A)
    f.update({
        "adj_eig_max": float(ev_a[-1]), "adj_eig_min": float(ev_a[0]),
        "adj_eig_2nd": float(ev_a[-2]), "adj_energy": float(np.abs(ev_a).sum()),
        "lap_algebraic_connectivity": float(ev_l[1]), "lap_eig_max": float(ev_l[-1]),
        "signless_lap_min": float(ev_q[0]),
        "n_spanning_trees": round(float(np.prod(ev_l[1:])) / n),
        "adj_spectrum": [round(float(x), 6) for x in ev_a],
        "lap_spectrum": [round(float(x), 6) for x in ev_l],
    })

    # symmetry
    f["aut_group_size"] = automorphism_group_size(G)

    # parity (C)
    f["odd_cycle_transversal"] = odd_cycle_transversal(n, adj)
    f["edge_frustration"] = m - max_cut(n, adj)

    # separated odd-cycle pairs (A) and normalization gap (B)
    f.update(separated_pair_features(G, n, adj))

    # standard invariants (E)
    f.update({
        "independence_number": independence_number(n, adj),
        "matching_number": len(nx.max_weight_matching(G, maxcardinality=True)),
        "chromatic_number": chromatic_number(n, adj),
        "treewidth": treewidth(n, adj),
    })
    return f
