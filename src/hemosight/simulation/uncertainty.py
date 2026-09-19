"""Phase 9C - propagate parameter uncertainty into the Phase 3 gate result.

The gate (Phase 3 Task 0; re-run at measured residuals in Phase 7) turns a residual
colour error in dE2000 into a haemoglobin MAE by inverting the layered forward model
under a calibrated illuminant perturbation. Every tissue parameter in that model was
held fixed. This module keeps the machinery - the same `diffuse_reflectance`, the same
sourced blood / water / scattering spectra, the same perturbation generator, the same
Hb grid, LUT and trial count - and exposes the fixed parameters as a vector theta so
the gate can be evaluated across a declared prior.

Nothing is re-derived. `reflectance_theta` at `NOMINAL` must equal
`forward.layered_reflectance` to floating precision (test-enforced), and the
perturbation banks are regenerated in the original RNG order so that theta = NOMINAL
reproduces the recorded point estimates exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.stats import qmc

from . import constants as C
from .forward import (camera_sensitivities, diffuse_reflectance, illuminant_spd,
                      spectrum_to_rgb)
from .optical_data import melanin_absorption, melanin_powerlaw_fit

SEED = 20260911
HB_GRID = np.arange(4.0, 18.01, 1.0)          # Phase 3 Task 0
FINE = np.arange(2.0, 24.01, 0.05)            # inversion LUT
N_TRIALS = 240                                # per Hb value
DEEP_WEIGHT_NOMINAL = 0.6                     # forward.layered_reflectance, hard-coded
N_REL_NOMINAL = 1.4                           # forward.diffuse_reflectance default

# The three measured residuals and how their banks were drawn (seed, order).
# Phase 3 Task 0: rng(20260911), residuals [0.0 (no draw), 1.0, 2.0, 3.935, 6.076].
# Phase 7:        rng(20260911), best residuals in dict order, then references.
RESIDUAL_3935 = 3.935
RESIDUAL_3456 = 3.455915414382271
RESIDUAL_1981 = 1.980842739340969
RESIDUAL_1062 = 1.0619403269983845
BANK_ORDERS = {
    "phase3": [1.0, 2.0, RESIDUAL_3935],
    "phase7": [RESIDUAL_3456, RESIDUAL_1981, RESIDUAL_1062],
}
RECORDED = {  # the point estimates on the record, to be reproduced exactly
    RESIDUAL_3935: ("Phase 3 Task 0, sourced constants", 3.892986587921596),
    RESIDUAL_3456: ("Phase 7, MOBIUS across 3 phones x 3 lighting", 3.470951373760089),
    RESIDUAL_1062: ("Phase 7, SBVPI studio", 1.0395917888283186),
}


# --------------------------------------------------------------------------- #
# The parameter prior - declared in CLAUDE.md before running
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Param:
    key: str
    label: str
    nominal: float
    lo: float
    hi: float
    log: bool            # log-uniform if True, uniform otherwise
    status: str          # SOURCED / SOURCED-GENERIC / UNSOURCED
    justification: str

    def sample(self, u: np.ndarray) -> np.ndarray:
        if self.log:
            return np.exp(np.log(self.lo) + u * (np.log(self.hi) - np.log(self.lo)))
        return self.lo + u * (self.hi - self.lo)


_fit = melanin_powerlaw_fit()
MELANIN_K_NOMINAL = -_fit["exponent"]          # spectralLIB fit, ~3.33

PARAMS: tuple[Param, ...] = (
    Param("sto2", "oxygenation StO2", 0.75, 0.60, 1.00, False, "UNSOURCED",
          "physiological assumption (constants.OXYGENATION_RANGE); Phase 3 Task 4 found it benign"),
    Param("bvf_stroma", "stromal blood volume fraction", 0.060, 0.01, 0.15, False, "UNSOURCED",
          "Jacques 2013 soft-tissue range, transcribed (constants.BVF_RANGE); Task 4 tolerance +/-30%"),
    Param("melanin", "epithelial melanin volume fraction", 0.0, 1e-4, 5e-2, True, "UNSOURCED",
          "top of constants.MELANIN_RANGE; log-uniform so the sparsely pigmented mucosa is not "
          "swamped by dermal values; gate nominal is 0.0 (the lower edge is 1e-4)"),
    Param("mel_k", "melanin power-law exponent k", MELANIN_K_NOMINAL, 3.0, 4.0, False, "UNSOURCED",
          "spectralLIB curve is a fit with exponent ~3.33; Jacques 1998 gives 3.48"),
    Param("mel_scale", "melanin amplitude scale at 500 nm", 1.0, 0.5, 2.0, True, "UNSOURCED",
          "inter-individual amplitude variation; a factor of two either way"),
    Param("t_epi_um", "epithelium thickness (um)", 32.0, 22.0, 46.0, False, "SOURCED",
          "Li et al. 2015 OCT: 34.0 +/- 5.8 um; range is +/- 2 SD"),
    Param("t_stroma_um", "stroma thickness (um)", 200.0, 100.0, 400.0, False, "UNSOURCED",
          "VERIFICATION REQUIRED banner (Efron 2009 / Zhivov 2006 never obtained); 0.5-2x"),
    Param("t_tarsal_um", "tarsal plate thickness (um)", 800.0, 400.0, 1600.0, False, "UNSOURCED",
          "VERIFICATION REQUIRED banner; 0.5-2x"),
    Param("bvf_epi", "epithelium blood volume fraction", 0.002, 0.0, 0.01, False, "UNSOURCED",
          "assumed; an epithelium is avascular in principle, so the range starts at zero"),
    Param("bvf_tarsal", "tarsal plate blood volume fraction", 0.010, 0.002, 0.03, False, "UNSOURCED",
          "assumed 'dense fibrous, low perfusion'"),
    Param("water_shift", "water fraction shift, all layers", 0.0, -0.10, 0.10, False, "UNSOURCED",
          "assumed 0.70 / 0.75 / 0.60; water is nearly transparent in the visible"),
    Param("scatter_scale", "reduced-scattering scale", 1.0, 0.5, 2.0, True, "SOURCED-GENERIC",
          "spectralLIB soft-tissue mu_s' is file-backed but not conjunctiva-specific; Jacques 2013 "
          "tabulates a >2x spread across soft tissues"),
    Param("deep_weight", "deep-layer contribution weight", DEEP_WEIGHT_NOMINAL, 0.3, 1.0, False,
          "UNSOURCED", "modelling constant hard-coded in forward.layered_reflectance"),
    Param("n_rel", "tissue refractive index n_rel", N_REL_NOMINAL, 1.33, 1.45, False, "UNSOURCED",
          "typical soft tissue; forward.diffuse_reflectance default"),
)
KEYS = [p.key for p in PARAMS]
NOMINAL = {p.key: p.nominal for p in PARAMS}


def sample_prior(u: np.ndarray) -> np.ndarray:
    """Map unit-hypercube rows (n, d) to parameter rows (n, d) in PARAMS order."""
    u = np.asarray(u, float)
    return np.stack([p.sample(u[:, i]) for i, p in enumerate(PARAMS)], axis=1)


def theta_dict(row: np.ndarray) -> dict[str, float]:
    return {k: float(v) for k, v in zip(KEYS, row)}


# --------------------------------------------------------------------------- #
# The forward model with theta exposed - vectorised over an Hb grid
# --------------------------------------------------------------------------- #
def melanin_mu_a(wl: np.ndarray, k: float, scale: float) -> np.ndarray:
    """mu_a(lambda) = mu_a_lib(500 nm) * scale * (lambda / 500)^-k.

    At k = MELANIN_K_NOMINAL and scale = 1 this reproduces the spectralLIB curve to
    the fit's own residual (< 1e-4 in log), which is why the library curve is used
    verbatim at nominal and the power law only when theta moves off it.
    """
    wl = np.asarray(wl, float)
    if abs(k - MELANIN_K_NOMINAL) < 1e-12 and abs(scale - 1.0) < 1e-12:
        return melanin_absorption(wl)
    a500 = float(melanin_absorption(np.array([500.0]))[0])
    return a500 * scale * (wl / 500.0) ** (-k)


class ForwardTheta:
    """Precomputes everything that does not depend on theta."""

    def __init__(self, wl: np.ndarray | None = None):
        self.wl = C.WAVELENGTHS_NM if wl is None else np.asarray(wl, float)
        wl = self.wl
        self.ill = illuminant_spd(wl, "D65")
        self.sens = camera_sensitivities(wl)
        # Blood absorption is linear in Hb: mu_a_blood(hb) = hb * unit(StO2).
        self.eps_o = C.eps_hbo2(wl)
        self.eps_d = C.eps_hb(wl)
        self.mu_w = C.mu_a_water(wl)
        self.musp = C.mu_s_reduced(wl, 1.0)
        self.layers = C.DEFAULT_LAYERS

    def _blood_unit(self, sto2: float) -> np.ndarray:
        conc_per_g_dl = 10.0 / C.MW_HB_MONOMER_G_PER_MOL
        eps = sto2 * self.eps_o + (1.0 - sto2) * self.eps_d
        return np.log(10.0) * eps * conc_per_g_dl

    def reflectance(self, hb: np.ndarray, th: dict[str, float]) -> np.ndarray:
        """(len(hb), len(wl)) reflectance, mirroring forward.layered_reflectance."""
        wl = self.wl
        hb = np.atleast_1d(np.asarray(hb, float))[:, None]
        unit = self._blood_unit(th["sto2"])[None, :]
        mel = melanin_mu_a(wl, th["mel_k"], th["mel_scale"])[None, :]
        thick = {"epithelium": th["t_epi_um"] * 1e-4, "stroma_vascular": th["t_stroma_um"] * 1e-4,
                 "tarsal_plate": th["t_tarsal_um"] * 1e-4}
        bvfs = {"epithelium": th["bvf_epi"], "stroma_vascular": th["bvf_stroma"],
                "tarsal_plate": th["bvf_tarsal"]}
        total = np.zeros((hb.shape[0], wl.size))
        atten = np.ones_like(total)
        for i, layer in enumerate(self.layers):
            use_mel = th["melanin"] if layer.name == "epithelium" else layer.melanin_volume_fraction
            water = layer.water_volume_fraction + th["water_shift"]
            mu_a = bvfs[layer.name] * (hb * unit) + use_mel * mel + water * self.mu_w[None, :]
            mu_s = (self.musp * layer.scatter_scale * th["scatter_scale"])[None, :]
            r = diffuse_reflectance(wl, mu_a, mu_s, n_rel=th["n_rel"])
            total += atten * r * (1.0 if i == 0 else th["deep_weight"])
            atten = atten * np.exp(-2.0 * mu_a * thick[layer.name])
        return np.clip(total, 0.0, 1.0)

    def chroma_lut(self, th: dict[str, float], hb: np.ndarray = FINE) -> np.ndarray:
        refl = self.reflectance(hb, th)
        e, s = self.ill, self.sens
        rgb = np.trapezoid(refl[:, :, None] * e[None, :, None] * s[None, :, :], self.wl, axis=1)
        white = np.trapezoid(e[:, None] * s, self.wl, axis=0)
        rgb = rgb / np.clip(white, 1e-12, None)[None, :]
        return rgb / np.clip(rgb.sum(axis=1, keepdims=True), 1e-12, None)


# --------------------------------------------------------------------------- #
# Perturbation banks - the exact Phase 3 / Phase 7 draws
# --------------------------------------------------------------------------- #
def _perturbation_for_delta_e(rng, target_de, tol=0.05, max_iter=40):
    """Verbatim copy of scripts/phase3_task0_gate.perturbation_for_delta_e."""
    from hemosight.calibration.metrics import delta_e2000_illuminant
    base = np.ones(3) / np.sqrt(3)
    if target_de <= 0:
        return np.ones(3)
    d = rng.normal(size=3)
    d -= d.mean()
    d /= np.linalg.norm(d)
    lo, hi = 0.0, 1.0
    for _ in range(max_iter):
        cand = base * np.exp(hi * d)
        if float(delta_e2000_illuminant(cand, base)[0]) >= target_de:
            break
        hi *= 1.8
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        cand = base * np.exp(mid * d)
        de = float(delta_e2000_illuminant(cand, base)[0])
        if abs(de - target_de) < tol:
            break
        if de < target_de:
            lo = mid
        else:
            hi = mid
    return np.exp(mid * d)


def perturbation_bank(rng: np.random.Generator, de: float,
                      n_hb: int = len(HB_GRID), n_trials: int = N_TRIALS) -> np.ndarray:
    """(n_hb * n_trials, 3) ratios, drawn in the gate's own loop order (h-major)."""
    return np.array([_perturbation_for_delta_e(rng, de) for _ in range(n_hb * n_trials)])


def build_banks(seed: int = SEED) -> dict[float, np.ndarray]:
    """Regenerate the banks for the three measured residuals in their original order."""
    banks: dict[float, np.ndarray] = {}
    for _, order in BANK_ORDERS.items():
        rng = np.random.default_rng(seed)
        for de in order:
            banks[de] = perturbation_bank(rng, de)
    return {de: banks[de] for de in RECORDED}


# --------------------------------------------------------------------------- #
# The gate, evaluated at theta
# --------------------------------------------------------------------------- #
def _invert(lut: np.ndarray, obs: np.ndarray) -> np.ndarray:
    """Vectorised nearest-chromaticity inversion with the gate's parabolic refinement.

    Squared distances via the BLAS expansion |o|^2 + |l|^2 - 2 o.l; the square root is
    taken only at the three columns the refinement needs. Agrees with the gate's
    per-sample np.linalg.norm loop to ~1e-10 g/dL.
    """
    d2 = (obs ** 2).sum(1)[:, None] + (lut ** 2).sum(1)[None, :] - 2.0 * obs @ lut.T
    i = np.argmin(d2, axis=1)
    out = FINE[i].copy()
    inner = (i > 0) & (i < len(FINE) - 1)
    ii = i[inner]
    rows = np.nonzero(inner)[0]
    y0 = np.sqrt(np.clip(d2[rows, ii - 1], 0.0, None))
    y1 = np.sqrt(np.clip(d2[rows, ii], 0.0, None))
    y2 = np.sqrt(np.clip(d2[rows, ii + 1], 0.0, None))
    den = y0 - 2 * y1 + y2
    ok = np.abs(den) > 1e-12
    out[rows[ok]] = FINE[ii[ok]] + 0.5 * (y0[ok] - y2[ok]) / den[ok] * (FINE[1] - FINE[0])
    return out


_TRUTH_IDX = np.rint((HB_GRID - FINE[0]) / (FINE[1] - FINE[0])).astype(int)
_HB_REPEAT = np.repeat(HB_GRID, N_TRIALS)


def errors_from_lut(lut: np.ndarray, truth: np.ndarray, bank: np.ndarray) -> np.ndarray:
    """|Hb_est - Hb_true| for every (Hb, trial); `truth` is the (len(HB_GRID), 3) chroma."""
    obs = np.repeat(truth, N_TRIALS, axis=0) * bank                    # h-major, trial-minor
    obs = obs / np.clip(obs.sum(axis=1, keepdims=True), 1e-12, None)
    return np.abs(_invert(lut, obs) - _HB_REPEAT)


def gate_errors(fwd: ForwardTheta, th: dict[str, float], bank: np.ndarray,
                lut_theta: dict[str, float] | None = None) -> np.ndarray:
    """|Hb_est - Hb_true| for every (Hb, trial) in the bank.

    `lut_theta` defaults to `th` (self-consistent). Passing NOMINAL gives the mismatch
    variant: the inversion assumes nominal tissue while the truth is `th`.
    """
    lut = fwd.chroma_lut(lut_theta or th)
    truth = fwd.chroma_lut(th)[_TRUTH_IDX] if lut_theta is not None else lut[_TRUTH_IDX]
    return errors_from_lut(lut, truth, bank)


def gate_mae(fwd, th, bank, lut_theta=None) -> float:
    return float(gate_errors(fwd, th, bank, lut_theta).mean())


def gate_mae_all(fwd: ForwardTheta, th: dict[str, float], banks: dict[float, np.ndarray],
                 lut_theta: dict[str, float] | None = None) -> dict[float, float]:
    """One LUT per theta, every residual's bank inverted against it."""
    lut = fwd.chroma_lut(lut_theta or th)
    truth = fwd.chroma_lut(th)[_TRUTH_IDX] if lut_theta is not None else lut[_TRUTH_IDX]
    return {de: float(errors_from_lut(lut, truth, bank).mean()) for de, bank in banks.items()}


def band(mae: float) -> str:
    return "VIABLE" if mae < 1.0 else "MARGINAL" if mae <= 2.0 else "NOT RECOVERABLE"


# --------------------------------------------------------------------------- #
# Sobol / Saltelli design and Jansen estimators
# --------------------------------------------------------------------------- #
def saltelli_design(n_base: int = 1024, seed: int = SEED) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Unit-hypercube A, B (n, d) and the stacked A_B^(i) matrices (d, n, d)."""
    d = len(PARAMS)
    sob = qmc.Sobol(d=2 * d, scramble=True, seed=seed)
    u = sob.random(n_base)
    A, B = u[:, :d], u[:, d:]
    AB = np.empty((d, n_base, d))
    for i in range(d):
        AB[i] = A
        AB[i][:, i] = B[:, i]
    return A, B, AB


def sobol_indices(fA: np.ndarray, fB: np.ndarray, fAB: np.ndarray,
                  n_boot: int = 200, seed: int = SEED) -> dict:
    """First-order (Saltelli 2010) and total (Jansen 1999) indices with bootstrap CIs."""
    n = fA.size
    var = np.var(np.concatenate([fA, fB]), ddof=1)

    def est(rows):
        a, b, ab = fA[rows], fB[rows], fAB[:, rows]
        s1 = np.mean(b[None, :] * (ab - a[None, :]), axis=1) / var
        st = 0.5 * np.mean((a[None, :] - ab) ** 2, axis=1) / var
        return s1, st

    s1, st = est(np.arange(n))
    rng = np.random.default_rng(seed)
    bs1, bst = [], []
    for _ in range(n_boot):
        r = rng.integers(0, n, n)
        a, b = est(r)
        bs1.append(a)
        bst.append(b)
    bs1, bst = np.array(bs1), np.array(bst)
    return {"variance": float(var),
            "first_order": s1.tolist(), "total": st.tolist(),
            "first_order_ci": np.percentile(bs1, [2.5, 97.5], axis=0).T.tolist(),
            "total_ci": np.percentile(bst, [2.5, 97.5], axis=0).T.tolist()}


def evaluate_design(f: Callable[[dict[str, float]], dict[float, float]], A, B, AB,
                    residuals: list[float]) -> dict:
    """Evaluate f (theta -> {residual: mae}) on the Saltelli design."""
    thA, thB = sample_prior(A), sample_prior(B)

    def run(rows):
        vals = [f(theta_dict(r)) for r in rows]
        return {de: np.array([v[de] for v in vals]) for de in residuals}

    fA, fB = run(thA), run(thB)
    fAB = {de: np.empty((AB.shape[0], AB.shape[1])) for de in residuals}
    for i in range(AB.shape[0]):
        r = run(sample_prior(AB[i]))
        for de in residuals:
            fAB[de][i] = r[de]
    return {"thetaA": thA, "thetaB": thB, "fA": fA, "fB": fB, "fAB": fAB}


def one_at_a_time(f: Callable[[dict[str, float]], float], n_points: int = 9) -> dict:
    """Swing of f when each parameter alone sweeps its prior, others at NOMINAL."""
    out = {}
    for p in PARAMS:
        grid = p.sample(np.linspace(0.0, 1.0, n_points))
        vals = []
        for v in grid:
            th = dict(NOMINAL)
            th[p.key] = float(v)
            vals.append(f(th))
        out[p.key] = {"grid": grid.tolist(), "values": vals}
        if all(isinstance(v, (int, float)) for v in vals):
            out[p.key]["swing"] = float(max(vals) - min(vals))
    return out


def summarise(values: np.ndarray, threshold: float = 2.0) -> dict:
    v = np.asarray(values, float)
    lo, hi = np.percentile(v, [2.5, 97.5])
    return {"n": int(v.size), "median": float(np.median(v)), "mean": float(v.mean()),
            "p2.5": float(lo), "p97.5": float(hi), "min": float(v.min()), "max": float(v.max()),
            "fraction_above_2.0": float(np.mean(v > 2.0)),
            "fraction_below_1.0": float(np.mean(v < 1.0)),
            "fraction_in_1_2": float(np.mean((v >= 1.0) & (v <= 2.0))),
            "robust_at_2.0": bool((lo > 2.0) or (hi < 2.0)),
            "robust_at_1.0": bool((lo > 1.0) or (hi < 1.0))}
