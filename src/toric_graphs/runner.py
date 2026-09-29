"""Parallel, resumable Macaulay2 job runner.

Per graph (cheapest test first):
  1. ideal stage (QQ): toric ideal + Hilbert series. A negative h-coefficient proves "not CM"; stop.
  2. depth over ZZ/32003 (fast screen), with a time limit.
  3. if the screen says CM: depth over QQ to confirm, with a time limit.

Every finished graph is appended as one JSON line to the output file and flushed, so the run can
be interrupted at any time (Ctrl+C, closing the laptop) and resumed: graphs already in the file
with a final status are skipped. Graphs that hit a time limit are recorded with status
"timeout"; rerun with a larger --timeout and --retry-timeouts to give them a second pass.
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


@dataclass
class Job:
    graph_number: int
    graph6: str
    order: int  # position in the processing order


def _m2(args: list[str], timeout: float) -> tuple[dict[str, str] | None, float]:
    """Run compute_one.m2; returns (parsed output or None on timeout/error, wall seconds)."""
    t0 = time.time()
    proc = subprocess.Popen(["M2", "--script", str(M2_SCRIPT), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None, time.time() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"M2 failed ({proc.returncode}): {err.strip()[-500:]}")
    parsed = dict(line.split(": ", 1) for line in out.splitlines() if ": " in line)
    return parsed, time.time() - t0


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
    if rec["depth_zzp"] < n:
        # Screen says not CM. Over QQ depth can only be >= the ZZ/p value in principle, so this is
        # recorded as a screening result; confirm over QQ later if it matters.
        rec.update(status="done", is_cm=0, decided_by="depth_ZZp")
        return _finish(rec)

    exact, wall = _m2([edges, str(n), "depth", "QQ"], timeout)
    rec["wall_depth_qq"] = wall
    if exact is None:
        rec.update(status="timeout", stage="depth_QQ")
        return _finish(rec)
    rec["depth"] = int(exact["Depth"])
    rec.update(status="done", is_cm=int(rec["depth"] == n), decided_by="depth_QQ")
    return _finish(rec)


def _finish(rec: dict) -> dict:
    rec["finished"] = time.time()
    rec["wall_total"] = rec["finished"] - rec["started"]
    return rec


def load_done(out: Path, retry_timeouts: bool) -> dict[int, dict]:
    done = {}
    if out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r["status"] == "done" or not retry_timeouts:
                    done[r["graph_number"]] = r
                else:
                    done.pop(r["graph_number"], None)
    return done


def run(jobs: list[Job], out: Path, workers: int, timeout: float, retry_timeouts: bool = False,
        limit: int | None = None) -> None:
    done = load_done(out, retry_timeouts)
    todo = [j for j in jobs if j.graph_number not in done][:limit]
    total = len(jobs)
    print(f"{len(done)} of {total} already recorded; {len(todo)} to run on {workers} workers, "
          f"time limit {timeout:.0f}s per stage. Ctrl+C to stop (progress is saved).", flush=True)
    lock = threading.Lock()
    stop = threading.Event()
    t_start = time.time()
    counts = {"done": 0, "cm": sum(r.get("is_cm", 0) == 1 for r in done.values()), "timeout": 0}

    def work(job: Job) -> dict | None:
        return None if stop.is_set() else run_one(job, timeout)

    with open(out, "a") as fh, ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, j) for j in todo]
        try:
            for fut in as_completed(futures):
                rec = fut.result()
                if rec is None:
                    continue
                with lock:
                    fh.write(json.dumps(rec) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
                    counts["done"] += 1
                    counts["cm"] += rec.get("is_cm") == 1
                    counts["timeout"] += rec["status"] == "timeout"
                    k = counts["done"]
                    if k % 10 == 0 or k == len(todo):
                        el = time.time() - t_start
                        eta = el / k * (len(todo) - k)
                        print(f"[{time.strftime('%H:%M:%S')}] {len(done) + k}/{total} graphs · "
                              f"CM found {counts['cm']} · timeouts {counts['timeout']} · "
                              f"elapsed {el / 60:.1f} min · ETA {eta / 60:.0f} min", flush=True)
        except KeyboardInterrupt:
            stop.set()
            print("\nStopping: finishing graphs already running, then exiting. Rerun the same "
                  "command to resume.", flush=True)
            for f in futures:
                f.cancel()
            raise
