"""Tests for the Phase 2 calibration code.

The important ones here are not the arithmetic checks - they are the two traps that
would each produce a spectacular but meaningless result:

  * reading 16-bit NUS PNGs through an 8-bit path, and
  * measuring sclera self-consistency on the same pixels used to estimate the
    illuminant, which collapses the spread to zero by construction.
"""

from __future__ import annotations

import numpy as np
import pytest

from hemosight.calibration.estimators import (
    grey_world,
    max_rgb,
    robust_patch_rgb,
    shades_of_grey,
)
from hemosight.calibration.metrics import angular_error, error_summary, trimean
from hemosight.calibration.priors import (
    FixedPopulationPrior,
    NeutralPrior,
    estimate_illuminant,
)
from hemosight.calibration.segmentation import vessel_exclusion_mask
from hemosight.calibration.selfconsistency import rgb_to_lab, split_sclera_halves


def test_angular_error_is_scale_invariant():
    """An illuminant is defined only up to scale; the metric must not see brightness."""
    a = np.array([0.5, 0.7, 0.3])
    assert angular_error(a, a * 7.3)[0] == pytest.approx(0.0, abs=1e-9)


def test_angular_error_known_value():
    e = angular_error(np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))[0]
    assert e == pytest.approx(90.0, abs=1e-6)


def test_error_summary_reports_the_nus_set():
    e = np.arange(1.0, 101.0)
    s = error_summary(e)
    assert s["n"] == 100
    assert s["median"] == pytest.approx(50.5)
    assert s["best25"] < s["mean"] < s["worst25"]
    assert s["trimean"] == pytest.approx(trimean(e))


def test_estimate_illuminant_inverts_the_measurement_model():
    """measured = illuminant * reflectance, so dividing by reflectance must recover it."""
    illum = np.array([0.4, 0.8, 0.45])
    refl = np.array([1.1, 1.0, 0.8])
    measured = illum * refl
    prior = FixedPopulationPrior(value=refl)
    est = estimate_illuminant(measured, prior)
    assert angular_error(est, illum)[0] == pytest.approx(0.0, abs=1e-8)


def test_neutral_prior_is_wrong_when_the_surface_is_not_neutral():
    """The premise of the phase: assuming neutrality costs real error."""
    illum = np.array([0.4, 0.8, 0.45])
    refl = np.array([1.25, 1.0, 0.75])  # yellowish, like a sclera
    measured = illum * refl
    naive = angular_error(estimate_illuminant(measured, NeutralPrior()), illum)[0]
    informed = angular_error(estimate_illuminant(measured, FixedPopulationPrior(refl)), illum)[0]
    assert informed < 1e-8
    assert naive > 5.0, "a non-neutral surface must penalise the neutral assumption"


def test_fixed_population_prior_recovers_reflectance():
    rng = np.random.default_rng(0)
    refl = np.array([1.2, 1.0, 0.8])
    illums = rng.uniform(0.2, 1.0, size=(200, 3))
    measured = illums * refl
    p = FixedPopulationPrior.fit(measured, illums)
    ratio = p.value / p.value[1]
    assert ratio == pytest.approx(refl / refl[1], rel=1e-6)


def test_classical_estimators_recover_a_flat_scene():
    """On a uniform grey scene every estimator should return the illuminant."""
    illum = np.array([0.5, 0.8, 0.33])
    img = np.ones((32, 32, 3)) * illum
    for fn in (grey_world, lambda i, m: max_rgb(i, m), lambda i, m: shades_of_grey(i, m, p=6)):
        est = fn(img, None)
        assert angular_error(est, illum)[0] == pytest.approx(0.0, abs=1e-6)


def test_robust_patch_rgb_ignores_specular_and_shadow():
    px = np.tile(np.array([0.4, 0.5, 0.3]), (100, 1))
    px[:5] = 10.0     # specular highlights
    px[5:10] = 0.001  # shadowed / mis-segmented
    v = robust_patch_rgb(px)
    assert v == pytest.approx(np.array([0.4, 0.5, 0.3]), rel=1e-6)


def test_vessel_exclusion_removes_the_red_pixels():
    img = np.ones((20, 20, 3)) * np.array([0.5, 0.5, 0.5])
    sclera = np.ones((20, 20), dtype=bool)
    img[:5, :, 0] = 2.0  # a red band = vasculature
    kept, removed = vessel_exclusion_mask(img, sclera, redness_percentile=75.0)
    assert removed > 0
    assert not kept[:5, :].any(), "the reddest pixels must be dropped"
    assert kept[10:, :].all(), "non-vascular sclera must be retained"


def test_vessel_exclusion_handles_empty_mask():
    img = np.ones((8, 8, 3))
    kept, removed = vessel_exclusion_mask(img, np.zeros((8, 8), bool))
    assert removed == 0.0 and kept.sum() == 0


def test_split_sclera_halves_is_disjoint_and_covers():
    m = np.zeros((10, 10), bool)
    m[2:8, 1:9] = True
    a, b = split_sclera_halves(m)
    assert not (a & b).any(), "halves must be disjoint"
    assert (a | b).sum() == m.sum(), "halves must cover the mask"


def test_selfconsistency_is_circular_on_the_reference_region():
    """Documents WHY the iris is the primary region.

    Correcting by an illuminant estimated from a region, then measuring that same
    region, returns the prior exactly - zero spread regardless of the data. This test
    asserts the degeneracy exists, so that if anyone later 'simplifies' the protocol
    to evaluate on the reference region, the reason it is wrong is written down.
    """
    prior = FixedPopulationPrior(value=np.array([1.2, 1.0, 0.8]))
    labs = []
    for illum in ([0.3, 0.9, 0.5], [0.8, 0.6, 0.2], [0.5, 0.5, 0.9]):
        measured = np.array(illum) * np.array([1.2, 1.0, 0.8])
        est = estimate_illuminant(measured, prior)
        labs.append(rgb_to_lab(measured / est))
    labs = np.array(labs)
    assert np.allclose(labs, labs[0], atol=1e-6), (
        "self-correction on the reference region is degenerate by construction"
    )
