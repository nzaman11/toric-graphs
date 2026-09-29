"""Turn "graphNumber graph6" lines into a Macaulay2 input file for m2/compute_graphs.m2.

Usage: python3 scripts/make_m2_input.py <in.txt> <out.m2>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from toric_graphs.graph6 import edge_list, parse_g6  # noqa: E402


def m2_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main(src: str, dst: str) -> None:
    items = []
    for line in Path(src).read_text().split("\n"):
        if not line.strip():
            continue
        num, g6 = line.split()
        edges = ",".join("{%d,%d}" % e for e in edge_list(*parse_g6(g6)))
        items.append("{%s,%s,{%s}}" % (num, m2_string(g6), edges))
    Path(dst).write_text("graphList = {\n" + ",\n".join(items) + "\n};\n")
    print(f"{len(items)} graphs -> {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
