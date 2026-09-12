"""Phase 4.5, TASK 2: how much Hb information can this signal contain at all?

"Our model failed" and "the signal is not present in this data" are different claims.
This phase makes the second one available if it is warranted, using three
model-independent measures:

  1. Mutual information between each feature and Hb - catches non-linear dependence a
     correlation would miss.
  2. Ranked Pearson and Spearman correlations with Benjamini-Hochberg FDR correction -
     with ~60 features, some will correlate at p<0.05 by chance alone.
  3. A permutation test - shuffle Hb across subjects, refit, and build the null
     distribution of MAE. This establishes numerically what "no signal" looks like, so
     the real result can be compared against chance rather than against intuition.

    .\\.venv\\Scripts\\python.exe scripts\\phase4_5_ceiling.py [--perms 500]
"""

from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from scipy import stats as sps
from sklearn.feature_selection import mutual_info_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from hemosight.audit.stats import benjamini_hochberg
from hemosight.io import paths

OUT = paths.INTERIM / "phase4_5"
SEED = 20260911
N_SPLITS = 10


# benjamini_hochberg() now lives in hemosight.audit.stats and is imported above.
# It is the same function, re-homed so the audit harness and this script cannot
# drift apart - the reason scripts/phase5_harden.py imports its CV driver from
# hemosight.ppg.cv. See reports/phase6_audit_harness.md.


def cv_mae(X, y, seed=SEED):
    kf = KFold(N_SPLITS, shuffle=True, random_state=seed)
    pred = np.full(len(y), np.nan)
    for tr, te in kf.split(X):
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          RidgeCV(alphas=np.logspace(-3, 3, 25)))
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return float(np.mean(np.abs(pred - y))), pred


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=500)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    d = pd.read_csv(paths.INTERIM / "phase4" / "features.csv")
    d = d[np.isfinite(d.hb_g_dl)].reset_index(drop=True)
    y = d.hb_g_dl.to_numpy()
    drop = {"subject_id", "hb_g_dl"}
    ppg_cols = [c for c in d.columns
                if c not in drop and c not in ("age", "sex", "height", "weight", "siglen",
                                               "n_samples")]
    X = d[ppg_cols].to_numpy(dtype=float)
    X = SimpleImputer(strategy="median").fit_transform(X)
    print(f"{len(d)} subjects, {len(ppg_cols)} PPG features, "
          f"Hb SD {y.std():.3f} g/dL")

    res: dict = {"n_subjects": int(len(d)), "n_features": len(ppg_cols)}

    # ---------------------------------------------------- 1. mutual information
    mi = mutual_info_regression(X, y, random_state=SEED)
    # Null: MI of the same features against shuffled Hb, to calibrate the scale.
    rng = np.random.default_rng(SEED)
    mi_null = np.concatenate([
        mutual_info_regression(X, rng.permutation(y), random_state=SEED + i)
        for i in range(5)])
    res["mutual_information"] = {
        "max": float(mi.max()), "mean": float(mi.mean()),
        "null_mean": float(mi_null.mean()), "null_p95": float(np.percentile(mi_null, 95)),
        "n_above_null_p95": int((mi > np.percentile(mi_null, 95)).sum()),
        "top": [{"feature": ppg_cols[i], "mi": float(mi[i])}
                for i in np.argsort(mi)[::-1][:8]],
    }
    print("\n=== mutual information with Hb ===")
    print(f"  max MI = {mi.max():.4f}   mean = {mi.mean():.4f}")
    print(f"  null (shuffled Hb): mean {mi_null.mean():.4f}, p95 "
          f"{np.percentile(mi_null, 95):.4f}")
    print(f"  features above the null p95: "
          f"{int((mi > np.percentile(mi_null, 95)).sum())} of {len(ppg_cols)}")
    for e in res["mutual_information"]["top"][:5]:
        print(f"    {e['feature']:26s} MI={e['mi']:.4f}")

    # ---------------------------------------- 2. correlations with FDR control
    pear = np.array([sps.pearsonr(X[:, i], y) for i in range(X.shape[1])])
    spear = np.array([sps.spearmanr(X[:, i], y)[:2] for i in range(X.shape[1])])
    rej_p, adj_p = benjamini_hochberg(pear[:, 1])
    rej_s, adj_s = benjamini_hochberg(spear[:, 1])
    order = np.argsort(-np.abs(pear[:, 0]))
    res["correlations"] = {
        "n_significant_pearson_fdr": int(rej_p.sum()),
        "n_significant_spearman_fdr": int(rej_s.sum()),
        "n_raw_p_below_05": int((pear[:, 1] < 0.05).sum()),
        "expected_false_positives_at_05": float(0.05 * len(ppg_cols)),
        "top": [{"feature": ppg_cols[i], "pearson_r": float(pear[i, 0]),
                 "p": float(pear[i, 1]), "p_fdr": float(adj_p[i]),
                 "significant_fdr": bool(rej_p[i])} for i in order[:10]],
    }
    print("\n=== correlations, Benjamini-Hochberg FDR at q=0.05 ===")
    print(f"  raw p<0.05: {int((pear[:,1]<0.05).sum())} features "
          f"(expected by chance alone: {0.05*len(ppg_cols):.1f})")
    print(f"  surviving FDR: Pearson {int(rej_p.sum())}, Spearman {int(rej_s.sum())}")
    print(f"  {'feature':26s} {'r':>7s} {'p':>9s} {'p(FDR)':>9s}  sig?")
    for e in res["correlations"]["top"][:8]:
        print(f"  {e['feature']:26s} {e['pearson_r']:+7.3f} {e['p']:9.4f} "
              f"{e['p_fdr']:9.4f}  {'YES' if e['significant_fdr'] else 'no'}")

    # ------------------------------------------------------ 3. permutation test
    print(f"\n=== permutation test ({args.perms} permutations) ===")
    real_mae, _ = cv_mae(X, y)
    null = np.empty(args.perms)
    rng = np.random.default_rng(SEED)
    for i in range(args.perms):
        if i % 100 == 0:
            print(f"  {i}/{args.perms}", end="\r", flush=True)
        null[i], _ = cv_mae(X, rng.permutation(y))
    p_val = float((null <= real_mae).mean())
    mean_mae = float(np.mean(np.abs(y - y.mean())))
    res["permutation"] = {
        "real_mae": real_mae, "null_mean": float(null.mean()),
        "null_sd": float(null.std()), "null_p05": float(np.percentile(null, 5)),
        "p_value": p_val, "population_mean_mae": mean_mae,
        "z_score": float((real_mae - null.mean()) / max(null.std(), 1e-12)),
    }
    print(f"\n  real PPG model MAE        : {real_mae:.4f} g/dL")
    print(f"  null distribution (shuffled Hb): mean {null.mean():.4f} "
          f"SD {null.std():.4f}  5th pct {np.percentile(null,5):.4f}")
    print(f"  permutation p-value       : {p_val:.4f}")
    print(f"  z vs null                 : "
          f"{(real_mae-null.mean())/max(null.std(),1e-12):+.2f}")
    print(f"  population-mean MAE       : {mean_mae:.4f}")

    distinguishable = p_val < 0.05
    res["distinguishable_from_chance"] = bool(distinguishable)
    res["conclusion"] = (
        "The PPG feature model is NOT distinguishable from a model trained on randomly "
        "shuffled haemoglobin labels. This supports the stronger claim: the signal is "
        "not present in these features, rather than merely that one model failed."
        if not distinguishable else
        "The model is distinguishable from chance, though the effect may still be too "
        "small to be useful.")
    print(f"\n  => distinguishable from chance? {distinguishable}")
    print(f"  {res['conclusion']}")

    (OUT / "ceiling.json").write_text(json.dumps(res, indent=2, default=float),
                                      encoding="utf-8")
    print(f"\nresults -> {OUT / 'ceiling.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
