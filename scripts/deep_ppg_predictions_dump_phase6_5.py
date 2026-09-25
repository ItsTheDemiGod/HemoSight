"""Phase 6.5 Task 3 - write the Phase 4.5/5 deep model's per-subject predictions.

`scripts/permutation_hardening_phase5.py` computed ten per-seed prediction vectors and the seed-
averaged point estimate in memory and wrote only their summary statistics, so the
three Phase 5 checks in the audit harness (permutation, seed stability, subgroup
robustness) could never be driven end to end on the model they were built from.
This script regenerates those predictions with the SAME driver, seeds and folds
(`hemosight.ppg.cv.fit_predict`, `SEED + s`, `PERM_SEED`) and writes them in the
audit contract's format:

    subject_id, y_true, y_pred (seed-averaged),
    y_pred_seed__0..9            the ten seeds of the selected model,
    y_pred__<arch>_<cond>        the six candidates the selection chose from,
    sex, age                     for the demographic baseline.

Output: data/interim/phase6/known_truth/phase5_deep_model.csv (untracked: real Hb).
Cost: 16 full 10-fold CV runs, ~26 s each on the reference GPU.

The per-seed MAEs are printed beside the values in harden.json so the reproduction
is checked, not assumed; cuDNN autotune makes the match approximate (~0.01, the
measured seed SD).
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
import torch

from hemosight.io import paths
from hemosight.ppg.cv import CONFIGS, SEED, SELECTED, build_windows, fit_predict

OUT_DIR = paths.INTERIM / "phase6" / "known_truth"
OUT = OUT_DIR / "phase5_deep_model.csv"
N_SEEDS = 10


def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    harden = json.loads((paths.INTERIM / "phase5" / "harden.json").read_text(encoding="utf-8"))
    recorded = harden["seed_stability"]["maes"]

    feats = pd.read_csv(paths.INTERIM / "phase4" / "features.csv")
    feats = feats[np.isfinite(feats.hb_g_dl)]
    hb = {int(r.subject_id): float(r.hb_g_dl) for r in feats.itertuples()}
    demo = {int(r.subject_id): (r.sex, r.age) for r in feats.itertuples()}

    data = {}
    for tag, ch in (("four", [0, 1, 2, 3]), ("660", [0])):
        X, sid = build_windows(ch)
        subs = np.array(sorted(set(sid.tolist()) & set(hb)))
        keep = np.isin(sid, subs)
        data[tag] = (X[keep], sid[keep], subs, np.array([hb[s] for s in subs]))
    X0, sid0, subs0, y0 = data[SELECTED[1]]

    cols = {"subject_id": subs0, "y_true": y0}
    seed_preds = []
    print(f"=== {N_SEEDS} seeds of {SELECTED[0]} on {SELECTED[1]} (recorded MAEs beside) ===")
    for s in range(N_SEEDS):
        p = fit_predict(SELECTED[0], X0, sid0, subs0, y0, dev, SEED + s)
        mae = float(np.mean(np.abs(p - y0)))
        seed_preds.append(p)
        cols[f"y_pred_seed__{s}"] = p
        print(f"  seed {s}: MAE {mae:.4f}  (harden.json {recorded[s]:.4f}, "
              f"diff {mae - recorded[s]:+.4f})  {time.time()-t0:.0f}s")
    mean_pred = np.mean(np.stack(seed_preds), 0)
    cols["y_pred"] = mean_pred
    real = float(np.mean(np.abs(mean_pred - y0)))
    print(f"  seed-averaged MAE {real:.4f}  (harden.json {harden['real_mae_seed_averaged']:.4f})")

    print("=== the six candidates of the selection step ===")
    for arch, cond in CONFIGS:
        Xc, sidc, subc, yc = data[cond]
        assert np.array_equal(subc, subs0), "candidate subject order differs"
        p = fit_predict(arch, Xc, sidc, subc, yc, dev, SEED)
        cols[f"y_pred__{arch}_{cond}"] = p
        print(f"  {arch}_{cond}: MAE {np.mean(np.abs(p - yc)):.4f}  {time.time()-t0:.0f}s")

    cols["sex"] = [demo[int(s)][0] for s in subs0]
    cols["age"] = [demo[int(s)][1] for s in subs0]
    df = pd.DataFrame(cols)
    df["sex"] = np.where(df["sex"].astype(float) > 0.5, "M", "F") if df["sex"].dtype != object else df["sex"]
    df.to_csv(OUT, index=False)
    summary = {"n_subjects": int(len(subs0)), "seed_maes": [float(np.mean(np.abs(p - y0))) for p in seed_preds],
               "seed_maes_recorded": recorded, "real_mae_seed_averaged": real,
               "real_mae_recorded": harden["real_mae_seed_averaged"],
               "max_abs_seed_diff": float(max(abs(float(np.mean(np.abs(p - y0))) - r)
                                              for p, r in zip(seed_preds, recorded))),
               "elapsed_s": time.time() - t0}
    (OUT_DIR / "phase5_deep_model_regeneration.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(df.columns)} columns) in {time.time()-t0:.0f}s; "
          f"max |seed MAE - recorded| = {summary['max_abs_seed_diff']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
