import json
import shutil

import pytest

from toric_graphs import runner
from toric_graphs.runner import Job, run, run_one

needs_m2 = pytest.mark.skipif(shutil.which("M2") is None, reason="Macaulay2 not installed")


@needs_m2
def test_cm_graph_proved_by_zzp_depth():
    # depth over ZZ/32003 = n proves CM over QQ, so no QQ stage is run
    rec = run_one(Job(1979, "GCOe`W", 0), timeout=120)
    assert rec["status"] == "done" and rec["is_cm"] == 1 and rec["decided_by"] == "depth_ZZp_eq_n"
    assert rec["depth_zzp"] == 8 and "depth" not in rec and "wall_depth_qq" not in rec
    assert rec["h_vector"] == [1, 1, 1, 1, 1, 1] and rec["num_gens"] == 1
    assert rec["cpu_total"] > 0 and rec["seconds_depth_zzp"] >= 0


@needs_m2
def test_non_cm_graph_decided_by_negative_h():
    rec = run_one(Job(89, "G?`Drg", 0), timeout=120)
    assert rec["status"] == "done" and rec["is_cm"] == 0 and rec["decided_by"] == "negative_h"
    assert "depth_zzp" not in rec and rec["h_vector"][-1] == -1


@needs_m2
def test_timeout_is_recorded():
    rec = run_one(Job(1, "G??F~{", 0), timeout=0.01)
    assert rec["status"] == "timeout" and rec["stage"] == "ideal"


@needs_m2
def test_resume_skips_finished(tmp_path):
    out = tmp_path / "runs.jsonl"
    jobs = [Job(1979, "GCOe`W", 0), Job(89, "G?`Drg", 1)]
    run(jobs, out, workers=2, timeout=120)
    run(jobs, out, workers=2, timeout=120)  # second call must not recompute
    recs = [json.loads(line) for line in out.read_text().splitlines()]
    assert sorted(r["graph_number"] for r in recs) == [89, 1979]


def _fake_run_one(job, timeout):
    if job.graph_number == 0:
        raise RuntimeError("M2 failed (137): killed")
    return runner._finish({"graph_number": job.graph_number, "graph6": job.graph6, "n": 8,
                           "order": job.order, "started": 0.0, "status": "done", "is_cm": 1})


def test_worker_exception_is_recorded_and_run_continues(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "run_one", _fake_run_one)
    out = tmp_path / "runs.jsonl"
    run([Job(i, f"g{i}", i) for i in range(9)], out, workers=4, timeout=1)
    recs = {r["graph_number"]: r for r in map(json.loads, out.read_text().splitlines())}
    assert len(recs) == 9
    assert recs[0]["status"] == "error" and "killed" in recs[0]["error"]
    assert all(recs[i]["status"] == "done" for i in range(1, 9))


def test_error_graphs_are_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "run_one", _fake_run_one)
    out = tmp_path / "runs.jsonl"
    run([Job(0, "g0", 0)], out, workers=1, timeout=1)
    assert 0 not in runner.load_done(out, retry_timeouts=True)


def test_partial_last_line_does_not_block_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "run_one", _fake_run_one)
    out = tmp_path / "runs.jsonl"
    good = json.dumps({"graph_number": 1, "graph6": "g1", "status": "done", "is_cm": 1})
    out.write_text(good + "\n" + '{"graph_number": 2, "graph6": "g2", "sta')  # crash mid-write
    run([Job(i, f"g{i}", i) for i in (1, 2, 3)], out, workers=2, timeout=1)
    recs = runner.read_records(out)
    assert sorted(r["graph_number"] for r in recs) == [1, 2, 3]  # 1 kept, 2 and 3 (re)computed
    lines = out.read_text().splitlines()
    assert sum(1 for line in lines if line.startswith('{"graph_number": 2, "graph6": "g2", "sta')) == 1
