"""Check 7 - subgroup robustness.

PROVENANCE. Phase 5, Task 1, "verify the effect is not carried by a small subset of
subjects". Dropping the best-performing decile moved MAE from 1.1124 to 1.2258 - the
model degraded rather than the effect vanishing, which is what a weak signal spread
across a cohort looks like, as opposed to a handful of lucky subjects.

ONE GENERALISATION, MADE DELIBERATELY. The raw Phase 5 number compares the model
before and after the drop, and on its own that comparison is unreadable: removing the
subjects the model does best on also removes the easiest subjects, so ANY model looks
worse afterwards, including a perfect one. What has to survive is the model's ADVANTAGE
over the baseline, recomputed on the same reduced set. This check therefore reports the
retained advantage fraction, and the Phase 5 result reproduces as a pass under it -
which it should, since Phase 5 read its own number that way in prose.

A per-subgroup breakdown by device, site and sex is reported alongside, because a model
that holds up overall while failing one device is a different object from one that
works everywhere, and Phase 2 of this project found exactly that asymmetry (lighting
cost 0.097 IoU, device only 0.035).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .contract import AuditInput
from .stats import grouped_cv_predict, mae
from .verdict import FAIL, PASS, CheckResult, Timer

CHECK_ID = "subgroup_robustness"
TITLE = "Subgroup robustness"
PROVENANCE = ("Phase 5 Task 1 - MAE 1.1124 -> 1.2258 after dropping the "
              "best-performing decile")


def run(inp: AuditInput, thresholds: dict | None = None, preregistered: bool = False,
        drop_fraction: float = 0.10, progress=None,
        cache: dict | None = None) -> CheckResult:
    th = {"min_retained_advantage_fraction": 0.5}
    th.update(thresholds or {})

    with Timer() as t:
        y = inp.y_true
        groups = inp.grouping
        subjects = inp.subject_id
        base = grouped_cv_predict(np.zeros((len(y), 0)), y, groups)

        err = np.abs(inp.y_pred - y)
        per_sub = pd.Series(err).groupby(pd.Series(subjects).values).mean()
        n_drop = max(1, int(round(len(per_sub) * drop_fraction)))
        best = set(per_sub.sort_values().index[:n_drop].tolist())
        keep = np.array([s not in best for s in subjects])

        adv_all = mae(base, y) - mae(inp.y_pred, y)
        adv_kept = (mae(base[keep], y[keep]) - mae(inp.y_pred[keep], y[keep])
                    if keep.any() else float("nan"))
        retained = float(adv_kept / adv_all) if adv_all > 0 else float("nan")

        subgroup_rows = []
        for col in ("device", "site", "sex"):
            if not inp.has(col):
                continue
            lab = inp.df[col].astype(str).to_numpy()
            for lev in sorted(pd.unique(lab)):
                m = lab == lev
                if m.sum() < 5:
                    continue
                subgroup_rows.append({
                    "variable": col, "level": lev, "n_rows": int(m.sum()),
                    "n_subjects": int(pd.unique(subjects[m]).size),
                    "model_mae": round(mae(inp.y_pred[m], y[m]), 4),
                    "baseline_mae": round(mae(base[m], y[m]), 4),
                    "advantage": round(mae(base[m], y[m]) - mae(inp.y_pred[m], y[m]), 4),
                })
        losing = [r for r in subgroup_rows if r["advantage"] <= 0]

        measured = {
            "n_subjects": int(len(per_sub)),
            "n_subjects_dropped": n_drop,
            "model_mae_all": round(mae(inp.y_pred, y), 4),
            "model_mae_after_dropping_best_decile": round(mae(inp.y_pred[keep],
                                                              y[keep]), 4),
            "baseline_mae_all": round(mae(base, y), 4),
            "baseline_mae_after_drop": round(mae(base[keep], y[keep]), 4),
            "advantage_all": round(adv_all, 4),
            "advantage_after_drop": round(float(adv_kept), 4),
            "retained_advantage_fraction": (None if not np.isfinite(retained)
                                            else round(retained, 3)),
            "n_subgroups_where_model_loses_to_baseline": len(losing),
        }
        details = {"subgroups": subgroup_rows,
                   "dropped_subjects": sorted(str(s) for s in list(best))[:25],
                   "note": ("the baseline is recomputed on the same reduced set, so the "
                            "comparison is of advantage, not of raw MAE")}

        need = float(th["min_retained_advantage_fraction"])
        # Same caveat as the baseline check: dropping a decile is a single resample, so
        # a retained fraction near the threshold is not a stable verdict. Measured on
        # clean inputs at 4 of 20 seeds; reported, not tuned away.
        measured["retained_fraction_is_near_the_threshold"] = bool(
            np.isfinite(retained) and abs(retained - need) < 0.15)
        edge = ("" if not measured["retained_fraction_is_near_the_threshold"] else
                f" The retained fraction sits within 0.15 of the {need} threshold, so "
                "this verdict is close to its boundary; the drop is a single resample "
                "and another draw could move it.")
        if adv_all <= 0:
            res = CheckResult(
                CHECK_ID, TITLE, FAIL,
                headline=(f"model MAE {mae(inp.y_pred, y):.4f} does not beat the "
                          f"population mean {mae(base, y):.4f}"),
                explanation=("There is no advantage to test the robustness of. A model "
                             "that does not beat predicting a constant cannot have that "
                             "advantage concentrated in a subset or spread across one."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
        elif retained >= need:
            res = CheckResult(
                CHECK_ID, TITLE, PASS,
                headline=(f"{retained:.0%} of the model's advantage survives dropping "
                          f"its best {n_drop} subjects"),
                explanation=(
                    "Removing the subjects the model does best on degrades it, but does "
                    "not remove its advantage over the baseline. That is the signature "
                    "of a weak effect spread across the cohort rather than a few lucky "
                    "subjects carrying a reported average."
                    + (f" Note the model loses to the baseline in "
                       f"{len(losing)} submitted subgroup(s): "
                       + ", ".join(f"{r['variable']}={r['level']}" for r in losing[:4])
                       + "." if losing else "") + edge),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
        else:
            res = CheckResult(
                CHECK_ID, TITLE, FAIL,
                headline=(f"only {retained:.0%} of the model's advantage survives "
                          f"dropping its best {n_drop} subjects"),
                explanation=(
                    "The model's advantage over the baseline is concentrated in a small "
                    "number of subjects: remove them and most of it goes. A headline "
                    "average computed over the full cohort is therefore not "
                    "representative of the cohort, and the reported score should be "
                    "accompanied by the per-subject distribution." + edge),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
    res.seconds = t.seconds
    return res
