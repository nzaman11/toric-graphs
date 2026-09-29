"""Phase 4 analysis of the n = 9 run: conjectures vs. truth, and model-guided vs random order.

Usage: .venv/bin/python scripts/analyze_n9.py
Writes reports/n9_results.md and reports/n9_speedup.png. Safe to run while the runner is going
(uses whatever has finished so far).
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from toric_graphs.loader import latest_runs  # noqa: E402

RUNS = ROOT / "data" / "derived" / "fail9_runs.jsonl"
PRED = ROOT / "data" / "derived" / "fail9_c4_predictions.csv"
REPORTS = ROOT / "reports"
WORKERS = 8
N_PERM = 2000
SEED = 0

# chart tokens (validated reference palette, light surface)
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
MODEL, RANDOM = "#2a78d6", "#eb6834"


def main() -> None:
    runs = latest_runs(RUNS)
    pred = {int(r["graph_number"]): r for r in csv.DictReader(PRED.open())}
    done = [r for r in runs.values() if r["status"] == "done"]
    timeouts = [r for r in runs.values() if r["status"] != "done"]
    lines = [f"# n = 9 results", "",
             f"Graphs failing OCC: {len(pred)}. Finished: {len(done)}. Timed out (so far): {len(timeouts)}. "
             f"Not yet run: {len(pred) - len(runs)}.", ""]

    # --- C4 scorecard (pre-registered in commit 26f8783)
    tab = Counter((int(pred[r["graph_number"]]["predicted_cm"]), r["is_cm"]) for r in done)
    tp, fn, fp, tn = tab[(1, 1)], tab[(0, 1)], tab[(1, 0)], tab[(0, 0)]
    lines += ["## C4 (pre-registered) vs truth", "",
              "| | actually CM | actually not CM |", "|---|---|---|",
              f"| C4 predicted CM | {tp} | {fp} |", f"| C4 predicted not CM | {fn} | {tn} |", ""]
    if done:
        acc = (tp + tn) / len(done)
        lines.append(f"Accuracy {acc:.3f}; precision for CM {tp / max(tp + fp, 1):.3f}; "
                     f"recall for CM {tp / max(tp + fn, 1):.3f}.")
    wrong = sorted(r["graph_number"] for r in done if int(pred[r["graph_number"]]["predicted_cm"]) != r["is_cm"])
    lines += [f"Counterexamples ({len(wrong)}): {wrong[:60]}{' …' if len(wrong) > 60 else ''}", ""]

    # --- C2: does a negative h-coefficient catch every non-CM graph?
    by = Counter(r["decided_by"] for r in done)
    noncm = [r for r in done if r["is_cm"] == 0]
    c2_bad = [r["graph_number"] for r in noncm if min(r["h_vector"]) >= 0]
    lines += ["## C2: non-CM ⇒ negative h-coefficient", "",
              f"Decided by: negative h {by['negative_h']}, depth over ZZ/32003 {by['depth_ZZp']}, "
              f"depth over QQ {by['depth_QQ']}.",
              f"Non-CM graphs with h ≥ 0 (C2 counterexamples): {len(c2_bad)} {c2_bad[:30]}", ""]
    depth_def = Counter(r["n"] - r["depth"] for r in done if r.get("depth") is not None)
    depth_def_zzp = Counter(r["n"] - r["depth_zzp"] for r in done if r.get("depth_zzp") is not None)
    lines += [f"n − depth over QQ (where computed): {dict(sorted(depth_def.items()))}; "
              f"over ZZ/32003: {dict(sorted(depth_def_zzp.items()))}", ""]

    # --- C1: Gorenstein <=> complete intersection among CM failing graphs
    cm = [r for r in done if r["is_cm"] == 1]
    gor = {r["graph_number"] for r in cm if r["h_vector"] == r["h_vector"][::-1]}
    m_of = {int(k): int(v["m"]) for k, v in pred.items()}
    ci = {r["graph_number"] for r in cm if r["num_gens"] == m_of[r["graph_number"]] - r["n"]}
    lines += ["## C1: Gorenstein ⇔ complete intersection (CM failing graphs)", "",
              f"CM: {len(cm)}. Gorenstein (symmetric h): {len(gor)}. Complete intersections: {len(ci)}. "
              f"Gorenstein but not CI: {sorted(gor - ci)[:30]}. CI but not Gorenstein: {sorted(ci - gor)[:30]}.", ""]

    # --- speedup: CM graphs found vs compute time, model order vs random order
    if cm:
        ordered = sorted(runs.values(), key=lambda r: r["order"])
        cost = np.array([r["wall_total"] for r in ordered]) / 3600 / WORKERS  # ≈ wall-clock hours on 8 workers
        hit = np.array([r.get("is_cm") == 1 for r in ordered], dtype=float)
        t_model, f_model = np.cumsum(cost), np.cumsum(hit)
        total_t, total_cm = t_model[-1], int(hit.sum())
        grid = np.linspace(0, total_t, 400)
        rng = np.random.default_rng(SEED)
        curves = np.empty((N_PERM, grid.size))
        t_half_rand = []
        for i in range(N_PERM):
            p = rng.permutation(len(cost))
            t, f = np.cumsum(cost[p]), np.cumsum(hit[p])
            curves[i] = np.interp(grid, t, f, left=0)
            t_half_rand.append(t[np.searchsorted(f, total_cm / 2)])
        mean, lo, hi = curves.mean(0), np.percentile(curves, 5, 0), np.percentile(curves, 95, 0)
        t_half_model = t_model[np.searchsorted(f_model, total_cm / 2)]
        speed = np.median(t_half_rand) / t_half_model
        t90_model = t_model[np.searchsorted(f_model, 0.9 * total_cm)]
        lines += ["## Model-guided vs random order", "",
                  f"Among {len(runs)} graphs run so far ({total_t:.2f} h on {WORKERS} workers), {total_cm} CM.",
                  f"Time to find half of them: model order {t_half_model * 60:.1f} min; random order "
                  f"{np.median(t_half_rand) * 60:.1f} min (median of {N_PERM} shuffles) → "
                  f"**{speed:.1f}× faster**. Model order finds 90% in {t90_model * 60:.1f} min.",
                  "", "![speedup](n9_speedup.png)", ""]
        plot(grid, t_model, f_model, mean, lo, hi, total_cm)

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "n9_results.md").write_text("\n".join(lines))
    print("\n".join(lines))


def plot(grid, t_model, f_model, mean, lo, hi, total_cm) -> None:
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    x = grid * 60
    ax.fill_between(x, lo, hi, color=RANDOM, alpha=0.15, linewidth=0)
    ax.plot(x, mean, color=RANDOM, lw=2, label="Random order (mean, 5–95% band)")
    ax.plot(np.r_[0, t_model * 60], np.r_[0, f_model], color=MODEL, lw=2, label="Model-guided order (C4)")
    ax.set_xlabel("Wall-clock minutes on 8 workers", color=INK2)
    ax.set_ylabel("Cohen–Macaulay graphs found", color=INK2)
    ax.set_title("Finding CM graphs at n = 9: model-guided vs random order", color=INK, loc="left", fontsize=11)
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_ylim(0, total_cm * 1.05)
    ax.set_xlim(0, x[-1])
    ax.text(x[-1] * 0.30, total_cm * 0.93, "model-guided", color=INK, fontsize=9)
    ax.text(x[-1] * 0.62, mean[int(len(mean) * 0.6)] * 0.78, "random", color=INK, fontsize=9)
    ax.legend(frameon=False, loc="lower right", labelcolor=INK2, fontsize=9)
    fig.tight_layout()
    fig.savefig(REPORTS / "n9_speedup.png", facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main()
