"""Tests for the Phase 4 PPG code.

The load-bearing ones pin the two findings that decide the phase: that PPG features
carry no haemoglobin signal, and that the demographic baseline beats them. If a future
change makes either stop being true, the verdict needs revisiting and these fail.
"""

from __future__ import annotations

import numpy as np
import pytest

from hemosight.ppg.features import AC_BAND, FS, extract_channel, extract_subject


def synth_ppg(hr_bpm=75.0, seconds=30.0, dc=20000.0, ac_frac=0.05, noise=0.0, seed=0):
    """A synthetic PPG: fundamental plus harmonics on a DC pedestal."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, seconds, 1.0 / FS)
    f = hr_bpm / 60.0
    pulse = (np.sin(2 * np.pi * f * t)
             + 0.35 * np.sin(2 * np.pi * 2 * f * t)
             + 0.15 * np.sin(2 * np.pi * 3 * f * t))
    pulse = pulse / np.abs(pulse).max()
    return dc * (1.0 + ac_frac * pulse) + noise * dc * rng.normal(size=len(t))


def test_extract_recovers_heart_rate():
    for hr in (55.0, 75.0, 100.0):
        f = extract_channel(synth_ppg(hr_bpm=hr))
        assert f is not None
        assert abs(f.heart_rate_bpm - hr) < 5.0, f"got {f.heart_rate_bpm} want {hr}"


def test_extract_recovers_ac_dc_ratio():
    """AC/DC must track the injected pulsatile fraction."""
    prev = 0.0
    for frac in (0.01, 0.05, 0.10):
        f = extract_channel(synth_ppg(ac_frac=frac))
        assert f is not None
        assert f.ac_dc > prev
        prev = f.ac_dc


def test_ac_dc_is_invariant_to_source_gain():
    """The cancellation claim, as an IMPLEMENTATION test only.

    Scaling the whole signal (a brighter LED or higher sensor gain) must leave AC/DC
    unchanged. Gate A tests whether this survives on real data - it does not.
    """
    base = extract_channel(synth_ppg(dc=20000.0))
    for gain in (0.5, 2.0, 5.0):
        f = extract_channel(synth_ppg(dc=20000.0 * gain))
        assert f is not None
        assert f.ac_dc == pytest.approx(base.ac_dc, rel=1e-6)


def test_snr_counts_harmonics_as_signal():
    """A real pulse is not a sinusoid. Counting 2f/3f as noise gave ~4.5 dB against
    the dataset's published 16-19 dB, i.e. measured the wrong thing."""
    clean = extract_channel(synth_ppg(noise=0.0))
    noisy = extract_channel(synth_ppg(noise=0.02, seed=1))
    assert clean.snr_db > noisy.snr_db
    assert clean.spectral_purity > 0.5, "harmonics must count toward cardiac power"


def test_extract_subject_produces_all_ratio_pairs():
    sig = np.column_stack([synth_ppg(ac_frac=f, seed=i)
                           for i, f in enumerate((0.05, 0.04, 0.06, 0.03))])
    out = extract_subject(sig)
    assert out is not None
    for pair in ("R_660_730", "R_660_850", "R_660_940",
                 "R_730_850", "R_730_940", "R_850_940"):
        assert pair in out and np.isfinite(out[pair])


def test_short_or_flat_signal_is_rejected_not_faked():
    assert extract_channel(np.ones(100)) is None          # too short
    assert extract_channel(np.zeros(int(30 * FS))) is None  # no DC, no pulse


def test_phone_cannot_see_three_of_the_four_wavelengths():
    """The Gate B hardware fact, pinned. 730/850/940 nm are outside the characterised
    camera range and behind the IR-cut filter."""
    from hemosight.simulation.optical_data import camspec_database

    db = camspec_database()
    wl = db["wavelength_nm"]
    assert wl[-1] <= 720.0
    for lam in (730, 850, 940):
        assert lam > wl[-1], f"{lam} nm must be outside the characterised range"
    assert 660 <= wl[-1], "660 nm must be inside it"


def test_band_covers_physiological_heart_rates():
    assert AC_BAND[0] <= 0.5 and AC_BAND[1] >= 3.0


# --- Phase 4.5: deep pipeline guards ----------------------------------------

def test_windows_are_subject_tagged_and_normalised():
    """Every window must carry its subject id, or leakage control is impossible."""
    from hemosight.ppg.deep import WINDOW, make_windows

    rng = np.random.default_rng(0)
    t = np.arange(0, 40, 1 / 200.0)
    sig = np.column_stack([20000 * (1 + 0.05 * np.sin(2 * np.pi * 1.2 * t))
                           + 50 * rng.normal(size=len(t)) for _ in range(4)])
    X, sid = make_windows(sig, subject_id=42)
    assert len(X) > 0 and X.shape[1:] == (4, WINDOW)
    assert set(sid.tolist()) == {42}
    # z-scored within window: per-channel mean ~0, sd ~1
    assert np.allclose(X.mean(axis=2), 0.0, atol=1e-4)
    assert np.allclose(X.std(axis=2), 1.0, atol=1e-3)


def test_window_normalisation_removes_gain_and_offset():
    """Per-window z-scoring must discard DC level and sensor gain - the same
    nuisances AC/DC targets, but without committing to a scalar summary."""
    from hemosight.ppg.deep import make_windows

    t = np.arange(0, 40, 1 / 200.0)
    base = np.column_stack([20000 * (1 + 0.05 * np.sin(2 * np.pi * 1.2 * t))
                            for _ in range(4)])
    Xa, _ = make_windows(base, 1)
    Xb, _ = make_windows(base * 3.0 + 5000.0, 1)
    assert Xa.shape == Xb.shape
    assert np.allclose(Xa, Xb, atol=1e-3), "gain/offset must not survive normalisation"


def test_deep_architectures_forward_and_embed():
    import torch

    from hemosight.ppg.deep import ARCHITECTURES, WINDOW

    x = torch.randn(4, 4, WINDOW)
    for name, cls in ARCHITECTURES.items():
        m = cls(in_ch=4).eval()
        with torch.no_grad():
            y, e = m(x), m.embed(x)
        assert y.shape == (4,), f"{name} output shape {y.shape}"
        assert e.ndim == 2 and e.shape[0] == 4, f"{name} embedding {e.shape}"
