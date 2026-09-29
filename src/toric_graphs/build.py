"""Build the SQLite database from the committed text files (raw + derived Macaulay2 output)."""

import os
from multiprocessing import Pool
from pathlib import Path

from . import db, loader
from .features import compute_features


def build(path: str | Path = db.DEFAULT_DB, fresh: bool = True, processes: int | None = None) -> Path:
    """(Re)build the database at `path`. Written to a temp file first so a crash never leaves half a DB."""
    path = Path(path)
    tmp = path.with_suffix(".building")
    tmp.unlink(missing_ok=True)
    if not fresh and path.exists():
        return path
    conn = db.connect(tmp)
    with conn:
        loader.load_ssri_n8(conn)
        loader.load_m2_results(conn, loader.DERIVED / "noncm8_results.txt")
    g6s = [r[0] for r in conn.execute("SELECT graph6 FROM graphs ORDER BY n, graph_number")]
    processes = processes or os.cpu_count() or 1
    if processes > 1:
        with Pool(processes) as pool:
            rows = pool.map(compute_features, g6s, chunksize=50)
    else:
        rows = [compute_features(g) for g in g6s]
    with conn:
        db.write_features(conn, rows)
    conn.close()
    os.replace(tmp, path)
    return path
