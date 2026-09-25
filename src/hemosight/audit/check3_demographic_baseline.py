"""Check 3 - demographic baseline comparison.

PROVENANCE. Phase 4, Task 3 (scripts/ppg_hb_estimation_gate_phase4.py, DECISION LOG 2026-09-11 "TASK 3
decided the phase: the best predictor of Hb is SEX"). On identical folds: population
mean MAE 1.175 g/dL, four-wavelength PPG 1.190, and SEX ALONE 0.831. A "PPG +
demographics" model scored 0.824 - inside the pre-declared viable band - and reported
without the baseline would have looked like a working PPG haemoglobin estimator. It
was a sex classifier with a PPG-shaped decoration attached.

The project's own literature survey found 0 of 5 applicable sources reporting a
demographic baseline at all. This check makes that omission impossible to repeat: it
fits the population mean, EACH demographic variable alone, and all of them together,
on whole-subject folds, and puts the submitted model's own score next to them.

The estimator is deliberately the weak one Phase 4 used - median imputation,
standardisation, RidgeCV - so a submitted model is judged against the baseline this
project actually measured, not against a strawman tuned to lose.
"""

from __future__ import annotations

import numpy as np

from .contract import AuditInput, encode_design
from .stats import grouped_cv_predict, mae, r2
from .verdict import FAIL, PASS, CheckResult, Timer, insufficient

CHECK_ID = "demographic_baseline"
TITLE = "Demographic baseline comparison"
PROVENANCE = ("Phase 4 Task 3 - sex alone beat the PPG model by 30% "
              "(scripts/ppg_hb_estimation_gate_phase4.py, RESULTS LOG 2026-09-11)")


def run(inp: AuditInput, thresholds: dict | None = None,
        preregistered: bool = False, progress=None,
        cache: dict | None = None) -> CheckResult:
    th = {"model_must_beat_best_demographic_by": 0.0}
    th.update(thresholds or {})

    with Timer() as t:
        demos = inp.demographics
        if not demos:
            return insufficient(
                CHECK_ID, TITLE, PROVENANCE,
                missing=["at least one of age, sex, device, site"],
                explanation=(
                    "No demographic or provenance variable was submitted, so the "
                    "comparison that decided Phase 4 of this project cannot be made. "
                    "The population-mean baseline below is reported for reference, but "
                    "the question this check exists to answer - does a single "
                    "demographic variable match the model - is unanswerable and is not "
                    "guessed at."),
            )

        y = inp.y_true
        groups = inp.grouping
        model_mae = mae(inp.y_pred, y)

        rows = []
        pred_mean = grouped_cv_predict(np.zeros((len(y), 0)), y, groups)
        rows.append({"name": "population mean", "variables": [],
                     "mae": mae(pred_mean, y), "r2": r2(y, pred_mean)})

        if progress:
            progress(0.2, "fitting single-variable baselines")
        for i, c in enumerate(demos):
            X, _ = encode_design(inp.df, [c])
            p = grouped_cv_predict(X, y, groups)
            rows.append({"name": f"{c} alone", "variables": [c],
                         "mae": mae(p, y), "r2": r2(y, p)})
            if progress:
                progress(0.2 + 0.5 * (i + 1) / len(demos), f"baseline: {c}")

        if len(demos) > 1:
            X, names = encode_design(inp.df, demos)
            p = grouped_cv_predict(X, y, groups)
            rows.append({"name": "all demographics", "variables": list(demos),
                         "mae": mae(p, y), "r2": r2(y, p)})

        singles = [r for r in rows if len(r["variables"]) == 1]
        best_single = min(singles, key=lambda r: r["mae"]) if singles else None
        best_any = min(rows, key=lambda r: r["mae"])
        margin = (best_single["mae"] - model_mae) if best_single else float("nan")

        measured = {
            "model_mae": round(model_mae, 4),
            "model_r2": round(r2(y, inp.y_pred), 4),
            "population_mean_mae": round(rows[0]["mae"], 4),
            "best_single_demographic": best_single["name"] if best_single else None,
            "best_single_demographic_mae": (round(best_single["mae"], 4)
                                            if best_single else None),
            "model_advantage_over_best_single": round(margin, 4),
            "best_baseline_overall": best_any["name"],
        }
        details = {"baselines": [{**r, "mae": round(r["mae"], 4),
                                  "r2": round(r["r2"], 4)} for r in rows],
                   "estimator": "median impute -> standardise -> RidgeCV, whole-subject "
                                "10-fold, the Phase 4 Gate B construction"}

        need = float(th["model_must_beat_best_demographic_by"])
        beaten = best_single is not None and margin <= need

        # This is a comparison of two point estimates with no interval attached, so a
        # margin much smaller than the spread of the target is not a stable verdict.
        # It is called out rather than smoothed over: the clean-input replicates in
        # scripts/validate_audit_harness_phase6.py flipped this check on 2 of 20 seeds, and
        # the honest reading is that those inputs were borderline, not that the tool
        # was wrong.
        narrow = abs(margin) < 0.05 * float(np.std(y))
        caveat = ("" if not narrow else
                  f" The margin ({margin:+.4f}) is small against the spread of the "
                  f"target (SD {np.std(y):.4f}), so this verdict is close to its "
                  "boundary and would be worth re-running on another split before "
                  "being relied on.")
        measured["margin_is_narrow"] = bool(narrow)

        if beaten:
            res = CheckResult(
                CHECK_ID, TITLE, FAIL,
                headline=(f"{best_single['name']} reaches MAE "
                          f"{best_single['mae']:.4f} against the model's "
                          f"{model_mae:.4f}"),
                explanation=(
                    "A single demographic variable matches or beats the submitted "
                    "model. Whatever the model measures, it is not adding information "
                    "beyond a variable that can be collected by asking one question. "
                    "Phase 4 of this project hit exactly this: a model inside the "
                    "pre-declared viable band was a sex classifier, and the finding was "
                    "only visible because the baseline was run on identical folds."
                    + caveat),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
        else:
            res = CheckResult(
                CHECK_ID, TITLE, PASS,
                headline=(f"model MAE {model_mae:.4f} beats the best single "
                          f"demographic ({best_single['name']}, "
                          f"{best_single['mae']:.4f}) by {margin:.4f}"),
                explanation=(
                    "The model carries information no single submitted demographic "
                    "variable carries. Note what this does and does not establish: it "
                    "is a comparison against the variables supplied, so an unsubmitted "
                    "confounder is untested, and beating a baseline is not the same as "
                    "being clinically useful." + caveat),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
    res.seconds = t.seconds
    return res
