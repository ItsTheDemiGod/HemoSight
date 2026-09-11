"""Phase 2, Task 3: N1b - sclera self-consistency across devices and lighting.

Per subject, samples the full 3 phones x 3 lighting grid from MOBIUS, segments each
frame, estimates the illuminant by several methods, and measures how tightly the
corrected colour of a HELD-OUT region agrees across conditions.

Primary region is the IRIS, which is never used to estimate the illuminant, so the
comparison is not circular. See selfconsistency.py for why that matters.

    .\\.venv\\Scripts\\python.exe scripts\\phase2_n1b_selfconsistency.py [--per-cell N]
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict

import cv2
import numpy as np
import torch

from hemosight.calibration.estimators import grey_world, max_rgb, shades_of_grey
from hemosight.calibration.priors import (
    FixedPopulationPrior,
    NeutralPrior,
    PerKeyPrior,
    estimate_illuminant,
)
from hemosight.calibration.segmentation import UNetResNet18, predict_mask, quality_score
from hemosight.calibration.segmentation_data import (
    index_mobius,
    index_mobius_all,
    index_sbvpi,
    subject_split,
)
from hemosight.calibration.selfconsistency import (
    corrected_lab,
    measure_regions,
    per_subject_spread,
    variance_decomposition,
)
from hemosight.io import paths

OUT = paths.INTERIM / "phase2"
CKPT = OUT / "segmentation_unet_r18.pt"
REGIONS = {"iris": "eval_iris_rgb", "sclera_holdout": "eval_sclera_right_rgb"}


def select_grid(samples, per_cell: int):
    """Per subject, take up to `per_cell` frames from each (phone, lighting) cell."""
    cells = defaultdict(list)
    for s in samples:
        if s.is_bad or not s.phone or not s.lighting:
            continue
        cells[(s.subject_id, s.phone, s.lighting)].append(s)
    out = []
    for k in sorted(cells):
        # Prefer straight gaze: the sclera is most visible and least foreshortened.
        v = sorted(cells[k], key=lambda s: (s.gaze != "s", s.image_path))
        out.extend(v[:per_cell])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cell", type=int, default=2)
    ap.add_argument("--redness-pct", type=float, default=75.0)
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = torch.load(CKPT, map_location=dev, weights_only=False)
    model = UNetResNet18().to(dev)
    model.load_state_dict(ck["model"])
    model.eval()
    print(f"model loaded (val sclera IoU={ck.get('sclera_iou'):.4f}) device={dev}")

    # Use EVERY MOBIUS frame, not just the 3,559 annotated ones: those come from only
    # 35 subjects, and they are the subjects the segmentation model trained on. N1b
    # needs no ground-truth masks - the trained model supplies them.
    all_mob = index_mobius_all()
    sel = select_grid(all_mob, args.per_cell)
    subjects = sorted({s.subject_id for s in sel})

    # Which subjects did the segmentation model never see? Same samples and seed as
    # training, so the split is reproduced exactly.
    seg_samples = [s for s in index_mobius() if not s.is_bad] + index_sbvpi()
    tr_idx, _va = subject_split(seg_samples)
    seg_train_subjects = {seg_samples[i].subject_id for i in tr_idx}
    unseen = [s for s in subjects if s not in seg_train_subjects]
    print(f"selected {len(sel)} frames over {len(subjects)} subjects "
          f"({args.per_cell} per (phone,lighting) cell)")
    print(f"  of these, {len(unseen)} subjects were NEVER seen in segmentation training")

    # ---- pass 1: segment and measure -----------------------------------------
    t0 = time.time()
    obs = []
    for i, s in enumerate(sel):
        if i % 100 == 0:
            print(f"  segment {i}/{len(sel)}  {time.time()-t0:.0f}s", end="\r", flush=True)
        bgr = cv2.imread(s.image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        rgb = bgr[:, :, ::-1].astype(np.float64) / 255.0
        labels, probs = predict_mask(model, (rgb * 255).astype(np.uint8), ck["size"], dev)
        q = quality_score(probs)
        m = measure_regions(rgb, labels, args.redness_pct)
        # Whole-image baselines are computed HERE and the image is then discarded.
        # Retaining rgb (3000x1700 float64 ~= 120 MB) and labels for ~900 frames would
        # need >100 GB of RAM; only the small per-image summaries are kept.
        valid = np.isfinite(rgb).all(axis=2)
        whole = {
            "none": np.ones(3) / np.sqrt(3),
            "grey_world": grey_world(rgb, valid),
            "max_rgb_p99": max_rgb(rgb, valid, percentile=99.0),
            "shades_of_grey_p6": shades_of_grey(rgb, valid, p=6),
        }
        obs.append({"sample": s, "meas": m, "quality": q, "whole": whole})
        del rgb, bgr, labels, probs
    print(f"\n  segmented {len(obs)} frames in {time.time()-t0:.0f}s")

    vf = np.array([o["meas"]["vessel_fraction_removed"] for o in obs])
    qs = np.array([o["quality"]["quality"] for o in obs])
    print(f"  vasculature removed from sclera: mean={vf.mean()*100:.1f}% "
          f"median={np.median(vf)*100:.1f}%")
    print(f"  segmentation quality: mean={qs.mean():.3f} "
          f"| below 0.3: {(qs<0.3).mean()*100:.1f}%")

    # ---- fit the sclera reflectance prior on TRAIN subjects only --------------
    rng = np.random.default_rng(20260911)
    subs = np.array(subjects)
    rng.shuffle(subs)
    n_tr = int(0.6 * len(subs))
    train_subs, test_subs = set(subs[:n_tr]), set(subs[n_tr:])
    print(f"  prior fitted on {len(train_subs)} subjects, evaluated on {len(test_subs)}")

    # MOBIUS ships no ground-truth illuminant, so the prior is fitted under the stated
    # assumption that grey-world is unbiased ON AVERAGE over the training population.
    # That assumption is recorded in the report; it is not free.
    fit_meas, fit_illum, fit_keys = [], [], []
    for o in obs:
        if o["sample"].subject_id not in train_subs:
            continue
        ref = o["meas"]["ref_rgb"]
        if not np.isfinite(ref).all():
            continue
        gw = o["whole"]["grey_world"]
        fit_meas.append(ref)
        fit_illum.append(gw)
        fit_keys.append(o["sample"].subject_id)
    pop_prior = FixedPopulationPrior.fit(np.array(fit_meas), np.array(fit_illum))
    per_subj_prior = PerKeyPrior.fit(fit_keys, np.array(fit_meas), np.array(fit_illum))
    print(f"  population sclera reflectance prior = {np.round(pop_prior.value,4).tolist()} "
          f"(fitted on {pop_prior.n_fitted_on} frames)")
    print(f"  per-subject priors fitted for {len(per_subj_prior.table)} subjects")

    PRIORS = {"neutral": NeutralPrior(), "fixed_population": pop_prior,
              "per_subject": per_subj_prior}

    # ---- pass 2: estimate illuminants and correct ----------------------------
    records = []
    for o in obs:
        s = o["sample"]
        if s.subject_id not in test_subs:
            continue
        lab: dict = {}
        base = dict(o["whole"])
        # Sclera-referenced under each prior, so the prior question is measured.
        # The reference is the LEFT half of the sclera only; the right half and the
        # iris are held out for evaluation (see selfconsistency.py on circularity).
        ref = o["meas"]["ref_rgb_left"]
        if np.isfinite(ref).all():
            for pname, prior in PRIORS.items():
                base[f"sclera_prior_{pname}"] = estimate_illuminant(ref, prior, s.subject_id)
        for mname, illum in base.items():
            for rname, key in REGIONS.items():
                lab[(mname, rname)] = corrected_lab(o["meas"][key], illum)
        records.append({"subject": s.subject_id, "phone": s.phone, "lighting": s.lighting,
                        "seg_unseen": s.subject_id not in seg_train_subjects,
                        "quality": o["quality"]["quality"], "lab": lab,
                        "methods": sorted(base)})

    methods = sorted({m for r in records for m in r["methods"]})
    print(f"\n  evaluating {len(records)} held-out frames, {len(methods)} methods")

    # ---- spreads and variance decomposition ----------------------------------
    results: dict = {"n_records": len(records), "methods": methods,
                     "n_subjects_total": len(subjects),
                     "n_subjects_unseen_by_segmentation": len(unseen),
                     "vessel_fraction_removed_mean": float(vf.mean()),
                     "population_prior": np.round(pop_prior.value, 5).tolist(),
                     "spread": {}, "variance": {}}
    print("\n=== N1b: within-subject DeltaE2000 spread (LOWER IS BETTER) ===")
    for region in REGIONS:
        print(f"\n--- region: {region}"
              + ("  [PRIMARY, non-circular]" if region == "iris"
                 else "  [secondary, spatial holdout, partially circular]"))
        rows = []
        for m in methods:
            sp = per_subject_spread(records, m, region)
            if not sp:
                continue
            mp = np.array([v["mean_pairwise"] for v in sp.values()])
            mc = np.array([v["mean_to_centroid"] for v in sp.values()])
            rows.append((m, float(np.nanmean(mp)), float(np.nanmedian(mp)),
                         float(np.nanmean(mc)), len(sp)))
            results["spread"].setdefault(region, {})[m] = {
                "mean_pairwise_dE": float(np.nanmean(mp)),
                "median_pairwise_dE": float(np.nanmedian(mp)),
                "mean_to_centroid_dE": float(np.nanmean(mc)),
                "n_subjects": len(sp),
                "per_subject_mean_pairwise": {k: v["mean_pairwise"] for k, v in sp.items()},
            }
        for m, mean, med, cen, n in sorted(rows, key=lambda r: r[1]):
            print(f"    {m:28s} meanDE={mean:6.2f}  medianDE={med:6.2f}  "
                  f"toCentroid={cen:6.2f}  (n={n} subjects)")

        for m in methods:
            v = variance_decomposition(records, m, region)
            if v:
                results["variance"].setdefault(region, {})[m] = v

    print("\n=== variance decomposition on the iris (fraction of total) ===")
    for m, v in sorted(results["variance"].get("iris", {}).items(),
                       key=lambda kv: kv[1]["frac_within_phone"]):
        print(f"    {m:28s} phone={v['frac_within_phone']:.3f} "
              f"lighting={v['frac_within_lighting']:.3f} "
              f"resid={v['frac_within_residual']:.3f} "
              f"between_subj={v['frac_between_subject']:.3f}")

    (OUT / "n1b_selfconsistency.json").write_text(
        json.dumps(results, indent=2, default=float), encoding="utf-8")
    print(f"\nresults -> {OUT / 'n1b_selfconsistency.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
