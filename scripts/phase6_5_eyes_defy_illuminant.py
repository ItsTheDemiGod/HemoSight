"""Phase 6.5 Task 4a - the Phase 2 Task 4 deliverable that was never stored.

The Phase 2 plan item read "apply the estimator to the conjunctiva datasets and inspect
stability within and across sites". What Phase 2 stored for Eyes-Defy was segmentation
QUALITY per image, not an illuminant estimate (audit 2026-09-12). This script applies
the Phase 2 estimator itself and stores the per-image estimates, so the tick is backed
by the artefact its wording implies.

Per image: Phase 2 U-Net segmentation -> sclera pixels -> vessel exclusion (the Phase 2
redness rule) -> robust inter-percentile RGB -> sclera-referenced illuminant under the
NEUTRAL prior (= the normalised sclera colour, the only prior evaluable without ground
truth), plus grey-world on the whole frame and on a 25% centre crop (the Phase 2.5
recommendation), all as unit RGB vectors.

Stability is reported as angular spread (degrees) about each site's mean estimate,
and the between-site angle between the two site means. One image per subject, so
WITHIN-SUBJECT stability is not measurable on this dataset - that is stated in the
output rather than approximated. Context that matters for reading the numbers:
Eyes-Defy was captured through a device that fixes distance and supplies its own white
LED while excluding ambient light (the dataset's own documentation), so the true
illuminant should be nearly constant; spread in the estimate is then mostly the
estimator's own per-subject error, which is what Phase 2 measured on MOBIUS.
"""
from __future__ import annotations

import json
import time

import cv2
import numpy as np
import pandas as pd
import torch

from hemosight.calibration.estimators import grey_world, robust_patch_rgb
from hemosight.calibration.metrics import angular_error
from hemosight.calibration.priors import NeutralPrior, estimate_illuminant
from hemosight.calibration.segmentation import (UNetResNet18, predict_mask,
                                                 vessel_exclusion_mask)
from hemosight.calibration.segmentation_data import SCLERA
from hemosight.io import paths

CKPT = paths.INTERIM / "phase2" / "segmentation_unet_r18.pt"
OUT_DIR = paths.INTERIM / "phase6_5"
OUT_CSV = OUT_DIR / "eyes_defy_illuminant.csv"
OUT_JSON = OUT_DIR / "eyes_defy_illuminant.json"
MIN_SCLERA_PX = 500


def centre_crop(img: np.ndarray, frac: float) -> np.ndarray:
    h, w = img.shape[:2]
    ch, cw = int(h * frac), int(w * frac)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    return img[y0:y0 + ch, x0:x0 + cw]


def spread(vectors: np.ndarray) -> dict:
    v = vectors[np.isfinite(vectors).all(axis=1)]
    if len(v) < 2:
        return {"n": int(len(v))}
    mean = v.mean(axis=0)
    mean = mean / np.linalg.norm(mean)
    ang = angular_error(v, np.tile(mean, (len(v), 1)))
    return {"n": int(len(v)), "mean_rgb": mean.tolist(), "mean_deg": float(np.mean(ang)),
            "median_deg": float(np.median(ang)), "p90_deg": float(np.percentile(ang, 90))}


def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = torch.load(CKPT, map_location=dev, weights_only=False)
    model = UNetResNet18().to(dev)
    model.load_state_dict(ck["model"])
    model.eval()
    size = ck["size"]
    prior = NeutralPrior()

    ed = pd.read_csv(paths.MANIFESTS / "eyes_defy.csv")
    rows = []
    for r in ed.itertuples():
        bgr = cv2.imread(r.file_path, cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        rgb = bgr[:, :, ::-1]
        # Work at a reduced resolution: the estimate is a robust mean over thousands
        # of pixels and does not need 12 MP; segmentation runs at `size` anyway.
        small = cv2.resize(rgb, (rgb.shape[1] // 4, rgb.shape[0] // 4), interpolation=cv2.INTER_AREA)
        lab, _ = predict_mask(model, small, size, dev)
        sclera = lab == SCLERA
        n_scl = int(sclera.sum())
        lin = (small.astype(np.float64) / 255.0) ** 2.2      # approximate linearisation
        row = {"image_id": r.image_id, "subject_id": r.subject_id, "site": r.site,
               "hb_g_dl": r.hb_g_dl, "n_sclera_px": n_scl,
               "sclera_area_fraction": n_scl / sclera.size}
        if n_scl >= MIN_SCLERA_PX:
            kept, removed = vessel_exclusion_mask(small, sclera)
            ref = robust_patch_rgb(lin[kept])
            est = estimate_illuminant(ref, prior)
            row.update({"vessel_removed_frac": removed,
                        "sclera_r": est[0], "sclera_g": est[1], "sclera_b": est[2]})
        gw = grey_world(lin)
        gw25 = grey_world(centre_crop(lin, 0.25))
        row.update({"gw_r": gw[0], "gw_g": gw[1], "gw_b": gw[2],
                    "gw25_r": gw25[0], "gw25_g": gw25[1], "gw25_b": gw25[2]})
        rows.append(row)
    d = pd.DataFrame(rows)
    d.to_csv(OUT_CSV, index=False)

    res = {"n": int(len(d)), "n_with_sclera_estimate": int(d["sclera_r"].notna().sum()),
           "min_sclera_px": MIN_SCLERA_PX, "prior": "neutral",
           "within_subject_stability": "NOT MEASURABLE: one image per subject",
           "capture_context": "fixed distance, own white LED, ambient light excluded "
                              "(dataset documentation) - the true illuminant is nearly "
                              "constant, so spread is mostly estimator error",
           "methods": {}}
    for name, cols in (("sclera_neutral", ["sclera_r", "sclera_g", "sclera_b"]),
                       ("grey_world_full", ["gw_r", "gw_g", "gw_b"]),
                       ("grey_world_25pct", ["gw25_r", "gw25_g", "gw25_b"])):
        v = d[cols].to_numpy(dtype=float)
        entry = {"all": spread(v), "by_site": {}}
        for s, g in d.groupby("site"):
            entry["by_site"][s] = spread(g[cols].to_numpy(dtype=float))
        sites = list(entry["by_site"])
        if len(sites) == 2 and all("mean_rgb" in entry["by_site"][s] for s in sites):
            a, b = (np.array(entry["by_site"][s]["mean_rgb"]) for s in sites)
            entry["between_site_angle_deg"] = float(angular_error(a[None], b[None])[0])
        res["methods"][name] = entry
    # Sclera vs grey-world agreement per image: are the two reading the same thing?
    both = d.dropna(subset=["sclera_r"])
    res["sclera_vs_gw25_angle_deg"] = {
        "mean": float(np.mean(angular_error(both[["sclera_r", "sclera_g", "sclera_b"]].to_numpy(float),
                                            both[["gw25_r", "gw25_g", "gw25_b"]].to_numpy(float)))),
        "n": int(len(both))}
    res["elapsed_s"] = time.time() - t0
    OUT_JSON.write_text(json.dumps(res, indent=2), encoding="utf-8")

    print(f"n={len(d)}; sclera estimate on {res['n_with_sclera_estimate']}")
    for name, e in res["methods"].items():
        bs = " | ".join(f"{s.split(':')[1]} spread {v.get('mean_deg', float('nan')):.2f} deg (n={v['n']})"
                        for s, v in e["by_site"].items())
        print(f"  {name:18s} all spread {e['all'].get('mean_deg', float('nan')):.2f} deg | {bs} | "
              f"between-site {e.get('between_site_angle_deg', float('nan')):.2f} deg")
    print(f"  sclera vs grey-world(25%) per image: {res['sclera_vs_gw25_angle_deg']['mean']:.2f} deg")
    print(f"wrote {OUT_CSV}, {OUT_JSON} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
