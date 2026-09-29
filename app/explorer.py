"""Interactive explorer for graph toric ideals.

Run from the repo root:  .venv/bin/streamlit run app/explorer.py
Needs data/toric_graphs.sqlite (scripts/build_db.py).
"""

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from toric_graphs.db import DEFAULT_DB  # noqa: E402
from toric_graphs.draw import CYCLE_A, CYCLE_B, graph_png  # noqa: E402
from toric_graphs.m2parse import ideal_generators  # noqa: E402

st.set_page_config(page_title="Toric graph explorer", layout="wide")


# ------------------------------------------------------------------ data

@st.cache_data
def load() -> tuple[pd.DataFrame, list[str]]:
    with sqlite3.connect(DEFAULT_DB) as c:
        g = pd.read_sql("SELECT * FROM graphs", c)
        r = pd.read_sql("SELECT * FROM m2_results", c)
        f = pd.read_sql("SELECT * FROM features", c)
    feature_cols = [c for c in f.columns if c != "graph6" and pd.api.types.is_numeric_dtype(f[c])]
    df = g.merge(r, on="graph6", how="left").merge(f.drop(columns=["n", "m"]), on="graph6", how="left")
    df["status"] = df.apply(lambda x: "satisfies OCC" if not x.fails_occ
                            else ("fails OCC, CM" if x.is_cm == 1 else "fails OCC, non-CM"), axis=1)
    df["h"] = df.h_vector.map(lambda s: tuple(json.loads(s)) if isinstance(s, str) else None)
    return df.sort_values(["n", "graph_number"]).reset_index(drop=True), feature_cols


@st.cache_data(max_entries=2000)
def png(g6: str, pair: int = 0, odd: bool = False, size: float = 3.2, labels: bool = True) -> bytes:
    return graph_png(g6, pair, odd, size, labels)


def h_str(h) -> str:
    if not h:
        return "–"
    terms = []
    for d, c in enumerate(h):
        if c == 0:
            continue
        mono = "" if d == 0 else ("T" if d == 1 else f"T^{d}")
        coef = str(abs(c)) if (abs(c) != 1 or d == 0) else ""
        terms.append(("- " if c < 0 else "+ ") + coef + mono)
    return " ".join(terms).lstrip("+ ")


def fmt(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


df, FEATURE_COLS = load()

PRESETS = {
    "All graphs": lambda d: d,
    "Fails OCC": lambda d: d[d.fails_occ == 1],
    "Gorenstein (CM + symmetric h)": lambda d: d[d.is_gorenstein == 1],
    "Gorenstein and fails OCC": lambda d: d[(d.is_gorenstein == 1) & (d.fails_occ == 1)],
    "C3: separated pair inside one block": lambda d: d[d.sep_same_block_pairs > 0],
    "C3 exceptions: cut-vertex-linked, non-CM": lambda d: d[(d.fails_occ == 1) & (d.sep_same_block_pairs == 0)
                                                           & (d.is_cm == 0)],
    "Cut-vertex-linked, CM": lambda d: d[(d.fails_occ == 1) & (d.sep_same_block_pairs == 0) & (d.is_cm == 1)],
}

# ------------------------------------------------------------------ sidebar filters

with st.sidebar:
    st.header("Filters")
    preset = st.selectbox("Preset", list(PRESETS))
    view = PRESETS[preset](df)
    ns = st.multiselect("Vertices n", sorted(df.n.unique()), default=sorted(df.n.unique()))
    view = view[view.n.isin(ns)]
    if len(view):
        lo, hi = int(df.m.min()), int(df.m.max())
        m_rng = st.slider("Edges m", lo, hi, (lo, hi))
        view = view[view.m.between(*m_rng)]
    occ = st.radio("OCC", ["any", "fails", "satisfies"], horizontal=True)
    if occ != "any":
        view = view[view.fails_occ == (1 if occ == "fails" else 0)]
    cm = st.radio("Cohen–Macaulay", ["any", "CM", "non-CM"], horizontal=True)
    if cm != "any":
        view = view[view.is_cm == (1 if cm == "CM" else 0)]
    if st.checkbox("Symmetric h-vector only"):
        view = view[view.h_symmetric == 1]
    st.subheader("Feature ranges")
    for i in range(2):
        col = st.selectbox(f"Feature {i + 1}", ["(none)"] + FEATURE_COLS, key=f"feat{i}")
        if col != "(none)":
            vals = df[col].dropna()
            a, b = float(vals.min()), float(vals.max())
            if a < b:
                rng = st.slider(col, a, b, (a, b), key=f"rng{i}")
                view = view[view[col].between(*rng)]
    st.metric("Graphs shown", f"{len(view):,}")

st.title("Toric graph explorer")
st.caption(f"Separated odd-cycle pair: cycle A in blue ({CYCLE_A}), cycle B in orange ({CYCLE_B}). "
           "Vertex labels match Macaulay2's v_1…v_n.")

tab_gallery, tab_graph, tab_compare, tab_table = st.tabs(["Gallery", "Graph", "Compare", "Table"])

# ------------------------------------------------------------------ gallery

with tab_gallery:
    per_page, ncols = 24, 6
    pages = max(1, -(-len(view) // per_page))
    c1, c2, c3 = st.columns([1, 1, 3])
    page = c1.number_input("Page", 1, pages, 1)
    sort_by = c2.selectbox("Sort by", ["graph_number", "m", "sep_pairs", "sep_dist_min", "aut_group_size"])
    c3.write(f"{len(view):,} graphs · page {page} of {pages}")
    chunk = view.sort_values([sort_by, "graph_number"]).iloc[(page - 1) * per_page: page * per_page]
    cols = st.columns(ncols)
    for k, (_, row) in enumerate(chunk.iterrows()):
        with cols[k % ncols]:
            st.image(png(row.graph6, size=2.2, labels=False))
            st.caption(f"**#{row.graph_number}** · m={row.m} · {row.status}  \n"
                       f"h = ({', '.join(map(str, row.h)) if row.h else '–'})")

# ------------------------------------------------------------------ single graph

def graph_panel(row: pd.Series, key: str) -> None:
    n_pairs = int(row.sep_pairs or 0)
    c1, c2 = st.columns(2)
    pair = c1.number_input("Separated pair", 1, max(1, n_pairs), 1, key=f"pair{key}",
                           disabled=n_pairs <= 1) - 1
    odd = c2.checkbox("Show all chordless odd cycles", key=f"odd{key}")
    st.image(png(row.graph6, pair, odd, size=4.2))
    st.markdown(f"**#{row.graph_number}** &nbsp; n={row.n}, m={row.m} &nbsp; · {row.status}")
    st.code(row.graph6, language=None)  # graph6 may contain backticks, so never put it in markdown
    st.markdown(f"**Hilbert numerator:** {h_str(row.h)}"
                + (" &nbsp; (symmetric)" if row.h_symmetric == 1 else ""))
    facts = {
        "depth": row.depth, "Gorenstein": row.is_gorenstein, "complete intersection": row.is_ci,
        "generators": row.num_gens, "generator degrees": row.gen_degrees,
        "separated pairs": row.sep_pairs, "pairs in one block": row.sep_same_block_pairs,
        "pair distance (min)": row.sep_dist_min, "linkage (max)": row.sep_linkage_max,
        "walk degree (max)": row.sep_walk_degree_max, "odd cycle transversal": row.odd_cycle_transversal,
        "threads": row.n_threads, "|Aut G|": row.aut_group_size, "data source": row.source,
    }
    st.dataframe(pd.DataFrame({"value": [fmt(v) for v in facts.values()]}, index=list(facts)),
                 width="stretch")
    if isinstance(row.toric_ideal, str):
        with st.expander(f"Toric ideal generators ({row.num_gens})"):
            st.code("\n".join(ideal_generators(row.toric_ideal)), language=None)


def pick(label: str, key: str, default_index: int = 0) -> pd.Series | None:
    source = view if len(view) else df
    nums = source.graph_number.tolist()
    typed = st.text_input(f"{label}: graph number or graph6", key=f"typed{key}")
    if typed.strip():
        hit = df[(df.graph6 == typed.strip()) | (df.graph_number.astype(str) == typed.strip())]
        if hit.empty:
            st.warning("No such graph in the database.")
            return None
        return hit.iloc[0]
    num = st.selectbox(f"{label} (from current filter)", nums, index=min(default_index, len(nums) - 1),
                       key=f"sel{key}")
    return source[source.graph_number == num].iloc[0]


with tab_graph:
    row = pick("Graph", "g")
    if row is not None:
        graph_panel(row, "g")

with tab_compare:
    left, right = st.columns(2)
    with left:
        a = pick("Left", "L", 0)
        if a is not None:
            graph_panel(a, "L")
    with right:
        b = pick("Right", "R", 1)
        if b is not None:
            graph_panel(b, "R")

# ------------------------------------------------------------------ table

with tab_table:
    default_cols = ["graph_number", "graph6", "n", "m", "status", "depth", "h_vector", "h_symmetric",
                    "is_gorenstein", "is_ci", "sep_pairs", "sep_same_block_pairs", "sep_dist_min",
                    "sep_linkage_max", "odd_cycle_transversal", "n_threads", "treewidth"]
    cols = st.multiselect("Columns", list(df.columns), default=default_cols)
    st.dataframe(view[cols], width="stretch", hide_index=True)
    st.download_button("Download CSV", view[cols].to_csv(index=False), "graphs.csv", "text/csv")
