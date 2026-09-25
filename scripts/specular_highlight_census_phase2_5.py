"""Phase 2.5, Task 1: corneal-highlight feasibility census. RUN THIS FIRST.

Gate declared before running: if fewer than 30% of images yield a detectable AND
unsaturated highlight, the method is not viable on this data and Task 2 is not
attempted.

Saturation is the crux. A highlight bright enough to see is often bright enough to
clip, and a clipped pixel's channel ratios are an artefact of the sensor ceiling
rather than a property of the light. So "detected" and "usable" are counted
separately and both are reported.

    .\\.venv\\Scripts\\python.exe scripts\\specular_highlight_census_phase2_5.py [--n 900]
"""

from __future__ import annotations

import argparse
import json
import time

import cv2
import numpy as np
import pandas as pd
import torch

from hemosight.calibration.segmentation import UNetResNet18, predict_mask
from hemosight.calibration.segmentation_data import index_mobius_all, index_sbvpi
from hemosight.calibration.specular import detect_highlights
from hemosight.io import paths

OUT = paths.INTERIM / "phase2_5"
CKPT = paths.INTERIM / "phase2" / "segmentation_unet_r18.pt"
FEASIBILITY_GATE = 0.30  # declared in CLAUDE.md before running


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=900, help="MOBIUS frames to census")
    ap.add_argument("--n-sbvpi", type=int, default=300)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = torch.load(CKPT, map_location=dev, weights_only=False)
    model = UNetResNet18().to(dev)
    model.load_state_dict(ck["model"])
    model.eval()
    print(f"segmentation model loaded (sclera IoU={ck['sclera_iou']:.4f}), device={dev}")

    rng = np.random.default_rng(20260911)
    mob = [s for s in index_mobius_all() if not s.is_bad]
    mob = [mob[i] for i in rng.choice(len(mob), size=min(args.n, len(mob)), replace=False)]
    sbv = index_sbvpi()
    sbv = [sbv[i] for i in rng.choice(len(sbv), size=min(args.n_sbvpi, len(sbv)), replace=False)]
    samples = [("mobius", s) for s in mob] + [("sbvpi", s) for s in sbv]
    print(f"census over {len(mob)} MOBIUS + {len(sbv)} SBVPI frames")

    rows = []
    t0 = time.time()
    for i, (ds, s) in enumerate(samples):
        if i % 100 == 0:
            print(f"  {i}/{len(samples)}  {time.time()-t0:.0f}s", end="\r", flush=True)
        bgr = cv2.imread(s.image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        rgb = bgr[:, :, ::-1]
        labels, _ = predict_mask(model, rgb, ck["size"], dev)
        obs = detect_highlights(rgb, labels)

        usable = [h for h in obs.highlights if h.unsaturated_rgb is not None]
        areas = [h.area_px for h in obs.highlights]
        rows.append({
            "dataset": ds, "image": s.image_path,
            "phone": s.phone, "lighting": s.lighting,
            "iris_pupil_px": obs.iris_pupil_px,
            "region_median_lum": obs.region_median_lum,
            "brightness_ratio": obs.brightness_ratio,
            "seg_found_iris_pupil": obs.iris_pupil_px >= 200,
            "n_highlights": obs.n_highlights,
            "n_usable": len(usable),
            "detected": obs.n_highlights > 0,
            "usable": len(usable) > 0,
            "max_area": max(areas) if areas else 0,
            "median_area": float(np.median(areas)) if areas else 0.0,
            "mean_saturated_frac": (float(np.mean([h.saturated_frac for h in obs.highlights]))
                                    if obs.highlights else np.nan),
            "any_fully_saturated": any(h.saturated_frac > 0.99 for h in obs.highlights),
            "max_unsat_px": max([h.n_unsaturated for h in obs.highlights], default=0),
            "pupil_usable": any(h.region == "pupil" and h.unsaturated_rgb is not None
                                for h in obs.highlights),
        })
    print()
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "census.csv", index=False)

    def frac(sub, col):
        return float(sub[col].mean()) if len(sub) else float("nan")

    res: dict = {"gate": FEASIBILITY_GATE, "n_total": len(d)}
    print("\n=== TASK 1: FEASIBILITY CENSUS ===")
    print(f"{'subset':28s} {'n':>5s} {'detected':>9s} {'USABLE':>8s} {'pupil':>7s} "
          f"{'medArea':>8s} {'satFrac':>8s}")
    for name, sub in [("ALL", d)] + [(f"dataset={k}", g) for k, g in d.groupby("dataset")]:
        print(f"{name:28s} {len(sub):5d} {frac(sub,'detected')*100:8.1f}% "
              f"{frac(sub,'usable')*100:7.1f}% {frac(sub,'pupil_usable')*100:6.1f}% "
              f"{sub.median_area.median():8.0f} {sub.mean_saturated_frac.mean():8.3f}")
        res[name] = {"n": len(sub), "detected": frac(sub, "detected"),
                     "usable": frac(sub, "usable"),
                     "pupil_usable": frac(sub, "pupil_usable"),
                     "median_area_px": float(sub.median_area.median()),
                     "mean_saturated_frac": float(sub.mean_saturated_frac.mean())}

    print("\n--- by phone (MOBIUS) ---")
    m = d[d.dataset == "mobius"]
    for key in ("phone", "lighting"):
        print(f"\n  by {key}:")
        by = {}
        for g, sub in m.groupby(key):
            print(f"    {str(g):26s} n={len(sub):4d} detected={frac(sub,'detected')*100:5.1f}% "
                  f"USABLE={frac(sub,'usable')*100:5.1f}% "
                  f"medArea={sub.median_area.median():5.0f} "
                  f"satFrac={sub.mean_saturated_frac.mean():.3f}")
            by[str(g)] = {"n": len(sub), "detected": frac(sub, "detected"),
                          "usable": frac(sub, "usable"),
                          "median_area_px": float(sub.median_area.median()),
                          "mean_saturated_frac": float(sub.mean_saturated_frac.mean())}
        res[f"by_{key}"] = by
        vals = [v["usable"] for v in by.values()]
        res[f"by_{key}_usable_spread"] = max(vals) - min(vals)
        print(f"    -> usable-rate spread across {key}: "
              f"{(max(vals)-min(vals))*100:.1f} percentage points")

    print("\n--- saturation distribution among detected highlights ---")
    det = d[d.detected]
    if len(det):
        qs = det.mean_saturated_frac.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).to_dict()
        print("    mean_saturated_frac quantiles: " +
              ", ".join(f"p{int(k*100)}={v:.3f}" for k, v in qs.items()))
        print(f"    frames where EVERY highlight is fully clipped: "
              f"{det.any_fully_saturated.mean()*100:.1f}%")
        print(f"    median unsaturated pixels in the best highlight: "
              f"{det.max_unsat_px.median():.0f}")
        res["saturation_quantiles"] = {f"p{int(k*100)}": float(v) for k, v in qs.items()}
        res["frac_frames_with_a_fully_clipped_highlight"] = float(det.any_fully_saturated.mean())
        res["median_unsat_px_best_highlight"] = float(det.max_unsat_px.median())

    # SBVPI is excluded from the gate denominator: Phase 2 established that iris and
    # pupil segmentation does not transfer to it (IoU 0.000), so a 0% highlight rate
    # there measures the segmentation, not the availability of highlights. Reported
    # separately and explicitly rather than silently averaged in.
    seg_ok = d[d.seg_found_iris_pupil]
    overall = frac(d, "usable")
    mob_rate = frac(d[d.dataset == "mobius"], "usable")
    res["overall_usable_rate"] = overall
    res["usable_rate_mobius_only"] = mob_rate
    res["usable_rate_where_segmentation_found_iris"] = frac(seg_ok, "usable")
    res["frac_frames_where_segmentation_found_iris"] = float(d.seg_found_iris_pupil.mean())
    res["sbvpi_seg_failure_note"] = (
        "SBVPI yields 0 iris/pupil pixels from the Phase 2 model (iris IoU 0.000 there), "
        "so its highlight rate measures segmentation transfer, not highlight availability."
    )
    res["gate_passed"] = bool(mob_rate >= FEASIBILITY_GATE)

    print("\n" + "=" * 62)
    print(f"usable rate, all frames incl. SBVPI : {overall*100:.1f}%")
    print(f"usable rate where segmentation works: {res['usable_rate_where_segmentation_found_iris']*100:.1f}%")
    print(f"USABLE RATE (MOBIUS, the gate)      : {mob_rate*100:.1f}%")
    print(f"PRE-DECLARED GATE            : {FEASIBILITY_GATE*100:.0f}%")
    print(f"VERDICT: {'PASS - proceed to Task 2' if res['gate_passed'] else 'FAIL - STOP, method not viable on this data'}")
    print("=" * 62)

    (OUT / "census.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nresults -> {OUT / 'census.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
