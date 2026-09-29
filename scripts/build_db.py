"""Build data/toric_graphs.sqlite from the raw and derived Macaulay2 outputs.

Usage: .venv/bin/python scripts/build_db.py [--fresh]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from toric_graphs import db, loader  # noqa: E402


def main() -> None:
    if "--fresh" in sys.argv and db.DEFAULT_DB.exists():
        db.DEFAULT_DB.unlink()
    conn = db.connect()
    with conn:
        print("SSRI n=8 CM graphs:", loader.load_ssri_n8(conn))
        print("recomputed n=8 non-CM graphs:", loader.load_m2_results(conn, loader.DERIVED / "noncm8_results.txt"))
    q = conn.execute("""
        SELECT g.fails_occ, r.is_cm, COUNT(*), SUM(r.is_gorenstein), SUM(COALESCE(r.is_ci, 0))
        FROM graphs g JOIN m2_results r USING (graph6)
        WHERE g.n = 8 GROUP BY 1, 2 ORDER BY 1, 2""").fetchall()
    print("fails_occ | is_cm | graphs | gorenstein | known CI")
    for row in q:
        print("   ", " | ".join(str(x) for x in row))
    print("wrote", db.DEFAULT_DB)


if __name__ == "__main__":
    main()
