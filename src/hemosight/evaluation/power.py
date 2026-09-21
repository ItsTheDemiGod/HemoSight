"""Phase 9D - minimum detectable effect for the comparisons that decided each arm.

What this module computes
------------------------
For a two-sided test at alpha and power 1 - beta, the smallest true difference a design
could detect:

    MDE = (z_{1-alpha/2} + z_{1-beta}) * SE(difference)

`SE` is the standard error of the *paired* difference statistic, because every comparison
in this project scores two models on the same subjects. An unpaired SE would be wider
than the evidence warrants and would inflate every MDE.

What this module deliberately does NOT compute
----------------------------------------------
**Observed / retrospective / post-hoc power** - power recomputed at the effect size that
was actually observed. It is a deterministic function of the observed p-value, so it adds
no information beyond the p-value, and it is guaranteed to look low whenever a result was
null. Reporting it here would manufacture an excuse for every negative finding in the
project. `observed_power` therefore does not exist in this module by design; see
`docs/archive/decision_log.md`, 2026-09-20.

The MDE does use the sample to estimate a nuisance variance. That is standard and is not
the same error: the effect size is not consulted. Two honest caveats travel with it and
are reported - the SE estimate carries its own sampling uncertainty, and for sensitivity
and specificity the SE depends mildly on the true effect size.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm

ALPHA = 0.05
POWERS = (0.80, 0.90)


def multiplier(power: float, alpha: float = ALPHA) -> float:
    """(z_{1-alpha/2} + z_{power}); 2.802 at 80% power, 3.242 at 90%."""
    return float(norm.ppf(1.0 - alpha / 2.0) + norm.ppf(power))


def mde(se: float, power: float, alpha: float = ALPHA) -> float:
    """Minimum detectable effect at the given power."""
    if not np.isfinite(se):
        return float("nan")
    return float(multiplier(power, alpha) * se)


def mde_table(se: float, alpha: float = ALPHA) -> dict[str, float]:
    return {f"mde_{int(p * 100)}": mde(se, p, alpha) for p in POWERS}


# --------------------------------------------------------------------------- #
# SE of a paired mean difference (the MAE comparisons)
# --------------------------------------------------------------------------- #
def paired_mean_se(a: np.ndarray, b: np.ndarray) -> dict:
    """SE of mean(a) - mean(b) for values measured on the SAME subjects.

    For the MAE comparisons `a` and `b` are per-subject absolute errors. The exact
    paired SE is sd(a - b)/sqrt(n); the correlation between the two models' errors is
    reported because it is what makes the paired SE smaller than the unpaired one, and
    a reader should be able to see how much of the precision comes from pairing.
    """
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    assert a.shape == b.shape, "paired comparison needs matched subjects"
    d = a - b
    n = d.size
    se_paired = float(np.std(d, ddof=1) / np.sqrt(n))
    se_unpaired = float(np.sqrt(np.var(a, ddof=1) / n + np.var(b, ddof=1) / n))
    r = float(np.corrcoef(a, b)[0, 1]) if n > 2 else float("nan")
    return {"n": int(n), "mean_a": float(a.mean()), "mean_b": float(b.mean()),
            "observed_difference": float(d.mean()),
            "se_paired": se_paired, "se_unpaired_for_reference": se_unpaired,
            "error_correlation": r,
            "pairing_variance_saving": (float(1.0 - se_paired / se_unpaired)
                                        if se_unpaired > 0 else float("nan"))}


def bootstrap_se(values: np.ndarray) -> float:
    """SE of a statistic from its bootstrap replicate distribution."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    return float(np.std(v, ddof=1)) if v.size > 1 else float("nan")


# --------------------------------------------------------------------------- #
# Clinical translation
# --------------------------------------------------------------------------- #
def subjects_moved(delta: float, n_group: int) -> float:
    """How many subjects a sensitivity/specificity change of `delta` corresponds to."""
    return float(delta * n_group)


WHO_BANDS = {"severe/moderate": 7.0, "moderate/mild": 10.0,
             "mild/normal_men": 13.0, "mild/normal_women": 12.0}
NARROWEST_WHO_BAND_G_DL = 1.0   # mild band for men, 10.0-10.9; the tightest boundary gap
GATE_BANDS = {"viable": 1.0, "marginal": 2.0}


def moves_a_who_boundary(mae_improvement: float) -> bool:
    """Could an MAE improvement of this size move a WHO severity boundary?

    The narrowest WHO band is 1.0 g/dL wide. An improvement in mean absolute error
    smaller than that cannot reclassify a subject across the nearest boundary except by
    coincidence, so it cannot change a clinical decision on the strength of the estimate.
    """
    return bool(mae_improvement >= NARROWEST_WHO_BAND_G_DL)


def power_at(effect: float, se: float, alpha: float = ALPHA) -> float:
    """Power to detect a PRE-SPECIFIED effect size.

    Legitimate and distinct from observed power: `effect` here is the clinical yardstick
    declared in advance, never the effect the study happened to observe. Two-sided,
    ignoring the negligible opposite-tail term.
    """
    if not np.isfinite(effect) or not np.isfinite(se) or se <= 0:
        return float("nan")
    return float(norm.cdf(abs(effect) / se - norm.ppf(1.0 - alpha / 2.0)))


def verdict(mde_80: float, yardstick: float) -> str:
    """The pre-declared rule: ADEQUATELY POWERED iff MDE(80%) <= the clinical yardstick."""
    if not np.isfinite(mde_80) or not np.isfinite(yardstick):
        return "INDETERMINATE"
    return "ADEQUATELY POWERED" if mde_80 <= yardstick else "UNDERPOWERED"


# --------------------------------------------------------------------------- #
# Phase 9E - turning an UNDERPOWERED verdict into a study specification
# --------------------------------------------------------------------------- #
def required_group_n(n_observed: int, mde_observed: float, target: float,
                     slope: float = 0.5) -> float:
    """Group size at which the MDE falls to `target`, under SE proportional to n**-slope.

    `n_observed` is the size of the group the metric is actually estimated on - the
    non-anaemic subjects for a specificity, the anaemic ones for a sensitivity - not the
    cohort. Quoting a total hides the composition problem that Phase 9D found: a cohort
    can be large and still estimate specificity on 27 people.

    `slope` defaults to the 1/sqrt(n) rate but is a parameter because Phase 9E measures
    it by subsampling rather than assuming it. Feed the measured slope in.
    """
    if not (np.isfinite(mde_observed) and np.isfinite(target)) or target <= 0 or slope <= 0:
        return float("nan")
    return float(n_observed * (mde_observed / target) ** (1.0 / slope))


def total_n_for_group(n_group: float, prevalence: float, group: str) -> float:
    """Cohort size that yields `n_group` subjects in the named group at `prevalence`."""
    if group not in ("anaemic", "non_anaemic"):
        raise ValueError(f"group must be anaemic or non_anaemic, not {group!r}")
    share = prevalence if group == "anaemic" else 1.0 - prevalence
    if not np.isfinite(share) or share <= 0:
        return float("inf")
    return float(n_group / share)


def scaling_slope(ns: np.ndarray, ses: np.ndarray) -> dict:
    """Fit log(SE) = c - slope * log(n); returns the slope and its fit quality.

    Reported so the required-n figures rest on a measured rate rather than a textbook
    one. A slope near 0.5 is the ordinary 1/sqrt(n); a materially different slope is
    reported and used, not corrected away.
    """
    n = np.asarray(ns, float)
    s = np.asarray(ses, float)
    ok = np.isfinite(n) & np.isfinite(s) & (n > 0) & (s > 0)
    if ok.sum() < 3:
        return {"slope": float("nan"), "r2": float("nan"), "n_points": int(ok.sum())}
    x, y = np.log(n[ok]), np.log(s[ok])
    b, a = np.polyfit(x, y, 1)
    resid = y - (a + b * x)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {"slope": float(-b), "intercept": float(a), "n_points": int(ok.sum()),
            "r2": float(1.0 - (resid ** 2).sum() / ss_tot) if ss_tot > 0 else float("nan")}
