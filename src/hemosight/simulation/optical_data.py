"""Loaders for the DOWNLOADED optical constants and camera sensitivities.

These replace the transcribed tables that Phase 3 used. Files live under
`data/raw/optical_constants/` and `data/raw/camera_sensitivities/`, are read-only,
and each carries its provenance in the sibling SOURCES.md.

PRIMARY SOURCE HIERARCHY (as specified by the user):
  * `spectralLIB.mat` - the mcxyz spectral library (Jacques). Carries oxy- and
    deoxy-haemoglobin, water, melanin, fat and reduced scattering on one common
    300-1000 nm / 1 nm grid. This is the PRIMARY source, because everything is
    internally consistent with everything else.
  * `hemoglobin_prahl.txt` - the Prahl compilation of Gratzer and Kollias, 250-1000
    nm at 2 nm. Higher resolution for haemoglobin specifically, and used as the
    CROSS-CHECK on spectralLIB's haemoglobin.

⚠️  MELANIN IS NOT MEASURED DATA. See `melanin_absorption()`.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from ..io import paths

OPTICAL_DIR = paths.RAW / "optical_constants"
CAMERA_DIR = paths.RAW / "camera_sensitivities"

# Files arrived with doubled extensions; accept either form.
_PRAHL = ("hemoglobin_prahl.txt.txt", "hemoglobin_prahl.txt")
_SPECLIB = ("spectralLIB.mat",)
_CAMSPEC = ("camspec_database.txt.txt", "camspec_database.txt")
_MOBILE_AVG = ("average.txt",)

# Molar mass per haem, g/mol. The Prahl tables are per-haem (64,500 / 4).
MW_HB_PER_HAEM = 64500.0 / 4.0


def _find(directory, names):
    for n in names:
        p = directory / n
        if p.exists():
            return p
    raise FileNotFoundError(f"none of {names} in {directory}")


# --------------------------------------------------------------------------- #
# spectralLIB.mat - PRIMARY
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def spectral_lib() -> dict:
    """mcxyz spectral library: mu_a in cm^-1 for pure chromophores, plus mu_s'.

    `muaoxy` / `muadeoxy` are the absorption coefficients of WHOLE BLOOD at a
    reference haemoglobin concentration of 150 g/L, which is the mcxyz convention.
    """
    from scipy.io import loadmat

    m = loadmat(_find(OPTICAL_DIR, _SPECLIB))
    wl = np.asarray(m["nmLIB"], dtype=float).ravel()
    return {
        "wavelength_nm": wl,
        "mua_oxy": np.asarray(m["muaoxy"], dtype=float).ravel(),
        "mua_deoxy": np.asarray(m["muadeoxy"], dtype=float).ravel(),
        "mua_water": np.asarray(m["muawater"], dtype=float).ravel(),
        "mua_melanin": np.asarray(m["muamel"], dtype=float).ravel(),
        "mua_fat": np.asarray(m["muafat"], dtype=float).ravel(),
        "musp": np.asarray(m["musp"], dtype=float).ravel(),
        "source": str(_find(OPTICAL_DIR, _SPECLIB)),
        "reference_hb_g_per_L": 150.0,
    }


# --------------------------------------------------------------------------- #
# Prahl haemoglobin - CROSS-CHECK
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def prahl_hemoglobin() -> dict:
    """Molar extinction coefficients, cm^-1/M. Columns: wavelength, HbO2, Hb."""
    rows = []
    for line in _find(OPTICAL_DIR, _PRAHL).read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) == 3:
            try:
                rows.append([float(x) for x in parts])
            except ValueError:
                continue
    a = np.array(rows, dtype=float)
    if a.size == 0:
        raise ValueError("could not parse hemoglobin_prahl")
    return {"wavelength_nm": a[:, 0], "eps_hbo2": a[:, 1], "eps_hb": a[:, 2],
            "source": str(_find(OPTICAL_DIR, _PRAHL))}


def eps_hbo2(wl) -> np.ndarray:
    d = prahl_hemoglobin()
    return np.interp(np.asarray(wl, float), d["wavelength_nm"], d["eps_hbo2"])


def eps_hb(wl) -> np.ndarray:
    d = prahl_hemoglobin()
    return np.interp(np.asarray(wl, float), d["wavelength_nm"], d["eps_hb"])


def blood_absorption(wl, hb_g_dl: float, oxygenation: float) -> np.ndarray:
    """mu_a of whole blood, cm^-1, from the Prahl molar extinction coefficients.

    mu_a = ln(10) * eps * C, C the molar haem concentration.
    """
    wl = np.asarray(wl, dtype=float)
    conc_m = (float(hb_g_dl) * 10.0) / MW_HB_PER_HAEM     # g/dL -> g/L -> mol/L
    eps = oxygenation * eps_hbo2(wl) + (1.0 - oxygenation) * eps_hb(wl)
    return np.log(10.0) * eps * conc_m


def water_absorption(wl) -> np.ndarray:
    """mu_a of water, cm^-1. Source: spectralLIB.mat."""
    d = spectral_lib()
    return np.interp(np.asarray(wl, float), d["wavelength_nm"], d["mua_water"])


def reduced_scattering(wl, scale: float = 1.0) -> np.ndarray:
    """mu_s', cm^-1. Source: spectralLIB.mat (mcxyz generic soft tissue)."""
    d = spectral_lib()
    return scale * np.interp(np.asarray(wl, float), d["wavelength_nm"], d["musp"])


# --------------------------------------------------------------------------- #
# MELANIN - the most consequential assumption in the model
# --------------------------------------------------------------------------- #
def melanin_absorption(wl) -> np.ndarray:
    """mu_a of a melanosome, cm^-1. Source: spectralLIB.mat.

    ⚠️  **THIS IS NOT MEASURED DATA AND MUST NOT BE TREATED AS A FIXED CONSTANT.**

    Every published melanin "spectrum" in this family, including the one in
    spectralLIB.mat, is a POWER-LAW APPROXIMATION of the form
    mu_a ~ A * lambda^-k fitted to a small number of samples. It is a smooth curve
    through sparse data, not a measurement, and real melanin absorption varies
    substantially between individuals - in both the amplitude A and the exponent k.

    This matters more here than anywhere else in the model. The Phase 3 gate found
    that a melanin volume fraction of just 0.005 shifts recovered haemoglobin by
    **+9.6 g/dL**. A quantity that (a) the result is extremely sensitive to,
    (b) varies between people, and (c) is known only through a fitted approximation,
    is the single largest source of unquantified uncertainty in this simulator.

    It is also the mechanism by which the method would be biased by skin tone, which
    is exactly what N5 exists to audit. Treat any melanin-dependent number as
    provisional and sweep the exponent, do not fix it. `melanin_powerlaw_fit()`
    returns the fitted exponent so the sensitivity can be propagated.
    """
    d = spectral_lib()
    return np.interp(np.asarray(wl, float), d["wavelength_nm"], d["mua_melanin"])


@lru_cache(maxsize=1)
def melanin_powerlaw_fit() -> dict:
    """Fit mu_a = A * lambda^-k to the library melanin curve, to expose it as a fit."""
    d = spectral_lib()
    m = (d["wavelength_nm"] >= 400) & (d["wavelength_nm"] <= 1000)
    x = np.log(d["wavelength_nm"][m])
    y = np.log(d["mua_melanin"][m])
    k, logA = np.polyfit(x, y, 1)
    resid = y - (k * x + logA)
    return {"amplitude": float(np.exp(logA)), "exponent": float(k),
            "max_abs_log_residual": float(np.abs(resid).max()),
            "is_essentially_a_power_law": bool(np.abs(resid).max() < 0.05)}


# --------------------------------------------------------------------------- #
# Camera spectral sensitivities
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def camspec_database() -> dict:
    """Jiang et al. camera spectral sensitivity database: 28 cameras, 400-720 nm.

    Format is a name line followed by three lines of 33 values (R, G, B).
    """
    lines = [ln.strip() for ln in
             _find(CAMERA_DIR, _CAMSPEC).read_text(errors="replace").splitlines()]
    # Jiang et al. sample 400-720 nm at 10 nm: 33 points per channel, NOT 31.
    wl = np.arange(400.0, 721.0, 10.0)
    cams: dict[str, np.ndarray] = {}
    i = 0
    while i < len(lines):
        if not lines[i]:
            i += 1
            continue
        name = lines[i]
        try:
            chans = [np.array([float(x) for x in lines[i + k].split()]) for k in (1, 2, 3)]
        except (IndexError, ValueError):
            i += 1
            continue
        if all(len(c) == len(wl) for c in chans):
            cams[name] = np.stack(chans, axis=1)   # (31, 3)
        i += 4
    return {"wavelength_nm": wl, "cameras": cams,
            "source": str(_find(CAMERA_DIR, _CAMSPEC))}


@lru_cache(maxsize=1)
def mobile_average_sensitivity() -> dict:
    """Average MOBILE-PHONE camera sensitivity, 400-700 nm at 10 nm.

    More representative of this project's actual inputs than a DSLR: MOBIUS and
    Eyes-Defy are both phone captures.
    """
    a = np.loadtxt(_find(OPTICAL_DIR, _MOBILE_AVG))
    return {"wavelength_nm": np.arange(400.0, 701.0, 10.0), "rgb": a,
            "source": str(_find(OPTICAL_DIR, _MOBILE_AVG))}


def camera_rgb_sensitivities(wl, camera: str | None = None) -> np.ndarray:
    """(len(wl), 3) sensitivities, zero outside the measured 400-700 nm range."""
    wl = np.asarray(wl, dtype=float)
    if camera == "mobile_average" or camera is None:
        d = mobile_average_sensitivity()
        src_wl, vals = d["wavelength_nm"], d["rgb"]
    else:
        db = camspec_database()
        if camera not in db["cameras"]:
            raise KeyError(f"{camera!r} not in camspec; have {len(db['cameras'])} cameras")
        src_wl, vals = db["wavelength_nm"], db["cameras"][camera]
    out = np.stack([np.interp(wl, src_wl, vals[:, i], left=0.0, right=0.0)
                    for i in range(3)], axis=1)
    return out


def compare_with_transcribed() -> dict:
    """Task 0: where does the DOWNLOADED data disagree with the Phase 3 transcription?

    Phase 3's numbers were computed from hand-transcribed tables. Any disagreement
    here changes those numbers, so it is reported rather than silently overwritten.
    """
    from . import constants_transcribed as old

    wl = np.arange(450.0, 1001.0, 10.0)
    rows = []
    for name, new_f, old_f in (("eps_hbo2", eps_hbo2, old.eps_hbo2),
                               ("eps_hb", eps_hb, old.eps_hb)):
        n, o = new_f(wl), old_f(wl)
        rel = np.abs(n - o) / np.clip(np.abs(n), 1e-9, None)
        for i, w in enumerate(wl):
            rows.append({"quantity": name, "wavelength_nm": float(w),
                         "downloaded": float(n[i]), "transcribed": float(o[i]),
                         "rel_error": float(rel[i])})
    worst = sorted(rows, key=lambda r: -r["rel_error"])[:12]
    med = float(np.median([r["rel_error"] for r in rows]))
    return {"n_points": len(rows), "median_rel_error": med,
            "max_rel_error": float(max(r["rel_error"] for r in rows)),
            "worst_points": worst,
            "frac_above_10pct": float(np.mean([r["rel_error"] > 0.10 for r in rows]))}
