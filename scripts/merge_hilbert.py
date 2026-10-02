"""Merge Hilbert-series result files from several machines into data/derived/fail<n>_hilbert.tsv.

Usage: python3 scripts/merge_hilbert.py 10 data/derived/fail10_hilbert_droplet.tsv [more.tsv ...]

One line per graph (a completed result beats a TIMEOUT/ERROR line), sorted by graph number. The
previous file is kept as fail<n>_hilbert.tsv.bak. Prints coverage against fail<n>_graphs.txt.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
n = int(sys.argv[1])
main = ROOT / "data" / "derived" / f"fail{n}_hilbert.tsv"
graphs = ROOT / "data" / "derived" / f"fail{n}_graphs.txt"

best: dict[int, str] = {}
for f in [main, *map(Path, sys.argv[2:])]:
    if not f.exists():
        continue
    for ln in f.read_text().splitlines():
        parts = ln.split("\t")
        if not parts or not parts[0].isdigit():
            continue
        k = int(parts[0])
        if k not in best or (len(parts) >= 5 and len(best[k].split("\t")) < 5):
            best[k] = ln
if main.exists():
    shutil.copy(main, main.with_name(main.name + ".bak"))
tmp = main.with_suffix(".tmp")
tmp.write_text("".join(best[k] + "\n" for k in sorted(best)))
tmp.replace(main)

wanted = {int(ln.split()[0]) for ln in graphs.read_text().splitlines() if ln.strip()}
done = {k for k, v in best.items() if len(v.split("\t")) >= 5}
print(f"merged {len(best)} graphs; complete results {len(done)}; "
      f"timeouts/errors {len(best) - len(done)}; missing {len(wanted - set(best))} of {len(wanted)}")
