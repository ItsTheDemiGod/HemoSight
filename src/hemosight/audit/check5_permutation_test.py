"""Check 5 - permutation test, with the empirical floor stated.

PROVENANCE. Phase 4.5 Task 2 and Phase 5 Task 1 (DECISION LOG 2026-09-11, "The
positive claim SURVIVES hardening"). Three lessons are built in:

  1. REPORT THE EMPIRICAL p, NOT ONLY A z. Phase 4.5 first reported z = -4.72 from
     n=30 permutations, where the smallest achievable empirical p is 0.032. A z assumes
     a normal null; the empirical p assumes nothing.
  2. SAY WHEN THE p IS A FLOOR. Phase 5's selection-aware test reported p = 0.0164 at
     n=60 with zero draws at or below the real value. That is 1/(60+1) - the smallest
     number the sample size allowed, a BOUND rather than a measurement. Printing it
     without that qualification is the error this check refuses to let a report repeat.
     The run was later extended to n=240 and STILL no draw reached the real value, so
     the figure moved to 0.0041 and remained a floor - which is exactly why a p and
     its floor have to travel together.
  3. PRICE IN THE SELECTION. A model chosen as best-of-six and then permutation-tested
     has a null that never selected anything. Phase 5 re-ran the full best-of-six
     selection inside every permutation; the selection was worth 0.0071 g/dL of MAE by
     chance alone - real, and an order of magnitude below the effect. Supplying the
     candidates as y_pred__<name> columns is what lets this check do the same.

WHAT IS AND IS NOT TESTED HERE. The submitted predictions are fixed, so this permutes
the labels against them rather than refitting. That tests the association between
predictions and truth, which is the claim a reported score makes. It does NOT re-run
the submitter's training, so it cannot price in anything that happened before the
predictions were written - tuning against the test set, for instance, is invisible to
it. The check says so in its own output rather than letting a reader assume otherwise.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .contract import AuditInput
from .stats import empirical_p, mae
from .verdict import FAIL, INSUFFICIENT, PASS, CheckResult, Timer

CHECK_ID = "permutation"
TITLE = "Permutation test"
PROVENANCE = ("Phase 5 Task 1 selection-aware permutation and Phase 4.5 Task 2 "
              "(scripts/permutation_hardening_phase5.py, scripts/permutation_extended_run_phase5.py)")

PERM_SEED = 770000          # the namespace Phase 5's extended runner uses


def permuted_labels(y: np.ndarray, subjects: np.ndarray, i: int) -> np.ndarray:
    """Permutation i's shuffled labels, as a pure function of (y, subjects, i).

    Shuffling happens ACROSS SUBJECTS, then broadcasts back to that subject's rows, so
    the permutation breaks the subject-level association without pretending a subject's
    rows are independent of each other.

    The purity matters beyond tidiness: Phase 5's first extended run drew its shuffles
    from one sequentially consumed generator, so permutation i depended on every
    permutation before it, and when the run was killed at n=41 the draws could neither
    be resumed nor reproduced. See the DECISION LOG, 2026-09-12.
    """
    rng = np.random.default_rng(PERM_SEED + i)
    s = pd.Series(y).groupby(pd.Series(subjects).values).first()
    shuffled = rng.permutation(s.to_numpy())
    lookup = dict(zip(s.index.tolist(), shuffled.tolist()))
    return np.array([lookup[k] for k in subjects], dtype=float)


def run(inp: AuditInput, thresholds: dict | None = None, preregistered: bool = False,
        n_permutations: int = 1000, progress=None,
        cache: dict | None = None) -> CheckResult:
    th = {"alpha": 0.05}
    th.update(thresholds or {})
    alpha = float(th["alpha"])

    with Timer() as t:
        y = inp.y_true
        subjects = inp.subject_id
        n_sub = int(pd.unique(subjects).size)

        within = (pd.Series(y).groupby(pd.Series(subjects).values).nunique() > 1)
        label_varies_within_subject = bool(within.any())

        cands = inp.candidates
        names = list(cands)
        M = np.vstack([cands[k] for k in names])

        real_each = {k: mae(cands[k], y) for k in names}
        real_selected = float(min(real_each.values()))
        argmin = min(real_each, key=real_each.get)
        submitted_mae = real_each["submitted"]

        floor = 1.0 / (n_permutations + 1)
        if floor >= alpha:
            return CheckResult(
                CHECK_ID, TITLE, INSUFFICIENT,
                headline=(f"{n_permutations} permutations cannot reach alpha="
                          f"{alpha}: the floor is {floor:.4f}"),
                explanation=(
                    f"The smallest empirical p obtainable from {n_permutations} "
                    f"permutations is 1/(n+1) = {floor:.4f}, which is not below the "
                    f"declared alpha of {alpha}. No outcome of this run could support a "
                    "positive verdict, so it is not run. Raise the permutation count to "
                    f"at least {int(np.ceil(1 / alpha)) - 1}."),
                provenance=PROVENANCE,
                measured={"n_permutations": n_permutations, "p_floor": round(floor, 5)},
                missing=[f"permutations (need >= {int(np.ceil(1 / alpha)) - 1})"],
                threshold=th, threshold_preregistered=preregistered)

        null_selected = np.empty(n_permutations)
        null_aware = np.empty(n_permutations)
        for i in range(n_permutations):
            yp = permuted_labels(y, subjects, i)
            d = np.mean(np.abs(M - yp[None, :]), axis=1)
            null_selected[i] = d[names.index("submitted")]
            # Re-picks the best of all candidates UNDER THIS PERMUTATION'S shuffled
            # labels - i.e. model selection is re-run inside every draw, not just once
            # against the real labels. Skipping this and taking d[argmin_on_real_data]
            # would let the null score better than it should, because the real run's
            # selection step has already thrown away every candidate that looked worse
            # by chance. See PROVENANCE point 3 above (Phase 5's measured selection
            # cost, 0.0071 g/dL).
            null_aware[i] = d.min()
            if progress and i % 50 == 0:
                progress(i / n_permutations, f"permutation {i}/{n_permutations}")

        sel = empirical_p(null_selected, submitted_mae)
        aware = empirical_p(null_aware, real_selected)
        primary, primary_name = ((aware, "selection-aware") if len(names) > 1
                                 else (sel, "selected-model-only"))

        measured = {
            "construction": primary_name,
            "n_permutations": n_permutations,
            "n_candidates": len(names),
            "real_mae": round(primary["real"], 4),
            "null_mean": round(primary["null_mean"], 4),
            "null_sd": round(primary["null_sd"], 4),
            "draws_at_or_below_real": primary["n_at_or_below_real"],
            "p_empirical": round(primary["p_empirical"], 5),
            "p_floor": round(primary["p_floor"], 5),
            "p_is_at_the_floor": primary["at_floor"],
            "z_parametric": (None if primary["z_parametric"] is None
                             else round(primary["z_parametric"], 3)),
        }
        details = {
            "selected_model_only": sel,
            "selection_aware": aware,
            "selection_cost_in_null_mean": (
                None if len(names) == 1
                else round(sel["null_mean"] - aware["null_mean"], 5)),
            "real_mae_per_candidate": {k: round(v, 4) for k, v in real_each.items()},
            "best_candidate": argmin,
            "submitted_is_best_candidate": argmin == "submitted",
            "labels_permuted_across": f"{n_sub} subjects",
            "label_varies_within_subject": label_varies_within_subject,
            "scope": ("labels are permuted against fixed predictions; the submitter's "
                      "training is not re-run, so anything that happened before the "
                      "predictions were written is outside this test"),
        }

        floor_note = ("" if not primary["at_floor"] else
                      f" - AT THE FLOOR 1/(n+1)={primary['p_floor']:.5f}, a bound, not "
                      "a measurement")
        if primary["p_empirical"] < alpha:
            res = CheckResult(
                CHECK_ID, TITLE, PASS,
                headline=(f"empirical p = {primary['p_empirical']:.5f} over "
                          f"{n_permutations} {primary_name} permutations{floor_note}"),
                explanation=(
                    "The model is distinguishable from the same model trained on "
                    "shuffled labels. "
                    + ("Because zero null draws reached the real value, the p reported "
                       "is the smallest the permutation count allows: the true p is "
                       "bounded above by it, and more permutations would tighten the "
                       "bound. " if primary["at_floor"] else "")
                    + ("The null includes the selection step, so the reported p already "
                       "prices in having chosen the best of "
                       f"{len(names)} candidates. "
                       if len(names) > 1 else
                       "Only one candidate was submitted, so this null does not price "
                       "in any selection. If the model was chosen as the best of "
                       "several, supply the others as y_pred__<name> columns - Phase 5 "
                       "of this project measured that selection to be worth real MAE by "
                       "chance alone. ")
                    + "Statistical distinguishability is not utility: this project's "
                      "own surviving claim is significant at z = -5.02 and clinically "
                      "useless."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
        else:
            res = CheckResult(
                CHECK_ID, TITLE, FAIL,
                headline=(f"empirical p = {primary['p_empirical']:.5f} over "
                          f"{n_permutations} {primary_name} permutations"),
                explanation=(
                    f"{primary['n_at_or_below_real']} of {n_permutations} label "
                    "shuffles matched or beat the real result, so the model is not "
                    "distinguishable from one fitted to randomly shuffled labels. "
                    "Phase 4.5 of this project reached p = 0.978 on its feature model - "
                    "worse than 97.8% of shuffled-label models - and that licensed the "
                    "stronger claim that the signal was absent, rather than that one "
                    "model had failed."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
    res.seconds = t.seconds
    return res
