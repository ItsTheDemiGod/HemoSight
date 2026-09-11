"""N1a: illuminant estimation accuracy across sensors, on the NUS benchmark.

nus8 contains no eyes, so it cannot test sclera segmentation. It CAN test the
estimation mathematics in isolation, which is the point: this phase separates
ESTIMATION error from SEGMENTATION error, and only nus8 can do that.

The ColorChecker's six neutral patches stand in for the reference surface. They are a
good analogue of the sclera precisely because they are *near*-neutral but not exactly
neutral, so the prior ablation here predicts how well a sclera prior must be known.

LEAKAGE CONTROL. The checker is the answer key. It is masked out of every input
except the designated reference patch, using the bounding box in the manifest dilated
by a margin. Any classical baseline computed over an image still containing the
checker would be reading the answer.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .estimators import CLASSICAL, load_linear_png
from .metrics import angular_error, delta_e2000_illuminant, error_summary
from .priors import FixedPopulationPrior, NeutralPrior, OraclePrior, estimate_illuminant


def parse_checker_mask(mask_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse a NUS CHECKER *_mask.txt.

    Row 0 is [y_offset, x_offset, height, width] of the checker crop. Rows 1..48 are
    24 patches, two rows each: the four x-coordinates then the four y-coordinates of
    the patch quadrilateral, RELATIVE to that crop origin.

    Returns (origin_yx, polys) with polys shaped (24, 4, 2) in absolute (x, y).
    """
    m = np.loadtxt(mask_path, delimiter=",")
    origin = np.array([m[0][0], m[0][1]], dtype=float)  # y, x
    polys = []
    for i in range(24):
        xs = m[1 + 2 * i]
        ys = m[2 + 2 * i]
        polys.append(np.stack([xs + origin[1], ys + origin[0]], axis=1))
    return origin, np.asarray(polys)


def checker_bbox(cc_coords: str, shape: tuple[int, int], margin: int = 40) -> tuple[int, int, int, int]:
    """Bounding box of the checker as (y0, y1, x0, x1), dilated by `margin`.

    `cc_coords` in the manifest is (x0, x1, y0, y1).
    """
    x0, x1, y0, y1 = (int(float(v)) for v in str(cc_coords).split(","))
    h, w = shape
    return (max(0, min(y0, y1) - margin), min(h, max(y0, y1) + margin),
            max(0, min(x0, x1) - margin), min(w, max(x1, x0) + margin))


def scene_mask_excluding_checker(shape, cc_coords, valid) -> np.ndarray:
    """Valid, unsaturated pixels with the ColorChecker region removed."""
    m = valid.copy()
    y0, y1, x0, x1 = checker_bbox(cc_coords, shape)
    m[y0:y1, x0:x1] = False
    return m


# The ColorChecker's neutral column, brightest to darkest, as they appear in the NUS
# color.txt (rows 0-5). The darkest patches sit near the noise floor once the dark
# level is removed, so only the brighter ones are used as a reference by default.
NEUTRAL_ROWS = (0, 1, 2, 3)


def reference_rgb_from_color_txt(color_path: str, darklevel: float,
                                 rows: tuple[int, ...] = NEUTRAL_ROWS) -> np.ndarray:
    """Mean dark-subtracted RGB of the chosen neutral patches.

    DARK LEVEL IS NOT OPTIONAL. On Canon600D (dark level 2048) skipping it inflates
    mean angular error from ~0.9 to ~12 degrees. The values in color.txt are raw
    sensor counts and include the black offset.
    """
    col = np.loadtxt(color_path, delimiter=",")
    patches = np.clip(col[list(rows)] - float(darklevel), 0.0, None)
    patches = patches[patches.sum(axis=1) > 0]
    if len(patches) == 0:
        return np.full(3, np.nan)
    return patches.mean(axis=0)


def build_reference_table(manifest: pd.DataFrame) -> pd.DataFrame:
    """Per-image reference-patch RGB and ground-truth illuminant. Cheap: no image IO."""
    rows = []
    for r in manifest.itertuples():
        ref = reference_rgb_from_color_txt(r.color_path, r.darklevel)
        rows.append({
            "image_id": r.image_id,
            "camera": r.camera,
            "ref_r": ref[0], "ref_g": ref[1], "ref_b": ref[2],
            "gt_r": r.illum_r, "gt_g": r.illum_g, "gt_b": r.illum_b,
        })
    return pd.DataFrame(rows)


def fit_oracle(ref: pd.DataFrame) -> OraclePrior:
    """Per-image true reflectance = measured / ground-truth illuminant. The ceiling."""
    table = {}
    for r in ref.itertuples():
        m = np.array([r.ref_r, r.ref_g, r.ref_b], dtype=float)
        g = np.array([r.gt_r, r.gt_g, r.gt_b], dtype=float)
        if not np.isfinite(m).all() or m.sum() <= 0:
            continue
        m = m / np.linalg.norm(m)
        val = m / np.clip(g / np.linalg.norm(g), 1e-8, None)
        table[r.image_id] = val / val.sum() * 3.0
    return OraclePrior(table=table)


def evaluate_reference_method(ref: pd.DataFrame, train_idx, test_idx) -> dict:
    """Reference-patch estimation under three priors, fitted on train, scored on test.

    This is the ablation that matters: the gap between `neutral` and
    `fixed_population` is exactly what knowing the reference reflectance buys, and it
    is the number that predicts how well a sclera prior must be known.
    """
    tr, te = ref.iloc[train_idx], ref.iloc[test_idx]
    meas_tr = tr[["ref_r", "ref_g", "ref_b"]].to_numpy()
    illum_tr = tr[["gt_r", "gt_g", "gt_b"]].to_numpy()

    priors = {
        "neutral": NeutralPrior(),
        "fixed_population": FixedPopulationPrior.fit(meas_tr, illum_tr),
        "oracle_per_image": fit_oracle(ref),
    }

    out = {}
    gt = te[["gt_r", "gt_g", "gt_b"]].to_numpy()
    for name, prior in priors.items():
        est = np.array([
            estimate_illuminant(np.array([r.ref_r, r.ref_g, r.ref_b]), prior, r.image_id)
            for r in te.itertuples()
        ])
        ang = angular_error(est, gt)
        de = delta_e2000_illuminant(est, gt)
        s = error_summary(ang)
        s["deltaE2000_mean"] = float(np.nanmean(de))
        s["deltaE2000_median"] = float(np.nanmedian(de))
        s["prior_value"] = (np.round(prior.reflectance(), 4).tolist()
                            if name != "oracle_per_image" else None)
        out[f"reference_patch/{name}"] = s
    return out


def evaluate_classical(manifest: pd.DataFrame, image_ids) -> dict:
    """Whole-image baselines, with the ColorChecker masked out."""
    sub = manifest[manifest.image_id.isin(set(image_ids))]
    acc: dict[str, list] = {k: [] for k in CLASSICAL}
    gts = []
    for r in sub.itertuples():
        img, valid = load_linear_png(r.png_path, r.darklevel, r.saturation_level)
        mask = scene_mask_excluding_checker(img.shape[:2], r.cc_coords, valid)
        if mask.sum() < 1000:
            continue
        gts.append([r.illum_r, r.illum_g, r.illum_b])
        for name, fn in CLASSICAL.items():
            acc[name].append(fn(img, mask))
    if not gts:
        return {}
    gt = np.asarray(gts)
    out = {}
    for name, ests in acc.items():
        est = np.asarray(ests)
        ang = angular_error(est, gt)
        s = error_summary(ang)
        de = delta_e2000_illuminant(est, gt)
        s["deltaE2000_mean"] = float(np.nanmean(de))
        s["deltaE2000_median"] = float(np.nanmedian(de))
        out[f"classical/{name}"] = s
    return out
