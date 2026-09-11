"""Forward model: tissue parameters -> reflectance spectrum -> camera RGB.

Two levels of fidelity share one interface:

* `diffuse_reflectance()` - an analytic diffusion-approximation solution for a
  semi-infinite turbid slab. Fast enough to invert inside an optimiser, which is what
  Task 0's error propagation needs.
* `mc_reflectance()` (montecarlo.py) - weighted-photon Monte Carlo over the layered
  model. Slower, used to generate the corpus and to check the analytic model.

The analytic form is used wherever speed matters and is validated against the Monte
Carlo in Task 1, so its approximation error is measured rather than assumed.
"""

from __future__ import annotations

import numpy as np

from . import constants as C


def diffuse_reflectance(wl: np.ndarray, mu_a: np.ndarray, mu_s_prime: np.ndarray,
                        n_rel: float = 1.4) -> np.ndarray:
    """Total diffuse reflectance of a semi-infinite turbid medium.

    Standard diffusion-approximation result (Farrell/Patterson form as given in
    Jacques 2013 [2], eq. for total diffuse reflectance):

        R = a' / (1 + 2k(1-a')ep + (1 + 2k/3) * sqrt(3(1-a')))

    with transport albedo a' = mu_s' / (mu_s' + mu_a) and `k` an internal-reflection
    parameter set by the tissue/air refractive index mismatch.

    The diffusion approximation is valid while mu_s' >> mu_a. Inside haemoglobin's
    Soret and alpha/beta bands that condition is violated, so this function is NOT
    trusted there without the Monte Carlo cross-check - which is exactly why Task 1
    compares the two.
    """
    mu_a = np.clip(np.asarray(mu_a, dtype=float), 1e-9, None)
    mu_s_prime = np.clip(np.asarray(mu_s_prime, dtype=float), 1e-9, None)

    # Internal reflection parameter from the refractive-index mismatch.
    r_d = -1.440 / n_rel**2 + 0.710 / n_rel + 0.668 + 0.0636 * n_rel
    k = (1 + r_d) / (1 - r_d)

    albedo = mu_s_prime / (mu_s_prime + mu_a)
    s = np.sqrt(3.0 * (1.0 - albedo))
    return albedo / (1.0 + 2.0 * k * (1.0 - albedo) + (1.0 + 2.0 * k / 3.0) * s)


def layered_reflectance(wl: np.ndarray, hb_g_dl: float, oxygenation: float,
                        bvf: float, melanin: float = 0.0,
                        layers: tuple[C.Layer, ...] | None = None,
                        thickness_scale: float = 1.0) -> np.ndarray:
    """Reflectance of the layered conjunctiva.

    Layers are combined by an attenuation-weighted scheme: light reaching layer i has
    been attenuated by the layers above it (double-pass Beer-Lambert), and each layer
    contributes its own diffuse reflectance weighted by that attenuation. This is a
    deliberate simplification of full radiative transfer between layers - the Monte
    Carlo model is the reference, and Task 1 measures the gap.
    """
    layers = layers or C.DEFAULT_LAYERS
    wl = np.asarray(wl, dtype=float)
    total = np.zeros_like(wl)
    attenuation = np.ones_like(wl)

    for i, layer in enumerate(layers):
        # The vascular stroma carries the Hb signal; the sweep's bvf applies there,
        # other layers keep their own (much smaller) blood content.
        use_bvf = bvf if layer.name == "stroma_vascular" else layer.blood_volume_fraction
        use_mel = melanin if layer.name == "epithelium" else layer.melanin_volume_fraction
        mu_a = C.layer_mu_a(layer, wl, hb_g_dl, oxygenation, use_bvf, use_mel)
        mu_s = C.mu_s_reduced(wl, layer.scatter_scale)

        r_layer = diffuse_reflectance(wl, mu_a, mu_s)
        total += attenuation * r_layer * (1.0 if i == 0 else 0.6)  # deeper layers contribute less
        d = layer.thickness_cm * thickness_scale
        attenuation = attenuation * np.exp(-2.0 * mu_a * d)   # double pass

    return np.clip(total, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# Spectrum -> RGB
# --------------------------------------------------------------------------- #
def cie_1931_sensitivities(wl: np.ndarray) -> np.ndarray:
    """CIE 1931 2-degree observer x,y,z at `wl`. Used as a camera proxy.

    THE SIX nus8 CAMERAS' SPECTRAL SENSITIVITIES ARE NOT AVAILABLE in this project -
    NUS ships ground-truth illuminants and colorchecker coordinates, not SSFs, and no
    installed package carries them. The CIE observer and the two measured cameras that
    colour-science does ship are used as proxies, and this substitution is reported as
    a limitation rather than glossed.
    """
    from colour.colorimetry import MSDS_CMFS

    cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
    return np.stack([np.interp(wl, cmfs.wavelengths, cmfs.values[:, i])
                     for i in range(3)], axis=1)


def camera_sensitivities(wl: np.ndarray, camera: str | None = None) -> np.ndarray:
    """(len(wl), 3) sensitivity curves. Falls back to the CIE observer."""
    if camera:
        from colour.characterisation import MSDS_CAMERA_SENSITIVITIES

        if camera in MSDS_CAMERA_SENSITIVITIES:
            m = MSDS_CAMERA_SENSITIVITIES[camera]
            return np.stack([np.interp(wl, m.wavelengths, m.values[:, i])
                             for i in range(3)], axis=1)
    return cie_1931_sensitivities(wl)


def illuminant_spd(wl: np.ndarray, name: str = "D65") -> np.ndarray:
    """Relative spectral power distribution of a named or blackbody illuminant.

    Accepts colour-science illuminant names (D65, A, ...) or "CCT:5000" for a
    Planckian radiator at that correlated colour temperature.
    """
    wl = np.asarray(wl, dtype=float)
    if name.startswith("CCT:"):
        t = float(name.split(":", 1)[1])
        lam = wl * 1e-9
        h, c, kb = 6.62607015e-34, 2.99792458e8, 1.380649e-23
        spd = (2 * h * c**2) / (lam**5 * (np.exp(h * c / (lam * kb * t)) - 1.0))
        return spd / spd.max()
    from colour.colorimetry import SDS_ILLUMINANTS

    sd = SDS_ILLUMINANTS[name]
    v = np.interp(wl, sd.wavelengths, sd.values)
    return v / max(v.max(), 1e-12)


def spectrum_to_rgb(wl: np.ndarray, reflectance: np.ndarray,
                    illuminant: np.ndarray, sensitivities: np.ndarray,
                    normalise: bool = True) -> np.ndarray:
    """Integrate reflectance * illuminant * sensitivity over wavelength."""
    r = np.asarray(reflectance, dtype=float)
    e = np.asarray(illuminant, dtype=float)
    s = np.asarray(sensitivities, dtype=float)
    rgb = np.trapezoid(r[:, None] * e[:, None] * s, wl, axis=0)
    if normalise:
        white = np.trapezoid(e[:, None] * s, wl, axis=0)
        rgb = rgb / np.clip(white, 1e-12, None)
    return rgb


def simulate_rgb(hb_g_dl: float, oxygenation: float = 0.75, bvf: float = 0.06,
                 melanin: float = 0.0, illuminant: str = "D65",
                 camera: str | None = None,
                 wl: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Convenience wrapper: parameters -> (reflectance spectrum, RGB)."""
    wl = C.WAVELENGTHS_NM if wl is None else np.asarray(wl, dtype=float)
    refl = layered_reflectance(wl, hb_g_dl, oxygenation, bvf, melanin)
    rgb = spectrum_to_rgb(wl, refl, illuminant_spd(wl, illuminant),
                          camera_sensitivities(wl, camera))
    return refl, rgb
