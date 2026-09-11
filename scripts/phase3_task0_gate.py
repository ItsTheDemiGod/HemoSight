"""Phase 3, TASK 0: THE GATE. Run and report this before anything else.

Question: does the colour-to-haemoglobin inversion survive the residual colour error
that the project's own recommended normalisation actually leaves?

Phase 2.5 measured that residual: grey-world on a tight periocular crop leaves
3.935 dE2000; on the full frame, 6.076. A best case of 1.0 is included as a bound.

Thresholds declared in CLAUDE.md BEFORE running:
    < 1.0 g/dL   VIABLE - proceed
    1.0-2.0      MARGINAL - coarse screening bands only, not point estimates
    > 2.0 g/dL   NOT RECOVERABLE - stop and report as a major finding

    .\\.venv\\Scripts\\python.exe scripts\\phase3_task0_gate.py
"""

from __future__ import annotations

import json

import numpy as np

from hemosight.calibration.metrics import delta_e2000_illuminant
from hemosight.io import paths
from hemosight.simulation import constants as C
from hemosight.simulation.forward import (
    camera_sensitivities,
    illuminant_spd,
    layered_reflectance,
    spectrum_to_rgb,
)

OUT = paths.INTERIM / "phase3"
RESIDUALS = [0.0, 1.0, 2.0, 3.935, 6.076]   # dE2000; 3.935 and 6.076 are measured
HB_GRID = np.arange(4.0, 18.01, 1.0)
N_TRIALS = 240

# WHO haemoglobin severity boundaries (non-pregnant adults / children 6-59 mo).
WHO_BOUNDARIES = {"severe/moderate": 7.0, "moderate/mild": 10.0, "mild/normal": 11.0}


def chroma(rgb: np.ndarray) -> np.ndarray:
    s = rgb.sum()
    return rgb / s if s > 0 else rgb


def perturbation_for_delta_e(rng, target_de: float, tol: float = 0.05,
                             max_iter: int = 40) -> np.ndarray:
    """Random illuminant perturbation calibrated to a target dE2000.

    Returns the elementwise ratio (true illuminant / estimated illuminant), which is
    exactly the multiplicative error a wrong white-balance leaves on corrected RGB.
    """
    base = np.ones(3) / np.sqrt(3)
    if target_de <= 0:
        return np.ones(3)
    d = rng.normal(size=3)
    d -= d.mean()
    d /= np.linalg.norm(d)
    lo, hi = 0.0, 1.0
    for _ in range(max_iter):     # grow until we bracket the target
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    wl = C.WAVELENGTHS_NM
    ill = illuminant_spd(wl, "D65")
    sens = camera_sensitivities(wl)

    # Precompute the forward model on a fine Hb grid for fast inversion.
    fine = np.arange(2.0, 24.01, 0.05)
    lut = np.array([chroma(spectrum_to_rgb(
        wl, layered_reflectance(wl, h, 0.75, 0.06, 0.0), ill, sens)) for h in fine])

    def invert(observed_chroma: np.ndarray) -> float:
        """Recover Hb by nearest chromaticity in the forward-model LUT."""
        d = np.linalg.norm(lut - observed_chroma[None, :], axis=1)
        i = int(np.argmin(d))
        # Parabolic refinement around the LUT minimum.
        if 0 < i < len(fine) - 1:
            y0, y1, y2 = d[i - 1], d[i], d[i + 1]
            denom = (y0 - 2 * y1 + y2)
            if abs(denom) > 1e-12:
                return float(fine[i] + 0.5 * (y0 - y2) / denom * (fine[1] - fine[0]))
        return float(fine[i])

    print("=== TASK 0 GATE: Hb error under realistic residual colour error ===")
    print(f"forward model: {len(wl)} wavelengths {wl[0]:.0f}-{wl[-1]:.0f} nm, "
          f"D65, CIE 1931 observer as camera proxy\n")

    # Sanity: with zero perturbation the inversion must be exact.
    exact = [abs(invert(chroma(spectrum_to_rgb(
        wl, layered_reflectance(wl, h, 0.75, 0.06, 0.0), ill, sens))) - h)
        for h in HB_GRID]
    print(f"inversion self-consistency (no perturbation): max error "
          f"{max(exact):.4f} g/dL\n")

    results: dict = {"residuals": {}, "thresholds": {"viable": 1.0, "marginal": 2.0},
                     "inversion_self_consistency_max_g_dl": float(max(exact))}
    rng = np.random.default_rng(20260911)

    print(f"{'residual dE2000':>16s} {'MAE g/dL':>9s} {'median':>8s} {'p90':>8s} "
          f"{'worst':>8s}   band")
    for de in RESIDUALS:
        per_hb, all_err = {}, []
        for h in HB_GRID:
            true_rgb = spectrum_to_rgb(
                wl, layered_reflectance(wl, h, 0.75, 0.06, 0.0), ill, sens)
            errs = []
            for _ in range(N_TRIALS):
                p = perturbation_for_delta_e(rng, de)
                est = invert(chroma(true_rgb * p))
                errs.append(est - h)
            errs = np.array(errs)
            per_hb[float(h)] = {
                "mae": float(np.abs(errs).mean()),
                "bias": float(errs.mean()),
                "p90": float(np.percentile(np.abs(errs), 90)),
            }
            all_err.append(np.abs(errs))
        all_err = np.concatenate(all_err)
        mae = float(all_err.mean())
        band = ("VIABLE" if mae < 1.0 else "MARGINAL" if mae <= 2.0
                else "NOT RECOVERABLE")
        results["residuals"][str(de)] = {
            "mae_g_dl": mae, "median_g_dl": float(np.median(all_err)),
            "p90_g_dl": float(np.percentile(all_err, 90)),
            "worst_g_dl": float(all_err.max()), "band": band, "per_hb": per_hb,
        }
        tag = " (measured: grey-world @25% FOV)" if de == 3.935 else (
            " (measured: grey-world full frame)" if de == 6.076 else "")
        print(f"{de:16.3f} {mae:9.3f} {np.median(all_err):8.3f} "
              f"{np.percentile(all_err, 90):8.3f} {all_err.max():8.3f}   {band}{tag}")

    # ---- is the error uniform, or worse where screening decisions are made? ----
    print("\n=== Hb error vs Hb level (is low Hb worse?) ===")
    key = "3.935"
    per_hb = results["residuals"][key]["per_hb"]
    print(f"at the measured residual {key} dE2000:")
    print(f"  {'Hb g/dL':>8s} {'MAE':>7s} {'bias':>7s} {'p90':>7s}")
    for h in sorted(per_hb, key=float):
        v = per_hb[h]
        print(f"  {float(h):8.1f} {v['mae']:7.3f} {v['bias']:+7.3f} {v['p90']:7.3f}")
    lo = np.mean([per_hb[h]["mae"] for h in per_hb if float(h) <= 8.0])
    hi = np.mean([per_hb[h]["mae"] for h in per_hb if float(h) >= 14.0])
    results["low_hb_mae"] = float(lo)
    results["high_hb_mae"] = float(hi)
    results["low_vs_high_ratio"] = float(lo / hi) if hi > 0 else None
    print(f"\n  mean MAE at Hb <= 8 (severe/moderate): {lo:.3f} g/dL")
    print(f"  mean MAE at Hb >= 14 (normal)        : {hi:.3f} g/dL")
    print(f"  ratio low/high                       : {lo/hi:.2f}x")

    # ---- which WHO boundaries survive? ----
    print("\n=== WHO severity boundaries: still distinguishable? ===")
    who = {}
    for name, b in WHO_BOUNDARIES.items():
        nearest = min(per_hb, key=lambda h: abs(float(h) - b))
        v = per_hb[nearest]
        # A boundary is "distinguishable" if the p90 error is smaller than the
        # distance to the neighbouring band centre (~1.5 g/dL for these bands).
        ok = v["p90"] < 1.5
        who[name] = {"boundary_g_dl": b, "mae_at_boundary": v["mae"],
                     "p90_at_boundary": v["p90"], "distinguishable": bool(ok)}
        print(f"  {name:18s} at {b:5.1f} g/dL: MAE={v['mae']:.3f} p90={v['p90']:.3f}  "
              f"{'DISTINGUISHABLE' if ok else 'NOT distinguishable'}")
    results["who_boundaries"] = who

    measured = results["residuals"]["3.935"]
    results["gate_band"] = measured["band"]
    results["gate_mae_at_measured_residual"] = measured["mae_g_dl"]

    print("\n" + "=" * 66)
    print("GATE RESULT at the project's own measured residual (3.935 dE2000):")
    print(f"  MAE = {measured['mae_g_dl']:.3f} g/dL   ->   **{measured['band']}**")
    print("=" * 66)

    (OUT / "task0_gate.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nresults -> {OUT / 'task0_gate.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
