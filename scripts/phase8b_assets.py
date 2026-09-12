"""Phase 8B - the visual assets, generated from public data and this project's own outputs.

Nothing licensed, nothing scraped, nothing derived from a dataset image. Every file this
writes is either public tabulated physics (OMLC haemoglobin extinction; CIE colour
matching, via colour-science) or an aggregate statistic this project produced.

Writes to app/frontend/src/data/ (committed: small JSON, no dataset content):
  hb_spectra.json      oxy- and deoxy-haemoglobin molar extinction, 380-1000 nm, log10,
                       normalised to [0, 1] for drawing, plus the isosbestic points
  spectral_band.json   wavelength -> sRGB stops across the visible range (CIE 1931 -> sRGB)
  null_distribution.json
                       the 240 selection-aware permutation minima vs the real MAE (Phase 5)
  noise_signal.json    residual dE2000 per capture condition vs the measured signal (Phase 7 / 6.5)
  breakeven.json       residual -> Hb MAE on the gate model, with the bands (Phase 7)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from hemosight.io import paths
from hemosight.simulation.optical_data import eps_hb, eps_hbo2

OUT = paths.ROOT / "app" / "frontend" / "src" / "data"


def spectra() -> dict:
    wl = np.arange(380.0, 1000.1, 4.0)
    o, d = eps_hbo2(wl), eps_hb(wl)
    lo_, ld = np.log10(np.clip(o, 1, None)), np.log10(np.clip(d, 1, None))
    lo, hi = float(min(lo_.min(), ld.min())), float(max(lo_.max(), ld.max()))
    norm = lambda v: ((v - lo) / (hi - lo)).round(4).tolist()
    # isosbestic points: where the two curves cross (sign change of the difference)
    diff = lo_ - ld
    iso = [float(wl[i]) for i in range(1, len(wl)) if np.sign(diff[i]) != np.sign(diff[i - 1])]
    return {"wavelength_nm": wl.tolist(), "hbo2_log10_norm": norm(lo_), "hb_log10_norm": norm(ld),
            "log10_range": [round(lo, 3), round(hi, 3)], "isosbestic_nm": iso,
            "source": "Prahl compilation (Gratzer; Kollias), omlc.org - public tabulated data"}


def spectral_band() -> dict:
    """Wavelength -> sRGB, so a gradient can stand for the visible spectrum."""
    from colour import MSDS_CMFS, XYZ_to_sRGB
    cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
    stops = []
    for nm in range(380, 701, 5):
        xyz = np.array(cmfs[nm], dtype=float)
        rgb = XYZ_to_sRGB(xyz / max(xyz.sum(), 1e-9) * 0.8)
        rgb = np.clip(rgb, 0, 1)
        stops.append({"nm": nm, "rgb": [int(round(255 * c)) for c in rgb]})
    return {"stops": stops, "source": "CIE 1931 2-degree observer via colour-science; sRGB"}


def null_distribution() -> dict:
    h = json.loads((paths.INTERIM / "phase5" / "harden.json").read_text(encoding="utf-8"))
    ext = h["permutation_selection_aware_extended"]
    draws = []
    jl = paths.INTERIM / "phase5" / "perm_selection_aware.jsonl"
    for ln in jl.read_text(encoding="utf-8").splitlines():
        if ln.strip().startswith("{"):
            draws.append(round(float(json.loads(ln)["min_mae"]), 4))
    return {"draws_mae": draws, "real_mae": round(ext["real_mae"], 4),
            "null_mean": round(ext["null_mean"], 4), "null_sd": round(ext["null_sd"], 4),
            "p_empirical": round(ext["p_empirical"], 5), "at_floor": bool(ext["at_floor"]),
            "n": ext["n"], "sex_alone_mae": 0.831, "population_mean_mae": 1.175,
            "source": "Phase 5 selection-aware permutation, 240 draws; harden.json"}


def noise_signal() -> dict:
    cc = json.loads((paths.INTERIM / "phase7" / "controlled_capture.json").read_text(encoding="utf-8"))
    emp = json.loads((paths.INTERIM / "phase3" / "empirical_signal.json").read_text(encoding="utf-8"))
    names = {"mobius_across_phone_x_lighting": "3 phones x 3 lighting",
             "mobius_within_cell_gaze_only": "same phone and lighting",
             "sbvpi_studio": "studio rig"}
    conds = [{"label": names[k], "residual_dE2000": round(v["residual_dE2000"], 3),
              "gate_mae_g_dl": round(cc["gate"][k]["mae_g_dl"], 3), "band": cc["gate"][k]["band"]}
             for k, v in cc["best_residual_per_condition"].items()]
    return {"conditions": conds,
            "signal_dE2000_per_g_dl": round(emp["headline"]["de_per_g_dl"], 3),
            "signal_ci95": [round(x, 3) for x in emp["headline"]["ci95"]],
            "simulated_signal": 0.452, "viable_residual": round(cc["breakeven"]["residual_for_viable_1.0"], 3),
            "source": "Phase 7 Task 1 (controlled_capture.json), Phase 6.5 Task 1 (empirical_signal.json)"}


def breakeven() -> dict:
    cc = json.loads((paths.INTERIM / "phase7" / "controlled_capture.json").read_text(encoding="utf-8"))
    return {"scan": [{"residual": round(s["residual"], 3), "mae": round(s["mae"], 3)} for s in cc["breakeven"]["scan"]],
            "bands": {"viable": 1.0, "marginal": 2.0},
            "measured": [{"label": "studio", "residual": round(cc["best_residual_per_condition"]["sbvpi_studio"]["residual_dE2000"], 3)},
                         {"label": "uncontrolled", "residual": 3.935}],
            "source": "Phase 7 gate model scan"}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("hb_spectra", spectra), ("spectral_band", spectral_band),
                     ("null_distribution", null_distribution), ("noise_signal", noise_signal),
                     ("breakeven", breakeven)):
        d = fn()
        (OUT / f"{name}.json").write_text(json.dumps(d, separators=(",", ":")), encoding="utf-8")
        print(f"{name}.json  {len(json.dumps(d)) / 1024:.1f} kB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
