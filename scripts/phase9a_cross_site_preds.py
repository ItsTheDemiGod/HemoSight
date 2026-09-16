"""Phase 9A: regenerate the CROSS-SITE image-CNN per-subject predictions.

Phase 6.5 Task 2 computed cross-site MAE, bias and r, but wrote only those summary
numbers to `image_cnn.json` - **the per-subject cross-site predictions were never
saved**. Screening metrics cannot be recovered from a MAE, so they are regenerated
here with the recorded construction: `hemosight.baseline.image_cnn.cross_site`, seed
20260911, 3 seeds, 30 epochs, the cached crops from Phase 6.5.

This is a regeneration, not a new experiment. The regenerated MAE is compared against
the recorded figure and the difference is reported, so a drift would be visible rather
than assumed away.

Outputs `data/interim/phase9a/cross_site_predictions.csv`.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hemosight.baseline import image_cnn as icnn   # noqa: E402
from hemosight.io import paths                     # noqa: E402

CACHE = paths.INTERIM / "phase6_5" / "eyes_defy_crops.npz"
RECORDED = paths.INTERIM / "phase6_5" / "image_cnn.json"
OUT = paths.INTERIM / "phase9a"
SEEDS = (0, 1, 2)
DIRECTIONS = (("eyes_defy:Italy", "eyes_defy:India", "italy_to_india"),
              ("eyes_defy:India", "eyes_defy:Italy", "india_to_italy"))


def main() -> int:
    if not CACHE.exists():
        print(f"missing {CACHE}; run scripts/phase6_5_image_cnn.py first", file=sys.stderr)
        return 1
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    z = np.load(CACHE, allow_pickle=False)
    y, site, subject = z["y"], z["site"], z["subject"]
    male, age, X = z["male"], z["age"], z["X"]
    recorded = json.loads(RECORDED.read_text(encoding="utf-8"))["cross_site"]

    t0 = time.time()
    rows = []
    for train_site, test_site, tag in DIRECTIONS:
        per_seed = []
        preds_by_seed, train_by_seed = {}, {}
        test_idx = train_idx = None
        for s in SEEDS:
            r = icnn.cross_site(X, y, site, train_site, test_site, dev,
                                seed=icnn.SEED + s, epochs=icnn.EPOCHS)
            test_idx, train_idx = r["test_idx"], r["train_idx"]
            preds_by_seed[s] = r["preds"]
            train_by_seed[s] = r["train_preds"]
            mae = float(np.mean(np.abs(r["preds"] - y[test_idx])))
            per_seed.append(mae)
            print(f"  {tag} seed {s}: MAE {mae:.4f}  ({time.time() - t0:.0f}s elapsed)")
        mean_pred = np.mean([preds_by_seed[s] for s in SEEDS], axis=0)
        mae = float(np.mean(np.abs(mean_pred - y[test_idx])))
        rec = float(recorded[tag]["cnn"]["mae_g_dl"])
        print(f"  {tag}: regenerated seed-averaged MAE {mae:.4f} | recorded {rec:.4f} "
              f"| delta {mae - rec:+.4f}")
        mean_train = np.mean([train_by_seed[s] for s in SEEDS], axis=0)
        for j, i in enumerate(test_idx):
            rows.append({"direction": tag, "train_site": train_site, "split": "test",
                         "subject_id": subject[i], "site": site[i],
                         "y_true": float(y[i]), "y_pred": float(mean_pred[j]),
                         **{f"y_pred_seed__{s}": float(preds_by_seed[s][j]) for s in SEEDS},
                         "sex": "M" if male[i] == 1 else "F", "age": float(age[i])})
        # Train-site rows: the screening operating point is chosen on these and applied
        # to the test site, so no test label is ever used to pick a cut.
        for j, i in enumerate(train_idx):
            rows.append({"direction": tag, "train_site": train_site, "split": "train",
                         "subject_id": subject[i], "site": site[i],
                         "y_true": float(y[i]), "y_pred": float(mean_train[j]),
                         **{f"y_pred_seed__{s}": float(train_by_seed[s][j]) for s in SEEDS},
                         "sex": "M" if male[i] == 1 else "F", "age": float(age[i])})

    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "cross_site_predictions.csv", index=False)
    print(f"\nwrote {OUT / 'cross_site_predictions.csv'}  ({len(df)} rows, "
          f"{time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
