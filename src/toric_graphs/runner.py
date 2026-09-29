"""Parallel, resumable Macaulay2 job runner.

Per graph (cheapest test first):
  1. ideal stage (QQ): toric ideal + Hilbert series. A negative h-coefficient proves "not CM"
     (the Hilbert series does not depend on the field); stop.
  2. depth over ZZ/32003. For a toric ring, R_Z/I_Z is a free Z-module, so Betti numbers over
     ZZ/p are >= those over QQ, i.e. depth_ZZp <= depth_QQ <= n. Hence depth_ZZp = n PROVES CM
     over QQ; stop.
  3. only if depth_ZZp < n: depth over QQ decides (ZZ/p alone does not prove "not CM").
     If this stage times out the graph is recorded as "unconfirmed" (screened not CM, no proof).

Every finished graph is appended as one JSON line and flushed, so the run can be interrupted
(Ctrl+C, closing the laptop) and resumed; graphs already recorded with a final status are skipped.
A crash inside one graph is recorded as status "error" and the run continues. Time limits give
status "timeout"; rerun with a larger --timeout and --retry-timeouts for a second pass.

Timing: wall_* fields include Macaulay2 start-up (~2 s per call); cpu_* fields are Macaulay2's
own cpuTime for the algebra and are the right cost measure for comparing orderings.
"""

import json
import os
import signal
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .graph6 import edge_list, parse_g6
from .m2parse import h_vector

ROOT = Path(__file__).resolve().parents[2]
M2_SCRIPT = ROOT / "m2" / "compute_one.m2"
FINAL = {"done", "unconfirmed"}  # statuses that are not retried

_live: set[subprocess.Popen] = set()
_live_lock = threading.Lock()


@dataclass
class Job:
    graph_number: int
    graph6: str
    order: int  # position in the processing order


def _m2(args: list[str], timeout: float) -> tuple[dict[str, str] | None, float]:
    """Run compute_one.m2; returns (parsed output, or None on timeout; wall seconds)."""
    t0 = time.time()
    proc = subprocess.Popen(["M2", "--script", str(M2_SCRIPT), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=True)
    with _live_lock:
        _live.add(proc)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill(proc)
        proc.communicate()
        return None, time.time() - t0
    finally:
        with _live_lock:
            _live.discard(proc)
    if proc.returncode != 0:
        raise RuntimeError(f"M2 failed ({proc.returncode}): {err.strip()[-500:]}")
    parsed = dict(line.split(": ", 1) for line in out.splitlines() if ": " in line)
    return parsed, time.time() - t0


def _kill(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def kill_all() -> None:
    """Kill every Macaulay2 process started by this runner (used on Ctrl+C)."""
    with _live_lock:
        procs = list(_live)
    for p in procs:
        _kill(p)


def run_one(job: Job, timeout: float) -> dict:
    n, adj = parse_g6(job.graph6)
    edges = "{" + ",".join("{%d,%d}" % e for e in edge_list(n, adj)) + "}"
    rec: dict = {"graph_number": job.graph_number, "graph6": job.graph6, "n": n, "order": job.order,
                 "started": time.time(), "timeout_s": timeout}

    ideal, wall = _m2([edges, str(n), "ideal"], timeout)
    rec["wall_ideal"] = wall
    if ideal is None:
        rec.update(status="timeout", stage="ideal")
        return _finish(rec)
    h = h_vector(ideal["ReducedHilbertSeries"])
    rec.update(toric_ideal=ideal["ToricIdeal"], num_gens=int(ideal["NumGens"]),
               gen_degrees=ideal["GenDegrees"], hilbert_series=ideal["ReducedHilbertSeries"], h_vector=h,
               seconds_ker=float(ideal["SecondsKer"]), seconds_hilbert=float(ideal["SecondsHilbert"]))
    if min(h) < 0:
        rec.update(status="done", is_cm=0, decided_by="negative_h")
        return _finish(rec)

    screen, wall = _m2([edges, str(n), "depth", "ZZp"], timeout)
    rec["wall_depth_zzp"] = wall
    if screen is None:
        rec.update(status="timeout", stage="depth_ZZp")
        return _finish(rec)
    rec["depth_zzp"] = int(screen["Depth"])
    rec["seconds_depth_zzp"] = float(screen["SecondsDepth"])
    if rec["depth_zzp"] == n:
        rec.update(status="done", is_cm=1, decided_by="depth_ZZp_eq_n")
        return _finish(rec)

    exact, wall = _m2([edges, str(n), "depth", "QQ"], timeout)
    rec["wall_depth_qq"] = wall
    if exact is None:
        rec.update(status="unconfirmed", stage="depth_QQ", decided_by="screen_ZZp")
        return _finish(rec)
    rec["depth"] = int(exact["Depth"])
    rec["seconds_depth_qq"] = float(exact["SecondsDepth"])
    rec.update(status="done", is_cm=int(rec["depth"] == n), decided_by="depth_QQ")
    return _finish(rec)


def _finish(rec: dict) -> dict:
    rec["finished"] = time.time()
    rec["wall_total"] = rec["finished"] - rec["started"]
    rec["cpu_total"] = sum(rec.get(k) or 0.0 for k in
                           ("seconds_ker", "seconds_hilbert", "seconds_depth_zzp", "seconds_depth_qq"))
    return rec


def _error(job: Job, exc: BaseException) -> dict:
    return _finish({"graph_number": job.graph_number, "graph6": job.graph6, "order": job.order,
                    "started": time.time(), "status": "error", "error": f"{type(exc).__name__}: {exc}"[:800]})


def read_records(out: Path) -> list[dict]:
    """All decodable records; a partially written last line (crash mid-write) is skipped."""
    recs = []
    if out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return recs


def load_done(out: Path, retry_timeouts: bool) -> dict[int, dict]:
    done: dict[int, dict] = {}
    for r in read_records(out):
        if r["status"] in FINAL or not retry_timeouts:
            done[r["graph_number"]] = r
        else:
            done.pop(r["graph_number"], None)
    return done


def _ensure_newline(out: Path) -> None:
    """If the file ends mid-line (crash during a write), end that line so appends stay separate."""
    if out.exists() and out.stat().st_size:
        with open(out, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                with open(out, "ab") as fa:
                    fa.write(b"\n")


def run(jobs: list[Job], out: Path, workers: int, timeout: float, retry_timeouts: bool = False,
        limit: int | None = None) -> None:
    done = load_done(out, retry_timeouts)
    todo = [j for j in jobs if j.graph_number not in done][:limit]
    total = len(jobs)
    print(f"{len(done)} of {total} already recorded; {len(todo)} to run on {workers} workers, "
          f"time limit {timeout:.0f}s per stage. Ctrl+C to stop (progress is saved).", flush=True)
    _ensure_newline(out)
    stop = threading.Event()
    t_start = time.time()
    counts = {"done": 0, "cm": sum(r.get("is_cm") == 1 for r in done.values()), "timeout": 0, "error": 0}

    def work(job: Job) -> dict | None:
        if stop.is_set():
            return None
        try:
            return run_one(job, timeout)
        except Exception as exc:  # one bad graph must not sink the run
            return None if stop.is_set() else _error(job, exc)

    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        with open(out, "a") as fh:
            futures = [pool.submit(work, j) for j in todo]
            for fut in as_completed(futures):
                rec = fut.result()
                if rec is None:
                    continue
                fh.write(json.dumps(rec) + "\n")  # only this (main) thread writes
                fh.flush()
                os.fsync(fh.fileno())
                counts["done"] += 1
                counts["cm"] += rec.get("is_cm") == 1
                counts["timeout"] += rec["status"] == "timeout"
                counts["error"] += rec["status"] == "error"
                k = counts["done"]
                if k % 10 == 0 or k == len(todo):
                    el = time.time() - t_start
                    eta = el / k * (len(todo) - k)
                    print(f"[{time.strftime('%H:%M:%S')}] {len(done) + k}/{total} graphs · "
                          f"CM found {counts['cm']} · timeouts {counts['timeout']} · "
                          f"errors {counts['error']} · elapsed {el / 60:.1f} min · ETA {eta / 60:.0f} min",
                          flush=True)
    except KeyboardInterrupt:
        stop.set()
        print("\nStopping: killing running Macaulay2 jobs (their graphs will be redone on resume). "
              "Rerun the same command to continue.", flush=True)
        pool.shutdown(wait=False, cancel_futures=True)
        kill_all()
        raise
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
