"""Minimal graph6 decoding (nauty's format), dependency-free.

Graphs are represented as (n, adj) where adj[v] is a bitmask of v's neighbours
(bit u set <=> {u, v} is an edge). Vertices are 0-indexed.
"""


def parse_g6(s: str) -> tuple[int, list[int]]:
    """Decode a graph6 string with n <= 62 vertices."""
    data = [ord(c) - 63 for c in s.strip()]
    n = data[0]
    if n > 62:
        raise ValueError("graph6 strings with n > 62 are not supported")
    bits = []
    for d in data[1:]:
        bits.extend((d >> k) & 1 for k in range(5, -1, -1))
    adj = [0] * n
    idx = 0
    # graph6 lists the upper triangle column by column: (0,1),(0,2),(1,2),(0,3),...
    for j in range(1, n):
        for i in range(j):
            if bits[idx]:
                adj[i] |= 1 << j
                adj[j] |= 1 << i
            idx += 1
    return n, adj


def num_edges(adj: list[int]) -> int:
    return sum(bin(a).count("1") for a in adj) // 2


def edge_list(n: int, adj: list[int]) -> list[tuple[int, int]]:
    """Edges as 1-indexed (i, j), i < j, ordered by j then i (Macaulay2/NautyGraphs order)."""
    return [(i + 1, j + 1) for j in range(n) for i in range(j) if (adj[i] >> j) & 1]


def triangle_count(n: int, adj: list[int]) -> int:
    return sum(
        bin(adj[i] & adj[j] & ~((1 << (j + 1)) - 1)).count("1")
        for i in range(n)
        for j in range(i + 1, n)
        if (adj[i] >> j) & 1
    )
