# toric-graphs

Data-driven conjecture testing for toric ideals of graphs that fail the odd cycle condition (OCC):
which edge rings k[G] are Cohen–Macaulay (CM) and Gorenstein, over k = ℚ.

> Private work in progress. Underlying research: Navila Zaman (Connecticut College), SSRI 2026.

## Results so far

- **Data.** Every connected, non-bipartite, leaf-free graph on 8 vertices in the edge-threshold
  band (6,971 graphs), plus every OCC-failing graph on 7 (6) and 9 (7,125) vertices, with toric
  ideal, Hilbert series and a proven CM verdict for each failing graph.
- **Edge-threshold theorem** (Navila): failing OCC forces n + 1 ≤ m ≤ C(n,2) − 9 for n ≥ 7, sharp;
  verified on all graphs with n = 7, 8.
- **Surviving conjecture C2′:** for G failing OCC, k[G] is CM **iff its h-vector is nonnegative**.
  Exact on all 7,292 failing graphs with n ≤ 9.
- **Pre-registered test at n = 9.** Rule C4 (conjectured from n ≤ 8 with help from a decision tree)
  was committed before any n = 9 computation. It classified 98.2% of the 7,125 graphs correctly but
  was refuted (21 + 107 counterexamples), as were C1 (Gorenstein ⇔ complete intersection; 18
  Gorenstein non-CI graphs, with Buchsbaum–Eisenbud-type generator counts) and C3.
  Details and counterexamples: [`conjectures.md`](conjectures.md), [`reports/n9_results.md`](reports/n9_results.md).
- **Ordering experiment** (cost = Macaulay2 CPU time; wall time was dominated by M2 start-up):
  screening in C4 order reached half of the 725 CM graphs with **23× less CPU than random order**
  and 2× less than "fewest edges first"; "fewest edges first" is better at 90%.

![ordering experiment](reports/n9_speedup.png)

## Layout

```
m2/                Macaulay2 scripts (compute_graphs.m2, compute_one.m2, time_depth.m2)
data/raw/          original SSRI Macaulay2 exports for n = 8 (committed, unmodified)
data/derived/      recomputed n = 7, 8 results, n = 9 predictions and runner output
data/toric_graphs.sqlite.gz   prebuilt database (+ .fingerprint of its inputs)
src/toric_graphs/  graph6, OCC check, features, loader, runner, drawing
scripts/           pipeline scripts (build_db, run_n9, analyze_n9, phase3_trees, ...)
app/explorer.py    Streamlit explorer
reports/           tree analysis, n = 9 results and chart
tests/             pytest suite
conjectures.md     conjectures, evidence, counterexamples, proof notes
```

## Setup (inside WSL)

```bash
sudo apt install python3.14-venv python3-pip
cd ~/toric-graphs
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

`requirements.txt` holds only what the explorer needs (used by Streamlit Cloud);
`requirements-dev.txt` adds testing and modelling packages.

## Build the database

```bash
.venv/bin/python scripts/build_db.py
```

Rebuilds `data/toric_graphs.sqlite` from the text files (~40 s on 12 threads) with tables
`graphs`, `m2_results`, `features` and `meta`, and writes the prebuilt copy
`data/toric_graphs.sqlite.gz` + `data/toric_graphs.fingerprint`. **Commit those two files
whenever data or loader/feature code changes**; `tests/test_build.py` fails if they are stale.

## Explorer

```bash
.venv/bin/streamlit run app/explorer.py
```

Opens at http://localhost:8501: gallery, single-graph view (separated odd-cycle pair in
blue/orange, Hilbert numerator, generators), side-by-side compare, and a filterable table, with
presets for the conjecture groups. Graphs are labelled `n=9 #7161` because graph numbers repeat
across n; look up a graph by graph6 or `n:number`.

### Hosting (Streamlit Community Cloud, invite-only)

Main file `app/explorer.py`, Python 3.12+, `requirements.txt`. On start the app unpacks the
committed prebuilt database (seconds) and redoes this whenever pushed data changes it; if the
prebuilt copy is stale it rebuilds from the text files (several minutes). Keep the sharing setting
on "Only specific people can view this app"; invited viewers can download the data as CSV.

## Computing with Macaulay2

```bash
# a list of graphs -> one M2 session
python3 scripts/make_m2_input.py data/derived/noncm8_graphs.txt data/derived/noncm8_input.m2
M2 --script m2/compute_graphs.m2 data/derived/noncm8_input.m2 data/derived/noncm8_results.txt 8

# n = 9: parallel, resumable, proof-only verdicts (see src/toric_graphs/runner.py)
.venv/bin/python scripts/run_n9.py
```
