from toric_graphs.draw import draw_graph, graph_png


def test_draw_failing_graph_reports_pairs():
    fig, n_pairs = draw_graph("GCOe`W")
    assert n_pairs == 1
    assert graph_png("GCOe`W").startswith(b"\x89PNG")


def test_draw_occ_graph_has_no_pairs():
    assert draw_graph("G??F~{")[1] == 0
