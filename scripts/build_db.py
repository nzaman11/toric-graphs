"""Build data/toric_graphs.sqlite from the raw and derived Macaulay2 outputs.

Usage: .venv/bin/python scripts/build_db.py
"""
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from toric_graphs.build import build  # noqa: E402


def main() -> None:
    t0 = time.time()
    path = build()
    conn = sqlite3.connect(path)
    n_feat = len(conn.execute("SELECT * FROM features LIMIT 1").description) - 1
    print(f"built {path} in {time.time() - t0:.1f}s ({n_feat} feature columns)")
    print("fails_occ | is_cm | graphs | gorenstein | known CI")
    for row in conn.execute("""
            SELECT g.fails_occ, r.is_cm, COUNT(*), SUM(r.is_gorenstein), SUM(COALESCE(r.is_ci, 0))
            FROM graphs g JOIN m2_results r USING (graph6) GROUP BY 1, 2 ORDER BY 1, 2"""):
        print("   ", " | ".join(str(x) for x in row))


if __name__ == "__main__":
    main()
