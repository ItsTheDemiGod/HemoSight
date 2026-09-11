"""Illuminant-estimation error metrics.

Angular error is the standard colour-constancy metric and is what the NUS benchmark
reports. The conventional reporting set is mean / median / trimean / best-25% /
worst-25%, because the error distribution is heavily skewed and a mean alone hides
catastrophic failures.

DeltaE2000 is reported alongside because angular error is not perceptually uniform:
two estimates with equal angular error can differ greatly in visible cast.
"""

from __future__ import annotations

import numpy as np

# sRGB (linear) -> CIE XYZ, D65.
_RGB2XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
_D65 = np.array([0.95047, 1.00000, 1.08883])


def angular_error(est: np.ndarray, gt: np.ndarray) -> np.ndarray:
    """Angle in degrees between estimated and ground-truth illuminant vectors.

    Accepts (3,) or (N, 3). Scale-invariant, which is correct: an illuminant estimate
    is only ever defined up to a scale factor.
    """
    est = np.atleast_2d(np.asarray(est, dtype=float))
    gt = np.atleast_2d(np.asarray(gt, dtype=float))
    en = est / np.linalg.norm(est, axis=1, keepdims=True)
    gn = gt / np.linalg.norm(gt, axis=1, keepdims=True)
    cos = np.clip((en * gn).sum(axis=1), -1.0, 1.0)
    return np.degrees(np.arccos(cos))


def _xyz_to_lab(xyz: np.ndarray) -> np.ndarray:
    r = xyz / _D65
    eps, kappa = 216 / 24389, 24389 / 27
    f = np.where(r > eps, np.cbrt(r), (kappa * r + 16) / 116)
    return np.stack([116 * f[..., 1] - 16,
                     500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e2000_illuminant(est: np.ndarray, gt: np.ndarray) -> np.ndarray:
    """CIEDE2000 between a neutral surface corrected by `est` versus by `gt`.

    An illuminant estimate has no colour of its own; what matters is the cast left on
    a corrected image. So both illuminants are used to white-balance a perfect neutral
    surface and the two results are compared.

    PROXY WARNING: NUS supplies no colorimetric characterisation for these cameras, so
    camera RGB is treated as linear sRGB. The absolute DeltaE values are therefore
    indicative, not colorimetric. Comparisons BETWEEN methods on the same camera remain
    valid because every method inherits the same approximation.
    """
    from colour.difference import delta_E_CIE2000

    est = np.atleast_2d(np.asarray(est, dtype=float))
    gt = np.atleast_2d(np.asarray(gt, dtype=float))
    est = est / np.linalg.norm(est, axis=1, keepdims=True)
    gt = gt / np.linalg.norm(gt, axis=1, keepdims=True)

    # White-balance a neutral surface: divide by the illuminant, then renormalise so
    # only the chromatic difference survives (brightness carries no information here).
    def corrected(i):
        c = 1.0 / np.clip(i, 1e-8, None)
        return c / c.sum(axis=1, keepdims=True)

    lab_e = _xyz_to_lab(corrected(est) @ _RGB2XYZ.T)
    lab_g = _xyz_to_lab(corrected(gt) @ _RGB2XYZ.T)
    return np.asarray(delta_E_CIE2000(lab_e, lab_g), dtype=float)


def trimean(x: np.ndarray) -> float:
    q1, q2, q3 = np.percentile(x, [25, 50, 75])
    return float((q1 + 2 * q2 + q3) / 4)


def error_summary(errors: np.ndarray) -> dict[str, float]:
    """The standard NUS reporting set."""
    e = np.asarray(errors, dtype=float)
    e = e[np.isfinite(e)]
    if e.size == 0:
        return {k: float("nan") for k in
                ("n", "mean", "median", "trimean", "best25", "worst25", "max")}
    s = np.sort(e)
    k = max(1, int(round(0.25 * s.size)))
    return {
        "n": int(e.size),
        "mean": float(e.mean()),
        "median": float(np.median(e)),
        "trimean": trimean(e),
        "best25": float(s[:k].mean()),
        "worst25": float(s[-k:].mean()),
        "max": float(s[-1]),
    }


def delta_e2000_pairwise_spread(lab: np.ndarray) -> dict[str, float]:
    """Spread of a set of Lab colours: mean and max pairwise CIEDE2000.

    This is the N1b self-consistency metric. Given one subject's corrected sclera
    colour under several capture conditions, a perfect illuminant correction would
    collapse them to a single point and every pairwise distance would be zero.
    """
    from colour.difference import delta_E_CIE2000

    lab = np.atleast_2d(np.asarray(lab, dtype=float))
    lab = lab[np.isfinite(lab).all(axis=1)]
    n = len(lab)
    if n < 2:
        return {"n": n, "mean_pairwise": float("nan"), "max_pairwise": float("nan"),
                "mean_to_centroid": float("nan")}
    i, j = np.triu_indices(n, k=1)
    d = np.asarray(delta_E_CIE2000(lab[i], lab[j]), dtype=float)
    centroid = lab.mean(axis=0, keepdims=True)
    dc = np.asarray(delta_E_CIE2000(lab, np.repeat(centroid, n, axis=0)), dtype=float)
    return {
        "n": n,
        "mean_pairwise": float(d.mean()),
        "max_pairwise": float(d.max()),
        "mean_to_centroid": float(dc.mean()),
    }
