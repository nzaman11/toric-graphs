"""Pre-register conjecture C4's predictions for a list of failing graphs BEFORE running Macaulay2.

Usage: .venv/bin/python scripts/predict_c4.py data/derived/fail9_graphs.txt data/derived/fail9_c4_predictions.csv

Writes graph_number, graph6, m, even_cycle_meets_pair, predicted_cm (= 1 - even_cycle_meets_pair).
Commit the output before computing results so the test cannot be tuned after the fact.
"""
import csv
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from toric_graphs.features import separated_pair_features, to_nx  # noqa: E402
from toric_graphs.graph6 import num_edges, parse_g6  # noqa: E402


def predict(item: tuple[str, str]) -> tuple[int, str, int, int]:
    num, g6 = item
    n, adj = parse_g6(g6)
    meets = separated_pair_features(to_nx(n, adj), n, adj)["even_cycle_meets_pair"]
    return int(num), g6, num_edges(adj), meets


def main(src: str, dst: str) -> None:
    items = [tuple(line.split()) for line in Path(src).read_text().splitlines() if line.strip()]
    with Pool() as pool:
        rows = pool.map(predict, items, chunksize=50)
    with open(dst, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["graph_number", "graph6", "m", "even_cycle_meets_pair", "predicted_cm"])
        for num, g6, m, meets in rows:
            w.writerow([num, g6, m, meets, 1 - meets])
    pred = Counter(1 - r[3] for r in rows)
    print(f"{len(rows)} graphs: C4 predicts CM for {pred[1]}, not CM for {pred[0]}")
    by_m = Counter((r[2], 1 - r[3]) for r in rows)
    for m in sorted({r[2] for r in rows}):
        print(f"  m={m:2d}: total {by_m[(m, 0)] + by_m[(m, 1)]:5d}, predicted CM {by_m[(m, 1)]:4d}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
