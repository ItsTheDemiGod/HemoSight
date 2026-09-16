"""Screening (triage) metrics for a haemoglobin estimator, Phase 9A.

The project's gates were all written in mean absolute error, g/dL. The product a
screening tool delivers is a binary referral decision, which is a different task with
different metrics. This module evaluates that task.

Everything here follows the criteria pre-declared in CLAUDE.md section 6, Phase 9A,
before any of it was run:

  * WHO thresholds are sex-specific for adults - men < 13.0 g/dL, non-pregnant women
    < 12.0 g/dL. `who_threshold` REFUSES to run on a subject under 15 rather than
    silently applying an adult threshold to a child.
  * The operating point is the highest specificity subject to sensitivity >= 0.90, and
    it is chosen on TRAINING folds only, then applied to the held-out fold. Choosing a
    cut on the data it is scored on is the single easiest way to flatter a screening
    model, so `nested_calls` never sees a test label when it picks a cut.
  * A referral rate is reported with every operating point, because a tool that refers
    everybody has sensitivity 1.00 and no value.

Scores here are PREDICTED HAEMOGLOBIN: lower means more likely anaemic, so a subject is
called positive when the prediction is strictly below a cut.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve

SEED = 20260911
N_BOOT = 2000
TARGET_SENS = 0.90          # pre-declared operating-point criterion
MARGIN = 0.10               # pre-declared clinically-meaningful margin
SPEC_FLOOR = 0.50           # pre-declared specificity floor for USEFUL

MALE_THRESHOLD = 13.0
FEMALE_THRESHOLD = 12.0


def who_threshold(male: np.ndarray, age: np.ndarray) -> np.ndarray:
    """Per-subject WHO anaemia threshold, g/dL. Adults only, by design.

    Pregnancy status is not recorded in either dataset, so the non-pregnant threshold
    is applied to every woman. A pregnant woman's threshold is 11.0, so any pregnant
    subject is over-called anaemic; this is a stated limitation, not an oversight.
    """
    age = np.asarray(age, dtype=float)
    if np.any(~np.isfinite(age)):
        raise ValueError("age missing; the applicable WHO threshold cannot be chosen")
    if np.any(age < 15):
        raise ValueError(
            f"{int((age < 15).sum())} subject(s) under 15: a child threshold applies "
            "(6-59 mo 11.0, 5-11 y 11.5, 12-14 y 12.0) and this function refuses to "
            "apply an adult threshold to them")
    return np.where(np.asarray(male).astype(bool), MALE_THRESHOLD, FEMALE_THRESHOLD)


def confusion(truth: np.ndarray, call: np.ndarray) -> dict:
    truth = np.asarray(truth).astype(bool)
    call = np.asarray(call).astype(bool)
    return {"tp": int((truth & call).sum()), "fp": int((~truth & call).sum()),
            "tn": int((~truth & ~call).sum()), "fn": int((truth & ~call).sum())}


def screening_metrics(truth: np.ndarray, call: np.ndarray) -> dict:
    """Sensitivity, specificity, PPV, NPV, referral rate, false-referral rate, NNS.

    Number needed to screen is 1 / (prevalence x sensitivity): the number of people who
    must be screened to correctly refer one anaemic case. It is infinite when the tool
    flags nobody, which is the honest reading of that situation.
    """
    c = confusion(truth, call)
    tp, fp, tn, fn = c["tp"], c["fp"], c["tn"], c["fn"]
    n = tp + fp + tn + fn
    pos, neg = tp + fn, tn + fp
    prevalence = pos / n if n else float("nan")
    sens = tp / pos if pos else float("nan")
    spec = tn / neg if neg else float("nan")
    referred = tp + fp
    ppv = tp / referred if referred else float("nan")
    npv = tn / (tn + fn) if (tn + fn) else float("nan")
    detected_per_screened = tp / n if n else 0.0
    return {**c, "n": n, "n_anaemic": pos, "prevalence": prevalence,
            "sensitivity": sens, "specificity": spec, "ppv": ppv, "npv": npv,
            "n_anaemic_flagged": tp,
            "referral_rate": referred / n if n else float("nan"),
            "false_referral_rate": (1.0 - ppv) if referred else float("nan"),
            "number_needed_to_screen": (1.0 / detected_per_screened
                                        if detected_per_screened > 0 else float("inf"))}


def _cut_candidates(scores: np.ndarray) -> np.ndarray:
    """Every distinct cut that can change a call, plus open ends."""
    s = np.unique(np.asarray(scores, dtype=float))
    mids = (s[:-1] + s[1:]) / 2.0 if len(s) > 1 else np.array([])
    return np.concatenate([[s.min() - 1.0], mids, [s.max() + 1.0]])


def choose_cut_for_sensitivity(scores: np.ndarray, truth: np.ndarray,
                              target: float = TARGET_SENS) -> tuple[float, bool]:
    """Highest-specificity cut reaching `target` sensitivity. Call positive if < cut.

    Returns (cut, reached). When no cut reaches the target, returns the most sensitive
    cut and reached=False, so the caller reports the failure rather than hiding it.
    """
    best, best_spec, reached = None, -1.0, False
    fallback, fallback_sens = None, -1.0
    for cut in _cut_candidates(scores):
        m = screening_metrics(truth, np.asarray(scores) < cut)
        sens, spec = m["sensitivity"], m["specificity"]
        if not np.isfinite(sens):
            continue
        if sens > fallback_sens or (sens == fallback_sens and spec > -1):
            if sens > fallback_sens:
                fallback, fallback_sens = cut, sens
        if sens >= target and spec > best_spec:
            best, best_spec, reached = cut, spec, True
    return (float(best), True) if reached else (float(fallback), False)


def choose_cut_for_specificity(scores: np.ndarray, truth: np.ndarray,
                               target: float) -> float:
    """Most sensitive cut whose specificity is at least `target`.

    Used to put a model and a baseline at MATCHED specificity so their sensitivities
    are comparable. Falls back to the cut with specificity closest to the target when
    none reaches it.
    """
    best, best_sens = None, -1.0
    closest, closest_gap = None, float("inf")
    for cut in _cut_candidates(scores):
        m = screening_metrics(truth, np.asarray(scores) < cut)
        sens, spec = m["sensitivity"], m["specificity"]
        if not np.isfinite(spec):
            continue
        gap = abs(spec - target)
        if gap < closest_gap:
            closest, closest_gap = cut, gap
        if spec >= target and sens > best_sens:
            best, best_sens = cut, sens
    return float(best if best is not None else closest)


def nested_calls(scores: np.ndarray, truth: np.ndarray, folds: list[tuple],
                 target: float = TARGET_SENS) -> dict:
    """Pick the cut on each TRAIN fold, apply it to the held-out fold.

    This is the whole point of the construction: the operating point never sees the
    labels it is scored against. Returns per-subject calls plus the per-fold cuts.
    """
    scores = np.asarray(scores, dtype=float)
    truth = np.asarray(truth).astype(bool)
    call = np.zeros(len(truth), dtype=bool)
    cuts, reached = [], []
    for tr, te in folds:
        cut, ok = choose_cut_for_sensitivity(scores[tr], truth[tr], target)
        call[te] = scores[te] < cut
        cuts.append(float(cut))
        reached.append(bool(ok))
    return {"call": call, "cuts": cuts,
            "folds_reaching_target": int(sum(reached)), "n_folds": len(folds),
            "mean_cut": float(np.mean(cuts))}


def nested_calls_matched_specificity(scores: np.ndarray, truth: np.ndarray,
                                     folds: list[tuple],
                                     reference_scores: np.ndarray,
                                     target: float = TARGET_SENS) -> dict:
    """Calls for `scores` matched, per fold, to the reference's TRAIN specificity.

    The reference picks its own cut on the train fold by the sensitivity rule; its
    train specificity becomes the target that `scores` must match on the same train
    fold. Both models are then scored on the held-out fold at matched specificity.
    """
    scores = np.asarray(scores, dtype=float)
    reference_scores = np.asarray(reference_scores, dtype=float)
    truth = np.asarray(truth).astype(bool)
    call = np.zeros(len(truth), dtype=bool)
    targets = []
    for tr, te in folds:
        ref_cut, _ = choose_cut_for_sensitivity(reference_scores[tr], truth[tr], target)
        ref_spec = screening_metrics(truth[tr], reference_scores[tr] < ref_cut)["specificity"]
        cut = choose_cut_for_specificity(scores[tr], truth[tr], ref_spec)
        call[te] = scores[te] < cut
        targets.append(float(ref_spec))
    return {"call": call, "matched_train_specificity": float(np.mean(targets))}


def nested_calls_matched_sensitivity(scores: np.ndarray, truth: np.ndarray,
                                     folds: list[tuple],
                                     reference_scores: np.ndarray,
                                     target: float = TARGET_SENS) -> dict:
    """Calls for `scores` matched, per fold, to the reference's TRAIN sensitivity.

    The symmetric half of the pre-declared margin rule: hold sensitivity level and
    compare specificity. The reference picks its own cut on the train fold by the
    sensitivity rule; the sensitivity it actually achieves there becomes the level
    `scores` must match on the same train fold, at the highest specificity available.
    """
    scores = np.asarray(scores, dtype=float)
    reference_scores = np.asarray(reference_scores, dtype=float)
    truth = np.asarray(truth).astype(bool)
    call = np.zeros(len(truth), dtype=bool)
    targets = []
    for tr, te in folds:
        ref_cut, _ = choose_cut_for_sensitivity(reference_scores[tr], truth[tr], target)
        ref_sens = screening_metrics(truth[tr], reference_scores[tr] < ref_cut)["sensitivity"]
        cut, _ = choose_cut_for_sensitivity(scores[tr], truth[tr], ref_sens)
        call[te] = scores[te] < cut
        targets.append(float(ref_sens))
    return {"call": call, "matched_train_sensitivity": float(np.mean(targets))}


def plugin_calls(scores: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """The naive rule Phase 7 reported: refer if the PREDICTED Hb is below the
    diagnostic threshold. A regression model shrinks toward the mean, so this is
    systematically insensitive - which is exactly what Phase 7 measured."""
    return np.asarray(scores, dtype=float) < np.asarray(thresholds, dtype=float)


def ranking_metrics(truth: np.ndarray, scores: np.ndarray) -> dict:
    """AUROC and AUPRC for the anaemia label. Anaemia score is -predicted Hb."""
    truth = np.asarray(truth).astype(int)
    s = -np.asarray(scores, dtype=float)
    if len(np.unique(truth)) < 2:
        return {"auroc": float("nan"), "auprc": float("nan"),
                "auprc_baseline": float("nan")}
    return {"auroc": float(roc_auc_score(truth, s)),
            "auprc": float(average_precision_score(truth, s)),
            "auprc_baseline": float(truth.mean())}


def roc_points(truth: np.ndarray, scores: np.ndarray) -> dict:
    fpr, tpr, thr = roc_curve(np.asarray(truth).astype(int), -np.asarray(scores, float))
    return {"fpr": [float(v) for v in fpr], "tpr": [float(v) for v in tpr],
            "cut_g_dl": [float(-v) if np.isfinite(v) else None for v in thr]}


def _resamples(n: int, n_boot: int = N_BOOT, seed: int = SEED) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n, size=(n_boot, n))


def bootstrap_ci(truth: np.ndarray, values: np.ndarray, statistic,
                 n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Subject-level percentile bootstrap. Degenerate resamples (one class only) are
    skipped and counted, never silently dropped."""
    truth = np.asarray(truth)
    values = np.asarray(values)
    out, skipped = [], 0
    for idx in _resamples(len(truth), n_boot, seed):
        t = truth[idx]
        if len(np.unique(np.asarray(t).astype(int))) < 2:
            skipped += 1
            continue
        v = statistic(t, values[idx])
        if v is not None and np.isfinite(v):
            out.append(v)
    if not out:
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "n_boot": 0, "skipped": skipped}
    return {"lo": float(np.percentile(out, 2.5)), "hi": float(np.percentile(out, 97.5)),
            "n_boot": len(out), "skipped": skipped}


def paired_difference_ci(truth: np.ndarray, call_a: np.ndarray, call_b: np.ndarray,
                         metric: str, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """CI on (A - B) for one screening metric, both recomputed on the same resample.

    Pairing matters: the two models are scored on the same subjects, so an unpaired
    interval would be wider than the evidence warrants.
    """
    truth = np.asarray(truth).astype(bool)
    call_a = np.asarray(call_a).astype(bool)
    call_b = np.asarray(call_b).astype(bool)
    diffs, skipped = [], 0
    for idx in _resamples(len(truth), n_boot, seed):
        t = truth[idx]
        if t.sum() == 0 or (~t).sum() == 0:
            skipped += 1
            continue
        a = screening_metrics(t, call_a[idx])[metric]
        b = screening_metrics(t, call_b[idx])[metric]
        if np.isfinite(a) and np.isfinite(b):
            diffs.append(a - b)
    if not diffs:
        return {"diff": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "n_boot": 0, "skipped": skipped, "excludes_zero": False}
    point = (screening_metrics(truth, call_a)[metric]
             - screening_metrics(truth, call_b)[metric])
    lo, hi = float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))
    return {"diff": float(point), "lo": lo, "hi": hi, "n_boot": len(diffs),
            "skipped": skipped, "excludes_zero": bool(lo > 0 or hi < 0)}


def margin_cleared(diff: float, lo: float) -> bool:
    """One direction of the pre-declared margin: >= 0.10 with a CI lower bound > 0."""
    return bool(np.isfinite(diff) and diff >= MARGIN and np.isfinite(lo) and lo > 0)


def verdict(sens: float, spec: float, sens_diff: float, sens_lo: float,
            spec_diff: float = float("nan"), spec_lo: float = float("nan")) -> str:
    """The pre-declared bands.

    The margin is cleared by EITHER direction, because the pre-declaration says the
    symmetric test "counts equally": a sensitivity gain at matched specificity, or a
    specificity gain at matched sensitivity, each >= 0.10 with a CI lower bound above
    zero. An earlier version of this function consulted only the first, which would
    have under-reported any model that buys specificity rather than sensitivity -
    fixed before any verdict here was reported.
    """
    floors = (np.isfinite(sens) and np.isfinite(spec)
              and sens >= TARGET_SENS and spec >= SPEC_FLOOR)
    cleared = margin_cleared(sens_diff, sens_lo) or margin_cleared(spec_diff, spec_lo)
    if not floors:
        return "NOT USEFUL"
    return "USEFUL" if cleared else "MARGINAL"
