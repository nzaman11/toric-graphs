import sqlite3

import pytest

from toric_graphs import build


@pytest.mark.skipif(not build.GZ.exists(), reason="no prebuilt database committed")
def test_prebuilt_database_is_current_and_unpacks(tmp_path):
    # the committed .gz must match the committed data/code, otherwise deployments rebuild slowly
    assert build.FP_FILE.read_text().strip() == build.fingerprint(), \
        "prebuilt DB is stale: run scripts/build_db.py and commit data/toric_graphs.sqlite.gz + .fingerprint"
    target = tmp_path / "db.sqlite"
    path, fp = build.ensure_db(target)
    assert path == target and build.db_fingerprint(target) == fp
    with sqlite3.connect(target) as c:
        assert c.execute("SELECT COUNT(*) FROM graphs WHERE n = 9").fetchone()[0] == 7125


def test_fingerprint_ignores_line_endings(tmp_path, monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"x\r\ny\r\n")
    b.write_bytes(b"x\ny\n")
    monkeypatch.setattr(build, "input_files", lambda: [a])
    fa = build.fingerprint()
    b.rename(a)
    assert build.fingerprint() == fa
