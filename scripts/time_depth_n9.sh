#!/bin/bash
# Re-measure depth CPU time (ZZ/32003, one M2 session per worker) for every n=9 graph whose
# Hilbert numerator is nonnegative, i.e. every graph that needed the depth stage.
# Output: data/derived/fail9_depth_cpu.txt  ("graphNumber depth seconds" per line)
set -euo pipefail
cd "$(dirname "$0")/.."
W=8
TMP=$(mktemp -d "$HOME/tg_timing.XXXX")
.venv/bin/python - "$TMP" "$W" <<'EOF'
import sys
sys.path.insert(0, "src")
from toric_graphs.loader import latest_runs
from pathlib import Path
tmp, w = Path(sys.argv[1]), int(sys.argv[2])
recs = [r for r in latest_runs(Path("data/derived/fail9_runs.jsonl")).values()
        if "h_vector" in r and min(r["h_vector"]) >= 0]
recs.sort(key=lambda r: r["graph_number"])
for k in range(w):
    (tmp / f"list{k}.txt").write_text("".join(f"{r['graph_number']} {r['graph6']}\n" for r in recs[k::w]))
print(len(recs), "graphs need depth timing")
EOF
for k in $(seq 0 $((W - 1))); do
  .venv/bin/python scripts/make_m2_input.py "$TMP/list$k.txt" "$TMP/in$k.m2" >/dev/null
done
seq 0 $((W - 1)) | xargs -P "$W" -I{} M2 --script m2/time_depth.m2 "$TMP/in{}.m2" "$TMP/out{}.txt" 9
cat "$TMP"/out*.txt | sort -n > data/derived/fail9_depth_cpu.txt
rm -rf "$TMP"
wc -l data/derived/fail9_depth_cpu.txt
