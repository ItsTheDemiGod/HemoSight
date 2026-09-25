"""Phase 2.5, Tasks 3 and 4: specular illuminant estimation, evaluated on the
IDENTICAL Phase 2 protocol so the numbers are directly comparable.

Task 3 - within-subject dE2000 spread on the HELD-OUT IRIS, circularity guard intact.
Task 4 - deployment realism: how grey-world degrades as the field of view narrows
         toward a tight periocular crop, which is what a real capture would give.

    .\\.venv\\Scripts\\python.exe scripts\\specular_illuminant_evaluation_phase2_5.py [--per-cell 2]
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict

import cv2
import numpy as np
import torch
from scipy import stats as sps

from hemosight.calibration.estimators import grey_world, max_rgb, shades_of_grey
from hemosight.calibration.priors import (
    FixedPopulationPrior,
    NeutralPrior,
    estimate_illuminant,
)
from hemosight.calibration.segmentation import UNetResNet18, predict_mask
from hemosight.calibration.segmentation_data import index_mobius, index_mobius_all, index_sbvpi, subject_split
from hemosight.calibration.selfconsistency import (
    corrected_lab,
    measure_regions,
    per_subject_spread,
    variance_decomposition,
)
from hemosight.calibration.specular import (
    estimate_specular_illuminant,
)
from hemosight.io import paths

OUT = paths.INTERIM / "phase2_5"
CKPT = paths.INTERIM / "phase2" / "segmentation_unet_r18.pt"
# Crop fractions for Task 4: 1.0 = full frame, 0.15 = tight periocular crop.
CROPS = (1.0, 0.6, 0.4, 0.25, 0.15)


def centre_crop(img: np.ndarray, frac: float, centre=None) -> np.ndarray:
    h, w = img.shape[:2]
    ch, cw = int(h * frac), int(w * frac)
    cy, cx = (h // 2, w // 2) if centre is None else centre
    y0 = int(np.clip(cy - ch // 2, 0, max(h - ch, 0)))
    x0 = int(np.clip(cx - cw // 2, 0, max(w - cw, 0)))
    return img[y0:y0 + ch, x0:x0 + cw]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cell", type=int, default=2)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = torch.load(CKPT, map_location=dev, weights_only=False)
    model = UNetResNet18().to(dev)
    model.load_state_dict(ck["model"])
    model.eval()

    # Identical selection to Phase 2 so subjects and frames match exactly.
    cells = defaultdict(list)
    for s in index_mobius_all():
        if s.is_bad or not s.phone or not s.lighting:
            continue
        cells[(s.subject_id, s.phone, s.lighting)].append(s)
    sel = []
    for k in sorted(cells):
        v = sorted(cells[k], key=lambda s: (s.gaze != "s", s.image_path))
        sel.extend(v[:args.per_cell])
    subjects = sorted({s.subject_id for s in sel})
    print(f"{len(sel)} frames over {len(subjects)} subjects (identical to Phase 2)")

    seg_samples = [s for s in index_mobius() if not s.is_bad] + index_sbvpi()
    tr_idx, _ = subject_split(seg_samples)
    seg_train = {seg_samples[i].subject_id for i in tr_idx}

    # ---- pass 1: segment, measure, estimate ---------------------------------
    t0 = time.time()
    obs_list = []
    for i, s in enumerate(sel):
        if i % 100 == 0:
            print(f"  {i}/{len(sel)}  {time.time()-t0:.0f}s", end="\r", flush=True)
        bgr = cv2.imread(s.image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        rgb8 = bgr[:, :, ::-1]
        rgb = rgb8.astype(np.float64) / 255.0
        labels, _ = predict_mask(model, rgb8, ck["size"], dev)
        meas = measure_regions(rgb, labels)
        valid = np.isfinite(rgb).all(axis=2)

        whole = {
            "none": np.ones(3) / np.sqrt(3),
            "grey_world": grey_world(rgb, valid),
            "max_rgb_p99": max_rgb(rgb, valid, percentile=99.0),
            "shades_of_grey_p6": shades_of_grey(rgb, valid, p=6),
        }

        spec = estimate_specular_illuminant(rgb8, labels)

        # Task 4: grey-world under progressively tighter crops, centred on the eye.
        ys, xs = np.nonzero(labels > 0)
        centre = (int(np.median(ys)), int(np.median(xs))) if len(ys) else None
        crop_gw = {}
        for f in CROPS:
            c = centre_crop(rgb, f, centre)
            if c.size and min(c.shape[:2]) > 8:
                crop_gw[f] = grey_world(c, np.isfinite(c).all(axis=2))

        obs_list.append({
            "sample": s, "meas": meas, "whole": whole, "crop_gw": crop_gw,
            "spec_illum": spec.illuminant, "spec_method": spec.method,
            "n_clusters": spec.n_chroma_clusters,
            "n_highlights": spec.n_highlights,
            "has_usable": spec.has_usable,
        })
        del rgb, rgb8, bgr, labels
    print(f"\n  processed {len(obs_list)} frames in {time.time()-t0:.0f}s")

    n_spec = sum(1 for o in obs_list if o["spec_illum"] is not None)
    print(f"  specular estimate available: {n_spec}/{len(obs_list)} "
          f"({100*n_spec/max(len(obs_list),1):.1f}%)")
    meth = defaultdict(int)
    for o in obs_list:
        meth[o["spec_method"]] += 1
    print(f"  by decomposition route: {dict(meth)}")
    clus = [o["n_clusters"] for o in obs_list if o["spec_illum"] is not None]
    if clus:
        vals, cnts = np.unique(clus, return_counts=True)
        print(f"  distinct chromatic clusters per frame: "
              f"{dict(zip(vals.tolist(), cnts.tolist()))} "
              f"(multi-source frames: {100*np.mean(np.array(clus) > 1):.1f}%)")

    # ---- sclera prior, fitted on train subjects (same as Phase 2) ------------
    rng = np.random.default_rng(20260911)
    subs = np.array(subjects)
    rng.shuffle(subs)
    n_tr = int(0.6 * len(subs))
    train_subs, test_subs = set(subs[:n_tr]), set(subs[n_tr:])
    fm, fi = [], []
    for o in obs_list:
        if o["sample"].subject_id in train_subs and np.isfinite(o["meas"]["ref_rgb"]).all():
            fm.append(o["meas"]["ref_rgb"])
            fi.append(o["whole"]["grey_world"])
    pop_prior = FixedPopulationPrior.fit(np.array(fm), np.array(fi))

    # ---- pass 2: build records ----------------------------------------------
    records = []
    for o in obs_list:
        s = o["sample"]
        if s.subject_id not in test_subs:
            continue
        base = dict(o["whole"])
        ref = o["meas"]["ref_rgb_left"]
        if np.isfinite(ref).all():
            base["sclera_neutral"] = estimate_illuminant(ref, NeutralPrior())
            base["sclera_fitted_prior"] = estimate_illuminant(ref, pop_prior, s.subject_id)
        if o["spec_illum"] is not None:
            base["specular"] = o["spec_illum"]
            # Combined: the specular estimate constrains the illuminant direction; the
            # sclera constrains magnitude balance. Geometric mean in log-chromaticity
            # is the natural combination for a multiplicative model.
            if "sclera_fitted_prior" in base:
                comb = np.exp(0.5 * (np.log(np.clip(base["specular"], 1e-8, None))
                                     + np.log(np.clip(base["sclera_fitted_prior"], 1e-8, None))))
                base["specular_plus_sclera"] = comb / np.linalg.norm(comb)
        for f, gw in o["crop_gw"].items():
            base[f"grey_world_crop{f:g}"] = gw

        lab = {}
        for mname, illum in base.items():
            lab[(mname, "iris")] = corrected_lab(o["meas"]["eval_iris_rgb"], illum)
        records.append({"subject": s.subject_id, "phone": s.phone,
                        "lighting": s.lighting, "lab": lab,
                        "seg_unseen": s.subject_id not in seg_train,
                        "methods": sorted(base)})

    methods = sorted({m for r in records for m in r["methods"]})
    print(f"\n  {len(records)} held-out frames, {len(test_subs)} subjects, "
          f"{len(methods)} methods")

    # ---- Task 3: spreads + paired stats vs grey-world ------------------------
    results: dict = {
        "n_records": len(records), "n_subjects": len(test_subs),
        "specular_available_rate": n_spec / max(len(obs_list), 1),
        "decomposition_routes": dict(meth),
        "cluster_histogram": {int(v): int(c) for v, c in
                              zip(*np.unique(clus, return_counts=True))} if clus else {},
        "spread": {}, "variance": {}, "paired_vs_grey_world": {}, "crop": {},
    }
    spreads = {m: per_subject_spread(records, m, "iris") for m in methods}
    spreads = {m: v for m, v in spreads.items() if v}

    print("\n=== TASK 3: within-subject dE2000 spread on the HELD-OUT IRIS ===")
    main_methods = [m for m in spreads if not m.startswith("grey_world_crop")]
    for m in sorted(main_methods, key=lambda m: np.nanmean(
            [v["mean_pairwise"] for v in spreads[m].values()])):
        vals = np.array([v["mean_pairwise"] for v in spreads[m].values()])
        results["spread"][m] = {
            "mean_pairwise_dE": float(np.nanmean(vals)),
            "median_pairwise_dE": float(np.nanmedian(vals)),
            "n_subjects": len(vals),
            "per_subject_mean_pairwise": {k: v["mean_pairwise"]
                                          for k, v in spreads[m].items()},
        }
        print(f"    {m:28s} mean={np.nanmean(vals):6.3f}  median={np.nanmedian(vals):6.3f}"
              f"  (n={len(vals)})")

    # Paired against grey-world on the subjects both methods cover.
    print("\n=== paired vs GREY-WORLD (the benchmark to beat) ===")
    gw = spreads.get("grey_world", {})
    for m in sorted(main_methods):
        if m == "grey_world":
            continue
        common = sorted(set(gw) & set(spreads[m]))
        if len(common) < 8:
            continue
        a = np.array([spreads[m][s]["mean_pairwise"] for s in common])
        b = np.array([gw[s]["mean_pairwise"] for s in common])
        p = float(sps.wilcoxon(a, b).pvalue)
        results["paired_vs_grey_world"][m] = {
            "n_subjects": len(common), "mean_diff": float((a - b).mean()),
            "wilcoxon_p": p, "win_rate": float((a < b).mean()),
        }
        print(f"    {m:28s} diff={float((a-b).mean()):+6.3f}  p={p:.2e}  "
              f"wins {int((a<b).sum())}/{len(common)}")

    for m in main_methods:
        v = variance_decomposition(records, m, "iris")
        if v:
            results["variance"][m] = v
    print("\n=== variance decomposition (iris) ===")
    for m, v in sorted(results["variance"].items(), key=lambda kv: kv[1]["frac_within_phone"]):
        print(f"    {m:28s} phone={v['frac_within_phone']:.3f} "
              f"lighting={v['frac_within_lighting']:.3f} "
              f"between_subj={v['frac_between_subject']:.3f}")

    # ---- Task 4: crop sensitivity -------------------------------------------
    print("\n=== TASK 4: grey-world under a narrowing field of view ===")
    for f in CROPS:
        key = f"grey_world_crop{f:g}"
        if key not in spreads:
            continue
        vals = np.array([v["mean_pairwise"] for v in spreads[key].values()])
        results["crop"][str(f)] = {"mean_pairwise_dE": float(np.nanmean(vals)),
                                   "n_subjects": len(vals)}
        print(f"    crop={f:<5g} (FOV {f*100:3.0f}%)  mean dE={np.nanmean(vals):6.3f}")
    for m in ("specular", "sclera_fitted_prior", "none"):
        if m in results["spread"]:
            results["crop"][m] = {"mean_pairwise_dE": results["spread"][m]["mean_pairwise_dE"]}
            print(f"    {m:22s} (crop-invariant) mean dE="
                  f"{results['spread'][m]['mean_pairwise_dE']:6.3f}")

    (OUT / "evaluation.json").write_text(json.dumps(results, indent=2, default=float),
                                         encoding="utf-8")
    print(f"\nresults -> {OUT / 'evaluation.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
