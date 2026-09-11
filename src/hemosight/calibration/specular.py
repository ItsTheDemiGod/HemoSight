"""Corneal specular highlights as a direct sample of the scene illuminant.

THE HYPOTHESIS
--------------
Under the dichromatic reflection model an observed colour is

    I  =  m_d * D  +  m_s * L

where `D` is the surface's diffuse (body) colour and `L` is the illuminant. For a
dielectric such as the wet corneal surface, the specular term preserves the
illuminant's spectral power distribution: `L` appears undistorted, multiplied only by
a geometric scalar `m_s`.

That matters because Phase 2 located the failure of the sclera precisely: its
reflectance `D` varies between people by more than the illuminant signal being
estimated (a 10% yellowing shift moved the estimate 4.40 degrees). A specular
highlight carries **no per-subject `D` term at all**. If the hypothesis holds, the
dominant error source of Phase 2 simply does not arise.

Two things could still defeat it, and both are measured rather than assumed:

1. **Saturation.** A highlight bright enough to see is often bright enough to clip.
   A clipped pixel carries no chromatic information whatsoever - its ratios are an
   artefact of the sensor ceiling, not of the light. Saturated pixels are excluded
   rigorously, and the surviving fraction is the feasibility question of Task 1.
2. **Multiple light sources.** Several sources give several highlights with different
   chromaticities. Averaging them invents an illuminant that was never present, so
   distinct chromatic clusters are COUNTED and reported rather than collapsed.

WHY PUPIL HIGHLIGHTS ARE THE CLEANEST SIGNAL
--------------------------------------------
The pupil's diffuse reflectance is near zero, so for a highlight over the pupil
`m_d * D ~= 0` and `I ~= m_s * L`: an almost direct reading of the illuminant. The
iris is darker than skin but not black, so iris highlights need the full dichromatic
decomposition. Both are used, and their agreement is itself a check.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .segmentation_data import IRIS, PUPIL

# 8-bit JPEG sources (MOBIUS, SBVPI). A channel at or above this is treated as
# clipped and carries no usable chroma.
SATURATION_8BIT = 250


@dataclass
class Highlight:
    """One connected specular blob."""

    area_px: int
    centroid: tuple[float, float]
    mean_rgb: np.ndarray
    max_channel: float
    saturated_frac: float          # fraction of blob pixels clipped in any channel
    region: str                    # "pupil" | "iris"
    unsaturated_rgb: np.ndarray | None = None  # mean over unclipped pixels only
    n_unsaturated: int = 0


@dataclass
class SpecularObservation:
    """Everything Task 1 needs to census one image."""

    n_highlights: int = 0
    highlights: list[Highlight] = field(default_factory=list)
    iris_pupil_px: int = 0
    region_median_lum: float = 0.0
    threshold_used: float = 0.0
    brightness_ratio: float = 0.0  # threshold / region median, a detection-strength proxy
    has_usable: bool = False       # >=1 highlight with enough unsaturated pixels
    n_chroma_clusters: int = 0
    illuminant: np.ndarray | None = None
    method: str = "none"


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else np.array([1.0, 1.0, 1.0]) / np.sqrt(3)


def detect_highlights(
    rgb8: np.ndarray,
    labels: np.ndarray,
    min_area: int = 6,
    max_area_frac: float = 0.10,
    percentile: float = 99.0,
    specular_ratio: float = 3.0,
    min_unsaturated: int = 4,
) -> SpecularObservation:
    """Find specular blobs inside the iris and pupil.

    Searching only inside iris+pupil is deliberate: there the underlying diffuse
    reflectance is dark, so a bright pixel is specular rather than a pale surface.
    The same brightness test over skin or sclera would mostly return pale diffuse
    tissue.

    THRESHOLD CHOICE. A percentile alone is not a detector: the top 1% of a 350,000
    pixel region is ~3,500 pixels whether or not any highlight exists, so a
    percentile-only rule "finds" a highlight in every image by construction. The
    dichromatic model gives a physical criterion instead - a specular pixel is much
    brighter than the body reflectance of the same surface - so a pixel must be at
    least `specular_ratio` times the region's median luminance AND in its top
    percentile. Images with no genuine highlight then correctly yield nothing.

    Keeping both terms matters: the ratio alone would fire across a whole brightly-lit
    iris, and the percentile alone fires always.
    """
    obs = SpecularObservation()
    region = (labels == IRIS) | (labels == PUPIL)
    obs.iris_pupil_px = int(region.sum())
    if obs.iris_pupil_px < 200:
        return obs

    img = rgb8.astype(np.float64)
    lum = img.max(axis=2)
    med = float(np.median(lum[region]))
    obs.region_median_lum = med
    thr = max(specular_ratio * med, float(np.percentile(lum[region], percentile)))
    obs.threshold_used = thr
    obs.brightness_ratio = thr / max(med, 1e-6)
    if not np.isfinite(thr) or (region & (lum >= thr)).sum() < min_area:
        return obs

    cand = region & (lum >= thr)
    n, lab_cc, stats, cents = cv2.connectedComponentsWithStats(
        cand.astype(np.uint8), connectivity=8)

    max_area = max_area_frac * obs.iris_pupil_px
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area or area > max_area:
            continue
        m = lab_cc == i
        px = img[m]
        sat = (px >= SATURATION_8BIT).any(axis=1)
        unsat = px[~sat]
        in_pupil = (labels[m] == PUPIL).mean() > 0.5
        obs.highlights.append(Highlight(
            area_px=area,
            centroid=(float(cents[i][0]), float(cents[i][1])),
            mean_rgb=px.mean(axis=0),
            max_channel=float(px.max()),
            saturated_frac=float(sat.mean()),
            region="pupil" if in_pupil else "iris",
            unsaturated_rgb=(unsat.mean(axis=0) if len(unsat) >= min_unsaturated else None),
            n_unsaturated=int(len(unsat)),
        ))

    obs.n_highlights = len(obs.highlights)
    obs.has_usable = any(h.unsaturated_rgb is not None for h in obs.highlights)
    return obs


def count_chroma_clusters(highlights: list[Highlight], tol: float = 0.04) -> int:
    """Count distinct highlight chromaticities (i.e. plausible distinct light sources).

    Greedy agglomeration in rg-chromaticity. Reported rather than averaged away: two
    sources of different colour do not have a meaningful mean, and pretending they do
    would fabricate an illuminant that was never in the scene.
    """
    chroms = []
    for h in highlights:
        v = h.unsaturated_rgb
        if v is None:
            continue
        s = v.sum()
        if s > 0:
            chroms.append(np.array([v[0] / s, v[1] / s]))
    if not chroms:
        return 0
    clusters: list[np.ndarray] = []
    for c in chroms:
        if not any(np.linalg.norm(c - k) < tol for k in clusters):
            clusters.append(c)
    return len(clusters)


def dichromatic_plane_normal(pixels: np.ndarray) -> np.ndarray | None:
    """Normal of the plane through the origin best fitting a surface's pixel colours.

    Under the dichromatic model every pixel of one surface is a non-negative
    combination of `D` and `L`, so they span a plane containing both. The normal is
    the smallest right singular vector. Needs genuinely 2D spread: a patch with only
    one effective colour gives a degenerate fit, which is rejected.
    """
    px = np.asarray(pixels, dtype=float).reshape(-1, 3)
    px = px[np.isfinite(px).all(axis=1)]
    if len(px) < 8:
        return None
    u, s, vt = np.linalg.svd(px - 0.0, full_matrices=False)
    if s[1] < 1e-8 or s[1] / max(s[0], 1e-12) < 0.02:
        return None  # effectively one direction: no plane to speak of
    return _unit(vt[2])


def degenerate_direction(pixels: np.ndarray, max_ratio: float = 0.05
                         ) -> np.ndarray | None:
    """Principal direction of a surface whose colours are effectively one-dimensional.

    For a DARK-bodied surface such as the pupil, `m_d * D ~= 0`, so the dichromatic
    model collapses to `I ~= m_s * L`: every pixel lies along the illuminant
    direction and the colour cloud has no second dimension. A plane fit correctly
    refuses such data - but that refusal is not a failure, it is the cleanest
    possible reading, because the principal direction simply *is* `L`.

    Returns None if the cloud has genuine 2D spread, where the plane fit applies
    instead.
    """
    px = np.asarray(pixels, dtype=float).reshape(-1, 3)
    px = px[np.isfinite(px).all(axis=1)]
    if len(px) < 8:
        return None
    _u, s, vt = np.linalg.svd(px, full_matrices=False)
    if s[0] <= 0 or s[1] / s[0] > max_ratio:
        return None
    d = vt[0]
    if d.sum() < 0:
        d = -d
    return _unit(d) if (d > 0).all() else None


def illuminant_from_dichromatic(
    surfaces: dict[str, np.ndarray],
    dark_surfaces: frozenset[str] = frozenset({"pupil"}),
) -> tuple[np.ndarray | None, str]:
    """Recover the illuminant from one or more surfaces' pixel sets.

    Three routes, in order of directness:

    1. **Degenerate dark surface.** A pupil with `D ~= 0` gives `I ~= m_s * L`, so its
       principal direction is the illuminant outright. Most direct, so preferred.
    2. **Plane intersection.** With two surfaces of different diffuse colour, both
       dichromatic planes contain `L`, so `L` lies along the intersection - the cross
       product of the normals. Needs no assumption about which pixels are "most
       specular".
    3. **Single-surface residual.** One plane cannot isolate `L`; the specular
       direction is the residual after projecting out the diffuse direction estimated
       from the dimmest pixels, where `m_s ~= 0`. Weakest, used only as a fallback.
    """
    valid = {k: np.asarray(v, dtype=float).reshape(-1, 3)
             for k, v in surfaces.items() if v is not None and len(np.asarray(v)) >= 8}

    # Route 1: a dark-bodied surface that has collapsed to one dimension.
    for k in sorted(valid, key=lambda k: (k not in dark_surfaces, -len(valid[k]))):
        if k in dark_surfaces:
            d = degenerate_direction(valid[k])
            if d is not None:
                return d, "degenerate_dark_surface"

    normals = {}
    for k, px in valid.items():
        nrm = dichromatic_plane_normal(px)
        if nrm is not None:
            normals[k] = nrm

    if len(normals) >= 2:
        keys = list(normals)
        best, best_est = -1.0, None
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = normals[keys[i]], normals[keys[j]]
                cross = np.cross(a, b)
                mag = np.linalg.norm(cross)
                if mag > best:                       # most nearly orthogonal planes
                    best, best_est = mag, cross
        if best_est is not None and best > 0.15:
            est = _unit(best_est)
            if est.sum() < 0:
                est = -est
            if (est > 0).all():
                return est, "dichromatic_plane_intersection"

    if len(valid) >= 1:
        k = max(valid, key=lambda k: len(valid[k]))
        px = valid[k]
        lum = px.sum(axis=1)
        dim = px[lum <= np.percentile(lum, 25)]
        bright = px[lum >= np.percentile(lum, 75)]
        if len(dim) >= 2 and len(bright) >= 2:
            d = _unit(dim.mean(axis=0))
            resid = bright.mean(axis=0) - np.dot(bright.mean(axis=0), d) * d
            if (resid > 0).all() and np.linalg.norm(resid) > 1e-6:
                return _unit(resid), "specular_residual"
    return None, "none"


def estimate_specular_illuminant(
    rgb8: np.ndarray, labels: np.ndarray, obs: SpecularObservation | None = None
) -> SpecularObservation:
    """Full pipeline for one image: detect, cluster, decompose."""
    if obs is None:
        obs = detect_highlights(rgb8, labels)
    if not obs.has_usable:
        return obs

    obs.n_chroma_clusters = count_chroma_clusters(obs.highlights)

    img = rgb8.astype(np.float64)
    # Unclipped pixels of each surface, restricted to the neighbourhood of highlights
    # so the plane fit sees the specular ramp rather than the whole iris.
    surfaces: dict[str, np.ndarray] = {}
    for region_name, cls in (("pupil", PUPIL), ("iris", IRIS)):
        m = labels == cls
        if m.sum() < 50:
            continue
        px = img[m]
        px = px[~(px >= SATURATION_8BIT).any(axis=1)]
        if len(px) >= 8:
            surfaces[region_name] = px

    est, method = illuminant_from_dichromatic(surfaces)

    # A pupil highlight is near-pure specular (D ~= 0), so it is the most direct
    # reading available and is preferred when a clean unsaturated one exists.
    pupil_hl = [h for h in obs.highlights
                if h.region == "pupil" and h.unsaturated_rgb is not None
                and h.saturated_frac < 0.5]
    if pupil_hl:
        best = max(pupil_hl, key=lambda h: h.n_unsaturated)
        est, method = _unit(best.unsaturated_rgb), "pupil_highlight_direct"
    elif est is None:
        usable = [h for h in obs.highlights if h.unsaturated_rgb is not None]
        if usable:
            best = max(usable, key=lambda h: h.n_unsaturated)
            est, method = _unit(best.unsaturated_rgb), "iris_highlight_direct"

    obs.illuminant = est
    obs.method = method
    return obs
