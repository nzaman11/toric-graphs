# toric-graphs

ML-guided discovery on toric ideals of graphs that fail the odd cycle condition.

> Private work in progress. Underlying research: Navila Zaman (Connecticut College), SSRI 2026.

## Layout

```
m2/          Macaulay2 scripts (compute_graphs.m2)
data/raw/    original Macaulay2 exports (not committed)
data/derived/ recomputed / processed data
src/toric_graphs/  graph6 decoding, pure-Python OCC check
scripts/     one-off pipeline scripts
tests/       pytest suite
conjectures.md  data-supported conjectures and proof notes
```

## Setup (inside WSL)

```bash
sudo apt install python3.14-venv python3-pip
cd ~/toric-graphs
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest
```

## Build the database

```bash
.venv/bin/python scripts/build_db.py --fresh
```

Creates `data/toric_graphs.sqlite` (not committed; rebuilt from the text files in ~15 s) with
tables `graphs`, `m2_results` and `features` (82 graph-only features, see
`src/toric_graphs/features.py`). Schema: `src/toric_graphs/db.py`.

## Explorer

```bash
.venv/bin/streamlit run app/explorer.py
```

Opens at http://localhost:8501. Gallery, single-graph view (separated odd-cycle pair in
blue/orange, Hilbert numerator, generators), side-by-side compare, and a filterable table.
Presets include the Gorenstein graphs and the C3 groups from `conjectures.md`.

## Recompute graphs with Macaulay2

```bash
python3 scripts/make_m2_input.py data/derived/noncm8_graphs.txt data/derived/noncm8_input.m2
M2 --script m2/compute_graphs.m2 data/derived/noncm8_input.m2 data/derived/noncm8_results.txt 8
```
