"""PPG AC/DC extraction and ratio-of-ratios features.

EXTRACTION METHOD - stated precisely, because every downstream number depends on it
====================================================================================
Signals are 200 Hz, up to 60 s, four wavelengths (660, 730, 850, 940 nm), fingertip
transmission/reflection from `Hb_PPG_Dataset`.

DC (static component)
    4th-order Butterworth low-pass at 0.4 Hz, applied zero-phase (`filtfilt`, so no
    group delay). 0.4 Hz sits below the slowest plausible heart rate (24 bpm) and above
    the slow baseline drift a 60 s recording contains. The DC term carries source
    intensity, sensor gain, static tissue absorption and skin tone - every nuisance the
    normalisation is supposed to cancel.

AC (pulsatile component)
    4th-order Butterworth band-pass 0.5-8.0 Hz, zero-phase. 0.5 Hz = 30 bpm lower
    bound; 8 Hz = 480 bpm upper bound, which also retains the dicrotic notch and the
    first few harmonics that define pulse shape. Amplitude is taken as the ROBUST
    peak-to-peak: the 5th-to-95th percentile range of the band-passed signal, rather
    than max-minus-min, so a single motion spike cannot define it.

THE NORMALISATION BEING TESTED
    ratio      = AC / DC                per wavelength
    R(l1, l2)  = (AC/DC at l1) / (AC/DC at l2)

`AC/DC` cancels source intensity and sensor gain because both scale AC and DC equally.
`R` additionally cancels anything wavelength-independent that survives that. This is a
TIME-domain self-normalisation: the same tissue is measured at two instants of the
cardiac cycle, so the static path is common-mode. It is structurally different from the
spatial ratio that failed in Phase 3.5, where the two regions were different tissue.

⚠️ That structural argument is a HYPOTHESIS. Phase 3.5 showed exact algebraic
cancellation on synthetic data and 139x that residual on real captures. Gate A tests
cancellation ON REAL DATA.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy import signal as sps

FS = 200.0                     # Hz, per the dataset README
WAVELENGTHS = (660, 730, 850, 940)
AC_BAND = (0.5, 8.0)           # Hz
DC_CUTOFF = 0.4                # Hz
FILTER_ORDER = 4
AC_PCTL = (5.0, 95.0)          # robust peak-to-peak percentiles


@dataclass
class ChannelFeatures:
    wavelength: int
    dc: float                  # mean static level (raw ADC units)
    ac: float                  # robust peak-to-peak of the pulsatile component
    ac_dc: float               # the normalised feature
    ac_rms: float
    perfusion_index: float     # 100 * AC/DC, the standard clinical definition
    snr_db: float
    heart_rate_bpm: float
    beat_cv: float             # beat-to-beat amplitude coefficient of variation
    spectral_purity: float     # fraction of band power in the cardiac fundamental
    n_beats: int


def _butter(order, cutoff, btype):
    return sps.butter(order, np.asarray(cutoff) / (FS / 2.0), btype=btype)


def extract_channel(x: np.ndarray) -> ChannelFeatures | None:
    """AC, DC and quality features for one wavelength channel."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < int(5 * FS):          # need at least 5 s
        return None

    b_lo, a_lo = _butter(FILTER_ORDER, DC_CUTOFF, "low")
    b_bp, a_bp = _butter(FILTER_ORDER, AC_BAND, "band")
    dc_sig = sps.filtfilt(b_lo, a_lo, x)
    ac_sig = sps.filtfilt(b_bp, a_bp, x)

    dc = float(np.mean(dc_sig))
    lo, hi = np.percentile(ac_sig, AC_PCTL)
    ac = float(hi - lo)   # robust peak-to-peak over the whole record
    ac_rms = float(np.sqrt(np.mean(ac_sig ** 2)))
    if not np.isfinite(dc) or abs(dc) < 1e-9:
        return None

    # --- cardiac rate and spectral purity ---------------------------------
    f, pxx = sps.welch(ac_sig, fs=FS, nperseg=min(len(ac_sig), int(8 * FS)))
    band = (f >= AC_BAND[0]) & (f <= AC_BAND[1])
    if not band.any() or pxx[band].sum() <= 0:
        return None
    f_peak = float(f[band][np.argmax(pxx[band])])
    # Cardiac power = the fundamental AND its harmonics. A real PPG pulse is not a
    # sinusoid - it has a sharp systolic upstroke and a dicrotic notch, so 2f and 3f
    # carry genuine signal. Counting them as noise (an earlier version did) puts SNR
    # at ~4.5 dB against the dataset's published 16-19 dB, i.e. measures the wrong
    # thing entirely.
    near = np.zeros_like(band)
    for k in (1, 2, 3):
        near |= band & (np.abs(f - k * f_peak) <= 0.15 * f_peak)
    purity = float(pxx[near].sum() / pxx[band].sum())

    # --- beats -------------------------------------------------------------
    min_dist = int(FS / max(f_peak * 1.6, 0.5))
    peaks, _ = sps.find_peaks(ac_sig, distance=max(min_dist, 1),
                              prominence=0.2 * np.std(ac_sig))
    if len(peaks) >= 3:
        amps = ac_sig[peaks]
        beat_cv = float(np.std(amps) / max(abs(np.mean(amps)), 1e-9))
    else:
        beat_cv = float("nan")

    # SNR: cardiac band power against out-of-band power in the same record.
    sig_p = float(pxx[near].sum())
    noise_p = float(pxx[band & ~near].sum())
    snr_db = 10.0 * np.log10(sig_p / max(noise_p, 1e-12))

    # Per-beat AC amplitude, the clinical definition: median trough-to-peak over
    # detected beats. More robust than a whole-record percentile range when perfusion
    # drifts across the 60 s recording.

    if len(peaks) >= 3:
        troughs = np.array([ac_sig[peaks[i]:peaks[i + 1]].min()
                            for i in range(len(peaks) - 1)])
        ac_beat = float(np.median(ac_sig[peaks[:-1]] - troughs))
        if np.isfinite(ac_beat) and ac_beat > 0:
            ac = ac_beat

    return ChannelFeatures(
        wavelength=0, dc=dc, ac=ac, ac_dc=ac / dc, ac_rms=ac_rms,
        perfusion_index=100.0 * ac / dc, snr_db=snr_db,
        heart_rate_bpm=60.0 * f_peak, beat_cv=beat_cv,
        spectral_purity=purity, n_beats=int(len(peaks)),
    )


def extract_subject(signals: np.ndarray) -> dict | None:
    """All channels plus every ratio-of-ratios. `signals` is (n_samples, 4)."""
    out: dict = {}
    chans = {}
    for i, wl in enumerate(WAVELENGTHS):
        f = extract_channel(signals[:, i])
        if f is None:
            return None
        f.wavelength = wl
        chans[wl] = f
        for k, v in asdict(f).items():
            if k != "wavelength":
                out[f"{k}_{wl}"] = v

    # Ratio-of-ratios for every ordered pair: R = (AC/DC)_l1 / (AC/DC)_l2
    for i, a in enumerate(WAVELENGTHS):
        for b in WAVELENGTHS[i + 1:]:
            denom = chans[b].ac_dc
            out[f"R_{a}_{b}"] = chans[a].ac_dc / denom if abs(denom) > 1e-12 else np.nan

    # Aggregate quality summaries.
    out["hr_consistency"] = float(np.std([chans[w].heart_rate_bpm for w in WAVELENGTHS]))
    out["min_snr_db"] = float(min(chans[w].snr_db for w in WAVELENGTHS))
    out["mean_snr_db"] = float(np.mean([chans[w].snr_db for w in WAVELENGTHS]))
    out["mean_purity"] = float(np.mean([chans[w].spectral_purity for w in WAVELENGTHS]))
    out["mean_beat_cv"] = float(np.nanmean([chans[w].beat_cv for w in WAVELENGTHS]))
    return out


def load_subject(csv_path) -> np.ndarray | None:
    try:
        a = np.loadtxt(csv_path, delimiter=",", skiprows=1)
    except Exception:
        return None
    return a if a.ndim == 2 and a.shape[1] == 4 else None
