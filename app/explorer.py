"""Interactive explorer for graph toric ideals.

Run from the repo root:  .venv/bin/streamlit run app/explorer.py
Uses data/toric_graphs.sqlite; if it is missing or out of date it is unpacked from the committed
data/toric_graphs.sqlite.gz (seconds) or, failing that, rebuilt from the text files (minutes).

Filters in the sidebar are drafts until "Show results" is pressed; "Clear filters" resets them.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from toric_graphs import build  # noqa: E402
from toric_graphs.draw import graph_png  # noqa: E402
from toric_graphs.m2parse import ideal_generators  # noqa: E402

st.set_page_config(page_title="Toric graph explorer", page_icon="🔺", layout="wide")
ss = st.session_state


# ------------------------------------------------------------------ data

def ensure_db() -> tuple[Path, str]:
    """Up-to-date database + fingerprint of its inputs (changes whenever new results are pushed)."""
    try:
        with st.spinner("Preparing the database (seconds; up to several minutes if it must be rebuilt)…"):
            return build.ensure_db(processes=1)  # no forking inside the Streamlit server
    except Exception:
        st.error("The database could not be prepared. Please try again later or contact the author.")
        st.stop()


@st.cache_data(show_spinner=False)
def load(fp: str) -> tuple[pd.DataFrame, list[str]]:
    """`fp` is the input fingerprint: a new value (new data pushed) invalidates this cache."""
    with sqlite3.connect(build.db.DEFAULT_DB) as c:
        g = pd.read_sql("SELECT * FROM graphs", c)
        r = pd.read_sql("SELECT * FROM m2_results", c)
        f = pd.read_sql("SELECT * FROM features", c)
    feature_cols = [c for c in f.columns if c not in ("graph6", "n", "m") and pd.api.types.is_numeric_dtype(f[c])]
    df = g.merge(r, on="graph6", how="left").merge(f.drop(columns=["n", "m"]), on="graph6", how="left")
    df["status"] = df.apply(lambda x: "satisfies OCC" if not x.fails_occ
                            else "fails OCC · screened not CM (unproven)" if x.decided_by == "screen_ZZp"
                            else "fails OCC · not computed yet" if pd.isna(x.is_cm)
                            else ("fails OCC · CM" if x.is_cm == 1 else "fails OCC · not CM"), axis=1)
    df["h"] = df.h_vector.map(lambda s: tuple(json.loads(s)) if isinstance(s, str) else None)
    # graph numbers repeat across n, so graphs are identified by graph6 and labelled "n=9 #7161"
    df["label"] = df.apply(lambda x: f"n={x.n} #{x.graph_number}", axis=1)
    return df.sort_values(["n", "graph_number"]).reset_index(drop=True), feature_cols


@st.cache_data(max_entries=3000)
def png(g6: str, pair: int = 0, odd: bool = False, size: float = 3.2, labels: bool = True) -> bytes:
    return graph_png(g6, pair, odd, size, labels)


_, FINGERPRINT = ensure_db()
df, FEATURE_COLS = load(FINGERPRINT)
ALL_N = sorted(int(x) for x in df.n.unique())
M_RANGE = (int(df.m.min()), int(df.m.max()))

LABELS = {
    "m": "edges", "m_minus_n": "edges − vertices (codimension)", "density": "edge density",
    "sep_pairs": "separated odd-cycle pairs", "sep_same_block_pairs": "separated pairs inside one block",
    "normalization_gap": "normalization gap (distinct pair unions)",
    "sep_dist_min": "closest pair: distance", "sep_dist_max": "farthest pair: distance",
    "sep_closest_geodesics": "closest pair: # shortest paths",
    "sep_linkage_min": "pair linkage (min # disjoint paths)", "sep_linkage_max": "pair linkage (max # disjoint paths)",
    "sep_walk_degree_min": "walk degree estimate (min)", "sep_walk_degree_max": "walk degree estimate (max)",
    "sep_len_sum_min": "pair cycle-length sum (min)", "sep_len_sum_max": "pair cycle-length sum (max)",
    "sep_pairs_3_3": "separated pairs: triangle + triangle", "sep_pairs_3_5": "separated pairs: triangle + pentagon",
    "n_chordless_odd_cycles": "chordless odd cycles", "odd_cycle_transversal": "odd cycle transversal",
    "edge_frustration": "edge frustration (edges to delete → bipartite)",
    "n_threads": "threads (runs of degree-2 vertices)", "thread_max_len": "longest thread (edges)",
    "n_triangles": "triangles", "girth": "girth", "odd_girth": "odd girth", "even_girth": "even girth",
    "n_cut_vertices": "cut vertices", "n_bridges": "bridges", "n_blocks": "blocks",
    "n_nonbipartite_blocks": "non-bipartite blocks", "aut_group_size": "|Aut G|", "treewidth": "treewidth",
    "independence_number": "independence number", "matching_number": "matching number",
    "chromatic_number": "chromatic number", "signless_lap_min": "smallest signless Laplacian eigenvalue",
    "graph_number": "graph number",
}


def label(col) -> str:
    return "(none)" if col is None else LABELS.get(col, col.replace("_", " "))


PRESETS = {
    "All graphs": ("Every graph in the database.", lambda d: d),
    "Fails OCC": ("Graphs with two separated odd cycles — the interesting ones.", lambda d: d[d.fails_occ == 1]),
    "Gorenstein": ("CM with a symmetric Hilbert numerator (Gorenstein by Stanley).",
                   lambda d: d[d.is_gorenstein == 1]),
    "Gorenstein, fails OCC": ("Evidence for conjecture C1 (these are complete intersections).",
                              lambda d: d[(d.is_gorenstein == 1) & (d.fails_occ == 1)]),
    "C3: pair inside one block": ("A separated pair joined by 2 disjoint paths. Conjecture C3: never CM.",
                                  lambda d: d[d.sep_same_block_pairs > 0]),
    "C3 exceptions: cut-vertex-linked, not CM": (
        "Every pair linked through a cut vertex, yet not CM. What do these share?",
        lambda d: d[(d.fails_occ == 1) & (d.sep_same_block_pairs == 0) & (d.is_cm == 0)]),
    "C4: even cycle meets a separated pair": (
        "Conjecture C4: for failing graphs, exactly these are not CM (167/167 at n ≤ 8).",
        lambda d: d[d.even_cycle_meets_pair == 1]),
    "C4 counterexamples": ("Failing graphs where C4 predicts wrong. Empty at n ≤ 8 — watch this at n = 9.",
                           lambda d: d[(d.fails_occ == 1) & (d.even_cycle_meets_pair == d.is_cm)]),
    "Cut-vertex-linked, CM": ("Compare against the exceptions above.",
                              lambda d: d[(d.fails_occ == 1) & (d.sep_same_block_pairs == 0) & (d.is_cm == 1)]),
}

DEFAULT_WIDGETS = {"w_preset": "All graphs", "w_n": ALL_N, "w_m": M_RANGE, "w_occ": "Any", "w_cm": "Any",
                   "w_sym": False, "w_feat0": None, "w_feat1": None}


def feature_bounds(col: str) -> tuple[float, float]:
    v = df[col].dropna()
    return float(v.min()), float(v.max())


def read_draft() -> dict:
    feats = []
    for i in range(2):
        col = ss.get(f"w_feat{i}")
        if col is not None:
            feats.append((col, tuple(ss.get(f"w_rng{i}_{col}", feature_bounds(col)))))
    return {"preset": ss.w_preset, "n": tuple(ss.w_n), "m": tuple(ss.w_m), "occ": ss.w_occ, "cm": ss.w_cm,
            "sym": ss.w_sym, "feats": tuple(feats)}


def apply_filters(d: pd.DataFrame, F: dict) -> pd.DataFrame:
    d = PRESETS[F["preset"]][1](d)
    d = d[d.n.isin(F["n"]) & d.m.between(*F["m"])]
    if F["occ"] != "Any":
        d = d[d.fails_occ == (1 if F["occ"] == "Fails" else 0)]
    if F["cm"] != "Any":
        d = d[d.is_cm == (1 if F["cm"] == "CM" else 0)]
    if F["sym"]:
        d = d[d.h_symmetric == 1]
    for col, (a, b) in F["feats"]:
        d = d[d[col].between(a, b)]
    return d


def describe(F: dict) -> list[str]:
    out = [] if F["preset"] == "All graphs" else [F["preset"]]
    if list(F["n"]) != ALL_N:
        out.append("n ∈ {" + ", ".join(map(str, F["n"])) + "}")
    if F["m"] != M_RANGE:
        out.append(f"{F['m'][0]} ≤ edges ≤ {F['m'][1]}")
    if F["occ"] != "Any":
        out.append(f"{F['occ'].lower()} OCC")
    if F["cm"] != "Any":
        out.append(F["cm"])
    if F["sym"]:
        out.append("symmetric h")
    out += [f"{a:g} ≤ {label(c)} ≤ {b:g}" for c, (a, b) in F["feats"]]
    return out


# ------------------------------------------------------------------ state + callbacks

for k, v in DEFAULT_WIDGETS.items():
    ss.setdefault(k, v)
ss.setdefault("applied", read_draft())
ss.setdefault("page", 1)
ss.setdefault("view", "Gallery")


def on_apply() -> None:
    ss.applied = read_draft()
    ss.page = 1


def on_clear() -> None:
    for k in [k for k in ss.keys() if k.startswith("w_")]:
        del ss[k]
    for k, v in DEFAULT_WIDGETS.items():
        ss[k] = v
    ss.applied = read_draft()
    ss.page = 1


def on_open(g6: str) -> None:
    ss.sel_graph = g6
    ss.lookup = ""
    ss.view = "Graph"


# ------------------------------------------------------------------ sidebar

with st.sidebar:
    st.header("Filters")
    st.selectbox("Start from", list(PRESETS), key="w_preset")
    st.caption(PRESETS[ss.w_preset][0])
    st.multiselect("Vertices (n)", ALL_N, key="w_n")
    st.slider("Edges (m)", *M_RANGE, key="w_m")
    st.radio("Odd cycle condition", ["Any", "Fails", "Satisfies"], key="w_occ", horizontal=True)
    st.radio("Cohen–Macaulay", ["Any", "CM", "Not CM"], key="w_cm", horizontal=True)
    st.toggle("Symmetric Hilbert numerator only", key="w_sym")
    with st.expander("Feature ranges", expanded=any(ss.get(f"w_feat{i}") for i in range(2))):
        for i in range(2):
            col = st.selectbox(f"Feature {i + 1}", [None] + sorted(FEATURE_COLS, key=label),
                               format_func=label, key=f"w_feat{i}")
            if col is not None:
                a, b = feature_bounds(col)
                if a < b:
                    ss.setdefault(f"w_rng{i}_{col}", (a, b))
                    st.slider(label(col), a, b, key=f"w_rng{i}_{col}")
                else:
                    st.caption(f"All graphs have {label(col)} = {a:g}.")

    draft = read_draft()
    c1, c2 = st.columns(2)
    c1.button("Show results", type="primary", on_click=on_apply, width="stretch")
    c2.button("Clear filters", on_click=on_clear, width="stretch")
    if draft != ss.applied:
        st.warning("You changed the filters. Press **Show results** to update.", icon="✏️")
    else:
        st.caption(f"Preview: {len(apply_filters(df, draft)):,} graphs match.")

view = apply_filters(df, ss.applied)

# ------------------------------------------------------------------ header

st.title("Toric graph explorer")
active = describe(ss.applied)
h1, h2 = st.columns([3, 1])
h1.markdown(f"### {len(view):,} graphs" + ("" if active else " · no filters"))
if active:
    h1.caption("Filters: " + " · ".join(active))
    h2.button("Clear filters", on_click=on_clear, key="clear_top", width="stretch")

with st.expander("How to use / legend"):
    st.markdown(
        "- Set filters in the sidebar, then press **Show results**. **Clear filters** resets everything.\n"
        "- **Gallery**: press **Open** under a drawing to see it in detail.\n"
        "- In drawings, the two separated odd cycles (the OCC violation) are **blue** and **orange**; "
        "vertex numbers match Macaulay2's v₁…vₙ.\n"
        "- **Compare** puts two graphs side by side; **Table** lets you sort, choose columns and download CSV.")

current = st.segmented_control("View", ["Gallery", "Graph", "Compare", "Table"], key="view",
                               label_visibility="collapsed") or "Gallery"

if view.empty and current != "Graph":
    st.info("No graphs match these filters.")
    st.button("Clear filters", on_click=on_clear, key="clear_empty")
    st.stop()


# ------------------------------------------------------------------ helpers

def h_latex(h) -> str:
    if not h:
        return "–"
    parts = []
    for d, c in enumerate(h):
        if c == 0:
            continue
        mono = "" if d == 0 else ("T" if d == 1 else f"T^{{{d}}}")
        coef = str(abs(c)) if (abs(c) != 1 or d == 0) else ""
        parts.append(("-" if c < 0 else "+") + " " + coef + mono)
    return " ".join(parts).lstrip("+ ")


def fmt(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def yesno(v) -> str:
    return "–" if v is None or pd.isna(v) else ("yes" if v else "no")


def graph_panel(row: pd.Series, key: str, size: float = 4.2) -> None:
    n_pairs = int(row.sep_pairs or 0)
    c1, c2 = st.columns(2)
    pair = 0
    if n_pairs > 1:
        pair = c1.selectbox(f"Separated pair (of {n_pairs})", range(n_pairs), format_func=lambda i: f"pair {i + 1}",
                            key=f"pair{key}")
    else:
        c1.caption("1 separated pair" if n_pairs == 1 else "No separated pairs (satisfies OCC)")
    odd = c2.toggle("Show all chordless odd cycles", key=f"odd{key}")
    st.image(png(row.graph6, pair, odd, size=size))
    st.markdown(f"**Graph {row.label}** · m = {row.m} · {row.status}")
    st.code(row.graph6, language=None)  # graph6 may contain backticks, so never put it in markdown
    st.markdown("**Hilbert numerator**" + (" (symmetric)" if row.h_symmetric == 1 else ""))
    st.latex(h_latex(row.h))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("depth", fmt(row.depth))
    m2.metric("Gorenstein", yesno(row.is_gorenstein))
    m3.metric("complete int.", yesno(row.is_ci))
    m4.metric("generators", fmt(row.num_gens))
    props = {
        "generator degrees": row.gen_degrees, "separated pairs": row.sep_pairs,
        "pairs inside one block": row.sep_same_block_pairs, "closest pair distance": row.sep_dist_min,
        "pair linkage (max)": row.sep_linkage_max, "walk degree estimate (max)": row.sep_walk_degree_max,
        "odd cycle transversal": row.odd_cycle_transversal, "threads": row.n_threads,
        "cut vertices": row.n_cut_vertices, "|Aut G|": row.aut_group_size, "data source": row.source,
    }
    st.dataframe(pd.DataFrame({"value": [fmt(v) if k != "generator degrees" else str(v) for k, v in props.items()]},
                              index=list(props)), width="stretch")
    if isinstance(row.toric_ideal, str):
        with st.expander(f"Toric ideal generators ({row.num_gens})"):
            st.code("\n".join(ideal_generators(row.toric_ideal)), language=None)


OPTION_LABELS = dict(zip(df.graph6, df.label + " · m=" + df.m.astype(str) + " · " + df.status))


def option_label(g6: str) -> str:
    return OPTION_LABELS[g6]


# ------------------------------------------------------------------ views

if current == "Gallery":
    per_page, ncols = 24, 4
    pages = max(1, -(-len(view) // per_page))
    ss.page = min(ss.page, pages)
    sort_opts = ["graph_number", "m", "sep_pairs", "sep_dist_min", "odd_cycle_transversal", "aut_group_size"]
    c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
    sort_by = c1.selectbox("Sort by", sort_opts, format_func=label)
    c2.button("◀ Previous", disabled=ss.page <= 1, on_click=lambda: ss.update(page=ss.page - 1), width="stretch")
    c3.markdown(f"<div style='text-align:center;padding-top:.5rem'>Page {ss.page} of {pages}</div>",
                unsafe_allow_html=True)
    c4.button("Next ▶", disabled=ss.page >= pages, on_click=lambda: ss.update(page=ss.page + 1), width="stretch")
    chunk = view.sort_values([sort_by, "graph_number"]).iloc[(ss.page - 1) * per_page: ss.page * per_page]
    cols = st.columns(ncols)
    for k, (_, row) in enumerate(chunk.iterrows()):
        with cols[k % ncols].container(border=True):
            st.image(png(row.graph6, size=2.2, labels=False))
            st.markdown(f"**{row.label}** · m = {row.m}")
            st.caption(f"{row.status}  \nh = ({', '.join(map(str, row.h)) if row.h else '–'})")
            st.button("Open", key=f"open{row.graph6}", on_click=on_open, args=(row.graph6,),
                      width="stretch")

elif current == "Graph":
    g6s = view.graph6.tolist()
    c1, c2 = st.columns([2, 1])
    if g6s:
        if ss.get("sel_graph") not in g6s:
            ss.sel_graph = g6s[0]
        c1.selectbox("Choose from current results", g6s, format_func=option_label, key="sel_graph")
    else:
        c1.info("No graphs in the current results — look one up instead.")
    lookup = c2.text_input("…or look up any graph", key="lookup",
                           placeholder="graph6, or n:number like 9:7161")
    if lookup.strip():
        q = lookup.strip()
        if ":" in q and q.split(":")[0].isdigit():
            n_q, num_q = q.split(":", 1)
            hit = df[(df.n.astype(str) == n_q) & (df.graph_number.astype(str) == num_q.strip())]
        else:
            hit = df[(df.graph6 == q) | (df.graph_number.astype(str) == q)]
        if hit.empty:
            st.warning(f"No graph “{q}” in the database.")
        else:
            if len(hit) > 1:
                st.info(f"Number {q} exists for n = {', '.join(map(str, hit.n))}; showing n = {hit.n.iloc[-1]}. "
                        f"Type e.g. {hit.n.iloc[0]}:{q} for another.")
            st.caption("Showing the looked-up graph. Clear the lookup box to go back to your results.")
            graph_panel(hit.iloc[-1], "g")
    elif g6s:
        graph_panel(view[view.graph6 == ss.sel_graph].iloc[0], "g")

elif current == "Compare":
    g6s = view.graph6.tolist()
    left, right = st.columns(2)
    for col, key, idx in ((left, "L", 0), (right, "R", 1)):
        with col:
            g6 = st.selectbox("Graph", g6s, index=min(idx, len(g6s) - 1), format_func=option_label,
                              key=f"cmp{key}")
            graph_panel(view[view.graph6 == g6].iloc[0], key, size=3.6)

else:  # Table
    default_cols = ["graph_number", "n", "m", "status", "depth", "h_vector", "h_symmetric", "is_gorenstein",
                    "is_ci", "sep_pairs", "sep_same_block_pairs", "sep_dist_min", "sep_linkage_max",
                    "odd_cycle_transversal", "n_threads", "treewidth"]
    cols = st.multiselect("Columns", [c for c in df.columns if c != "h"], default=default_cols)
    st.dataframe(view[cols], width="stretch", hide_index=True)
    st.download_button("Download CSV", view[cols].to_csv(index=False), "graphs.csv", "text/csv")
