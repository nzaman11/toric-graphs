"""Phase 4: compute the 7125 OCC-failing 9-vertex graphs, model-guided order.

Order: graphs conjecture C4 predicts to be CM first, then the rest; ties by graph number.
(The random-order baseline is computed afterwards by reshuffling the recorded per-graph times.)

Usage (from ~/toric-graphs):
    .venv/bin/python scripts/run_n9.py                      # full run, resumable
    .venv/bin/python scripts/run_n9.py --limit 50           # quick test
    .venv/bin/python scripts/run_n9.py --timeout 3600 --retry-timeouts   # second pass
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from toric_graphs.runner import Job, run  # noqa: E402

PRED = ROOT / "data" / "derived" / "fail9_c4_predictions.csv"
OUT = ROOT / "data" / "derived" / "fail9_runs.jsonl"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=300, help="seconds per Macaulay2 stage")
    ap.add_argument("--limit", type=int, default=None, help="only run this many new graphs")
    ap.add_argument("--retry-timeouts", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    rows = list(csv.DictReader(PRED.open()))
    rows.sort(key=lambda r: (-int(r["predicted_cm"]), int(r["graph_number"])))
    jobs = [Job(int(r["graph_number"]), r["graph6"], i) for i, r in enumerate(rows)]
    try:
        run(jobs, a.out, a.workers, a.timeout, a.retry_timeouts, a.limit)
    except KeyboardInterrupt:
        sys.exit(130)
    print(f"Results in {a.out}")


if __name__ == "__main__":
    main()
