"""Phase 5, TASK 1: subject the project's only positive claim to the project's own standard.

The claim: a spectrogram CNN on raw 660 nm PPG is distinguishable from chance
(Phase 4.5, z = -4.72, n=30 permutations). Three weaknesses, all addressed here:

1. SELECTION. The model was chosen best-of-six and THEN permutation-tested, so the null
   did not include the selection step. Fixed by running the full best-of-six selection
   INSIDE each permutation and taking the min MAE - the null then reflects the actual
   procedure, which is the correct construction rather than a post-hoc correction.
2. EMPIRICAL FLOOR. n=30 puts the smallest achievable empirical p near 0.032, so the
   reported z was parametric and assumed a normal null. Fixed by >=200 permutations of
   the selected model, reporting the EMPIRICAL p alongside the parametric z.
3. STABILITY. A claim resting on one training run is not a claim. The real MAE is
   re-estimated under multiple seeds; if seed spread is comparable to the real-vs-null
   gap, the finding does not survive.

Plus: a subject-level check that the effect is not carried by a small subset.

Results are written incrementally so a partial run is still reportable.

The CV driver lives in `hemosight.ppg.cv` so that this script and the extended
permutation runner cannot drift apart. To push the selection-aware null past its n=60
empirical floor use `scripts/permutation_extended_run_phase5.py`, which checkpoints and resumes;
test B below is the n=60 version already on record.

    .\\.venv\\Scripts\\python.exe scripts\\permutation_hardening_phase5.py [--perms 200] [--sel-perms 60]
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd
import torch

from hemosight.io import paths
from hemosight.ppg.cv import (CONFIGS, EPOCHS, N_SPLITS, SEED, SELECTED, build_windows,
                              fit_predict)

OUT = paths.INTERIM / "phase5"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=200)
    ap.add_argument("--sel-perms", type=int, default=60)
    ap.add_argument("--seeds", type=int, default=10)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    feats = pd.read_csv(paths.INTERIM / "phase4" / "features.csv")
    feats = feats[np.isfinite(feats.hb_g_dl)]
    hb = {int(r.subject_id): float(r.hb_g_dl) for r in feats.itertuples()}

    data = {}
    for tag, ch in (("four", [0, 1, 2, 3]), ("660", [0])):
        X, sid = build_windows(ch)
        subs = np.array(sorted(set(sid.tolist()) & set(hb)))
        keep = np.isin(sid, subs)
        data[tag] = (X[keep], sid[keep], subs, np.array([hb[s] for s in subs]))
    X0, sid0, subs0, y0 = data[SELECTED[1]]
    res: dict = {"selected_model": f"{SELECTED[0]}_{SELECTED[1]}",
                 "n_subjects": int(len(subs0)), "epochs": EPOCHS, "folds": N_SPLITS}

    def save():
        (OUT / "harden.json").write_text(json.dumps(res, indent=2, default=float),
                                         encoding="utf-8")

    # ---------------------------------------------- 1. seed stability --------
    print(f"=== seed stability: {args.seeds} seeds of {SELECTED[0]} on {SELECTED[1]} ===")
    maes, all_preds = [], []
    t0 = time.time()
    for s in range(args.seeds):
        p = fit_predict(SELECTED[0], X0, sid0, subs0, y0, dev, SEED + s)
        maes.append(float(np.mean(np.abs(p - y0))))
        all_preds.append(p)
        print(f"  seed {s}: MAE={maes[-1]:.4f}  ({time.time()-t0:.0f}s)")
    maes = np.array(maes)
    res["seed_stability"] = {
        "n_seeds": args.seeds, "maes": maes.tolist(), "mean": float(maes.mean()),
        "sd": float(maes.std()), "min": float(maes.min()), "max": float(maes.max()),
        "range": float(maes.max() - maes.min()),
    }
    print(f"  mean={maes.mean():.4f} SD={maes.std():.4f} "
          f"range={maes.min():.4f}-{maes.max():.4f}")
    save()

    # Seed-averaged predictions are the honest point estimate.
    mean_pred = np.mean(np.stack(all_preds), axis=0)
    real_mae = float(np.mean(np.abs(mean_pred - y0)))
    res["real_mae_seed_averaged"] = real_mae
    res["real_mae_single_seed"] = float(maes[0])
    print(f"  seed-averaged prediction MAE = {real_mae:.4f}")

    # ---------------------------------------------- 2. subject robustness ----
    err = np.abs(mean_pred - y0)
    order = np.argsort(err)
    n_dec = max(1, len(err) // 10)
    keep = order[n_dec:]                      # drop the BEST-performing decile
    res["subject_robustness"] = {
        "mae_all": float(err.mean()),
        "mae_drop_best_decile": float(err[keep].mean()),
        "n_dropped": int(n_dec),
        "mae_drop_worst_decile": float(err[order[:-n_dec]].mean()),
        "per_subject_error_sd": float(err.std()),
    }
    print("\n=== subject robustness ===")
    print(f"  MAE all subjects              : {err.mean():.4f}")
    print(f"  MAE after dropping BEST decile: {err[keep].mean():.4f}")
    save()

    # ---------------------------------------------- 3. permutations ----------
    rng = np.random.default_rng(SEED)
    print(f"\n=== permutation test A: selected model alone, n={args.perms} ===")
    nullA = []
    t0 = time.time()
    for i in range(args.perms):
        yp = rng.permutation(y0)
        p = fit_predict(SELECTED[0], X0, sid0, subs0, yp, dev, SEED + 1000 + i)
        nullA.append(float(np.mean(np.abs(p - yp))))
        if (i + 1) % 10 == 0:
            a = np.array(nullA)
            print(f"  {i+1}/{args.perms}  null mean={a.mean():.4f} "
                  f"p_emp={(a <= real_mae).mean():.4f}  ({time.time()-t0:.0f}s)",
                  flush=True)
            res["permutation_selected_only"] = {
                "n": len(nullA), "null_mean": float(a.mean()), "null_sd": float(a.std()),
                "real_mae": real_mae,
                "p_empirical": float((np.sum(a <= real_mae) + 1) / (len(a) + 1)),
                "z_parametric": float((real_mae - a.mean()) / max(a.std(), 1e-12)),
            }
            save()

    # ------------------------------- 4. selection-aware permutations ---------
    print(f"\n=== permutation test B: FULL best-of-six inside each permutation, "
          f"n={args.sel_perms} ===")
    print("  (this is the correct null: it includes the selection step)")
    nullB = []
    t0 = time.time()
    for i in range(args.sel_perms):
        yp_by_sub = {}
        perm_idx = rng.permutation(len(subs0))
        best = np.inf
        for arch, tag in CONFIGS:
            Xc, sidc, subc, yc = data[tag]
            # Same shuffled assignment across configs, keyed by subject id.
            if not yp_by_sub:
                yp_by_sub = {s: y0[perm_idx[j]] for j, s in enumerate(subs0)}
            ycp = np.array([yp_by_sub.get(s, np.nan) for s in subc])
            ok = np.isfinite(ycp)
            p = fit_predict(arch, Xc[np.isin(sidc, subc[ok])],
                            sidc[np.isin(sidc, subc[ok])], subc[ok], ycp[ok],
                            dev, SEED + 5000 + i)
            best = min(best, float(np.mean(np.abs(p - ycp[ok]))))
        nullB.append(best)
        if (i + 1) % 5 == 0:
            b = np.array(nullB)
            print(f"  {i+1}/{args.sel_perms}  null(min-of-6) mean={b.mean():.4f} "
                  f"p_emp={(np.sum(b <= real_mae)+1)/(len(b)+1):.4f}  "
                  f"({time.time()-t0:.0f}s)", flush=True)
            res["permutation_selection_aware"] = {
                "n": len(nullB), "null_mean": float(b.mean()), "null_sd": float(b.std()),
                "real_mae": real_mae,
                "p_empirical": float((np.sum(b <= real_mae) + 1) / (len(b) + 1)),
                "z_parametric": float((real_mae - b.mean()) / max(b.std(), 1e-12)),
            }
            save()

    save()
    print(f"\nresults -> {OUT / 'harden.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
