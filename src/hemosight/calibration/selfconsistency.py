"""N1b: is the sclera a valid endogenous white reference across devices and lighting?

MOBIUS gives 3 phones x 3 lighting conditions x 100 subjects and needs no haemoglobin
label. A subject's sclera and iris have fixed physical reflectance, so after a correct
illuminant compensation the corrected colours should agree across all conditions.
Residual disagreement IS the calibration error.

THE CIRCULARITY TRAP - the single most important design point in this phase
--------------------------------------------------------------------------
If the illuminant is estimated FROM the sclera and consistency is then measured ON
the sclera, the result is guaranteed:

    corrected = measured / illuminant_est = measured / (measured / prior) = prior

which is a constant, so the spread collapses to exactly zero for every subject. That
would look like a spectacular confirmation of N1b and would mean nothing at all.

So the primary evaluation region is the **IRIS**: a different surface, with its own
fixed per-subject reflectance, never used to estimate the illuminant. Every method is
scored on identical iris pixels, so the comparison is fair and non-circular.

A secondary sclera-based figure uses a SPATIAL HOLDOUT - the illuminant is estimated
from one half of the sclera and consistency measured on the other half. That is still
partially circular (the two halves share a surface) and is reported as such, never as
the headline.
"""

from __future__ import annotations

import numpy as np

from .estimators import grey_world, max_rgb, robust_patch_rgb, shades_of_grey
from .metrics import delta_e2000_pairwise_spread
from .priors import NeutralPrior, ReflectancePrior, estimate_illuminant
from .segmentation import vessel_exclusion_mask
from .segmentation_data import IRIS, SCLERA

_RGB2XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
_D65 = np.array([0.95047, 1.00000, 1.08883])


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Linear RGB (relative, any scale) -> CIELAB.

    Normalised to unit sum first so only chromaticity is compared: an illuminant
    estimate is scale-free, so absolute brightness carries no information here.
    PROXY: camera RGB is treated as linear sRGB (no colorimetric characterisation
    ships with MOBIUS). Comparisons between methods remain valid.
    """
    v = np.asarray(rgb, dtype=float)
    s = v.sum()
    if not np.isfinite(s) or s <= 0:
        return np.full(3, np.nan)
    xyz = (v / s) @ _RGB2XYZ.T
    r = xyz / _D65
    eps, kappa = 216 / 24389, 24389 / 27
    f = np.where(r > eps, np.cbrt(r), (kappa * r + 16) / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def split_sclera_halves(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split a sclera mask into two spatial halves about its centroid x."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return mask, mask
    cx = np.median(xs)
    left = np.zeros_like(mask)
    right = np.zeros_like(mask)
    left[ys[xs <= cx], xs[xs <= cx]] = True
    right[ys[xs > cx], xs[xs > cx]] = True
    return left, right


def measure_regions(img: np.ndarray, labels: np.ndarray,
                    redness_percentile: float = 75.0) -> dict:
    """Extract the reference and evaluation region colours from one image.

    `img` is float RGB (any linear scale). Returns NaNs for absent regions rather
    than raising, so a failed segmentation degrades to a missing observation.
    """
    sclera = labels == SCLERA
    iris = labels == IRIS

    kept, removed = vessel_exclusion_mask(img, sclera, redness_percentile)
    left, right = split_sclera_halves(kept)

    out = {
        "sclera_px": int(sclera.sum()),
        "iris_px": int(iris.sum()),
        "vessel_fraction_removed": removed,
        "ref_rgb": robust_patch_rgb(img[kept]) if kept.sum() > 50 else np.full(3, np.nan),
        "ref_rgb_left": robust_patch_rgb(img[left]) if left.sum() > 50 else np.full(3, np.nan),
        "eval_iris_rgb": robust_patch_rgb(img[iris]) if iris.sum() > 50 else np.full(3, np.nan),
        "eval_sclera_right_rgb": (robust_patch_rgb(img[right]) if right.sum() > 50
                                  else np.full(3, np.nan)),
    }
    return out


def method_illuminants(img: np.ndarray, meas: dict, labels: np.ndarray,
                       prior: ReflectancePrior, subject: str | None = None) -> dict:
    """Illuminant estimate per method for one image. None means "no correction"."""
    valid = np.isfinite(img).all(axis=2)
    ests = {
        "none": np.ones(3) / np.sqrt(3),
        "grey_world": grey_world(img, valid),
        "max_rgb_p99": max_rgb(img, valid, percentile=99.0),
        "shades_of_grey_p6": shades_of_grey(img, valid, p=6),
    }
    ref = meas["ref_rgb_left"]  # spatial holdout: estimate from the LEFT half only
    if np.isfinite(ref).all():
        ests["sclera_neutral_prior"] = estimate_illuminant(ref, NeutralPrior())
        ests["sclera_fitted_prior"] = estimate_illuminant(ref, prior, subject)
    return ests


def corrected_lab(rgb: np.ndarray, illum: np.ndarray) -> np.ndarray:
    if not np.isfinite(rgb).all():
        return np.full(3, np.nan)
    return rgb_to_lab(rgb / np.clip(illum, 1e-8, None))


def per_subject_spread(records: list[dict], method: str, region: str) -> dict:
    """Within-subject DeltaE2000 spread across capture conditions, per subject."""
    by_subject: dict[str, list] = {}
    for r in records:
        lab = r["lab"].get((method, region))
        if lab is not None and np.isfinite(lab).all():
            by_subject.setdefault(r["subject"], []).append(lab)
    out = {}
    for s, labs in by_subject.items():
        if len(labs) >= 2:
            out[s] = delta_e2000_pairwise_spread(np.array(labs))
    return out


def variance_decomposition(records: list[dict], method: str, region: str) -> dict:
    """Two-way (phone x lighting) ANOVA within subject, pooled over subjects.

    A PHONE effect that survives correction is the failure mode that matters most:
    it means the method does not transfer across devices, which is precisely what
    calibration-free operation requires.
    """
    rows = [r for r in records
            if r["lab"].get((method, region)) is not None
            and np.isfinite(r["lab"][(method, region)]).all()]
    if not rows:
        return {}

    subs = sorted({r["subject"] for r in rows})
    ss = {"phone": 0.0, "lighting": 0.0, "interaction": 0.0, "residual": 0.0}
    ss_between = 0.0
    grand = np.mean([r["lab"][(method, region)] for r in rows], axis=0)
    n_used = 0

    for s in subs:
        rs = [r for r in rows if r["subject"] == s]
        if len(rs) < 4:
            continue
        lab = np.array([r["lab"][(method, region)] for r in rs])
        phones = np.array([r["phone"] for r in rs])
        lights = np.array([r["lighting"] for r in rs])
        mu = lab.mean(axis=0)
        ss_between += len(rs) * float(((mu - grand) ** 2).sum())

        pm = {p: lab[phones == p].mean(axis=0) for p in set(phones)}
        lm = {c: lab[lights == c].mean(axis=0) for c in set(lights)}
        for r_i, v in enumerate(lab):
            a = pm[phones[r_i]] - mu
            b = lm[lights[r_i]] - mu
            resid = v - mu - a - b
            ss["phone"] += float((a ** 2).sum())
            ss["lighting"] += float((b ** 2).sum())
            ss["residual"] += float((resid ** 2).sum())
        n_used += len(rs)

    within_total = sum(ss.values())
    total = within_total + ss_between
    if total <= 0:
        return {}
    return {
        "n_observations": n_used,
        "n_subjects": len(subs),
        "frac_between_subject": ss_between / total,
        "frac_within_phone": ss["phone"] / total,
        "frac_within_lighting": ss["lighting"] / total,
        "frac_within_residual": ss["residual"] / total,
        "within_subject_total_frac": within_total / total,
        "phone_share_of_within": ss["phone"] / within_total if within_total else None,
        "lighting_share_of_within": ss["lighting"] / within_total if within_total else None,
    }
