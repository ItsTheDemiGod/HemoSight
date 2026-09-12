"""Check 6 - seed stability.

PROVENANCE. Phase 5, Task 1 (DECISION LOG 2026-09-11). The rule declared before the
run was: "if seed spread is comparable to the real-vs-null gap, the finding does not
survive". Ten seeds of the selected model gave SD 0.0069 g/dL over a range of
1.1069-1.1279, against a real-vs-null gap of 0.0815 - a ratio of 11.9, which is why
the claim was retained rather than retracted.

A claim resting on one training run is not a claim. This check asks for at least three
independent re-runs of the SAME model, submitted as y_pred_seed__<k> columns, and
compares their spread against the effect being claimed. Two runs give a range, not a
spread, so it declines below three rather than reporting a standard deviation nobody
should trust.
"""

from __future__ import annotations

import numpy as np

from .contract import AuditInput
from .stats import grouped_cv_predict, mae
from .verdict import FAIL, PASS, CheckResult, Timer, insufficient

CHECK_ID = "seed_stability"
TITLE = "Seed stability"
PROVENANCE = "Phase 5 Task 1 - 10 seeds, SD 0.0069 against a gap of 0.0815 (11.9x)"

MIN_SEEDS = 3


def run(inp: AuditInput, thresholds: dict | None = None, preregistered: bool = False,
        effect_size: float | None = None, progress=None,
        cache: dict | None = None) -> CheckResult:
    th = {"min_effect_to_seed_sd_ratio": 3.0}
    th.update(thresholds or {})

    with Timer() as t:
        seeds = inp.seed_predictions
        if len(seeds) < MIN_SEEDS:
            return insufficient(
                CHECK_ID, TITLE, PROVENANCE,
                missing=[f"y_pred_seed__<k> columns (have {len(seeds)}, "
                         f"need >= {MIN_SEEDS})"],
                explanation=(
                    "Seed stability needs the same model retrained under independent "
                    f"seeds; {len(seeds)} were submitted. With fewer than {MIN_SEEDS} "
                    "there is a range but no spread worth quoting, and a single-run "
                    "result cannot be distinguished from a lucky initialisation. This "
                    "is reported as not measured, not as stable."))

        y = inp.y_true
        maes = np.array([mae(v, y) for v in seeds.values()])
        sd = float(maes.std(ddof=1))
        spread = float(maes.max() - maes.min())

        if effect_size is None:
            mean_mae = mae(grouped_cv_predict(np.zeros((len(y), 0)), y, inp.grouping), y)
            effect_size = float(mean_mae - maes.mean())
            effect_basis = ("advantage over the population mean "
                            f"({mean_mae:.4f} - {maes.mean():.4f})")
        else:
            effect_basis = "supplied by the caller (e.g. the permutation real-vs-null gap)"

        ratio = float(effect_size / sd) if sd > 0 else float("inf")

        measured = {
            "n_seeds": len(seeds),
            "mae_mean": round(float(maes.mean()), 4),
            "mae_sd": round(sd, 5),
            "mae_min": round(float(maes.min()), 4),
            "mae_max": round(float(maes.max()), 4),
            "mae_range": round(spread, 5),
            "claimed_effect": round(float(effect_size), 5),
            "effect_to_seed_sd_ratio": (None if not np.isfinite(ratio)
                                        else round(ratio, 2)),
        }
        details = {"per_seed_mae": {k: round(mae(v, y), 5) for k, v in seeds.items()},
                   "effect_basis": effect_basis,
                   "rule": ("Phase 5's pre-declared rule: retract if the seed spread is "
                            "comparable to the effect being claimed")}

        need = float(th["min_effect_to_seed_sd_ratio"])
        if effect_size <= 0:
            res = CheckResult(
                CHECK_ID, TITLE, FAIL,
                headline=(f"seed SD {sd:.5f} against a claimed effect of "
                          f"{effect_size:.5f}"),
                explanation=("There is no positive effect to compare the seed spread "
                             "against: the model's mean score across seeds does not "
                             "improve on the baseline. Seed noise is therefore the only "
                             "thing being measured."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
        elif ratio >= need:
            res = CheckResult(
                CHECK_ID, TITLE, PASS,
                headline=(f"effect is {ratio:.1f}x the seed SD "
                          f"({effect_size:.4f} against {sd:.5f} over "
                          f"{len(seeds)} seeds)"),
                explanation=(
                    "The claimed effect is large relative to how much the result moves "
                    "when only the seed changes, so it is not an artefact of one lucky "
                    "run. Note the spread is also the reproduction tolerance: anyone "
                    f"re-running this model should expect MAE within about {spread:.4f} "
                    "of the reported value, and a reproduction attempt that lands inside "
                    "that band has succeeded, not failed."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
        else:
            res = CheckResult(
                CHECK_ID, TITLE, FAIL,
                headline=(f"effect is only {ratio:.1f}x the seed SD "
                          f"({effect_size:.4f} against {sd:.5f})"),
                explanation=(
                    "Re-running the same model with a different seed moves the score by "
                    "an amount comparable to the effect being claimed. The reported "
                    "number is therefore not separable from initialisation noise, and "
                    f"the claim should be re-stated with a {spread:.4f} spread attached "
                    "or withdrawn. This is the test Phase 5 of this project declared in "
                    "advance as grounds for retraction."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
    res.seconds = t.seconds
    return res
