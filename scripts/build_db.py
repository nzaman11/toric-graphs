"""Build data/toric_graphs.sqlite from the raw and derived Macaulay2 outputs, plus the committed
prebuilt copy (data/toric_graphs.sqlite.gz + data/toric_graphs.fingerprint) used by deployments.

Usage: .venv/bin/python scripts/build_db.py
Rerun (and commit the .gz and .fingerprint) whenever data files or the loader/feature code change.
"""
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from toric_graphs.build import GZ, build, write_prebuilt  # noqa: E402


def main() -> None:
    t0 = time.time()
    path = build()
    write_prebuilt(path)
    conn = sqlite3.connect(path)
    n_feat = len(conn.execute("SELECT * FROM features LIMIT 1").description) - 1
    print(f"built {path} in {time.time() - t0:.1f}s ({n_feat} feature columns); "
          f"prebuilt copy {GZ.stat().st_size / 1e6:.1f} MB")
    print("n | fails_occ | is_cm | graphs | gorenstein | known CI")
    for row in conn.execute("""
            SELECT g.n, g.fails_occ, r.is_cm, COUNT(*), SUM(r.is_gorenstein), SUM(COALESCE(r.is_ci, 0))
            FROM graphs g LEFT JOIN m2_results r USING (graph6) GROUP BY 1, 2, 3 ORDER BY 1, 2, 3"""):
        print("   ", " | ".join(str(x) for x in row))


if __name__ == "__main__":
    main()
