"""Phase 7 Task 1 - is the refutation about PHOTOGRAPHS or about UNCONTROLLED photographs?

Thresholds and outcomes were declared in CLAUDE.md before this ran (Phase 7 section).

Part A - MEASURED residual colour error per capture condition. The residual is the
within-subject spread (mean pairwise CIEDE2000) of the segmented sclera's colour across
captures of the same person - the same construction as Phase 3.5 Task 3 - under three
conditions ordered from least to most controlled, and under three corrections each:
    conditions:  MOBIUS across 3 phones x 3 lighting (one capture per cell, straight gaze)
                 MOBIUS within one phone x lighting cell, gaze varying (geometry only)
                 SBVPI studio (fixed rig, several captures per subject)
    corrections: none | grey-world on the full frame | grey-world on a 25% crop centred
                 on the segmented eye (the Phase 2.5 recommendation)
Part B - the Phase 3 gate re-run at each measured residual, same forward model, same
inversion, same bands (< 1.0 VIABLE, 1.0-2.0 MARGINAL, > 2.0 NOT RECOVERABLE).
Part C - the residual at which the gate crosses into VIABLE, read off the same model,
against every measured condition.
Part D - Eyes-Defy: one image per subject, so no within-subject residual exists; its
empirical colour-model MAE under a fixed LED (Phase 6.5) is the controlled-capture
measurement it does support, and is read from image_cnn.json, not retyped.

Everything that can be measured is; nothing is assumed.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hemosight.calibration.estimators import robust_patch_rgb            # noqa: E402
from hemosight.calibration.metrics import delta_e2000_pairwise_spread     # noqa: E402
from hemosight.calibration.segmentation import (UNetResNet18, predict_mask,  # noqa: E402
                                                 vessel_exclusion_mask)
from hemosight.calibration.segmentation_data import (IRIS, PUPIL, SCLERA,   # noqa: E402
                                                      index_mobius_all, index_sbvpi)
from hemosight.calibration.selfconsistency import rgb_to_lab               # noqa: E402
from hemosight.io import paths                                              # noqa: E402
from hemosight.simulation import constants as C                             # noqa: E402
from hemosight.simulation.forward import (camera_sensitivities,             # noqa: E402
                                          illuminant_spd, layered_reflectance,
                                          spectrum_to_rgb)
from tissue_simulator_gate_phase3 import (HB_GRID, N_TRIALS, chroma,                   # noqa: E402
                               perturbation_for_delta_e)

OUT = paths.INTERIM / "phase7"
CKPT = paths.INTERIM / "phase2" / "segmentation_unet_r18.pt"
SEED = 20260911
MAX_SBVPI = 700
WITHIN_CELL_CAPTURES = 4      # left eye, four gazes, first shot each
CORRECTIONS = ("none", "grey_world_full", "grey_world_crop25")


def grey_world_gain(lin: np.ndarray) -> np.ndarray:
    g = lin.reshape(-1, 3).mean(axis=0)
    g = g / g.mean()
    return 1.0 / np.clip(g, 1e-6, None)


def eye_centre_crop(lin: np.ndarray, labels: np.ndarray, frac: float = 0.25) -> np.ndarray:
    eye = np.isin(labels, [SCLERA, IRIS, PUPIL])
    h, w = lin.shape[:2]
    if eye.sum() == 0:
        cy, cx = h // 2, w // 2
    else:
        ys, xs = np.where(eye)
        cy, cx = int(ys.mean()), int(xs.mean())
    ch, cw = int(h * frac), int(w * frac)
    y0, x0 = max(0, min(h - ch, cy - ch // 2)), max(0, min(w - cw, cx - cw // 2))
    return lin[y0:y0 + ch, x0:x0 + cw]


def measure(model, ck, dev, samples, label):
    """Per sample: sclera colour (Lab) under each correction. Grouped by subject key."""
    out = {c: defaultdict(list) for c in CORRECTIONS}
    t0 = time.time()
    for i, (key, s) in enumerate(samples):
        if i % 100 == 0:
            print(f"  [{label}] {i}/{len(samples)} {time.time()-t0:.0f}s", flush=True)
        bgr = cv2.imread(s.image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        rgb8 = bgr[:, :, ::-1]
        labels, _ = predict_mask(model, rgb8, ck["size"], dev)
        m = labels == SCLERA
        if m.sum() < 200:
            continue
        lin = rgb8.astype(np.float64) / 255.0
        m, _ = vessel_exclusion_mask(lin, m)
        v = robust_patch_rgb(lin[m])
        if not np.isfinite(v).all():
            continue
        gains = {"none": np.ones(3),
                 "grey_world_full": grey_world_gain(lin),
                 "grey_world_crop25": grey_world_gain(eye_centre_crop(lin, labels))}
        for c, g in gains.items():
            out[c][key].append(rgb_to_lab(v * g))
    return {c: {k: np.array(v) for k, v in d.items() if len(v) >= 2} for c, d in out.items()}


def within_spread(labs: dict) -> dict:
    per = []
    for v in labs.values():
        d = delta_e2000_pairwise_spread(v)
        if np.isfinite(d["mean_pairwise"]):
            per.append(d["mean_pairwise"])
    cents = np.array([v.mean(axis=0) for v in labs.values()])
    between = delta_e2000_pairwise_spread(cents)["mean_pairwise"] if len(cents) >= 2 else float("nan")
    return {"n_groups": len(labs), "n_captures": int(sum(len(v) for v in labs.values())),
            "within_dE": float(np.mean(per)) if per else float("nan"),
            "within_median_dE": float(np.median(per)) if per else float("nan"),
            "between_dE": float(between),
            "within_over_between": float(np.mean(per) / between) if per and between > 0 else None}


def build_gate(seed: int = SEED):
    wl = C.WAVELENGTHS_NM
    ill = illuminant_spd(wl, "D65")
    sens = camera_sensitivities(wl)
    fine = np.arange(2.0, 24.01, 0.05)
    lut = np.array([chroma(spectrum_to_rgb(wl, layered_reflectance(wl, h, 0.75, 0.06, 0.0),
                                           ill, sens)) for h in fine])

    def invert(obs):
        d = np.linalg.norm(lut - obs[None, :], axis=1)
        i = int(np.argmin(d))
        if 0 < i < len(fine) - 1:
            y0, y1, y2 = d[i - 1], d[i], d[i + 1]
            den = y0 - 2 * y1 + y2
            if abs(den) > 1e-12:
                return float(fine[i] + 0.5 * (y0 - y2) / den * (fine[1] - fine[0]))
        return float(fine[i])

    truth = {float(h): spectrum_to_rgb(wl, layered_reflectance(wl, h, 0.75, 0.06, 0.0), ill, sens)
             for h in HB_GRID}

    def run(de: float, rng, n_trials: int = N_TRIALS) -> dict:
        errs = []
        for h, true_rgb in truth.items():
            for _ in range(n_trials):
                p = perturbation_for_delta_e(rng, de)
                errs.append(abs(invert(chroma(true_rgb * p)) - h))
        errs = np.array(errs)
        mae = float(errs.mean())
        return {"residual_dE2000": de, "mae_g_dl": mae, "median_g_dl": float(np.median(errs)),
                "p90_g_dl": float(np.percentile(errs, 90)),
                "band": "VIABLE" if mae < 1.0 else "MARGINAL" if mae <= 2.0 else "NOT RECOVERABLE"}
    return run


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = torch.load(CKPT, map_location=dev, weights_only=False)
    model = UNetResNet18().to(dev)
    model.load_state_dict(ck["model"])
    model.eval()

    # ------------------------------------------------------------ samples
    cells = defaultdict(list)
    for s in index_mobius_all():
        if s.is_bad or not s.phone or not s.lighting:
            continue
        cells[(s.subject_id, s.phone, s.lighting)].append(s)
    across, within = [], []
    for k in sorted(cells):
        left = sorted([s for s in cells[k] if s.eye == "L"], key=lambda s: (s.gaze != "s", s.image_path))
        if not left:
            left = sorted(cells[k], key=lambda s: (s.gaze != "s", s.image_path))
        across.append((k[0], left[0]))                       # one per cell: subject key
        seen, chosen = set(), []
        for s in left:                                       # one per gaze, same cell
            if s.gaze not in seen:
                seen.add(s.gaze); chosen.append(s)
        for s in chosen[:WITHIN_CELL_CAPTURES]:
            within.append((f"{k[0]}|{k[1]}|{k[2]}", s))     # cell key
    sbv_all = index_sbvpi()
    rng = np.random.default_rng(0)
    idx = rng.choice(len(sbv_all), min(MAX_SBVPI, len(sbv_all)), replace=False)
    studio = [(sbv_all[i].subject_id, sbv_all[i]) for i in idx]
    print(f"frames: across {len(across)}, within-cell {len(within)}, studio {len(studio)}")

    # ------------------------------------------------------------ Part A
    conds = {}
    for name, samples in (("mobius_across_phone_x_lighting", across),
                          ("mobius_within_cell_gaze_only", within),
                          ("sbvpi_studio", studio)):
        labs = measure(model, ck, dev, samples, name)
        conds[name] = {c: within_spread(labs[c]) for c in CORRECTIONS}
        for c in CORRECTIONS:
            r = conds[name][c]
            print(f"  {name:32s} {c:18s} within {r['within_dE']:.3f} between {r['between_dE']:.3f} "
                  f"(n={r['n_groups']} groups, {r['n_captures']} captures)")
    # The residual carried into the gate is the BEST correction per condition.
    best = {}
    for name, d in conds.items():
        c = min(CORRECTIONS, key=lambda c: d[c]["within_dE"])
        best[name] = {"correction": c, "residual_dE2000": d[c]["within_dE"]}
    print("best residual per condition:", {k: round(v["residual_dE2000"], 3) for k, v in best.items()})

    # ------------------------------------------------------------ Part B + C
    run_gate = build_gate()
    rng_g = np.random.default_rng(SEED)
    gate = {}
    for name, b in best.items():
        gate[name] = run_gate(b["residual_dE2000"], rng_g)
        print(f"  GATE at {name} residual {b['residual_dE2000']:.3f}: MAE {gate[name]['mae_g_dl']:.3f} "
              f"p90 {gate[name]['p90_g_dl']:.3f} -> {gate[name]['band']}")
    # Reference points from Phase 3, re-run on the same RNG stream for comparability.
    for de in (3.935, 1.0, 2.0):
        gate[f"reference_{de}"] = run_gate(de, rng_g)
    # Breakeven: residual at which the model crosses 1.0 and 2.0 g/dL.
    scan = [(de, run_gate(de, rng_g, n_trials=80)["mae_g_dl"]) for de in np.arange(0.25, 3.01, 0.25)]
    def cross(th):
        for (d0, m0), (d1, m1) in zip(scan[:-1], scan[1:]):
            if m0 < th <= m1:
                return float(d0 + (th - m0) * (d1 - d0) / (m1 - m0))
        return None
    breakeven = {"scan": [{"residual": float(d), "mae": m} for d, m in scan],
                 "residual_for_viable_1.0": cross(1.0), "residual_for_marginal_2.0": cross(2.0)}
    print(f"  breakeven: VIABLE needs residual < {breakeven['residual_for_viable_1.0']}, "
          f"MARGINAL < {breakeven['residual_for_marginal_2.0']}")

    # ------------------------------------------------------------ Part D
    cnn = json.loads((paths.INTERIM / "phase6_5" / "image_cnn.json").read_text(encoding="utf-8"))
    emp = json.loads((paths.INTERIM / "phase3" / "empirical_signal.json").read_text(encoding="utf-8"))
    eyes = {
        "within_subject_residual": "NOT MEASURABLE - one image per subject",
        "capture": "fixed distance, own white LED, ambient light excluded (dataset documentation)",
        "colour_model_mae_pooled": cnn["baselines"]["colour_features_lab"]["mae_g_dl"],
        "colour_plus_site_sex_age_mae": cnn["baselines"]["colour_features_lab_plus_site_sex_age"]["mae_g_dl"],
        "site_sex_age_mae": cnn["baselines"]["demographics_site_sex_age"]["mae_g_dl"],
        "cnn_mae_pooled": cnn["cnn_pooled"]["mae_g_dl"],
        "cnn_cross_site": {k: v["cnn"]["mae_g_dl"] for k, v in cnn["cross_site"].items()},
        "between_subject_residual_at_fixed_hb_sex_age_site_dE": emp["headline"][
            "residual_between_subject_de2000_at_fixed_hb_sex_age_site"],
        "empirical_signal_dE_per_g_dl": emp["headline"]["de_per_g_dl"],
    }
    eyes["band_colour_model"] = ("VIABLE" if eyes["colour_model_mae_pooled"] < 1.0 else
                                 "MARGINAL" if eyes["colour_model_mae_pooled"] <= 2.0 else "NOT RECOVERABLE")

    # ------------------------------------------------------------ verdict
    studio_band = gate["sbvpi_studio"]["band"]
    ed_band = eyes["band_colour_model"]
    if studio_band == "VIABLE" and ed_band == "VIABLE":
        outcome = "A"
    elif "NOT RECOVERABLE" not in (studio_band, ed_band) or studio_band == "VIABLE" or ed_band == "VIABLE":
        outcome = "B"
    else:
        outcome = "C"
    sig = emp["headline"]["de_per_g_dl"]
    ns = {name: {"noise_dE": b["residual_dE2000"], "over_empirical_signal": b["residual_dE2000"] / sig,
                 "over_simulated_signal": b["residual_dE2000"] / 0.452} for name, b in best.items()}
    res = {"declared_in": "CLAUDE.md Phase 7 section, before running", "conditions": conds,
           "best_residual_per_condition": best, "gate": gate, "breakeven": breakeven,
           "noise_over_signal": ns, "eyes_defy": eyes,
           "outcome": outcome, "outcome_key": {"A": "closes the gap - restate narrowly",
                                               "B": "partial - controlled capture reaches MARGINAL only",
                                               "C": "generalises - refutation stronger"},
           "achieves_viable_residual": {name: (breakeven["residual_for_viable_1.0"] is not None and
                                              b["residual_dE2000"] < breakeven["residual_for_viable_1.0"])
                                        for name, b in best.items()},
           "elapsed_s": time.time() - t0}
    (OUT / "controlled_capture.json").write_text(json.dumps(res, indent=2, default=float), encoding="utf-8")
    print(f"\nOUTCOME {outcome}: {res['outcome_key'][outcome]}")
    print(f"wrote {OUT / 'controlled_capture.json'} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
