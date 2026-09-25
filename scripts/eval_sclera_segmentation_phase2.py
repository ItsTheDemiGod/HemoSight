"""Phase 2, Task 1 (evaluation) + Task 4: segmentation quality, broken down.

Reports IoU and Dice overall and BY MOBIUS DEVICE AND LIGHTING. If segmentation
quality varies by device it confounds every N1b number downstream, so it is measured
here rather than discovered later.

Also:
  * validates the per-image quality score against MOBIUS's deliberately-unusable
    `_bad` frames, which are a free labelled negative set;
  * quantifies how much sclera area the vasculature exclusion removes, and checks it
    against SBVPI's 128 ground-truth vessel masks;
  * Task 4 - runs the model on Eyes-Defy-Anemia, which has no masks, and reports
    confidence and failure rate rather than IoU.

    .\\.venv\\Scripts\\python.exe scripts\\eval_sclera_segmentation_phase2.py
"""

from __future__ import annotations

import json

import cv2
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Subset

from hemosight.calibration.segmentation import (
    UNetResNet18,
    confusion,
    iou_dice_from_confusion,
    predict_mask,
    quality_score,
    vessel_exclusion_mask,
)
from hemosight.calibration.segmentation_data import (
    CLASSES,
    N_CLASSES,
    SCLERA,
    EyeSegDataset,
    _read_binary,
    index_mobius,
    index_sbvpi,
    subject_split,
)
from hemosight.io import paths

OUT = paths.INTERIM / "phase2"
CKPT = OUT / "segmentation_unet_r18.pt"


def eval_subset(model, samples, idx, size, dev, batch=12):
    ds = EyeSegDataset(samples, size=size, augment=False)
    dl = DataLoader(Subset(ds, idx), batch_size=batch, shuffle=False, num_workers=4)
    cm = torch.zeros(N_CLASSES, N_CLASSES, dtype=torch.int64)
    with torch.no_grad():
        for x, y, _mg, _ in dl:
            x, y = x.to(dev), y.to(dev)
            with torch.autocast("cuda", dtype=torch.float16, enabled=dev == "cuda"):
                logits = model(x)
            cm += confusion(logits.float(), y).cpu()
    return cm.numpy()


def main() -> int:
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = torch.load(CKPT, map_location=dev, weights_only=False)
    model = UNetResNet18().to(dev)
    model.load_state_dict(ck["model"])
    model.eval()
    size = ck["size"]
    print(f"model: val sclera IoU={ck['sclera_iou']:.4f}, size={size}, device={dev}")

    mob_all = index_mobius()
    sbv = index_sbvpi()
    mob_bad = [s for s in mob_all if s.is_bad]
    mob = [s for s in mob_all if not s.is_bad]
    samples = mob + sbv
    _tr, va = subject_split(samples)  # identical seed -> identical held-out subjects
    results: dict = {}

    # ------------------------------------------------ overall + per dataset
    print("\n=== held-out IoU / Dice ===")
    for name, sel in (("all", va),
                      ("mobius", [i for i in va if samples[i].dataset == "mobius"]),
                      ("sbvpi", [i for i in va if samples[i].dataset == "sbvpi"])):
        if not sel:
            continue
        cm = eval_subset(model, samples, sel, size, dev)
        iou, dice = iou_dice_from_confusion(cm)
        results.setdefault("by_dataset", {})[name] = {
            "n": len(sel),
            "iou": {c: (None if np.isnan(v) else float(v)) for c, v in zip(CLASSES, iou)},
            "dice": {c: (None if np.isnan(v) else float(v)) for c, v in zip(CLASSES, dice)},
        }
        print(f"  {name:8s} n={len(sel):5d} "
              f"IoU sclera={iou[1]:.4f} iris={iou[2]:.4f} pupil={iou[3]:.4f} "
              f"periocular={iou[4]:.4f} | Dice sclera={dice[1]:.4f}")

    # ------------------------------------- BY DEVICE and BY LIGHTING (critical)
    print("\n=== MOBIUS held-out IoU BY DEVICE (confounder check) ===")
    for key in ("phone", "lighting"):
        groups: dict[str, list] = {}
        for i in va:
            s = samples[i]
            if s.dataset != "mobius":
                continue
            groups.setdefault(getattr(s, key), []).append(i)
        for g, sel in sorted(groups.items()):
            cm = eval_subset(model, samples, sel, size, dev)
            iou, dice = iou_dice_from_confusion(cm)
            results.setdefault(f"by_{key}", {})[str(g)] = {
                "n": len(sel), "sclera_iou": float(iou[1]), "sclera_dice": float(dice[1]),
                "iris_iou": float(iou[2]), "pupil_iou": float(iou[3]),
            }
            print(f"  {key:8s} {str(g):24s} n={len(sel):4d} "
                  f"sclera IoU={iou[1]:.4f} Dice={dice[1]:.4f} iris={iou[2]:.4f}")
        vals = [v["sclera_iou"] for v in results[f"by_{key}"].values()]
        spread = max(vals) - min(vals)
        results[f"by_{key}_spread"] = spread
        print(f"    -> sclera IoU spread across {key}: {spread:.4f}")

    # -------------------------------------------- quality score vs 'bad' frames
    print("\n=== quality score validated against MOBIUS '_bad' frames ===")
    rng = np.random.default_rng(0)
    good = [mob[i] for i in rng.choice(len(mob), size=min(120, len(mob)), replace=False)]
    qual = {"bad": [], "good": []}
    for tag, group in (("bad", mob_bad), ("good", good)):
        for s in group:
            bgr = cv2.imread(s.image_path, cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            _lab, probs = predict_mask(model, bgr[:, :, ::-1], size, dev)
            qual[tag].append(quality_score(probs)["quality"])
    for tag in ("good", "bad"):
        a = np.array(qual[tag])
        if len(a):
            print(f"  {tag:5s} n={len(a):4d} quality mean={a.mean():.3f} "
                  f"median={np.median(a):.3f} frac<0.3={float((a<0.3).mean()):.3f}")
    if qual["good"] and qual["bad"]:
        g, b = np.array(qual["good"]), np.array(qual["bad"])
        auc = float((g[:, None] > b[None, :]).mean() + 0.5 * (g[:, None] == b[None, :]).mean())
        results["quality_score"] = {
            "good_mean": float(g.mean()), "bad_mean": float(b.mean()),
            "n_good": len(g), "n_bad": len(b), "auroc_good_vs_bad": auc,
        }
        print(f"  AUROC separating good from deliberately-bad frames: {auc:.3f}")

    # ------------------------------------ vasculature exclusion vs SBVPI truth
    print("\n=== vasculature exclusion (SBVPI ground-truth vessel masks) ===")
    with_v = [s for s in sbv if s.vessels_path][:60]
    rec = []
    for s in with_v:
        bgr = cv2.imread(s.image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        rgb = bgr[:, :, ::-1]
        lab, _ = predict_mask(model, rgb, size, dev)
        sclera = lab == SCLERA
        if sclera.sum() < 200:
            continue
        kept, removed = vessel_exclusion_mask(rgb.astype(np.float64) / 255.0, sclera)
        truth = _read_binary(s.vessels_path, sclera.shape) & sclera
        if truth.sum() == 0:
            continue
        dropped = sclera & ~kept
        recall = float((dropped & truth).sum() / truth.sum())
        precision = float((dropped & truth).sum() / max(dropped.sum(), 1))
        rec.append({"removed_frac": removed, "vessel_frac_of_sclera":
                    float(truth.sum() / sclera.sum()),
                    "recall": recall, "precision": precision})
    if rec:
        d = pd.DataFrame(rec)
        results["vasculature"] = {
            "n": len(d),
            "mean_area_removed": float(d.removed_frac.mean()),
            "mean_true_vessel_frac_of_sclera": float(d.vessel_frac_of_sclera.mean()),
            "mean_recall_of_true_vessels": float(d.recall.mean()),
            "mean_precision": float(d.precision.mean()),
        }
        print(f"  n={len(d)} | sclera area removed: {d.removed_frac.mean()*100:.1f}%")
        print(f"  true vessels occupy {d.vessel_frac_of_sclera.mean()*100:.1f}% of sclera")
        print(f"  recall of true vessel pixels={d.recall.mean():.3f} "
              f"precision={d.precision.mean():.3f}")

    # ------------------------------------------------- Task 4: Eyes-Defy-Anemia
    print("\n=== Task 4: cross-dataset behaviour on Eyes-Defy-Anemia (no masks) ===")
    ed = pd.read_csv(paths.MANIFESTS / "eyes_defy.csv")
    rows = []
    for r in ed.itertuples():
        bgr = cv2.imread(r.file_path, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        lab, probs = predict_mask(model, bgr[:, :, ::-1], size, dev)
        q = quality_score(probs)
        rows.append({"image_id": r.image_id, "site": r.site, **q})
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "eyes_defy_segmentation_quality.csv", index=False)
    fail = float((d.quality < 0.3).mean())
    results["eyes_defy"] = {
        "n": len(d),
        "quality_mean": float(d.quality.mean()),
        "quality_median": float(d.quality.median()),
        "failure_rate_q_lt_0.3": fail,
        "sclera_area_fraction_mean": float(d.area_fraction.mean()),
        "confidence_mean": float(d.confidence.mean()),
        "by_site": {s: {"n": int(len(g)), "quality_mean": float(g.quality.mean()),
                        "failure_rate": float((g.quality < 0.3).mean())}
                    for s, g in d.groupby("site")},
    }
    print(f"  n={len(d)} quality mean={d.quality.mean():.3f} median={d.quality.median():.3f}")
    print(f"  sclera area fraction mean={d.area_fraction.mean():.4f}")
    print(f"  FAILURE RATE (quality<0.3): {fail*100:.1f}%")
    for s, g in d.groupby("site"):
        print(f"    {s:20s} n={len(g):3d} quality={g.quality.mean():.3f} "
              f"fail={float((g.quality<0.3).mean())*100:.1f}%")

    (OUT / "segmentation_eval.json").write_text(
        json.dumps(results, indent=2, default=float), encoding="utf-8")
    print(f"\nresults -> {OUT / 'segmentation_eval.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
