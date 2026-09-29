"""Build the SQLite database from the committed text files (raw + derived Macaulay2 output).

The build is stamped with a fingerprint of its inputs (data files + the code that turns them into
tables). `scripts/build_db.py` also writes a gzipped copy plus the fingerprint, which are committed,
so a fresh deployment (Streamlit Cloud) unpacks the database in seconds instead of recomputing all
features, and any change to the inputs is detected and triggers a rebuild.
"""

import gzip
import hashlib
import os
import shutil
import sqlite3
from multiprocessing import Pool
from pathlib import Path

from . import db, loader
from .features import compute_features

PKG = Path(__file__).resolve().parent
GZ = db.DEFAULT_DB.with_suffix(".sqlite.gz")
FP_FILE = db.DEFAULT_DB.with_name("toric_graphs.fingerprint")
CODE = ["build.py", "db.py", "features.py", "graph6.py", "loader.py", "m2parse.py", "occ.py"]


def input_files() -> list[Path]:
    d = loader.RAW.parent
    files = sorted(loader.RAW.glob("*.txt")) + sorted(loader.DERIVED.glob("*_results.txt")) \
        + sorted(loader.DERIVED.glob("*_runs.jsonl"))
    return files + [PKG / c for c in CODE] if d.exists() else [PKG / c for c in CODE]


def fingerprint() -> str:
    h = hashlib.sha256()
    for f in input_files():
        h.update(f.name.encode())
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def db_fingerprint(path: Path) -> str | None:
    try:
        with sqlite3.connect(path) as c:
            row = c.execute("SELECT value FROM meta WHERE key = 'fingerprint'").fetchone()
            return row[0] if row else None
    except sqlite3.Error:
        return None


def build(path: str | Path = db.DEFAULT_DB, fresh: bool = True, processes: int | None = None) -> Path:
    """(Re)build the database at `path`. Written to a temp file first so a crash never leaves half a DB."""
    path = Path(path)
    if not fresh and path.exists():
        return path
    tmp = path.with_suffix(f".building.{os.getpid()}")
    for leftover in (tmp, tmp.with_name(tmp.name + "-journal")):
        leftover.unlink(missing_ok=True)
    conn = db.connect(tmp)
    with conn:
        loader.load_ssri_n8(conn)
        for results in sorted(loader.DERIVED.glob("*_results.txt")):  # recomputed / new Macaulay2 runs
            loader.load_m2_results(conn, results)
        for runs in sorted(loader.DERIVED.glob("*_runs.jsonl")):  # parallel runner output (n = 9)
            loader.load_runs_jsonl(conn, runs)
    g6s = [r[0] for r in conn.execute("SELECT graph6 FROM graphs ORDER BY n, graph_number")]
    processes = processes or os.cpu_count() or 1
    if processes > 1:
        with Pool(processes) as pool:
            rows = pool.map(compute_features, g6s, chunksize=50)
    else:
        rows = [compute_features(g) for g in g6s]
    with conn:
        db.write_features(conn, rows)
        conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('fingerprint', ?)", (fingerprint(),))
    conn.close()
    os.replace(tmp, path)
    return path


def write_prebuilt(path: Path = db.DEFAULT_DB) -> None:
    """Gzip the database and record its fingerprint (both committed, for fast deployment)."""
    with open(path, "rb") as src, gzip.open(GZ, "wb", compresslevel=9) as dst:
        shutil.copyfileobj(src, dst)
    FP_FILE.write_text(db_fingerprint(path) + "\n")


def ensure_db(path: Path = db.DEFAULT_DB, processes: int = 1) -> tuple[Path, str]:
    """Return an up-to-date database and its fingerprint: reuse it if current, else unpack the
    committed prebuilt copy if current, else rebuild from the text files (slow)."""
    want = fingerprint()
    if path.exists() and db_fingerprint(path) == want:
        return path, want
    if GZ.exists() and FP_FILE.exists() and FP_FILE.read_text().strip() == want:
        tmp = path.with_suffix(f".unpacking.{os.getpid()}")
        with gzip.open(GZ, "rb") as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.replace(tmp, path)
        return path, want
    build(path, processes=processes)
    return path, want
