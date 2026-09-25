"""Shared statistics for the audit checks.

Everything here was lifted from a Phase 1-5 script rather than written fresh, so the
harness measures what this project measured. Provenance is named per function.
`scripts/ppg_ceiling_analysis_phase4_5.py` imports benjamini_hochberg() from this module for the
same reason `scripts/permutation_hardening_phase5.py` imports its CV driver from `hemosight.ppg.cv`:
two copies of a statistical routine drift, and the drift is invisible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEED = 20260911          # the project's frozen seed (configs/phase1_splits.yaml)
N_SPLITS = 10


def mae(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(a, float) - np.asarray(b, float))))


def r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, float)
    y_pred = np.asarray(y_pred, float)
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    return float("nan") if ss_tot == 0 else 1.0 - ss_res / ss_tot


def benjamini_hochberg(p: np.ndarray, q: float = 0.05):
    """Return (rejected, adjusted p) under BH FDR control.

    Provenance: Phase 4.5 ceiling analysis (scripts/ppg_ceiling_analysis_phase4_5.py), where 4 of
    51 features cleared raw p<0.05 against 2.6 expected by chance and none survived
    this correction.
    """
    p = np.asarray(p, dtype=float)
    n = len(p)
    if n == 0:
        return np.zeros(0, dtype=bool), np.zeros(0)
    order = np.argsort(p)
    ranked = p[order]
    adj = ranked * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(adj, 0, 1)
    return out <= q, out


def empirical_p(null_draws: np.ndarray, real: float) -> dict:
    """The empirical p of a lower-is-better statistic, with its floor stated.

    Provenance: Phase 5 Task 1. p = (k+1)/(n+1) cannot go below 1/(n+1), so at n=60
    with zero draws at or below the real value the reported 0.0164 was the smallest
    number the sample size allowed - a BOUND, not a measurement. Extending that run
    to n=240 moved the figure to 0.0041 and it was STILL the floor. Any caller that
    prints p without at_floor is reproducing the error this project logged.
    """
    d = np.asarray(null_draws, dtype=float)
    n = len(d)
    if n == 0:
        return {"n": 0, "p_empirical": None, "p_floor": None, "at_floor": None}
    k = int(np.sum(d <= real))
    sd = float(d.std())
    return {
        "n": n,
        "null_mean": float(d.mean()),
        "null_sd": sd,
        "null_min": float(d.min()),
        "real": float(real),
        "n_at_or_below_real": k,
        "p_empirical": float((k + 1) / (n + 1)),
        "p_floor": float(1 / (n + 1)),
        "at_floor": k == 0,
        "z_parametric": (float((real - d.mean()) / max(sd, 1e-12)) if n > 1 else None),
    }


def group_kfold_indices(groups: np.ndarray, n_splits: int = N_SPLITS,
                        seed: int = SEED):
    """Whole-group folds. Groups are shuffled once, then dealt round-robin.

    Provenance: hemosight.io.splits.kfold_by_group, the Phase 1 construction. A group
    never spans a fold boundary, which is the property every number downstream rests
    on.
    """
    groups = np.asarray(groups)
    uniq = pd.unique(groups)
    rng = np.random.default_rng(seed)
    order = np.array(uniq, dtype=object)
    rng.shuffle(order)
    fold_of = {g: i % n_splits for i, g in enumerate(order)}
    fold = np.array([fold_of[g] for g in groups])
    for k in range(min(n_splits, len(uniq))):
        te = np.flatnonzero(fold == k)
        tr = np.flatnonzero(fold != k)
        if len(te) and len(tr):
            yield tr, te


def grouped_cv_predict(X: np.ndarray, y: np.ndarray, groups: np.ndarray,
                       n_splits: int = N_SPLITS, seed: int = SEED) -> np.ndarray:
    """Out-of-fold ridge predictions under whole-group folds.

    Provenance: the baseline estimator of Phase 4 Gate B (scripts/ppg_hb_estimation_gate_phase4.py) -
    median imputation, standardisation, RidgeCV over logspace(-3, 3, 25). It is
    deliberately the same weak, well-regularised learner that produced the sex-alone
    MAE of 0.831 g/dL, so a submitted model is compared against the baseline this
    project actually measured rather than a stronger one invented here.

    With no features at all (X of width 0) this is the population mean: the train
    fold's mean, predicted for the held-out fold.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    pred = np.full(len(y), np.nan)

    if X.shape[1] == 0:
        for tr, te in group_kfold_indices(groups, n_splits, seed):
            pred[te] = y[tr].mean()
        return pred

    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import RidgeCV
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    for tr, te in group_kfold_indices(groups, n_splits, seed):
        model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                              RidgeCV(alphas=np.logspace(-3, 3, 25)))
        model.fit(X[tr], y[tr])
        pred[te] = model.predict(X[te])
    # A group larger than n_splits folds can leave a row unpredicted only if a fold
    # came out empty; fall back to the global mean rather than silently dropping it.
    if np.isnan(pred).any():
        pred[np.isnan(pred)] = y.mean()
    return pred


def subject_level(values: np.ndarray, subjects: np.ndarray) -> tuple[np.ndarray,
                                                                    np.ndarray]:
    """Collapse row-level values to one per subject by mean.

    Several checks are about subjects, not rows: a subject contributing 40 windows
    would otherwise count 40 times and make every interval look tighter than it is.
    """
    s = pd.Series(np.asarray(values, dtype=float))
    g = s.groupby(pd.Series(np.asarray(subjects)).values).mean()
    return g.index.to_numpy(), g.to_numpy()
