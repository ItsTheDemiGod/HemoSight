"""Tests for the Phase 3 forward model.

The important one is `test_constants_self_validation`: the optical tables are
transcribed rather than read from primary sources, and this check is the only thing
standing between a transcription error and every downstream number. It already caught
two real errors (the 500 nm isosbestic at 515 nm, and a collapsed 529/545 pair).
"""

from __future__ import annotations

import numpy as np
import pytest

from hemosight.simulation import constants as C
from hemosight.simulation.forward import (
    diffuse_reflectance,
    illuminant_spd,
    layered_reflectance,
    simulate_rgb,
    spectrum_to_rgb,
)


def test_constants_self_validation():
    """All six haemoglobin isosbestic points must land where the literature puts them."""
    v = C.validate_constants()
    assert v["all_isosbestic_ok"], v["isosbestic"]
    assert v["hbo2_peak_ok"], f"HbO2 visible peak at {v['hbo2_visible_peak_nm']} nm"
    assert v["red_ratio_ok"], v["deoxy_over_oxy_ratio_650_700nm"]


@pytest.mark.parametrize("iso", C.KNOWN_ISOSBESTIC_NM)
def test_each_isosbestic_point_individually(iso):
    d = C.validate_constants()["isosbestic"][iso]
    assert d["ok"], f"isosbestic {iso} nm found at {d['nearest_crossing_nm']}"


def test_deoxy_absorbs_more_in_the_red():
    """The basis of every colour- and PPG-based haemoglobin method."""
    wl = np.array([660.0])
    assert C.eps_hb(wl)[0] > 5 * C.eps_hbo2(wl)[0]


def test_blood_absorption_scales_with_concentration():
    wl = np.array([540.0])
    a = C.mu_a_blood(wl, 7.0, 0.75)[0]
    b = C.mu_a_blood(wl, 14.0, 0.75)[0]
    assert b == pytest.approx(2 * a, rel=1e-9)


def test_scattering_decreases_with_wavelength():
    """mu_s' falls monotonically across the visible for a Mie+Rayleigh mixture."""
    wl = np.array([450.0, 550.0, 650.0, 750.0, 900.0])
    mus = C.mu_s_reduced(wl)
    assert np.all(np.diff(mus) < 0)


def test_diffuse_reflectance_bounds_and_monotonicity():
    wl = np.array([550.0])
    mus = np.array([20.0])
    high = diffuse_reflectance(wl, np.array([0.1]), mus)[0]
    low = diffuse_reflectance(wl, np.array([50.0]), mus)[0]
    assert 0.0 <= low < high <= 1.0, "more absorption must mean less reflectance"


def test_reflectance_falls_monotonically_with_haemoglobin():
    """Pallor: more haemoglobin, less light returned."""
    wl = C.WAVELENGTHS_NM
    r = [layered_reflectance(wl, h, 0.75, 0.06).mean() for h in (4, 8, 12, 16, 18)]
    assert all(a > b for a, b in zip(r, r[1:])), r


def test_rgb_red_ratio_increases_with_haemoglobin():
    """Higher Hb means relatively more red - the signal the whole project rests on."""
    ratios = []
    for hb in (4, 8, 12, 18):
        _refl, rgb = simulate_rgb(hb)
        ratios.append(rgb[0] / rgb[1])
    assert all(a < b for a, b in zip(ratios, ratios[1:])), ratios


def test_the_haemoglobin_signal_is_small():
    """Guards the gate result itself.

    The Phase 3 conclusion is that the colour change per g/dL (~0.45 dE2000) is far
    below the achievable calibration residual (3.935). If a future change to the
    forward model made the signal dramatically larger, the gate verdict would need
    revisiting - so the magnitude is pinned here deliberately.
    """
    from hemosight.calibration.metrics import delta_e2000_illuminant

    sig = np.mean([
        float(delta_e2000_illuminant(simulate_rgb(h)[1], simulate_rgb(h + 1)[1])[0])
        for h in range(4, 18)
    ])
    assert 0.2 < sig < 1.5, f"signal {sig:.3f} dE2000/g/dL is outside the measured range"
    assert sig < 3.935, "if the signal exceeded the calibration residual, revisit the gate"


def test_oxygenation_barely_changes_rgb_but_melanin_wrecks_it():
    """Task 4's two headline sensitivities, pinned as regression guards."""
    from hemosight.calibration.metrics import delta_e2000_illuminant

    base = simulate_rgb(12.0, oxygenation=0.75, melanin=0.0)[1]
    ox = simulate_rgb(12.0, oxygenation=1.00, melanin=0.0)[1]
    mel = simulate_rgb(12.0, oxygenation=0.75, melanin=0.005)[1]
    d_ox = float(delta_e2000_illuminant(base, ox)[0])
    d_mel = float(delta_e2000_illuminant(base, mel)[0])
    assert d_mel > d_ox, "melanin must perturb colour more than full oxygenation swing"


def test_illuminant_spd_blackbody_and_named():
    wl = np.linspace(450, 700, 20)
    d65 = illuminant_spd(wl, "D65")
    warm = illuminant_spd(wl, "CCT:2700")
    cool = illuminant_spd(wl, "CCT:6500")
    assert d65.max() == pytest.approx(1.0, abs=1e-6)
    # A 2700 K radiator is red-weighted relative to 6500 K.
    assert (warm[-1] / warm[0]) > (cool[-1] / cool[0])


def test_spectrum_to_rgb_of_a_perfect_reflector_is_neutral():
    wl = C.WAVELENGTHS_NM
    from hemosight.simulation.forward import camera_sensitivities

    rgb = spectrum_to_rgb(wl, np.ones_like(wl), illuminant_spd(wl, "D65"),
                          camera_sensitivities(wl))
    assert np.allclose(rgb, rgb[0], rtol=1e-6), "unit reflectance must normalise to white"


# --- Phase 3.5: sourced constants and the ratio algebra ----------------------

def test_constants_now_load_from_downloaded_files():
    """The spectral tables must come from data/raw/optical_constants/, not memory."""
    from hemosight.simulation.optical_data import prahl_hemoglobin, spectral_lib

    p = prahl_hemoglobin()
    assert "optical_constants" in p["source"]
    assert len(p["wavelength_nm"]) > 300
    s = spectral_lib()
    assert "spectralLIB" in s["source"]
    assert len(s["wavelength_nm"]) == 701


def test_melanin_is_a_power_law_not_measured_data():
    """Guards the warning in constants.py: if this ever stops being an exact power
    law the source has changed and the sweep-never-fix advice needs revisiting."""
    from hemosight.simulation.optical_data import melanin_powerlaw_fit

    f = melanin_powerlaw_fit()
    assert f["is_essentially_a_power_law"]
    assert 2.5 < -f["exponent"] < 4.5


def test_camspec_parses_all_28_cameras():
    from hemosight.simulation.optical_data import camspec_database

    db = camspec_database()
    assert len(db["cameras"]) == 28, "grid is 400-720 nm (33 points), not 400-700"
    assert len(db["wavelength_nm"]) == 33
    for v in db["cameras"].values():
        assert v.shape == (33, 3)


def test_ratio_cancels_a_diagonal_illuminant_exactly():
    """The Phase 3.5 premise. With a plain mean the illuminant cancels to machine
    precision - so the observed failure on real data is a property of the data, not
    of the algebra or the implementation."""
    import sys

    sys.path.insert(0, "scripts")
    from phase3_5_task1_cancellation import ratio_feature

    rng = np.random.default_rng(0)
    region_a = rng.uniform(0.1, 0.6, size=(500, 3))
    region_b = rng.uniform(0.2, 0.8, size=(500, 3))
    base = ratio_feature(region_a.mean(axis=0), region_b.mean(axis=0))
    for gain in ([1.3, 1.0, 0.7], [0.6, 1.1, 1.4], [2.0, 0.5, 1.2]):
        g = np.asarray(gain)
        r = ratio_feature((region_a * g).mean(axis=0), (region_b * g).mean(axis=0))
        assert np.allclose(r, base, atol=1e-12), f"illuminant must cancel for gain {gain}"


def test_ratio_does_not_cancel_a_non_diagonal_transform():
    """A channel-mixing transform (overlapping sensitivities) is NOT cancelled -
    which is the mechanism behind the surviving phone effect."""
    import sys

    sys.path.insert(0, "scripts")
    from phase3_5_task1_cancellation import ratio_feature

    rng = np.random.default_rng(1)
    a = rng.uniform(0.1, 0.6, size=(500, 3))
    b = rng.uniform(0.2, 0.8, size=(500, 3))
    mix = np.array([[0.9, 0.08, 0.02], [0.05, 0.9, 0.05], [0.02, 0.1, 0.88]])
    base = ratio_feature(a.mean(axis=0), b.mean(axis=0))
    mixed = ratio_feature((a @ mix.T).mean(axis=0), (b @ mix.T).mean(axis=0))
    assert not np.allclose(mixed, base, atol=1e-3)
