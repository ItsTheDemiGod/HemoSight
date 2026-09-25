"""Phase 3.5, TASK 1: does the illuminant actually cancel in a within-image ratio?

Run and report this before anything else in the phase.

Under a von Kries diagonal model, observed = reflectance x illuminant per channel, so
the ratio of two regions in the SAME image should be illuminant-free:

    region_A / region_B  =  R_A / R_B

If that holds, the within-subject spread of the ratio across MOBIUS's 3 phones x 3
lighting conditions should be far smaller than the spread of any absolute-colour
method, because no estimation step happens at all.

Two things can break it, and both are measured rather than assumed:
  1. **von Kries diagonality failing** - real camera sensitivities overlap, so a
     change of illuminant is not exactly a per-channel gain. A surviving PHONE effect
     is the signature of this, since it is the sensor that sets the diagonality error.
  2. **Region instability** - the ratio is only illuminant-free if both regions are
     the same tissue under the same geometry each time. Specular highlights, gaze
     angle and segmentation error all violate that.

REGION PAIR AVAILABILITY. MOBIUS segments sclera, iris and pupil - NOT conjunctiva.
The pair the deployed method would actually use (conjunctiva/sclera) therefore cannot
be tested here; Eyes-Defy has palpebral masks but only ONE capture per subject, so it
cannot test within-subject stability at all. `iris/sclera` is the available proxy:
two stable per-subject surfaces with different reflectances, which is the same
algebraic situation. This substitution is reported, not hidden.

    .\\.venv\\Scripts\\python.exe scripts\\illuminant_ratio_cancellation_phase3_5.py
"""

from __future__ import annotations

import json
import time
from collections import defaultdict

import cv2
import numpy as np
import torch

from hemosight.calibration.estimators import grey_world, robust_patch_rgb
from hemosight.calibration.metrics import delta_e2000_pairwise_spread
from hemosight.calibration.segmentation import UNetResNet18, predict_mask, vessel_exclusion_mask
from hemosight.calibration.segmentation_data import IRIS, PUPIL, SCLERA, index_mobius_all
from hemosight.calibration.selfconsistency import rgb_to_lab, variance_decomposition
from hemosight.io import paths
from hemosight.simulation import constants as C
from hemosight.simulation.forward import layered_reflectance

OUT = paths.INTERIM / "phase3_5"
CKPT = paths.INTERIM / "phase2" / "segmentation_unet_r18.pt"

# Phase 2 / 2.5 absolute-colour baselines on the identical protocol, for comparison.
BASELINES = {"none": 9.530, "grey_world_full": 6.076, "grey_world_25pct_fov": 3.935,
             "sclera_referenced": 7.427, "specular": 7.821}


def ratio_feature(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Per-channel ratio, normalised to unit sum. The illuminant cancels in a/b."""
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        return np.full(3, np.nan)
    r = a / np.clip(b, 1e-8, None)
    s = r.sum()
    return r / s if s > 0 else np.full(3, np.nan)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = torch.load(CKPT, map_location=dev, weights_only=False)
    model = UNetResNet18().to(dev)
    model.load_state_dict(ck["model"])
    model.eval()

    # Identical frame selection to Phase 2 and 2.5.
    cells = defaultdict(list)
    for s in index_mobius_all():
        if s.is_bad or not s.phone or not s.lighting:
            continue
        cells[(s.subject_id, s.phone, s.lighting)].append(s)
    sel = []
    for k in sorted(cells):
        v = sorted(cells[k], key=lambda s: (s.gaze != "s", s.image_path))
        sel.extend(v[:2])
    print(f"{len(sel)} frames over {len({s.subject_id for s in sel})} subjects "
          f"(identical protocol to Phase 2/2.5)")

    PAIRS = {"iris_over_sclera": (IRIS, SCLERA),
             "pupil_over_sclera": (PUPIL, SCLERA),
             "pupil_over_iris": (PUPIL, IRIS)}

    records = []
    t0 = time.time()
    for i, s in enumerate(sel):
        if i % 100 == 0:
            print(f"  {i}/{len(sel)}  {time.time()-t0:.0f}s", end="\r", flush=True)
        bgr = cv2.imread(s.image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        rgb = bgr[:, :, ::-1].astype(np.float64) / 255.0
        labels, _ = predict_mask(model, (rgb * 255).astype(np.uint8), ck["size"], dev)

        region_rgb = {}
        for cls, name in ((SCLERA, "sclera"), (IRIS, "iris"), (PUPIL, "pupil")):
            m = labels == cls
            if cls == SCLERA and m.sum() > 50:
                m, _ = vessel_exclusion_mask(rgb, m)   # same treatment as Phase 2
            region_rgb[name] = (robust_patch_rgb(rgb[m]) if m.sum() > 50
                                else np.full(3, np.nan))

        lab = {}
        for pname, (ca, cb) in PAIRS.items():
            na = {IRIS: "iris", PUPIL: "pupil", SCLERA: "sclera"}[ca]
            nb = {IRIS: "iris", PUPIL: "pupil", SCLERA: "sclera"}[cb]
            r = ratio_feature(region_rgb[na], region_rgb[nb])
            lab[(pname, "ratio")] = rgb_to_lab(r) if np.isfinite(r).all() else np.full(3, np.nan)

        # Control: the raw sclera colour with NO correction, same frames.
        lab[("uncorrected_sclera", "ratio")] = (
            rgb_to_lab(region_rgb["sclera"]) if np.isfinite(region_rgb["sclera"]).all()
            else np.full(3, np.nan))
        # Control: grey-world corrected sclera, the current best method.
        gw = grey_world(rgb, np.isfinite(rgb).all(axis=2))
        lab[("greyworld_sclera", "ratio")] = (
            rgb_to_lab(region_rgb["sclera"] / np.clip(gw, 1e-8, None))
            if np.isfinite(region_rgb["sclera"]).all() else np.full(3, np.nan))

        records.append({"subject": s.subject_id, "phone": s.phone,
                        "lighting": s.lighting, "lab": lab})
        del rgb, bgr, labels
    print(f"\n  processed {len(records)} frames in {time.time()-t0:.0f}s")

    # ---- ratio sensitivity to Hb, from the forward model ---------------------
    # Needed to express the spread in equivalent-Hb units, as the thresholds require.
    wl = C.WAVELENGTHS_NM
    from hemosight.simulation.forward import (
        camera_sensitivities,
        illuminant_spd,
        spectrum_to_rgb,
    )
    ill = illuminant_spd(wl, "D65")
    sens = camera_sensitivities(wl)

    def sim_ratio(hb):
        conj = layered_reflectance(wl, hb, 0.75, 0.06, 0.0)
        # A stable reference surface: same tissue stack, minimal blood (sclera-like).
        ref = layered_reflectance(wl, hb, 0.75, 0.002, 0.0)
        a = spectrum_to_rgb(wl, conj, ill, sens)
        b = spectrum_to_rgb(wl, ref, ill, sens)
        return ratio_feature(a, b)

    sens_de = []
    for h in range(4, 18):
        la, lb = rgb_to_lab(sim_ratio(h)), rgb_to_lab(sim_ratio(h + 1))
        sens_de.append(float(np.linalg.norm(la - lb)))
    ratio_sensitivity = float(np.mean(sens_de))
    print(f"\n  ratio-feature sensitivity: {ratio_sensitivity:.3f} dE2000-equivalent "
          f"per g/dL  (absolute-colour signal was 0.452)")

    # ---- spreads --------------------------------------------------------------
    methods = sorted({m for r in records for (m, _) in r["lab"]})
    results = {"n_frames": len(records), "ratio_sensitivity_de_per_g_dl": ratio_sensitivity,
               "baselines_absolute_colour": BASELINES, "spread": {}, "variance": {}}

    print("\n=== TASK 1: within-subject spread of the RATIO across 3 phones x 3 lighting ===")
    print(f"  {'feature':24s} {'meanDE':>8s} {'medianDE':>9s} {'equiv g/dL':>11s} {'n':>4s}")
    by_subject_cache = {}
    for m in methods:
        per = defaultdict(list)
        for r in records:
            lab = r["lab"].get((m, "ratio"))
            if lab is not None and np.isfinite(lab).all():
                per[r["subject"]].append(lab)
        spreads = {s: delta_e2000_pairwise_spread(np.array(v))["mean_pairwise"]
                   for s, v in per.items() if len(v) >= 2}
        if not spreads:
            continue
        vals = np.array([v for v in spreads.values() if np.isfinite(v)])
        equiv = float(vals.mean() / ratio_sensitivity) if ratio_sensitivity > 0 else np.nan
        by_subject_cache[m] = spreads
        results["spread"][m] = {
            "mean_pairwise_dE": float(vals.mean()),
            "median_pairwise_dE": float(np.median(vals)),
            "equivalent_hb_g_dl": equiv,
            "n_subjects": int(len(vals)),
            "per_subject": {k: float(v) for k, v in spreads.items()},
        }
        print(f"  {m:24s} {vals.mean():8.3f} {np.median(vals):9.3f} {equiv:11.3f} "
              f"{len(vals):4d}")

    print("\n=== variance decomposition (phone / lighting) ===")
    for m in methods:
        v = variance_decomposition(records, m, "ratio")
        if v:
            results["variance"][m] = v
            print(f"  {m:24s} phone={v['frac_within_phone']:.3f} "
                  f"lighting={v['frac_within_lighting']:.3f} "
                  f"resid={v['frac_within_residual']:.3f} "
                  f"between_subj={v['frac_between_subject']:.3f}")

    # ---- verdict against the pre-declared thresholds -------------------------
    best_ratio = min(
        (m for m in results["spread"] if m in PAIRS),
        key=lambda m: results["spread"][m]["equivalent_hb_g_dl"], default=None)
    if best_ratio:
        eq = results["spread"][best_ratio]["equivalent_hb_g_dl"]
        band = ("CANCELS" if eq < 1.0 else "PARTIAL" if eq <= 2.0 else "FAILS")
        results["best_ratio_feature"] = best_ratio
        results["best_equivalent_hb_g_dl"] = eq
        results["band"] = band
        print("\n" + "=" * 68)
        print(f"TASK 1 RESULT: best ratio feature = {best_ratio}")
        print(f"  within-subject spread     : "
              f"{results['spread'][best_ratio]['mean_pairwise_dE']:.3f} dE2000")
        print(f"  ratio sensitivity         : {ratio_sensitivity:.3f} dE2000 per g/dL")
        print(f"  EQUIVALENT Hb RESIDUAL    : {eq:.3f} g/dL   ->   **{band}**")
        print("  (pre-declared: <1.0 cancels, 1.0-2.0 partial, >2.0 fails)")
        print("=" * 68)

    (OUT / "task1_cancellation.json").write_text(
        json.dumps(results, indent=2, default=float), encoding="utf-8")
    print(f"\nresults -> {OUT / 'task1_cancellation.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
