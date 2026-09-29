"""Quick summary of data/derived/noncm8_results.txt."""
import re
from collections import Counter
from pathlib import Path

text = Path(__file__).resolve().parents[1].joinpath("data/derived/noncm8_results.txt").read_text()
recs = [dict(re.findall(r"^(\w+): (.*)$", b, re.M)) for b in text.split("====") if "Graph6" in b]


def h_vector(hs: str) -> tuple[int, ...]:
    num = re.match(r"\((.*)\)/\(\(1-T\)\^\d+\)$", hs).group(1)
    c = Counter()
    for term in num.replace("-", "+-").split("+"):
        if term:
            m = re.match(r"^(-?\d*)\*?(T(?:\^(\d+))?)?$", term)
            coef = {"": 1, "-": -1}.get(m.group(1), None)
            coef = int(m.group(1)) if coef is None else coef
            c[0 if not m.group(2) else int(m.group(3) or 1)] += coef
    return tuple(c[d] for d in range(max(c) + 1))


hv = [h_vector(r["ReducedHilbertSeries"]) for r in recs]
print("graphs:", len(recs))
print("8 - depth:", Counter(r["VerticesMinusDepth"] for r in recs))
print("h-vector has a negative entry:", sum(min(h) < 0 for h in hv))
print("negative entries only in top degree:", sum(min(h[:-1]) >= 0 and h[-1] < 0 for h in hv))
print("top coefficient values:", Counter(h[-1] for h in hv))
print("max generator degree:", Counter(max(eval(r["GenDegrees"].replace("{", "[").replace("}", "]"))) for r in recs))
print("edges:", sorted(Counter(int(r["NumEdges"]) for r in recs).items()))
print("total M2 seconds:", round(sum(float(r[k]) for r in recs for k in r if k.startswith("Seconds")), 2))
