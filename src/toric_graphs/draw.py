"""Draw graphs with their OCC violations highlighted (matplotlib)."""

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

from .features import chordless_odd_cycles, separated_pairs, to_nx  # noqa: E402
from .graph6 import parse_g6  # noqa: E402

# Okabe-Ito colors: distinguishable with color-vision deficiency, readable on light and dark.
CYCLE_A = "#0072B2"
CYCLE_B = "#E69F00"
ODD = "#CC79A7"
EDGE = "#8a8f98"
NODE_FACE = "#ffffff"
NODE_EDGE = "#3b3f45"


def _cycle_edges(G: nx.Graph, vs: frozenset) -> list[tuple[int, int]]:
    return [(u, v) for u, v in G.subgraph(vs).edges()]


def draw_graph(g6: str, pair_index: int = 0, show_odd_cycles: bool = False,
               size: float = 3.2, labels: bool = True) -> tuple[plt.Figure, int]:
    """Figure of the graph; separated pair #pair_index in blue/orange. Returns (figure, number of pairs).

    Vertex labels are 1-indexed to match Macaulay2's v_1..v_n.
    """
    n, adj = parse_g6(g6)
    G = to_nx(n, adj)
    pos = nx.kamada_kawai_layout(G)
    pairs = separated_pairs(G, adj)

    fig, ax = plt.subplots(figsize=(size, size))
    fig.patch.set_alpha(0)
    ax.set_axis_off()
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color=EDGE, width=1.4)

    node_colors = {v: NODE_FACE for v in G}
    if show_odd_cycles:
        for c in chordless_odd_cycles(G):
            nx.draw_networkx_edges(G, pos, edgelist=_cycle_edges(G, c), ax=ax, edge_color=ODD,
                                   width=3.5, alpha=0.35)
    if pairs:
        A, B = pairs[pair_index % len(pairs)]
        for vs, color in ((A, CYCLE_A), (B, CYCLE_B)):
            nx.draw_networkx_edges(G, pos, edgelist=_cycle_edges(G, vs), ax=ax, edge_color=color, width=3.2)
            node_colors.update({v: color for v in vs})

    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=260 if labels else 90,
                           node_color=[node_colors[v] for v in G], edgecolors=NODE_EDGE, linewidths=1.2)
    if labels:
        font = {v: ("white" if node_colors[v] == CYCLE_A else "black") for v in G}
        for v, (x, y) in pos.items():
            ax.text(x, y, str(v + 1), ha="center", va="center", fontsize=8, color=font[v])
    ax.margins(0.12)
    return fig, len(pairs)


def graph_png(g6: str, pair_index: int = 0, show_odd_cycles: bool = False,
              size: float = 3.2, labels: bool = True) -> bytes:
    fig, _ = draw_graph(g6, pair_index, show_odd_cycles, size, labels)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", transparent=True)
    plt.close(fig)
    return buf.getvalue()
