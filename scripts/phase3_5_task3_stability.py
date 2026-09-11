"""Phase 3.5, TASK 3: is the sclera reference stable WITHIN a subject?

The ratio reformulation does not need the sclera to be identical across people. It
needs it to be identical across captures OF THE SAME PERSON. Those are different
requirements and the data can satisfy one without the other, so they are measured
separately and their ratio reported.

    within-subject variation  <<  between-subject variation   -> the regime the
                                                                 method needs
    within-subject variation  ~=  between-subject variation   -> the reference is
                                                                 not a reference

Also tests whether a per-subject calibration offset would help, and - more
importantly - whether such an offset could ever be obtained in deployment.

    .\\.venv\\Scripts\\python.exe scripts\\phase3_5_task3_stability.py
"""

from __future__ import annotations

import json
import time
from collections import defaultdict

import cv2
import numpy as np
import torch

from hemosight.calibration.estimators import robust_patch_rgb
from hemosight.calibration.metrics import delta_e2000_pairwise_spread
from hemosight.calibration.segmentation import UNetResNet18, predict_mask, vessel_exclusion_mask
from hemosight.calibration.segmentation_data import SCLERA, index_mobius_all, index_sbvpi
from hemosight.calibration.selfconsistency import rgb_to_lab
from hemosight.io import paths

OUT = paths.INTERIM / "phase3_5"
CKPT = paths.INTERIM / "phase2" / "segmentation_unet_r18.pt"


def measure(model, ck, dev, samples, label):
    out = defaultdict(list)
    t0 = time.time()
    for i, s in enumerate(samples):
        if i % 100 == 0:
            print(f"  [{label}] {i}/{len(samples)} {time.time()-t0:.0f}s", end="\r", flush=True)
        bgr = cv2.imread(s.image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        rgb = bgr[:, :, ::-1].astype(np.float64) / 255.0
        labels, _ = predict_mask(model, (rgb * 255).astype(np.uint8), ck["size"], dev)
        m = labels == SCLERA
        if m.sum() < 200:
            continue
        m, _ = vessel_exclusion_mask(rgb, m)
        v = robust_patch_rgb(rgb[m])
        if np.isfinite(v).all():
            out[s.subject_id].append(rgb_to_lab(v))
        del rgb, bgr, labels
    print()
    return {k: np.array(v) for k, v in out.items() if len(v) >= 2}


def stability(labs: dict, name: str) -> dict:
    """Within- versus between-subject spread of sclera colour, both in dE2000."""
    within = []
    for _s, v in labs.items():
        d = delta_e2000_pairwise_spread(v)
        if np.isfinite(d["mean_pairwise"]):
            within.append(d["mean_pairwise"])
    centroids = np.array([v.mean(axis=0) for v in labs.values()])
    between = delta_e2000_pairwise_spread(centroids)

    w = float(np.mean(within)) if within else float("nan")
    b = float(between["mean_pairwise"])
    res = {"dataset": name, "n_subjects": len(labs),
           "n_captures_total": int(sum(len(v) for v in labs.values())),
           "within_subject_dE": w, "between_subject_dE": b,
           "ratio_within_over_between": float(w / b) if b > 0 else None,
           "within_subject_per_subject": {k: float(np.mean(
               [delta_e2000_pairwise_spread(v)["mean_pairwise"]])) for k, v in labs.items()}}
    print(f"  {name}: {len(labs)} subjects, {res['n_captures_total']} captures")
    print(f"    within-subject  dE2000 = {w:.3f}")
    print(f"    between-subject dE2000 = {b:.3f}")
    print(f"    within/between         = {res['ratio_within_over_between']:.3f}")
    return res


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = torch.load(CKPT, map_location=dev, weights_only=False)
    model = UNetResNet18().to(dev)
    model.load_state_dict(ck["model"])
    model.eval()

    # MOBIUS: same 3x3 grid as every other phase.
    cells = defaultdict(list)
    for s in index_mobius_all():
        if s.is_bad or not s.phone or not s.lighting:
            continue
        cells[(s.subject_id, s.phone, s.lighting)].append(s)
    mob = []
    for k in sorted(cells):
        mob.extend(sorted(cells[k], key=lambda s: (s.gaze != "s", s.image_path))[:1])

    # SBVPI: multiple captures per subject, controlled studio conditions.
    sbv = index_sbvpi()
    rng = np.random.default_rng(0)
    if len(sbv) > 700:
        sbv = [sbv[i] for i in rng.choice(len(sbv), 700, replace=False)]

    print("=== TASK 3: sclera reference stability ===")
    res = {}
    for name, samples in (("MOBIUS (3 phones x 3 lighting)", mob), ("SBVPI (studio)", sbv)):
        labs = measure(model, ck, dev, samples, name.split()[0])
        if labs:
            res[name] = stability(labs, name)

    # ---- would a per-subject offset help, and could it be obtained? ----------
    print("\n=== would a per-subject offset help? ===")
    for name, r in res.items():
        w, b = r["within_subject_dE"], r["between_subject_dE"]
        # Subtracting a per-subject mean removes the between-subject term entirely
        # and leaves the within-subject term untouched - that is what an offset does.
        r["residual_after_perfect_offset_dE"] = w
        r["offset_removes_dE"] = b
        print(f"  {name}:")
        print(f"    a PERFECT per-subject offset removes {b:.3f} dE2000 (the between "
              f"term) and leaves {w:.3f} (the within term)")
    res["offset_obtainable_in_deployment"] = False
    res["offset_note"] = (
        "A per-subject offset requires at least one capture of that subject with a "
        "KNOWN answer - a reference haemoglobin measurement, or a calibrated colour "
        "target in frame. In a screening deployment neither exists: the whole premise "
        "is a first, uncalibrated capture of a person whose haemoglobin is unknown. "
        "The offset is therefore NOT obtainable, and any performance figure that "
        "assumes it is reporting an oracle, not a method."
    )
    print(f"\n  OBTAINABLE IN DEPLOYMENT: {res['offset_obtainable_in_deployment']}")
    print(f"  {res['offset_note']}")

    (OUT / "task3_stability.json").write_text(json.dumps(res, indent=2, default=float),
                                              encoding="utf-8")
    print(f"\nresults -> {OUT / 'task3_stability.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
