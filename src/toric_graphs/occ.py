"""Pure-Python odd cycle condition (OCC) check.

G fails OCC  <=>  there are two vertex-disjoint odd cycles C, C' with no edge
between V(C) and V(C').

Equivalent set formulation used here: G fails OCC iff there are disjoint vertex
sets S, T with no edges between them such that G[S] and G[T] are both
non-bipartite. (Each non-bipartite induced subgraph contains an odd cycle, and
"no edges between S and T" is inherited by subsets.) So for every S with G[S]
non-bipartite we test T = V minus the closed neighbourhood of S.

Cost is O(2^n * n^2), which is fine for n <= ~12.
"""

from functools import lru_cache

from .graph6 import parse_g6


@lru_cache(maxsize=None)
def _subsets_by_size(n: int) -> tuple[int, ...]:
    """All vertex bitmasks with >= 3 vertices, smallest first."""
    return tuple(sorted((x for x in range(1 << n) if bin(x).count("1") >= 3),
                        key=lambda x: bin(x).count("1")))


def is_nonbipartite(adj: list[int], mask: int) -> bool:
    """True if the subgraph induced on the vertex bitmask `mask` has an odd cycle."""
    color: dict[int, int] = {}
    for s in range(len(adj)):
        if not (mask >> s) & 1 or s in color:
            continue
        color[s] = 0
        stack = [s]
        while stack:
            u = stack.pop()
            nb = adj[u] & mask
            while nb:
                low = nb & -nb
                v = low.bit_length() - 1
                nb ^= low
                if v not in color:
                    color[v] = 1 - color[u]
                    stack.append(v)
                elif color[v] == color[u]:
                    return True
    return False


def occ_witness(n: int, adj: list[int]) -> tuple[int, int] | None:
    """Return vertex bitmasks (S, T) witnessing failure of OCC, or None if G satisfies OCC.

    S and T are disjoint, non-adjacent, and each induces a non-bipartite subgraph.
    S is chosen with the fewest vertices first, so small odd cycles are reported.
    """
    full = (1 << n) - 1
    for S in _subsets_by_size(n):
        if not is_nonbipartite(adj, S):
            continue
        closed = S
        rest = S
        while rest:
            low = rest & -rest
            closed |= adj[low.bit_length() - 1]
            rest ^= low
        T = full & ~closed
        if bin(T).count("1") >= 3 and is_nonbipartite(adj, T):
            return S, T
    return None


def fails_occ(n: int, adj: list[int]) -> bool:
    return occ_witness(n, adj) is not None


def fails_occ_g6(g6: str) -> bool:
    return fails_occ(*parse_g6(g6))
