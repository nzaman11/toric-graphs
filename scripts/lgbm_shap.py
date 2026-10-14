"""LightGBM + SHAP: which graph features predict Cohen-Macaulayness for graphs failing OCC?

Two feature sets:
  A (basic)  n, m, m - n, density, degree statistics, connected components, cycle counts of length 3-8
  B (all)    A plus every numeric structural feature in the `features` table
Three experiments:
  1  5-fold CV on the failing graphs with n <= 9 (labels proved; database)
  2  train on n <= 9, test on n = 10
  3  5-fold CV on the n = 10 graphs with h >= 0 and known depth (where the Hilbert series does not decide)

n = 10 labels: CM = depth 10 over ZZ/32003 (proved); not CM = a negative h-coefficient (proved) or depth < 10
over ZZ/32003 (screen). Graphs whose depth run failed or has not run yet are left out. Features never use
Macaulay2 output.

Usage:  python3 scripts/lgbm_shap.py [--workers 6] [--neg-sample 40000]
Writes reports/lgbm_shap.md and reports/shap_*.png; caches n = 10 features in data/derived/fail10_features.csv.gz.
"""
import argparse
import random
import sqlite3
import sys
from multiprocessing import Pool
from pathlib import Path

import lightgbm as lgb
import matplotlib
import networkx as nx
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import accuracy_score, balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from toric_graphs.features import compute_features  # noqa: E402
import run_n10  # noqa: E402

DB = ROOT / "data" / "toric_graphs.sqlite"
DERIVED = ROOT / "data" / "derived"
REPORTS = ROOT / "reports"
CACHE10 = DERIVED / "fail10_features.csv.gz"

BASIC = (["n", "m", "m_minus_n", "density", "n_components", "deg_min", "deg_max", "deg_mean", "deg_std",
          "deg_count_2", "deg_count_3", "deg_count_4", "deg_count_5plus", "frac_deg_2"]
         + [f"cyc_len_{k}" for k in range(3, 9)])
PARAMS = dict(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=20, subsample=0.8,
              subsample_freq=1, colsample_bytree=0.8, class_weight="balanced", random_state=0, verbose=-1)


def n_components(g6: str) -> int:
    return nx.number_connected_components(nx.from_graph6_bytes(g6.encode()))


def load_small() -> pd.DataFrame:
    con = sqlite3.connect(DB)
    df = pd.read_sql("""select f.*, r.is_cm from features f join graphs g using (graph6)
                        join m2_results r using (graph6) where g.fails_occ = 1""", con)
    df["n_components"] = [n_components(g) for g in df["graph6"]]
    df["label_proved"] = 1
    return df


def _feat(item: tuple) -> dict:
    num, g6 = item
    f = compute_features(g6)
    f.update(graph_number=num, graph6=g6, n_components=n_components(g6))
    return f


def load_n10(workers: int, neg_sample: int) -> pd.DataFrame:
    graphs = dict(run_n10.read_graphs(10))
    neg = set(graphs) - {k for k, _ in run_n10.nonneg_graphs(10)}
    depth = {}
    for ln in (DERIVED / "fail10_depth.txt").read_text().splitlines():
        t = ln.split()
        if len(t) >= 3 and t[0].isdigit() and t[1].lstrip("-").isdigit():
            depth[int(t[0])] = int(t[1])
    labels = {k: int(d == 10) for k, d in depth.items() if k not in neg}
    for k in random.Random(0).sample(sorted(neg), min(neg_sample, len(neg))):
        labels[k] = 0
    cached = pd.read_csv(CACHE10) if CACHE10.exists() else pd.DataFrame(columns=["graph_number"])
    todo = sorted(set(labels) - set(cached["graph_number"].astype(int)))
    if todo:
        print(f"computing features for {len(todo)} graphs on {workers} workers", flush=True)
        with Pool(workers) as pool:
            rows = pool.map(_feat, [(k, graphs[k]) for k in todo], chunksize=200)
        cached = pd.concat([cached, pd.DataFrame(rows)], ignore_index=True)
        cached.to_csv(CACHE10, index=False)
    df = cached[cached["graph_number"].astype(int).isin(labels)].copy()
    df["is_cm"] = [labels[int(k)] for k in df["graph_number"]]
    df["h_nonneg"] = [int(int(k) not in neg) for k in df["graph_number"]]
    df["label_proved"] = [int(int(k) in neg or labels[int(k)] == 1) for k in df["graph_number"]]
    return df


def numeric_features(df: pd.DataFrame) -> list[str]:
    skip = {"graph6", "graph_number", "is_cm", "h_nonneg", "label_proved", "n"}
    cols = [c for c in df.columns if c not in skip and pd.api.types.is_numeric_dtype(df[c])]
    return ["n"] + cols if "n" in df.columns else cols


def scores(y, p) -> dict:
    return dict(accuracy=accuracy_score(y, p >= 0.5), balanced_acc=balanced_accuracy_score(y, p >= 0.5),
                auc=roc_auc_score(y, p) if len(set(y)) == 2 else float("nan"))


def cv(df: pd.DataFrame, cols: list[str]) -> dict:
    X, y = df[cols].astype(float), df["is_cm"].astype(int).to_numpy()
    p = np.zeros(len(y))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(X, y):
        p[te] = lgb.LGBMClassifier(**PARAMS).fit(X.iloc[tr], y[tr]).predict_proba(X.iloc[te])[:, 1]
    return scores(y, p)


def shap_report(df: pd.DataFrame, cols: list[str], tag: str, title: str) -> pd.Series:
    X, y = df[cols].astype(float), df["is_cm"].astype(int)
    model = lgb.LGBMClassifier(**PARAMS).fit(X, y)
    sv = shap.TreeExplainer(model).shap_values(X)
    if isinstance(sv, list):
        sv = sv[1]
    if sv.ndim == 3:
        sv = sv[:, :, 1]
    plt.figure()
    shap.summary_plot(sv, X, max_display=15, show=False)
    plt.title(title, fontsize=11)
    plt.tight_layout()
    plt.savefig(REPORTS / f"shap_{tag}.png", dpi=150)
    plt.close("all")
    return pd.Series(np.abs(sv).mean(axis=0), index=cols).sort_values(ascending=False)


def table(rows: list[tuple]) -> str:
    out = ["| experiment | features | graphs (CM / not) | accuracy | balanced acc. | AUC |", "|---|---|---|---|---|---|"]
    for name, fs, n_cm, n_not, s in rows:
        out.append(f"| {name} | {fs} | {n_cm:,} / {n_not:,} | {s['accuracy']:.3f} | {s['balanced_acc']:.3f} | "
                   f"{s['auc']:.3f} |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--neg-sample", type=int, default=40000)
    a = ap.parse_args()
    small, big = load_small(), load_n10(a.workers, a.neg_sample)
    full = [c for c in numeric_features(small) if c in big.columns]
    basic = [c for c in BASIC if c in full]
    hard = big[big["h_nonneg"] == 1]
    sets = {"A (basic)": basic, "B (all)": full}
    count = lambda d: (int(d["is_cm"].sum()), int((1 - d["is_cm"]).sum()))  # noqa: E731

    rows, shap_tables = [], {}
    for fs, cols in sets.items():
        rows.append(("1. CV, n ≤ 9", fs, *count(small), cv(small, cols)))
    for fs, cols in sets.items():
        model = lgb.LGBMClassifier(**PARAMS).fit(small[cols].astype(float), small["is_cm"].astype(int))
        for part, d in (("all sampled", big), ("h ≥ 0 only", hard)):
            p = model.predict_proba(d[cols].astype(float))[:, 1]
            rows.append((f"2. train n ≤ 9 → test n = 10 ({part})", fs, *count(d), scores(d["is_cm"].to_numpy(), p)))
    for fs, cols in sets.items():
        rows.append(("3. CV, n = 10 with h ≥ 0", fs, *count(hard), cv(hard, cols)))
    for tag, d, title in (("n9", small, "n ≤ 9 failing graphs"), ("n10_hnonneg", hard, "n = 10, h ≥ 0")):
        for fs, cols in sets.items():
            key = f"{tag}_{'basic' if fs.startswith('A') else 'all'}"
            shap_tables[key] = shap_report(d, cols, key, f"SHAP: {title}, features {fs}")

    lines = ["# LightGBM + SHAP: predicting CM for graphs failing OCC", "",
             "Generated by `scripts/lgbm_shap.py`. Label: k[G] Cohen–Macaulay (1) or not (0). Features are purely",
             "graph-theoretic (no Macaulay2 output). Feature set A: " + ", ".join(f"`{c}`" for c in basic) + ".",
             f"Feature set B: A plus all {len(full) - len(basic)} other numeric structural features.", "",
             "n = 10 labels: CM = depth 10 over ZZ/32003 (proved); not CM = negative h-coefficient (proved) or depth < 10",
             f"over ZZ/32003 (screen). The n = 10 set is every graph with h ≥ 0 and known depth plus a random sample of "
             f"{a.neg_sample:,} graphs with a negative h-coefficient.", "", table(rows), "",
             "## Most important features (mean |SHAP|, log-odds of CM)", ""]
    for key, s in shap_tables.items():
        lines += [f"**{key}** — ![](shap_{key}.png)", "", "| feature | mean abs. SHAP |", "|---|---|"]
        lines += [f"| `{f}` | {v:.3f} |" for f, v in s.head(10).items()] + [""]
    (REPORTS / "lgbm_shap.md").write_text("\n".join(lines) + "\n")
    print(table(rows))
    for key, s in shap_tables.items():
        print(f"\n{key}: " + ", ".join(f"{f} {v:.2f}" for f, v in s.head(8).items()))


if __name__ == "__main__":
    main()
