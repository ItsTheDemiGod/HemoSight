"""Tests for the Phase 2.5 specular code.

The load-bearing test is `test_dichromatic_intersection_recovers_illuminant`: it
builds two synthetic surfaces under a known illuminant from the dichromatic model and
checks the plane-intersection actually returns that illuminant. Without it, a
decomposition that silently degrades to "mean of bright pixels" would be
indistinguishable from a working one.
"""

from __future__ import annotations

import numpy as np
import pytest

from hemosight.calibration.metrics import angular_error
from hemosight.calibration.segmentation_data import IRIS, PUPIL
from hemosight.calibration.specular import (
    SATURATION_8BIT,
    degenerate_direction,
    Highlight,
    count_chroma_clusters,
    detect_highlights,
    dichromatic_plane_normal,
    illuminant_from_dichromatic,
)


def _dichromatic_pixels(diffuse, illum, n=200, seed=0):
    """Synthesise one surface under the dichromatic model I = m_d*D + m_s*L."""
    rng = np.random.default_rng(seed)
    md = rng.uniform(0.2, 1.0, size=(n, 1))
    ms = rng.uniform(0.0, 0.8, size=(n, 1))
    return md * np.asarray(diffuse) + ms * np.asarray(illum)


def test_dichromatic_plane_normal_is_orthogonal_to_both_components():
    D = np.array([0.6, 0.3, 0.2])
    L = np.array([0.5, 0.7, 0.5])
    px = _dichromatic_pixels(D, L)
    n = dichromatic_plane_normal(px)
    assert n is not None
    assert abs(float(n @ D)) < 1e-6
    assert abs(float(n @ L)) < 1e-6


def test_dichromatic_intersection_recovers_illuminant():
    """Two surfaces of different body colour: the plane intersection must be L."""
    L = np.array([0.45, 0.78, 0.44])
    surfaces = {
        "iris": _dichromatic_pixels([0.60, 0.30, 0.18], L, seed=1),
        "pupil": _dichromatic_pixels([0.05, 0.05, 0.06], L, seed=2),
    }
    est, method = illuminant_from_dichromatic(surfaces)
    assert est is not None
    # The pupil (D ~= 0) collapses to one dimension, which is the MOST direct route:
    # its principal direction is L itself. Either that or the plane intersection is a
    # correct answer; both must land on the true illuminant.
    assert method in ("degenerate_dark_surface", "dichromatic_plane_intersection")
    assert angular_error(est, L)[0] < 2.0


def test_single_surface_falls_back_not_crashes():
    L = np.array([0.45, 0.78, 0.44])
    est, method = illuminant_from_dichromatic(
        {"iris": _dichromatic_pixels([0.6, 0.3, 0.18], L, seed=3)})
    assert method in ("specular_residual", "dichromatic_plane_intersection", "none")
    if est is not None:
        assert np.isfinite(est).all()


def test_degenerate_surface_is_rejected():
    """A patch with a single effective colour has no plane to fit."""
    px = np.tile(np.array([0.4, 0.5, 0.3]), (100, 1))
    assert dichromatic_plane_normal(px) is None


def test_too_few_pixels_returns_none():
    assert dichromatic_plane_normal(np.random.rand(3, 3)) is None


def test_chroma_clusters_counts_distinct_sources():
    def hl(rgb):
        return Highlight(area_px=10, centroid=(0, 0), mean_rgb=np.array(rgb),
                         max_channel=float(max(rgb)), saturated_frac=0.0,
                         region="pupil", unsaturated_rgb=np.array(rgb), n_unsaturated=10)

    warm, cool = [200.0, 150.0, 90.0], [90.0, 150.0, 200.0]
    assert count_chroma_clusters([hl(warm), hl(warm)]) == 1
    assert count_chroma_clusters([hl(warm), hl(cool)]) == 2
    assert count_chroma_clusters([]) == 0


def test_saturated_highlight_yields_no_usable_rgb():
    """Clipped pixels carry no chroma; they must not become an illuminant estimate."""
    img = np.full((60, 60, 3), 20, dtype=np.uint8)
    labels = np.full((60, 60), PUPIL, dtype=np.uint8)
    img[28:33, 28:33] = 255  # fully blown highlight
    obs = detect_highlights(img, labels, min_area=4)
    assert obs.n_highlights >= 1
    assert all(h.unsaturated_rgb is None or h.saturated_frac < 1.0 for h in obs.highlights)
    blown = [h for h in obs.highlights if h.saturated_frac > 0.99]
    assert all(h.unsaturated_rgb is None for h in blown)


def test_uniform_region_yields_no_highlight():
    """A flat iris must not produce a 'highlight' just because some pixel is brightest.

    This is the failure mode of a percentile-only detector: the top 1% of any region
    is non-empty by construction.
    """
    rng = np.random.default_rng(0)
    img = (rng.normal(60, 2, size=(200, 200, 3))).clip(0, 255).astype(np.uint8)
    labels = np.full((200, 200), IRIS, dtype=np.uint8)
    obs = detect_highlights(img, labels)
    assert obs.n_highlights == 0, "flat region must yield no specular detection"


def test_genuine_highlight_is_detected():
    img = np.full((200, 200, 3), 30, dtype=np.uint8)
    labels = np.full((200, 200), IRIS, dtype=np.uint8)
    img[95:105, 95:105] = [200, 180, 140]   # bright, unclipped, warm
    obs = detect_highlights(img, labels, min_area=4)
    assert obs.n_highlights == 1
    h = obs.highlights[0]
    assert h.unsaturated_rgb is not None
    assert h.saturated_frac == 0.0
    assert h.max_channel < SATURATION_8BIT


def test_detection_requires_the_region_to_exist():
    img = np.full((50, 50, 3), 40, dtype=np.uint8)
    labels = np.zeros((50, 50), dtype=np.uint8)  # no iris/pupil at all
    obs = detect_highlights(img, labels)
    assert obs.n_highlights == 0 and obs.iris_pupil_px == 0


@pytest.mark.parametrize("scale", [0.5, 1.0, 2.0])
def test_specular_estimate_is_scale_invariant(scale):
    """An illuminant estimate is defined up to scale; brightness must not change it."""
    L = np.array([0.45, 0.78, 0.44])
    surfaces = {
        "iris": _dichromatic_pixels([0.6, 0.3, 0.18], L, seed=5) * scale,
        "pupil": _dichromatic_pixels([0.05, 0.05, 0.06], L, seed=6) * scale,
    }
    est, _ = illuminant_from_dichromatic(surfaces)
    assert est is not None
    assert angular_error(est, L)[0] < 2.0


def test_plane_intersection_route_when_neither_surface_is_dark():
    """With two genuinely 2D surfaces, the intersection route must fire and be right."""
    L = np.array([0.45, 0.78, 0.44])
    surfaces = {
        "iris": _dichromatic_pixels([0.60, 0.30, 0.18], L, seed=11),
        "skin": _dichromatic_pixels([0.55, 0.40, 0.35], L, seed=12),
    }
    est, method = illuminant_from_dichromatic(surfaces, dark_surfaces=frozenset())
    assert est is not None
    assert method == "dichromatic_plane_intersection"
    assert angular_error(est, L)[0] < 2.0


def test_degenerate_direction_recovers_l_for_a_dark_surface():
    L = np.array([0.45, 0.78, 0.44])
    px = _dichromatic_pixels([0.02, 0.02, 0.02], L, seed=13)
    d = degenerate_direction(px)
    assert d is not None
    assert angular_error(d, L)[0] < 2.0


def test_degenerate_direction_rejects_a_2d_cloud():
    L = np.array([0.45, 0.78, 0.44])
    px = _dichromatic_pixels([0.60, 0.30, 0.18], L, seed=14)
    assert degenerate_direction(px) is None
