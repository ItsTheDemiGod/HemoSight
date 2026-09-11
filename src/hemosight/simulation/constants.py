"""Optical constants for conjunctival tissue. EVERY number here carries a citation.

=============================================================================
 SOURCING STATUS (updated 2026-09-11, Phase 3.5 Task 0)
=============================================================================
✅ **SOURCED FROM DOWNLOADED FILES** - the VERIFICATION REQUIRED banner is lifted
   for these, which now load from `data/raw/optical_constants/`:
     - haemoglobin extinction (Prahl/Gratzer/Kollias, 250-1000 nm @ 2 nm)
     - water absorption, reduced scattering (spectralLIB.mat, mcxyz)
     - camera spectral sensitivities (Jiang et al. camspec, 28 cameras;
       plus an average mobile-phone SSF)

⚠️  **STILL TRANSCRIBED - banner REMAINS** for these, which no downloaded file
   backs:
     - layer thicknesses and blood volume fractions (Efron 2009, Zhivov 2006,
       Jacques 2013). These are read from the literature by hand and must be
       re-verified before publication.

⚠️  **MELANIN IS A POWER-LAW APPROXIMATION, NOT MEASURED DATA.** It is sourced
   from spectralLIB.mat, but that curve is a fitted power law
   (mu_a = 6.6e11 * lambda^-3.33, log-residual < 1e-4, i.e. exactly a power law)
   and real melanin varies substantially between individuals in BOTH amplitude
   and exponent. Because the Phase 3 gate found that a melanin volume fraction
   of 0.005 shifts recovered haemoglobin by **+9.6 g/dL**, this approximation is
   now one of the most consequential assumptions in the entire model. It must be
   SWEPT, never fixed. See `optical_data.melanin_absorption`.

The transcribed tables this module previously used are preserved in
`constants_transcribed.py` for comparison; Phase 3.5 Task 0 reports where the
downloaded data disagrees with them.
=============================================================================

SOURCES
-------
[1] Prahl S. "Optical Absorption of Hemoglobin." Oregon Medical Laser Center,
    omlc.org/spectra/hemoglobin/summary.html. Compilation of:
      - Gratzer W.B., Med. Res. Council Labs, Holly Hill, London (450-800 nm)
      - Kollias N., Wellman Laboratories, Harvard Medical School (near-IR)
    Molar extinction coefficients in cm^-1 / (moles/litre).
[2] Jacques S.L. "Optical properties of biological tissues: a review."
    Phys. Med. Biol. 58(11):R37-R61, 2013. Reduced scattering power law
    mu_s'(lambda) = a * (lambda/500nm)^-b, and tabulated a, b for soft tissue.
[3] Jacques S.L. "Skin Optics." Oregon Medical Laser News, 1998.
    Melanosome absorption mu_a = 1.70e12 * lambda^-3.48 cm^-1.
[4] Hale G.M., Querry M.R. "Optical constants of water in the 200-nm to 200-um
    wavelength region." Applied Optics 12(3):555-563, 1973.
[5] Efron N., Al-Dossari M., Pritchard N. "In vivo confocal microscopy of the
    palpebral conjunctiva and tarsal plate." Optom. Vis. Sci. 86(11):E1303-8,
    2009. Palpebral conjunctival epithelium thickness.
[6] Zhivov A. et al. "In vivo confocal microscopic evaluation of the ocular
    surface." Cornea, 2006. Conjunctival epithelial/stromal architecture.
[7] Bosschaart N. et al. "A literature review and novel theoretical approach on
    the optical properties of whole blood." Lasers Med Sci 29:453-479, 2014.
    Whole-blood absorption and scattering; haematocrit relations.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Molecular weight of haemoglobin monomer, g/mol. Standard value; used to convert
# g/dL to molar concentration. [1] uses the 64,500 g/mol tetramer convention divided
# by 4 for the per-haem basis, which is what the extinction coefficients assume.
MW_HB_MONOMER_G_PER_MOL = 64500.0 / 4.0

# --------------------------------------------------------------------------- #
# Haemoglobin molar extinction coefficients, cm^-1/M.  Source [1].
# Columns: wavelength nm, HbO2, Hb.
# --------------------------------------------------------------------------- #
_HB_TABLE = np.array([
    [450.0,  62816.0, 103292.0],
    [460.0,  53236.0,  75326.0],
    [470.0,  45072.0,  56880.0],
    [480.0,  37020.0,  45072.0],
    [490.0,  28324.0,  31647.0],
    [500.0,  20932.0,  20862.0],   # ISOSBESTIC 500 [1]
    [510.0,  20035.0,  19452.0],
    [520.0,  24202.0,  20932.0],
    [529.0,  38700.0,  38700.0],   # ISOSBESTIC 529 [1]
    [542.0,  53236.0,  50900.0],   # HbO2 alpha peak 542 [1]
    [545.0,  52000.0,  52000.0],   # ISOSBESTIC 545 [1]
    [550.0,  43016.0,  49968.0],
    [560.0,  32613.0,  46592.0],
    [570.0,  44496.0,  44496.0],   # isosbestic 570
    [576.0,  61538.0,  37020.0],   # HbO2 beta peak
    [584.0,  29652.0,  29652.0],   # isosbestic 584
    [590.0,  14550.0,  26629.0],
    [600.0,   3200.0,  14677.0],
    [610.0,   1506.0,   9443.0],
    [620.0,    942.0,   6509.0],
    [640.0,    430.0,   3796.0],
    [660.0,    320.0,   3226.0],   # pulse-oximetry red
    [680.0,    292.0,   2308.0],
    [700.0,    290.0,   1794.0],
    [730.0,    390.0,   1102.0],   # Hb_PPG_Dataset wavelength
    [760.0,    586.0,   1548.0],   # Hb deoxy peak
    [800.0,    816.0,    761.0],   # isosbestic ~797-800
    [850.0,   1058.0,    692.0],   # Hb_PPG_Dataset wavelength
    [900.0,   1198.0,    726.0],
    [940.0,   1214.0,    693.0],   # Hb_PPG_Dataset wavelength
    [1000.0,  1132.0,    726.0],
])

# Isosbestic points where HbO2 and Hb extinction coefficients cross. Source [1].
# Used by validate_constants() as an internal check on the transcription.
KNOWN_ISOSBESTIC_NM = (500.0, 529.0, 545.0, 570.0, 584.0, 797.0)

# Reduced scattering, mu_s'(lambda) = A_MIE*(l/500)^-B_MIE + A_RAY*(l/500)^-4.
# Soft-tissue values from [2] Table 1 (mucosal/dermal range).
SCATTER_A_MIE_CM_INV = 18.0     # [2]
SCATTER_B_MIE = 1.5             # [2]
SCATTER_A_RAY_CM_INV = 8.0      # [2] Rayleigh component
ANISOTROPY_G = 0.9              # [2], typical for soft tissue in the visible

# Melanin: mu_a = 1.70e12 * lambda_nm^-3.48 cm^-1 for a melanosome. Source [3].
MELANIN_A = 1.70e12
MELANIN_POWER = -3.48

# Water absorption, cm^-1, sparse tabulation from [4]. Negligible in the visible
# but included so the model is not silently wrong in the near-IR.
_WATER_TABLE = np.array([
    [450.0, 0.00009], [500.0, 0.00021], [550.0, 0.00057], [600.0, 0.00240],
    [650.0, 0.00340], [700.0, 0.00600], [750.0, 0.02610], [800.0, 0.02000],
    [850.0, 0.04300], [900.0, 0.06800], [950.0, 0.39000], [1000.0, 0.36000],
])


@dataclass(frozen=True)
class Layer:
    """One tissue layer. Thicknesses in cm."""

    name: str
    thickness_cm: float
    blood_volume_fraction: float
    melanin_volume_fraction: float
    water_volume_fraction: float
    scatter_scale: float = 1.0
    citation: str = ""


# Layered palpebral conjunctiva. Thicknesses from [5] and [6]; blood volume
# fractions in the ranges reported by [2] for well-perfused mucosa.
DEFAULT_LAYERS: tuple[Layer, ...] = (
    Layer("epithelium", 0.0032, 0.002, 0.0005, 0.70, 1.0,
          "[5] palpebral conjunctival epithelium ~32 um"),
    Layer("stroma_vascular", 0.0200, 0.060, 0.0000, 0.75, 1.0,
          "[6] substantia propria; [2] mucosal blood volume fraction"),
    Layer("tarsal_plate", 0.0800, 0.010, 0.0000, 0.60, 1.2,
          "[5] tarsal plate, dense fibrous, low perfusion"),
)

# Physiological sweep ranges for Task 3.
HB_RANGE_G_DL = (4.0, 18.0)          # spans severe anemia to high-normal
OXYGENATION_RANGE = (0.60, 1.00)     # venous-to-arterial in surface vasculature
BVF_RANGE = (0.01, 0.15)             # [2] range across perfused soft tissue
MELANIN_RANGE = (0.0, 0.05)          # conjunctival melanin is low but nonzero

WAVELENGTHS_NM = np.arange(450.0, 1001.0, 5.0)


def _interp(table: np.ndarray, col: int, wl: np.ndarray) -> np.ndarray:
    return np.interp(wl, table[:, 0], table[:, col])


def eps_hbo2(wl: np.ndarray) -> np.ndarray:
    """HbO2 molar extinction, cm^-1/M. SOURCED: hemoglobin_prahl.txt."""
    from .optical_data import eps_hbo2 as _sourced
    return _sourced(wl)


def eps_hb(wl: np.ndarray) -> np.ndarray:
    """Deoxy-Hb molar extinction, cm^-1/M. SOURCED: hemoglobin_prahl.txt."""
    from .optical_data import eps_hb as _sourced
    return _sourced(wl)


def mu_a_blood(wl: np.ndarray, hb_g_dl: float, oxygenation: float) -> np.ndarray:
    """Absorption coefficient of WHOLE BLOOD at a given haemoglobin concentration.

    mu_a = ln(10) * eps * C, with C the molar haem concentration. Source [1], [7].
    `hb_g_dl` is the blood haemoglobin concentration as a clinical assay reports it.
    """
    wl = np.asarray(wl, dtype=float)
    conc_molar = (float(hb_g_dl) * 10.0) / MW_HB_MONOMER_G_PER_MOL  # g/dL -> g/L -> M
    eps = oxygenation * eps_hbo2(wl) + (1.0 - oxygenation) * eps_hb(wl)
    return np.log(10.0) * eps * conc_molar


def mu_a_melanin(wl: np.ndarray) -> np.ndarray:
    """Melanosome absorption, cm^-1. SOURCED: spectralLIB.mat.

    ⚠️ A FITTED POWER LAW, NOT MEASURED DATA, and the model's most consequential
    assumption (0.005 volume fraction -> +9.6 g/dL of Hb error). Sweep it.
    """
    from .optical_data import melanin_absorption
    return melanin_absorption(wl)


def mu_a_water(wl: np.ndarray) -> np.ndarray:
    """Water absorption, cm^-1. SOURCED: spectralLIB.mat."""
    from .optical_data import water_absorption
    return water_absorption(wl)


def mu_s_reduced(wl: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """Reduced scattering mu_s', cm^-1. SOURCED: spectralLIB.mat."""
    from .optical_data import reduced_scattering
    return reduced_scattering(wl, scale)


def layer_mu_a(layer: Layer, wl: np.ndarray, hb_g_dl: float,
               oxygenation: float, bvf_override: float | None = None,
               melanin_override: float | None = None) -> np.ndarray:
    """Total absorption of one layer: volume-weighted sum of its chromophores."""
    bvf = layer.blood_volume_fraction if bvf_override is None else bvf_override
    mel = layer.melanin_volume_fraction if melanin_override is None else melanin_override
    return (bvf * mu_a_blood(wl, hb_g_dl, oxygenation)
            + mel * mu_a_melanin(wl)
            + layer.water_volume_fraction * mu_a_water(wl))


def validate_constants(tol_nm: float = 12.0) -> dict:
    """Internal consistency checks on the transcribed spectral tables.

    Verifies that haemoglobin isosbestic points (where HbO2 and Hb extinction
    coefficients cross) fall where the literature places them, and that the known
    absorption peaks appear at the right wavelengths. A transcription error large
    enough to matter will move these, so this catches gross mistakes without
    certifying full precision.
    """
    wl = np.arange(450.0, 1001.0, 0.5)
    d = eps_hbo2(wl) - eps_hb(wl)
    crossings = wl[:-1][np.sign(d[:-1]) != np.sign(d[1:])]

    found = {}
    for iso in KNOWN_ISOSBESTIC_NM:
        if len(crossings):
            nearest = float(crossings[np.argmin(np.abs(crossings - iso))])
            found[iso] = {"nearest_crossing_nm": nearest,
                          "error_nm": abs(nearest - iso),
                          "ok": abs(nearest - iso) <= tol_nm}
        else:
            found[iso] = {"nearest_crossing_nm": None, "error_nm": None, "ok": False}

    # HbO2 has two well-known peaks in the visible: ~542 nm (alpha) and ~577 nm (beta).
    o = eps_hbo2(wl)
    region = (wl >= 520) & (wl <= 600)
    peak_wl = float(wl[region][np.argmax(o[region])])

    # Deoxy-Hb must absorb more than HbO2 in the red, which is what makes pulse
    # oximetry and every colour-based Hb method work at all.
    red = (wl >= 650) & (wl <= 700)
    red_ratio = float(np.mean(eps_hb(wl)[red] / np.clip(eps_hbo2(wl)[red], 1e-9, None)))

    return {
        "isosbestic": found,
        "all_isosbestic_ok": all(v["ok"] for v in found.values()),
        "hbo2_visible_peak_nm": peak_wl,
        "hbo2_peak_ok": 535.0 <= peak_wl <= 585.0,
        "deoxy_over_oxy_ratio_650_700nm": red_ratio,
        "red_ratio_ok": red_ratio > 3.0,
        "n_crossings_found": int(len(crossings)),
    }
