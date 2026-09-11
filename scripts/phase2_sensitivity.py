"""Phase 2 plan item 6: sensitivity of the sclera-referenced estimate to
mask error, specular highlights, scleral yellowing and vessel coverage.

The estimate is only as good as the region it is measured on. This quantifies how
each failure mode moves the illuminant estimate, in the same angular-error units as
N1a, so the two are directly comparable.

    .\\.venv\\Scripts\\python.exe scripts\\phase2_sensitivity.py
"""

from __future__ import annotations

import json

import cv2
import numpy as np
import torch

from hemosight.calibration.estimators import robust_patch_rgb
from hemosight.calibration.metrics import angular_error
from hemosight.calibration.priors import NeutralPrior, estimate_illuminant
from hemosight.calibration.segmentation import (
    UNetResNet18,
    predict_mask,
    vessel_exclusion_mask,
)
from hemosight.calibration.segmentation_data import SCLERA, index_mobius
from hemosight.io import paths

OUT = paths.INTERIM / "phase2"
CKPT = OUT / "segmentation_unet_r18.pt"


def est_from_mask(img, mask, exclude_vessels=True, pct=75.0):
    if mask.sum() < 50:
        return None
    m = mask
    if exclude_vessels:
        m, _ = vessel_exclusion_mask(img, mask, pct)
        if m.sum() < 50:
            m = mask
    return estimate_illuminant(robust_patch_rgb(img[m]), NeutralPrior())


def main() -> int:
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = torch.load(CKPT, map_location=dev, weights_only=False)
    model = UNetResNet18().to(dev)
    model.load_state_dict(ck["model"])
    model.eval()

    mob = [s for s in index_mobius() if not s.is_bad and s.gaze == "s"]
    rng = np.random.default_rng(0)
    sel = [mob[i] for i in rng.choice(len(mob), size=min(120, len(mob)), replace=False)]
    print(f"sensitivity analysis over {len(sel)} MOBIUS frames")

    rows = []
    for s in sel:
        bgr = cv2.imread(s.image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        img = bgr[:, :, ::-1].astype(np.float64) / 255.0
        labels, _ = predict_mask(model, (img * 255).astype(np.uint8), ck["size"], dev)
        sclera = labels == SCLERA
        if sclera.sum() < 500:
            continue
        base = est_from_mask(img, sclera)
        if base is None:
            continue
        r = {"image": s.image_path, "phone": s.phone, "lighting": s.lighting,
             "sclera_px": int(sclera.sum())}

        # --- mask error: erode / dilate the sclera boundary -------------------
        for k in (5, 15, 31):
            ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
            for op, tag in ((cv2.MORPH_ERODE, "erode"), (cv2.MORPH_DILATE, "dilate")):
                m2 = cv2.morphologyEx(sclera.astype(np.uint8), op, ker).astype(bool)
                e = est_from_mask(img, m2)
                r[f"mask_{tag}{k}"] = (float(angular_error(e, base)[0])
                                       if e is not None else np.nan)

        # --- specular highlights: keep them in, versus the robust trim --------
        m_v, _ = vessel_exclusion_mask(img, sclera)
        raw_mean = img[m_v].mean(axis=0)
        r["specular_naive_mean_vs_robust"] = float(
            angular_error(raw_mean / np.linalg.norm(raw_mean), base)[0])

        # --- vessel coverage: how far the estimate moves if vessels stay ------
        e_novess = est_from_mask(img, sclera, exclude_vessels=False)
        r["vessels_included_shift"] = (float(angular_error(e_novess, base)[0])
                                       if e_novess is not None else np.nan)
        for pct in (50.0, 90.0):
            e_p = est_from_mask(img, sclera, pct=pct)
            r[f"vessel_pct{int(pct)}_shift"] = (float(angular_error(e_p, base)[0])
                                                if e_p is not None else np.nan)

        # --- scleral yellowing: simulate an ageing sclera ---------------------
        # A yellower sclera raises R and G relative to B. With a NEUTRAL prior the
        # estimate absorbs that entirely as if it were illuminant colour, which is
        # exactly the error mode the reflectance prior exists to prevent.
        for amt in (0.05, 0.10, 0.20):
            yellow = np.array([1 + amt, 1 + amt * 0.6, 1 - amt])
            e_y = est_from_mask(img * yellow, sclera)
            r[f"yellowing_{int(amt*100)}pct"] = (float(angular_error(e_y, base)[0])
                                                 if e_y is not None else np.nan)
        rows.append(r)

    import pandas as pd
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "sensitivity.csv", index=False)

    cols = [c for c in d.columns if c not in ("image", "phone", "lighting", "sclera_px")]
    summary = {c: {"mean_deg": float(d[c].mean()), "median_deg": float(d[c].median()),
                   "p90_deg": float(d[c].quantile(0.9))} for c in cols}
    (OUT / "sensitivity.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n{'perturbation':34s} {'mean':>8s} {'median':>8s} {'p90':>8s}   "
          f"(angular shift, degrees)")
    for c in cols:
        v = summary[c]
        print(f"  {c:32s} {v['mean_deg']:8.3f} {v['median_deg']:8.3f} {v['p90_deg']:8.3f}")
    print(f"\nn={len(d)}  ->  {OUT / 'sensitivity.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
