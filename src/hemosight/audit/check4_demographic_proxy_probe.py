"""Check 4 - demographic proxy probe.

PROVENANCE. Phase 4 Task 3 and Phase 4.5 Task 1 (DECISION LOG 2026-09-11, "the best
predictor of Hb is SEX" and "Memorisation was measured, not assumed"). Two measurements
that catch different halves of the same failure:

  1. INCREMENTAL VALUE. Phase 4 found a PPG+demographics model at MAE 0.824 against
     demographics alone at 0.831 - a difference the phase called noise. The model's
     apparent skill was almost entirely the demographic. This check computes the same
     comparison generically: how much of the model's advantage over the population mean
     survives once the demographic variable is already in the model.

  2. REPRESENTATION PROBE. Phase 4.5 ran a sex probe on each learned representation
     BEFORE accepting any result, because Phase 4 had shown how easily an apparent
     haemoglobin model is really a sex classifier. Those probes came back at 43.6-52.3%
     against a 57.0% base rate - below chance, therefore clean. This check runs the same
     probe on whatever is available: a supplied representation matrix, or failing that
     the prediction vector itself, which is the one representation every submission has.

A model can pass check 3 and fail this one. Beating a demographic baseline says the
model adds something; this says whether what it adds is the demographic in disguise.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .contract import AuditInput, encode_design
from .stats import grouped_cv_predict, group_kfold_indices, mae
from .verdict import FAIL, PASS, CheckResult, Timer, insufficient

CHECK_ID = "proxy_probe"
TITLE = "Demographic proxy probe"
PROVENANCE = ("Phase 4 Task 3 (PPG+demographics 0.824 vs demographics 0.831) and "
              "Phase 4.5 sex probe (DECISION LOG 2026-09-11)")


def _probe(X: np.ndarray, labels: np.ndarray, groups: np.ndarray) -> dict:
    """Out-of-fold accuracy of recovering a categorical variable from X.

    Logistic regression on whole-subject folds, against the majority-class base rate.
    A probe above its base rate means the representation carries the variable.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler

    lab = pd.Series(labels).astype(str).to_numpy()
    base = float(pd.Series(lab).value_counts(normalize=True).max())
    if pd.unique(lab).size < 2:
        return {"accuracy": None, "base_rate": base, "n_classes": 1}

    pred = np.array([None] * len(lab), dtype=object)
    for tr, te in group_kfold_indices(groups):
        if pd.unique(lab[tr]).size < 2:
            continue
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          LogisticRegression(max_iter=2000))
        m.fit(X[tr], lab[tr])
        pred[te] = m.predict(X[te])
    ok = pred != None            # noqa: E711 - object array, `is not None` is elementwise-wrong
    if not ok.any():
        return {"accuracy": None, "base_rate": base,
                "n_classes": int(pd.unique(lab).size)}
    acc = float(np.mean(pred[ok] == lab[ok]))
    return {"accuracy": acc, "base_rate": base, "margin": acc - base,
            "n_classes": int(pd.unique(lab).size), "n_scored": int(ok.sum())}


def run(inp: AuditInput, thresholds: dict | None = None,
        preregistered: bool = False, representation: np.ndarray | None = None,
        progress=None, cache: dict | None = None) -> CheckResult:
    th = {"max_skill_explained_by_demographic": 0.75, "max_probe_margin": 0.10}
    th.update(thresholds or {})

    with Timer() as t:
        demos = inp.demographics
        if not demos:
            return insufficient(
                CHECK_ID, TITLE, PROVENANCE,
                missing=["at least one of age, sex, device, site"],
                explanation=("There is no demographic variable to probe for. Whether "
                             "the model's skill is a demographic in disguise cannot be "
                             "tested, and no verdict is inferred."))

        y = inp.y_true
        groups = inp.grouping
        model_mae = mae(inp.y_pred, y)
        mean_mae = mae(grouped_cv_predict(np.zeros((len(y), 0)), y, groups), y)
        raw_advantage = mean_mae - model_mae

        if raw_advantage <= 0:
            return insufficient(
                CHECK_ID, TITLE, PROVENANCE,
                missing=["a model advantage to decompose"],
                explanation=(
                    f"The model (MAE {model_mae:.4f}) does not beat the population mean "
                    f"(MAE {mean_mae:.4f}), so there is no apparent skill for a "
                    "demographic variable to account for. This is not a pass: the "
                    "question is unanswerable because its premise does not hold."))

        per_var = {}
        for i, c in enumerate(demos):
            Xd, _ = encode_design(inp.df, [c])
            mae_d = mae(grouped_cv_predict(Xd, y, groups), y)
            Xdp = np.hstack([Xd, inp.y_pred[:, None]])
            mae_dp = mae(grouped_cv_predict(Xdp, y, groups), y)
            incremental = mae_d - mae_dp
            explained = float(np.clip(1.0 - incremental / raw_advantage, 0.0, 1.0))

            probe_source = "supplied representation" if representation is not None \
                else "prediction vector"
            Xp = (np.asarray(representation, dtype=float) if representation is not None
                  else inp.y_pred[:, None])
            probe = _probe(Xp, inp.df[c].to_numpy(), groups) if c != "age" else None

            per_var[c] = {
                "demographic_alone_mae": round(mae_d, 4),
                "demographic_plus_model_mae": round(mae_dp, 4),
                "incremental_value_of_model": round(incremental, 4),
                "skill_explained_by_this_demographic": round(explained, 4),
                "probe": probe, "probe_source": probe_source,
            }
            if progress:
                progress(0.2 + 0.7 * (i + 1) / len(demos), f"probing {c}")

        worst = max(per_var, key=lambda c:
                    per_var[c]["skill_explained_by_this_demographic"])
        worst_explained = per_var[worst]["skill_explained_by_this_demographic"]

        # The probe only counts against a model when it ran on a SUPPLIED
        # representation, which is the Phase 4.5 construction. Probing the prediction
        # vector instead is still reported, but it cannot be a finding on its own: a
        # model legitimately given sex as an input will of course encode sex in its
        # output, and calling that a proxy would flag correct models. The clean
        # replicates in scripts/validate_audit_harness_phase6.py failed 2 of 5 on exactly
        # that mistake before this distinction was drawn.
        probe_is_evidence = representation is not None
        probe_hits = [(c, v["probe"]) for c, v in per_var.items()
                      if probe_is_evidence and v["probe"]
                      and v["probe"].get("margin") is not None
                      and v["probe"]["margin"] >= th["max_probe_margin"]]

        measured = {
            "model_mae": round(model_mae, 4),
            "population_mean_mae": round(mean_mae, 4),
            "model_advantage_over_mean": round(raw_advantage, 4),
            "worst_demographic": worst,
            "skill_explained_by_worst_demographic": round(worst_explained, 4),
            "n_probes_above_base_rate": len(probe_hits),
            "probe_ran_on": ("a supplied representation" if representation is not None
                             else "the prediction vector (reported, not a finding)"),
        }
        details = {"per_variable": per_var,
                   "method": ("advantage over the population mean, versus the "
                              "advantage still present once the demographic is already "
                              "in the model - the Phase 4 Task 3 comparison")}

        reasons = []
        if worst_explained >= th["max_skill_explained_by_demographic"]:
            reasons.append(f"{worst} accounts for {worst_explained:.0%} of the model's "
                           "advantage over the population mean")
        for c, p in probe_hits:
            reasons.append(f"{c} is recoverable from the model's own output at "
                           f"{p['accuracy']:.1%} against a {p['base_rate']:.1%} base "
                           "rate")

        if reasons:
            res = CheckResult(
                CHECK_ID, TITLE, FAIL,
                headline="; ".join(reasons),
                explanation=(
                    "Most of what looks like model skill is a demographic variable. "
                    "The model can still be reported, but not as evidence that the "
                    "measured signal carries the target: Phase 4 of this project "
                    "reported exactly such a model at MAE 0.824, inside its viable "
                    "band, and it was a sex classifier. A submitted score that survives "
                    "the baseline comparison but fails here is the specific failure "
                    "this project was built to make visible."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
        else:
            res = CheckResult(
                CHECK_ID, TITLE, PASS,
                headline=(f"at most {worst_explained:.0%} of the model's advantage is "
                          f"explained by any submitted demographic ({worst})"),
                explanation=(
                    "The model's advantage survives having the demographic variables "
                    "already in the model, and its output does not recover them above "
                    "their base rate. What it measures is not one of the submitted "
                    "demographics. An unsubmitted confounder is, of course, untested - "
                    "Phase 4.5 recorded the same caveat about its own clean sex probe."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
    res.seconds = t.seconds
    return res
