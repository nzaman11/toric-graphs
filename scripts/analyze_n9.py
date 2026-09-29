"""Phase 4 analysis of the n = 9 run: conjectures vs truth, and ordering experiment.

Usage: .venv/bin/python scripts/analyze_n9.py      (after scripts/time_depth_n9.sh)
Writes reports/n9_results.md and reports/n9_speedup.png.

Verdicts use only proofs (loader.run_verdict). Cost of a graph = Macaulay2 CPU time of the pipeline
it needs: ideal + Hilbert series over QQ (recorded by the runner), plus depth over ZZ/32003 when
the Hilbert numerator is nonnegative (re-measured in one M2 session: data/derived/fail9_depth_cpu.txt).
Start-up overhead is excluded because it only counts how many times M2 is launched.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from toric_graphs.loader import latest_runs, run_verdict  # noqa: E402

DERIVED, REPORTS = ROOT / "data" / "derived", ROOT / "reports"
N_PERM, SEED = 2000, 0

# chart tokens (validated reference palette, light surface; first three categorical slots)
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
C_MODEL, C_RANDOM, C_EDGES = "#2a78d6", "#eb6834", "#1baf7a"


def first_reach(cost: np.ndarray, hit: np.ndarray, frac: float) -> tuple[float, int]:
    """(cumulative cost, number of graphs) when `frac` of all CM graphs have been found."""
    t, f = np.cumsum(cost), np.cumsum(hit)
    i = int(np.searchsorted(f, np.ceil(frac * hit.sum())))
    return float(t[i]), i + 1


def main() -> None:
    runs = latest_runs(DERIVED / "fail9_runs.jsonl")
    pred = {int(r["graph_number"]): r for r in csv.DictReader((DERIVED / "fail9_c4_predictions.csv").open())}
    depth_cpu = {int(a): (int(b), float(c)) for a, b, c in
                 (line.split() for line in (DERIVED / "fail9_depth_cpu.txt").read_text().splitlines())}
    L = [f"# n = 9 results", "",
         "Pre-registered predictions: commit `26f8783`. Raw results committed before scoring: `fb90de6`.", ""]

    verdict = {num: run_verdict(r) for num, r in runs.items()}
    cm = {num for num, (v, _) in verdict.items() if v == 1}
    noncm = {num for num, (v, _) in verdict.items() if v == 0}
    unknown = sorted(set(pred) - cm - noncm)
    L += [f"Graphs failing OCC: {len(pred)}. Proven CM: {len(cm)}. Proven not CM: {len(noncm)}. "
          f"Undecided: {len(unknown)} {unknown[:20]}.",
          f"How decided: {dict(Counter(h for v, h in verdict.values()))}.", ""]

    # --- C4 scorecard
    pc = {num for num, r in pred.items() if r["predicted_cm"] == "1"}
    tp, fp = len(pc & cm), len(pc & noncm)
    fn, tn = len(cm - pc), len(noncm - pc)
    L += ["## C4 (pre-registered) vs truth", "",
          "| | actually CM | actually not CM |", "|---|---|---|",
          f"| C4 predicted CM | {tp} | {fp} |", f"| C4 predicted not CM | {fn} | {tn} |", "",
          f"Accuracy {(tp + tn) / (tp + tn + fp + fn):.4f}. Precision for CM {tp / (tp + fp):.3f}, "
          f"recall for CM {tp / (tp + fn):.3f}.", "",
          f"**C4′ (even cycle meets a separated pair ⇒ not CM):** {fn} counterexamples "
          f"{sorted(cm - pc)[:30]}{' …' if fn > 30 else ''}.",
          f"**C4 ⇐ direction (no such cycle ⇒ CM):** {fp} counterexamples: {sorted(pc & noncm)}", ""]

    # --- C2
    neg = {num for num, r in runs.items() if "h_vector" in r and min(r["h_vector"]) < 0}
    L += ["## C2: not CM ⇔ some h-coefficient is negative (failing graphs)", "",
          f"Negative h: {len(neg)}, all not CM (theorem). Nonnegative h: {len(cm | noncm) - len(neg)}, "
          f"of which not CM: {len(noncm - neg)}. Depth over ZZ/32003 re-measured for all "
          f"{len(depth_cpu)} nonnegative-h graphs: {dict(Counter(d for d, _ in depth_cpu.values()))} (value: count).",
          "So at n = 9, as at n = 8, the Hilbert series alone decides CM for every failing graph.", ""]
    tops = Counter(runs[k]["h_vector"][-1] for k in noncm)
    L += [f"Top h-coefficient among non-CM graphs: {dict(sorted(tops.items()))}.", ""]

    # --- C1
    m_of = {int(k): int(v["m"]) for k, v in pred.items()}
    gor = {k for k in cm if runs[k]["h_vector"] == runs[k]["h_vector"][::-1]}
    ci = {k for k in cm if runs[k]["num_gens"] == m_of[k] - 9}
    L += ["## C1: Gorenstein ⇔ complete intersection (CM failing graphs)", "",
          f"CM {len(cm)}; Gorenstein {len(gor)}; complete intersections {len(ci)}; "
          f"CI but not Gorenstein {len(ci - gor)} (must be 0); Gorenstein but not CI {len(gor - ci)}: "
          f"{sorted(gor - ci)}", ""]
    rows = sorted(gor - ci)
    if rows:
        L += ["| graph | m | codim | gens | degrees | h |", "|---|---|---|---|---|---|"]
        L += [f"| {k} | {m_of[k]} | {m_of[k] - 9} | {runs[k]['num_gens']} | {runs[k]['gen_degrees']} | "
              f"{tuple(runs[k]['h_vector'])} |" for k in rows]
        L.append("")

    # --- ordering experiment (CPU time)
    nums = sorted(pred)
    cost = {k: runs[k].get("seconds_ker", 0) + runs[k].get("seconds_hilbert", 0)
            + (depth_cpu[k][1] if k in depth_cpu else 0) for k in nums}
    orders = {
        "C4 (pre-registered)": sorted(nums, key=lambda k: (pred[k]["predicted_cm"] != "1", k)),
        "fewest edges first": sorted(nums, key=lambda k: (m_of[k], k)),
        "perfect oracle": sorted(nums, key=lambda k: (k not in cm, k)),
    }
    res = {}
    for name, o in orders.items():
        c, h = np.array([cost[k] for k in o]), np.array([k in cm for k in o], float)
        res[name] = (c, h, first_reach(c, h, .5), first_reach(c, h, .9))
    rng = np.random.default_rng(SEED)
    base_c, base_h = np.array([cost[k] for k in nums]), np.array([k in cm for k in nums], float)
    r50, r90, n50, n90, curves = [], [], [], [], []
    total = base_c.sum()
    grid = np.linspace(0, total, 500)
    for _ in range(N_PERM):
        p = rng.permutation(len(nums))
        c, h = base_c[p], base_h[p]
        (t5, k5), (t9, k9) = first_reach(c, h, .5), first_reach(c, h, .9)
        r50.append(t5); r90.append(t9); n50.append(k5); n90.append(k9)
        curves.append(np.interp(grid, np.cumsum(c), np.cumsum(h), left=0))
    curves = np.array(curves)
    rand = ((float(np.median(r50)), int(np.median(n50))), (float(np.median(r90)), int(np.median(n90))))
    L += ["## Ordering experiment: how fast are the CM graphs found?", "",
          f"Total Macaulay2 CPU for all {len(nums)} graphs: {total / 60:.1f} min on one core "
          f"(the wall-clock run was dominated by Macaulay2 start-up, ~2 s per launch).", "",
          "| order | CPU to find 50% of CM | graphs screened | CPU to find 90% | graphs screened |",
          "|---|---|---|---|---|",
          f"| random (median of {N_PERM}) | {rand[0][0] / 60:.1f} min | {rand[0][1]} | "
          f"{rand[1][0] / 60:.1f} min | {rand[1][1]} |"]
    for name, (_, _, a, b) in res.items():
        L.append(f"| {name} | {a[0] / 60:.2f} min | {a[1]} | {b[0] / 60:.2f} min | {b[1]} |")
    m4, me = res["C4 (pre-registered)"], res["fewest edges first"]
    L += ["", f"C4 vs random: **{rand[0][0] / m4[2][0]:.1f}×** less CPU to reach 50% of CM graphs, "
          f"{rand[1][0] / m4[3][0]:.1f}× to reach 90%. C4 vs fewest-edges-first: "
          f"**{me[2][0] / m4[2][0]:.1f}×** (50%), {me[3][0] / m4[3][0]:.1f}× (90%). "
          f"Perfect-oracle ceiling vs random: {rand[0][0] / res['perfect oracle'][2][0]:.1f}× (50%).",
          "", "![ordering experiment](n9_speedup.png)", ""]
    plot(grid, curves, res, int(base_h.sum()))
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "n9_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def plot(grid, curves, res, total_cm) -> None:
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})
    fig, ax = plt.subplots(figsize=(7.4, 4.4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    x = grid / 60
    ax.fill_between(x, np.percentile(curves, 5, 0), np.percentile(curves, 95, 0), color=C_RANDOM, alpha=.15, lw=0)
    ax.plot(x, curves.mean(0), color=C_RANDOM, lw=2, label="random order (mean, 5–95% band)")
    for name, color, style in (("fewest edges first", C_EDGES, "-"), ("C4 (pre-registered)", C_MODEL, "-"),
                               ("perfect oracle", MUTED, ":")):
        c, h, _, _ = res[name]
        ax.plot(np.r_[0, np.cumsum(c)] / 60, np.r_[0, np.cumsum(h)], color=color, lw=2, ls=style,
                label=name)
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xlabel("Macaulay2 CPU minutes (one core, log scale above 1)", color=INK2)
    ax.set_ylabel("Cohen–Macaulay graphs found", color=INK2)
    ax.set_title(f"Finding the {total_cm} CM graphs among 7,125 at n = 9", color=INK, loc="left", fontsize=11)
    ax.grid(True, color=GRID, lw=.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_ylim(0, total_cm * 1.04)
    ax.set_xlim(0, x[-1])
    ax.legend(frameon=False, loc="lower right", labelcolor=INK2, fontsize=9)
    fig.tight_layout()
    fig.savefig(REPORTS / "n9_speedup.png", facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main()
