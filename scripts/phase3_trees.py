"""Phase 3, first pass: shallow decision trees for CM vs not CM among graphs failing OCC.

Usage: .venv/bin/python scripts/phase3_trees.py > reports/phase3_trees.txt
"""
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, balanced_accuracy_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from toric_graphs.db import DEFAULT_DB  # noqa: E402

SEED = 0
EXCLUDE = {"graph6", "n", "adj_spectrum", "lap_spectrum"}


def load() -> tuple[pd.DataFrame, list[str]]:
    with sqlite3.connect(DEFAULT_DB) as c:
        d = pd.read_sql("""SELECT g.graph_number, r.is_cm, f.* FROM graphs g
                           JOIN m2_results r USING (graph6) JOIN features f USING (graph6)
                           WHERE g.fails_occ = 1""", c)
    feats = [c for c in d.columns if c not in EXCLUDE | {"graph_number", "is_cm"}
             and pd.api.types.is_numeric_dtype(d[c]) and d[c].nunique() > 1]
    d[feats] = d[feats].fillna(-1)  # e.g. even_girth when there is no even cycle
    return d, feats


def rules(tree: DecisionTreeClassifier, X: pd.DataFrame, y: pd.Series) -> str:
    """Tree as indented rules with the true CM / not-CM counts in every node."""
    t, leaf_of = tree.tree_, tree.apply(X)
    path = tree.decision_path(X)
    out = []

    def counts(node: int) -> str:
        mask = path[:, node].toarray().ravel().astype(bool)
        c = Counter(y[mask])
        return f"[CM {c.get(1, 0)}, not CM {c.get(0, 0)}]"

    def walk(node: int, depth: int) -> None:
        pad = "    " * depth
        if t.children_left[node] == -1:
            mask = leaf_of == node
            c = Counter(y[mask])
            verdict = "CM" if c.get(1, 0) > c.get(0, 0) else "not CM"
            out.append(f"{pad}→ predict {verdict}  {counts(node)}")
            return
        f, thr = X.columns[t.feature[node]], t.threshold[node]
        out.append(f"{pad}if {f} <= {thr:g}:  {counts(t.children_left[node])}")
        walk(t.children_left[node], depth + 1)
        out.append(f"{pad}else ({f} > {thr:g}):  {counts(t.children_right[node])}")
        walk(t.children_right[node], depth + 1)

    walk(0, 0)
    return "\n".join(out)


def cv_scores(X: pd.DataFrame, y: pd.Series, depth: int) -> tuple[float, float, float, float]:
    """Repeated stratified 5-fold CV: balanced accuracy and PR-AUC (positive class = CM)."""
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=20, random_state=SEED)
    bal, ap = [], []
    for tr, te in cv.split(X, y):
        m = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=3, class_weight="balanced",
                                   random_state=SEED).fit(X.iloc[tr], y.iloc[tr])
        bal.append(balanced_accuracy_score(y.iloc[te], m.predict(X.iloc[te])))
        ap.append(average_precision_score(y.iloc[te], m.predict_proba(X.iloc[te])[:, 1]))
    return float(np.mean(bal)), float(np.std(bal)), float(np.mean(ap)), float(np.std(ap))


def single_feature_splits(X: pd.DataFrame, y: pd.Series, top: int = 12) -> pd.DataFrame:
    """Best one-threshold rule per feature, ranked by training balanced accuracy."""
    rows = []
    for f in X.columns:
        m = DecisionTreeClassifier(max_depth=1, class_weight="balanced", random_state=SEED).fit(X[[f]], y)
        if m.tree_.node_count < 3:
            continue
        thr = m.tree_.threshold[0]
        left = y[X[f] <= thr]
        right = y[X[f] > thr]
        rows.append({"feature": f, "rule": f"<= {thr:g}",
                     "left (CM/notCM)": f"{(left == 1).sum()}/{(left == 0).sum()}",
                     "right (CM/notCM)": f"{(right == 1).sum()}/{(right == 0).sum()}",
                     "bal_acc": balanced_accuracy_score(y, m.predict(X[[f]]))})
    return pd.DataFrame(rows).sort_values("bal_acc", ascending=False).head(top)


def root_stability(X: pd.DataFrame, y: pd.Series, depth: int = 2, reps: int = 300) -> Counter:
    rng = np.random.default_rng(SEED)
    roots = Counter()
    for _ in range(reps):
        idx = rng.choice(len(X), len(X), replace=True)
        m = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=3, class_weight="balanced",
                                   random_state=SEED).fit(X.iloc[idx], y.iloc[idx])
        roots[X.columns[m.tree_.feature[0]]] += 1
    return roots


def section(title: str) -> None:
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


def main() -> None:
    d, feats = load()
    d8, d7 = d[d.n == 8], d[d.n == 7]
    X, y = d8[feats].reset_index(drop=True), d8.is_cm.reset_index(drop=True)
    print(f"Graphs failing OCC: n=8: {len(d8)} (CM {int(y.sum())}, not CM {int((y == 0).sum())}); "
          f"n=7: {len(d7)} (CM {int(d7.is_cm.sum())})")
    print(f"Features used: {len(feats)} (graph-only; no Macaulay2 output)")
    print(f"PR-AUC baseline (random guessing) = share of CM = {y.mean():.3f}")

    section("A. All 161 failing graphs at n = 8: cross-validated scores by tree depth")
    print("depth | balanced accuracy (mean ± sd) | PR-AUC for CM (mean ± sd)")
    for depth in (1, 2, 3):
        b, bs, a, as_ = cv_scores(X, y, depth)
        print(f"  {depth}   |        {b:.3f} ± {bs:.3f}          |      {a:.3f} ± {as_:.3f}")

    for depth in (1, 2, 3):
        section(f"B{depth}. Depth-{depth} tree fit on all 161 (rules with true counts)")
        m = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=3, class_weight="balanced",
                                   random_state=SEED).fit(X, y)
        print(rules(m, X, y))
        if len(d7):
            p7 = m.predict(d7[feats])
            print(f"\n  applied to the {len(d7)} failing n=7 graphs (all CM): {int(p7.sum())} predicted CM")

    section("C. Best single-feature rules on all 161")
    print(single_feature_splits(X, y).to_string(index=False))

    section("D. Root-split stability: depth-2 trees on 300 bootstrap resamples of the 161")
    for f, k in root_stability(X, y).most_common(8):
        print(f"  {f:35s} {k / 300:6.1%}")

    sub = d8[d8.sep_same_block_pairs == 0]
    Xs, ys = sub[feats].reset_index(drop=True), sub.is_cm.reset_index(drop=True)
    section(f"E. The {len(sub)} cut-vertex-linked graphs (C3 does not apply): CM {int(ys.sum())} "
            f"vs not CM {int((ys == 0).sum())}")
    print("depth | balanced accuracy | PR-AUC for CM   (baseline PR-AUC = %.3f)" % ys.mean())
    for depth in (1, 2):
        b, bs, a, as_ = cv_scores(Xs, ys, depth)
        print(f"  {depth}   |  {b:.3f} ± {bs:.3f}  |  {a:.3f} ± {as_:.3f}")
    m = DecisionTreeClassifier(max_depth=2, min_samples_leaf=3, class_weight="balanced",
                               random_state=SEED).fit(Xs, ys)
    print("\nDepth-2 tree:")
    print(rules(m, Xs, ys))
    print("\nBest single-feature rules:")
    print(single_feature_splits(Xs, ys).to_string(index=False))
    print("\nRoot-split stability (depth 2, 300 bootstraps):")
    for f, k in root_stability(Xs, ys).most_common(8):
        print(f"  {f:35s} {k / 300:6.1%}")
    print("\nNot-CM graph numbers in this group:",
          sorted(int(x) for x in sub[sub.is_cm == 0].graph_number))


if __name__ == "__main__":
    main()
