import json
import shutil

import pytest

from toric_graphs.runner import Job, run, run_one

pytestmark = pytest.mark.skipif(shutil.which("M2") is None, reason="Macaulay2 not installed")


def test_cm_graph_confirmed_over_qq():
    rec = run_one(Job(1979, "GCOe`W", 0), timeout=120)
    assert rec["status"] == "done" and rec["is_cm"] == 1 and rec["decided_by"] == "depth_QQ"
    assert rec["depth"] == 8 and rec["h_vector"] == [1, 1, 1, 1, 1, 1] and rec["num_gens"] == 1


def test_non_cm_graph_decided_by_negative_h():
    rec = run_one(Job(89, "G?`Drg", 0), timeout=120)
    assert rec["status"] == "done" and rec["is_cm"] == 0 and rec["decided_by"] == "negative_h"
    assert "depth" not in rec and rec["h_vector"][-1] == -1


def test_timeout_is_recorded():
    rec = run_one(Job(1, "G??F~{", 0), timeout=0.01)
    assert rec["status"] == "timeout" and rec["stage"] == "ideal"


def test_resume_skips_finished(tmp_path):
    out = tmp_path / "runs.jsonl"
    jobs = [Job(1979, "GCOe`W", 0), Job(89, "G?`Drg", 1)]
    run(jobs, out, workers=2, timeout=120)
    run(jobs, out, workers=2, timeout=120)  # second call must not recompute
    recs = [json.loads(line) for line in out.read_text().splitlines()]
    assert sorted(r["graph_number"] for r in recs) == [89, 1979]
