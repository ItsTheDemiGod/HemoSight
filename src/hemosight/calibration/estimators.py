"""Classical colour-constancy baselines, plus linear-image loading for NUS.

Every baseline here is a statistic over the whole image and needs no reference
surface. They are the bar the sclera-referenced method must clear: if a method that
needs a segmented sclera cannot beat grey-world, the segmentation is not earning its
cost.

The general framework (Finlayson & Trezzi) covers grey-world, max-RGB and
shades-of-grey as special cases of a Minkowski norm, and grey-edge extends it to
image derivatives.
"""

from __future__ import annotations

import cv2
import numpy as np


def load_linear_png(path: str, darklevel: float = 0.0,
                    saturation_level: float | None = None) -> np.ndarray:
    """Load a NUS 16-bit linear PNG as float RGB in [0, 1], with a saturation mask.

    CRITICAL: these files are 16-bit. PIL silently truncates them to 8-bit - on a
    typical NUS frame that collapses ~1800 distinct values to ~11, destroying the
    data. cv2.IMREAD_UNCHANGED preserves uint16; cv2 returns BGR, so channels are
    reversed here.

    Returns (image, valid_mask) where `valid_mask` is False wherever any channel was
    at or above the saturation level BEFORE dark subtraction. Saturated pixels carry
    no colour information and must be excluded from every estimator.
    """
    arr = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if arr is None:
        raise FileNotFoundError(path)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    arr = arr[:, :, ::-1].astype(np.float64)  # BGR -> RGB

    sat = float(saturation_level) if saturation_level else float(np.iinfo(np.uint16).max)
    valid = (arr < sat).all(axis=2)

    arr = np.clip(arr - float(darklevel), 0.0, None)
    denom = max(sat - float(darklevel), 1.0)
    return arr / denom, valid


def _masked_pixels(img: np.ndarray, mask: np.ndarray | None) -> np.ndarray:
    """Flatten to (N, 3), keeping only pixels where mask is True."""
    if mask is None:
        return img.reshape(-1, 3)
    return img[mask]


def _normalise(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else np.array([1.0, 1.0, 1.0]) / np.sqrt(3)


def grey_world(img: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """Assume the scene's average reflectance is achromatic."""
    px = _masked_pixels(img, mask)
    return _normalise(px.mean(axis=0)) if len(px) else _normalise(np.ones(3))


def max_rgb(img: np.ndarray, mask: np.ndarray | None = None,
            percentile: float = 100.0) -> np.ndarray:
    """White-patch / max-RGB: the brightest response per channel is the illuminant.

    `percentile` below 100 gives the standard robust variant, which matters because a
    single hot pixel otherwise decides the answer.
    """
    px = _masked_pixels(img, mask)
    if not len(px):
        return _normalise(np.ones(3))
    v = px.max(axis=0) if percentile >= 100 else np.percentile(px, percentile, axis=0)
    return _normalise(v)


def shades_of_grey(img: np.ndarray, mask: np.ndarray | None = None,
                   p: int = 6) -> np.ndarray:
    """Minkowski-norm generalisation. p=1 is grey-world, p->inf is max-RGB.

    p=6 is the value Finlayson & Trezzi report as generally best.
    """
    px = _masked_pixels(img, mask)
    if not len(px):
        return _normalise(np.ones(3))
    return _normalise(np.power(np.power(px, p).mean(axis=0), 1.0 / p))


def grey_edge(img: np.ndarray, mask: np.ndarray | None = None,
              order: int = 1, p: int = 6, sigma: float = 2.0) -> np.ndarray:
    """Grey-edge: the same Minkowski statistic over image derivatives.

    Assumes the average of the scene's reflectance *differences* is achromatic, which
    is often more robust than assuming the average reflectance itself is.
    """
    im = img.copy()
    if sigma > 0:
        k = int(max(3, round(sigma * 4) | 1))
        im = cv2.GaussianBlur(im, (k, k), sigma)
    gx = cv2.Sobel(im, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(im, cv2.CV_64F, 0, 1, ksize=3)
    if order == 2:
        gx = cv2.Sobel(gx, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gy, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(gx ** 2 + gy ** 2)
    px = _masked_pixels(mag, mask)
    if not len(px):
        return _normalise(np.ones(3))
    return _normalise(np.power(np.power(px, p).mean(axis=0), 1.0 / p))


CLASSICAL = {
    "grey_world": lambda im, m: grey_world(im, m),
    "max_rgb": lambda im, m: max_rgb(im, m),
    "max_rgb_p99": lambda im, m: max_rgb(im, m, percentile=99.0),
    "shades_of_grey_p6": lambda im, m: shades_of_grey(im, m, p=6),
    "grey_edge_1": lambda im, m: grey_edge(im, m, order=1, p=6),
    "grey_edge_2": lambda im, m: grey_edge(im, m, order=2, p=6),
}


def robust_patch_rgb(pixels: np.ndarray, low: float = 20.0, high: float = 80.0) -> np.ndarray:
    """Summarise a reference patch's pixels to one RGB triple.

    Uses an inter-percentile mean rather than a plain mean: reference regions contain
    specular highlights at the top end and shadowed or mis-segmented pixels at the
    bottom, and both bias a mean badly. For the sclera the same trimming also
    suppresses residual vasculature.
    """
    px = np.asarray(pixels, dtype=float).reshape(-1, 3)
    px = px[np.isfinite(px).all(axis=1)]
    if len(px) == 0:
        return np.full(3, np.nan)
    lum = px.sum(axis=1)
    lo, hi = np.percentile(lum, [low, high])
    keep = px[(lum >= lo) & (lum <= hi)]
    return (keep if len(keep) else px).mean(axis=0)
