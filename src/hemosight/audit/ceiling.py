"""Check 8 - ceiling analysis: can this signal contain the target at all?

PROVENANCE. Phase 4.5, Task 2 (scripts/phase4_5_ceiling.py, RESULTS LOG 2026-09-11).
"Our model failed" and "the signal is not present in this data" are different claims,
and only the second is worth writing down. Three model-independent measures separate
them:

  1. Mutual information between each feature and the target, against a null built by
     shuffling the target - which calibrates the scale, since MI of anything against
     anything is positive on finite samples. Phase 4.5 found 0 of 51 features above the
     null p95.
  2. Pearson and Spearman correlations with Benjamini-Hochberg FDR control. Phase 4.5
     found 4 features at raw p<0.05 against 2.6 expected by chance, and 0 surviving FDR.
  3. The submitted model's own score, placed against those, so a strong model on
     information-free features is visible as the contradiction it is.

VERDICT SEMANTICS ARE INVERTED HERE, deliberately. PASS means "this signal plausibly
contains the target" - features clear the null. FAIL means the features carry no
detectable information about the target, which is a finding about the data and not a
criticism of the model. The explanation says so, because a FAIL that reads as "your
model is bad" would misreport the strongest negative result this project produced.
"""

from __future__ import annotations

import numpy as np
from scipy import stats as sps

from .contract import AuditInput
from .stats import SEED, benjamini_hochberg, mae
from .verdict import FAIL, PASS, CheckResult, Timer, insufficient

CHECK_ID = "ceiling"
TITLE = "Ceiling analysis"
PROVENANCE = ("Phase 4.5 Task 2 - 0 of 51 features above the MI null, 0 surviving FDR "
              "(scripts/phase4_5_ceiling.py)")

MIN_FEATURES = 1
N_NULL_REPEATS = 5


def run(inp: AuditInput, thresholds: dict | None = None, preregistered: bool = False,
        progress=None, cache: dict | None = None) -> CheckResult:
    th = {"min_features_above_null": 1, "fdr_q": 0.05}
    th.update(thresholds or {})

    with Timer() as t:
        cols = inp.feature_columns
        if len(cols) < MIN_FEATURES:
            return insufficient(
                CHECK_ID, TITLE, PROVENANCE,
                missing=["feature columns"],
                explanation=(
                    "No feature columns were submitted, so there is nothing to measure "
                    "the information content of. The predictions alone cannot answer "
                    "this question: a prediction vector is a model's output, and the "
                    "point of a ceiling analysis is to ask what the INPUT could support "
                    "independently of any model. Add the model's input features as "
                    "numeric columns to enable it."))

        from sklearn.feature_selection import mutual_info_regression
        from sklearn.impute import SimpleImputer

        y = inp.y_true
        X = SimpleImputer(strategy="median").fit_transform(
            inp.df[cols].to_numpy(dtype=float))
        keep = np.array([np.std(X[:, j]) > 0 for j in range(X.shape[1])])
        dropped = [c for c, k in zip(cols, keep) if not k]
        X, cols = X[:, keep], [c for c, k in zip(cols, keep) if k]
        if not cols:
            return insufficient(
                CHECK_ID, TITLE, PROVENANCE, missing=["non-constant feature columns"],
                explanation="Every submitted feature column is constant.")

        if progress:
            progress(0.15, "mutual information")
        mi = mutual_info_regression(X, y, random_state=SEED)
        rng = np.random.default_rng(SEED)
        mi_null = np.concatenate([
            mutual_info_regression(X, rng.permutation(y), random_state=SEED + i)
            for i in range(N_NULL_REPEATS)])
        null_p95 = float(np.percentile(mi_null, 95))
        n_above = int((mi > null_p95).sum())

        if progress:
            progress(0.7, "correlations and FDR control")
        pear = np.array([sps.pearsonr(X[:, j], y)[:2] for j in range(X.shape[1])])
        spear = np.array([sps.spearmanr(X[:, j], y)[:2] for j in range(X.shape[1])])
        rej_p, adj_p = benjamini_hochberg(pear[:, 1], q=float(th["fdr_q"]))
        rej_s, _ = benjamini_hochberg(spear[:, 1], q=float(th["fdr_q"]))
        raw_hits = int((pear[:, 1] < 0.05).sum())
        expected = 0.05 * len(cols)

        order = np.argsort(-np.abs(pear[:, 0]))
        measured = {
            "n_features": len(cols),
            "max_mutual_information": round(float(mi.max()), 5),
            "mi_null_p95": round(null_p95, 5),
            "n_features_above_mi_null_p95": n_above,
            "n_raw_p_below_0.05": raw_hits,
            "expected_by_chance_at_0.05": round(expected, 1),
            "n_surviving_fdr_pearson": int(rej_p.sum()),
            "n_surviving_fdr_spearman": int(rej_s.sum()),
            "model_mae": round(mae(inp.y_pred, y), 4),
        }
        details = {
            "dropped_constant_columns": dropped,
            "top_features": [
                {"feature": cols[j], "mi": round(float(mi[j]), 5),
                 "pearson_r": round(float(pear[j, 0]), 4),
                 "p": round(float(pear[j, 1]), 5),
                 "p_fdr": round(float(adj_p[j]), 5),
                 "significant_fdr": bool(rej_p[j])}
                for j in order[:10]],
            "null_construction": (f"{N_NULL_REPEATS} shuffles of the target, MI "
                                  "recomputed each time"),
        }

        informative = (n_above >= int(th["min_features_above_null"])
                       or int(rej_p.sum()) > 0 or int(rej_s.sum()) > 0)
        if informative:
            res = CheckResult(
                CHECK_ID, TITLE, PASS,
                headline=(f"{n_above} of {len(cols)} features exceed the shuffled-target "
                          f"MI null, {int(rej_p.sum())} survive FDR at q="
                          f"{th['fdr_q']}"),
                explanation=(
                    "The submitted features carry detectable information about the "
                    "target independently of any model, so a model that finds signal in "
                    "them is not, on the face of it, finding noise. This bounds nothing "
                    "about how MUCH information is there, only that it is above the "
                    "null."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
        else:
            res = CheckResult(
                CHECK_ID, TITLE, FAIL,
                headline=(f"0 of {len(cols)} features exceed the shuffled-target MI "
                          f"null; {raw_hits} raw p<0.05 against {expected:.1f} expected "
                          "by chance, 0 surviving FDR"),
                explanation=(
                    "No submitted feature carries detectable information about the "
                    "target. This is a statement about the DATA, not about the model: "
                    "it licenses the stronger claim that the signal is absent from this "
                    "representation rather than that one model failed to find it. If "
                    "the submitted model nevertheless reports skill, the two results "
                    "contradict each other and the discrepancy has to be explained - "
                    "leakage is the usual explanation. Phase 4.5 of this project "
                    "reached this verdict on its own hand-engineered features and "
                    "reported it as its firmest negative finding."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
    res.seconds = t.seconds
    return res
