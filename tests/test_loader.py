import json

import pytest

from toric_graphs import db, loader
from toric_graphs.m2parse import binomial_degree, h_vector, hilbert_dim, ideal_generators


def test_run_verdict_uses_only_proofs():
    v = loader.run_verdict
    assert v({"n": 9, "decided_by": "negative_h", "is_cm": 0}) == (0, "negative_h")
    assert v({"n": 9, "depth_zzp": 9}) == (1, "depth_ZZp_eq_n")
    # first-run format: QQ confirmation timed out after ZZ/p already proved CM
    assert v({"n": 9, "status": "timeout", "stage": "depth_QQ", "depth_zzp": 9}) == (1, "depth_ZZp_eq_n")
    # ZZ/p depth < n alone is only a screen, never "not CM"
    assert v({"n": 9, "decided_by": "depth_ZZp", "is_cm": 0, "depth_zzp": 8}) == (None, "screen_ZZp")
    assert v({"n": 9, "depth_zzp": 8, "depth": 9}) == (1, "depth_QQ")
    assert v({"n": 9, "status": "timeout", "stage": "ideal"}) == (None, None)


def test_latest_runs_prefers_final_records(tmp_path):
    p = tmp_path / "runs.jsonl"
    rows = [{"graph_number": 5, "status": "timeout", "stage": "ideal"},
            {"graph_number": 5, "status": "done", "is_cm": 1},
            {"graph_number": 5, "status": "error"},
            {"graph_number": 6, "status": "timeout"},
            {"graph_number": 6, "status": "timeout", "stage": "depth_ZZp"}]
    p.write_text("\n".join(json.dumps(r) for r in rows) + '\n{"graph_number": 7, "sta')
    recs = loader.latest_runs(p)
    assert recs[5]["status"] == "done" and recs[6]["stage"] == "depth_ZZp" and 7 not in recs


def test_h_vector_parsing():
    assert h_vector("(1+5*T)/((1-T)^8)") == [1, 5]
    assert h_vector("(1+2*T+2*T^2+2*T^3+2*T^4-T^5)/((1-T)^8)") == [1, 2, 2, 2, 2, -1]
    assert h_vector("(1+T+T^2)/((1-T)^8)") == [1, 1, 1]
    assert h_vector("(1+3*T+4*T^2+4*T^3+2*T^4-2*T^5)/((1-T)^8)") == [1, 3, 4, 4, 2, -2]
    assert hilbert_dim("(1+5*T)/((1-T)^8)") == 8


def test_ideal_and_binomial_parsing():
    gens = ideal_generators("ideal(e_4*e_8-e_3*e_10,e_1*e_5*e_7*e_9^2-e_2*e_6^2*e_8*e_10)")
    assert gens == ["e_4*e_8-e_3*e_10", "e_1*e_5*e_7*e_9^2-e_2*e_6^2*e_8*e_10"]
    assert [binomial_degree(g) for g in gens] == [2, 5]
    assert binomial_degree("e_1*e_3*e_5^2*e_8^2-e_2^2*e_4*e_6*e_7*e_9") == 6


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    c = db.connect(tmp_path_factory.mktemp("db") / "test.sqlite")
    with c:
        loader.load_ssri_n8(c)
        for results in sorted(loader.DERIVED.glob("*_results.txt")):
            loader.load_m2_results(c, results)
    return c


def test_n8_counts(conn):
    rows = dict(((f, cm), cnt) for f, cm, cnt in conn.execute(
        "SELECT fails_occ, is_cm, COUNT(*) FROM graphs JOIN m2_results USING (graph6) "
        "WHERE n = 8 GROUP BY 1, 2"))
    assert rows == {(0, 1): 6810, (1, 1): 51, (1, 0): 110}
    assert conn.execute("SELECT SUM(h_symmetric) FROM m2_results JOIN graphs USING (graph6) "
                        "WHERE is_cm = 1 AND n = 8").fetchone()[0] == 435


def test_numbering_is_complete(conn):
    nums = [r[0] for r in conn.execute("SELECT graph_number FROM graphs WHERE n = 8 ORDER BY 1")]
    assert nums == list(range(1, 6972))


def test_theorems_hold_in_data(conn):
    # OCC => normal => CM (Ohsugi-Hibi, Hochster)
    assert conn.execute("SELECT COUNT(*) FROM graphs JOIN m2_results USING (graph6) "
                        "WHERE fails_occ = 0 AND is_cm = 0").fetchone()[0] == 0
    # CM standard graded domain: h_1 = m - n and h >= 0
    for m, n, h, cm in conn.execute("SELECT m, n, h_vector, is_cm FROM graphs JOIN m2_results USING (graph6)"):
        h = json.loads(h)
        assert h[0] == 1 and h[1] == m - n
        if cm:
            assert min(h) >= 0


def test_conjecture_c4_holds_in_data(conn):
    """C4: for G failing OCC, k[G] is CM iff no even cycle meets both cycles of a separated pair."""
    from toric_graphs.features import compute_features

    rows = conn.execute("SELECT graph6, is_cm FROM graphs JOIN m2_results USING (graph6) "
                        "WHERE fails_occ = 1").fetchall()
    assert len(rows) == 167  # 6 at n=7, 161 at n=8
    for g6, cm in rows:
        assert compute_features(g6)["even_cycle_meets_pair"] == 1 - cm, g6


def test_gorenstein_failing_graphs_are_ci(conn):
    rows = conn.execute("SELECT graph_number, is_ci FROM graphs JOIN m2_results USING (graph6) "
                        "WHERE fails_occ = 1 AND is_gorenstein = 1 AND n = 8 ORDER BY 1").fetchall()
    assert rows == [(1979, 1), (2305, 1), (5222, 1)]
