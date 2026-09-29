"""SQLite storage.

graphs      what the graph is (one row per graph, keyed by graph6)
m2_results  what Macaulay2 computed (expensive, permanent; appended by the job runner)
features    what Python computes from the graph (cheap, rebuilt from code)
"""

import json
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "toric_graphs.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS graphs (
    graph6        TEXT PRIMARY KEY,
    n             INTEGER NOT NULL,
    graph_number  INTEGER,            -- Navila's numbering (geng order after filters), per n
    m             INTEGER NOT NULL,
    edges         TEXT NOT NULL,      -- JSON [[i,j],...], 1-indexed, M2 edge order
    fails_occ     INTEGER NOT NULL,   -- 0/1
    occ_witness   TEXT,               -- JSON [[vertices of S],[vertices of T]] (1-indexed) if fails
    UNIQUE (n, graph_number)
);

CREATE TABLE IF NOT EXISTS m2_results (
    graph6          TEXT PRIMARY KEY REFERENCES graphs(graph6),
    source          TEXT NOT NULL,    -- 'ssri_2026', 'recomputed', or 'runner_n9'
    depth           INTEGER,          -- over QQ; NULL if CM was decided without it
    is_cm           INTEGER,          -- depth == n
    decided_by      TEXT,             -- 'depth_QQ', 'negative_h' (proof), or 'depth_ZZp' (screen)
    h_vector        TEXT,             -- JSON list; numerator of reduced Hilbert series
    h_symmetric     INTEGER,
    is_gorenstein   INTEGER,          -- CM and symmetric h (Stanley); 0 if not CM
    num_gens        INTEGER,
    gen_degrees     TEXT,             -- JSON sorted list
    gens_minimal    INTEGER,          -- 1 if generating set known minimal (trim), NULL if unknown
    is_ci           INTEGER,          -- num_gens == m - n (1 is certain; 0 certain only if gens_minimal)
    toric_ideal     TEXT,
    seconds_ker     REAL,
    seconds_depth   REAL,
    seconds_hilbert REAL
);
"""


def write_features(conn: sqlite3.Connection, rows: list[dict]) -> None:
    """Replace the features table. Columns come from the feature dicts; lists are stored as JSON."""
    cols = list(rows[0])
    conn.execute("DROP TABLE IF EXISTS features")
    decl = ", ".join(f'"{c}" {"TEXT PRIMARY KEY REFERENCES graphs(graph6)" if c == "graph6" else ""}' for c in cols)
    conn.execute(f"CREATE TABLE features ({decl})")
    conn.executemany(
        f"INSERT INTO features VALUES ({', '.join('?' * len(cols))})",
        [[json.dumps(r[c]) if isinstance(r[c], list) else r[c] for c in cols] for r in rows],
    )


def connect(path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
