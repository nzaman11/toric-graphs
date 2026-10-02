"""Resumable batch runner: many graphs per Macaulay2 session, several sessions in parallel.

For large runs (n = 10) the per-launch start-up of Macaulay2 (~2 s) would dominate, so graphs are
processed in batches by one M2 script that writes one output line per graph, flushed as it goes.

Output is an append-only text file whose lines start with the graph number. A batch writes to its
own part file first; completed lines are appended to the main output when the batch ends (or is
killed), so an interrupted run loses at most the graph that was being computed. On restart,
graphs already in the output are skipped and leftover part files are merged first.

If a batch hits its time limit, the graph it was stuck on is recorded as `<num>\tTIMEOUT\t<secs>`
(so it is not retried forever) and the rest of the batch is re-queued.
"""

import os
import signal
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .graph6 import edge_list, parse_g6


def _prefer_oom_kill() -> None:
    """Runs in each Macaulay2 child: if memory runs out, the kernel kills this process first
    (not the runner or tmux), so the batch is recorded as ERROR and the run continues."""
    try:
        with open("/proc/self/oom_score_adj", "w") as fh:
            fh.write("1000")
    except OSError:
        pass
    cap = os.environ.get("TORIC_M2_MEM_GB")  # optional hard cap: a heavy graph fails fast (ERROR)
    if cap:
        import resource
        limit = int(float(cap) * 1024 ** 3)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def _m2_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_m2_input(items: list[tuple[int, str]], dst: Path) -> None:
    rows = []
    for num, g6 in items:
        edges = ",".join("{%d,%d}" % e for e in edge_list(*parse_g6(g6)))
        rows.append("{%d,%s,{%s}}" % (num, _m2_string(g6), edges))
    dst.write_text("graphList = {\n" + ",\n".join(rows) + "\n};\n")


def _complete_lines(path: Path, min_fields: int) -> list[str]:
    """Lines that were fully written (newline-terminated, enough whitespace-separated fields)."""
    if not path.exists():
        return []
    text = path.read_text()
    lines = text.split("\n")[:-1]  # last element is "" or a partial line
    return [ln for ln in lines if len(ln.split()) >= min_fields]


def done_numbers(out: Path) -> set[int]:
    done = set()
    if out.exists():
        for ln in out.read_text().split("\n"):
            tok = ln.split(maxsplit=1)
            if tok and tok[0].isdigit():
                done.add(int(tok[0]))
    return done


def run_batches(items: list[tuple[int, str]], script: Path, out: Path, n: int, *, workers: int = 8,
                batch_size: int = 500, timeout: float = 3600, min_fields: int = 3,
                log=lambda s: print(s, flush=True)) -> None:
    out = Path(out)
    parts = out.with_name(out.name + ".parts")
    parts.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    def merge(part: Path) -> list[str]:
        lines = _complete_lines(part, min_fields)
        if lines:
            with lock, open(out, "a") as fh:
                fh.write("\n".join(lines) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        part.unlink(missing_ok=True)
        return lines

    for leftover in sorted(parts.glob("*.out")):  # from an interrupted previous run
        merge(leftover)
    for stale in parts.glob("*.m2"):
        stale.unlink()

    total = len(items)
    t0 = time.time()
    start_done = len(done_numbers(out) & {num for num, _ in items})
    round_no = 0
    while True:
        done = done_numbers(out)
        todo = [it for it in items if it[0] not in done]
        if not todo:
            break
        round_no += 1
        batches = [todo[i:i + batch_size] for i in range(0, len(todo), batch_size)]
        log(f"round {round_no}: {len(todo)} graphs to do in {len(batches)} batches on {workers} workers")
        progress = {"n": total - len(todo)}

        def work(k: int, batch: list[tuple[int, str]]) -> int:
            tag = f"r{round_no}_b{k}_{os.getpid()}"
            inp, part = parts / f"{tag}.m2", parts / f"{tag}.out"
            write_m2_input(batch, inp)
            proc = subprocess.Popen(["M2", "--script", str(script), str(inp), str(part), str(n)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                    start_new_session=True, preexec_fn=_prefer_oom_kill)
            try:
                _, err = proc.communicate(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                timed_out, err = True, ""
            got = merge(part)
            inp.unlink(missing_ok=True)
            if timed_out or proc.returncode not in (0, None):
                finished = {int(ln.split(maxsplit=1)[0]) for ln in got}
                stuck = next((num for num, _ in batch if num not in finished), None)
                if stuck is not None:
                    with lock, open(out, "a") as fh:
                        why = "TIMEOUT" if timed_out else "ERROR"
                        fh.write(f"{stuck}\t{why}\t{timeout if timed_out else proc.returncode}\n")
                if not timed_out:
                    log(f"  batch {tag}: M2 exited {proc.returncode}: {err.strip()[-300:]}")
            return len(got)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(work, k, b) for k, b in enumerate(batches)]
            for fut in as_completed(futs):
                progress["n"] += fut.result()
                el = time.time() - t0
                rate = (progress["n"] - start_done) / el if el > 0 else 0
                eta = (total - progress["n"]) / rate / 3600 if rate > 0 else float("nan")
                log(f"[{time.strftime('%H:%M:%S')}] {progress['n']}/{total} graphs · "
                    f"{rate:.1f}/s · elapsed {el / 3600:.2f} h · ETA {eta:.1f} h")
