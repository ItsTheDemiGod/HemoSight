"""Phase 2, Task 2: N1a - illuminant estimation accuracy across sensors (nus8).

Runs per-camera 3-fold CV and leave-one-camera-out, using the splits frozen in
Phase 1. Reference-patch estimation is evaluated under three reflectance priors so
the value of knowing the reference's true reflectance is measured, not assumed.

    .\\.venv\\Scripts\\python.exe scripts\\illuminant_estimation_nus8_phase2.py [--quick]
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd

from hemosight.calibration.nus8_experiment import (
    build_reference_table,
    evaluate_classical,
    evaluate_reference_method,
)
from hemosight.io import paths

OUT = paths.INTERIM / "phase2"


def main() -> int:
    quick = "--quick" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    man = pd.read_csv(paths.MANIFESTS / "nus8.csv")
    cv = pd.read_csv(paths.SPLITS / "nus8_cv3.csv")
    man = man.merge(cv[["image_id", "fold"]], on="image_id", how="left")

    print(f"nus8: {len(man)} images, {man.camera.nunique()} cameras")
    ref = build_reference_table(man)
    ref = ref.merge(man[["image_id", "fold"]], on="image_id", how="left")
    bad = ref[["ref_r", "ref_g", "ref_b"]].isna().any(axis=1).sum()
    print(f"reference patches parsed: {len(ref) - bad}/{len(ref)}")

    results: dict = {"protocols": {}}

    # ---------------------------------------------------------- per-camera 3-fold
    print("\n=== per-camera 3-fold CV (reference-patch estimation) ===")
    percam: dict = {}
    for cam, g in ref.groupby("camera"):
        gi = g.reset_index(drop=True)
        agg: dict[str, list] = {}
        for f in sorted(gi.fold.dropna().unique()):
            tr = np.where(gi.fold != f)[0]
            te = np.where(gi.fold == f)[0]
            for k, v in evaluate_reference_method(gi, tr, te).items():
                agg.setdefault(k, []).append(v)
        percam[cam] = {
            k: {m: float(np.mean([x[m] for x in v]))
                for m in ("mean", "median", "trimean", "best25", "worst25",
                          "deltaE2000_mean")}
            for k, v in agg.items()
        }
        line = " | ".join(
            f"{k.split('/')[-1]}: {percam[cam][k]['mean']:.3f}deg" for k in sorted(percam[cam]))
        print(f"  {cam:24s} {line}")
    results["protocols"]["per_camera_3fold"] = percam

    # Pooled across cameras
    pooled: dict[str, dict] = {}
    for method in sorted({k for c in percam.values() for k in c}):
        vals = [c[method] for c in percam.values() if method in c]
        pooled[method] = {m: float(np.mean([v[m] for v in vals])) for m in vals[0]}
    results["protocols"]["per_camera_3fold_pooled"] = pooled
    print("\n  pooled over cameras:")
    for k, v in sorted(pooled.items(), key=lambda kv: kv[1]["mean"]):
        print(f"    {k:42s} mean={v['mean']:6.3f}  median={v['median']:6.3f}  "
              f"worst25={v['worst25']:6.3f}  dE={v['deltaE2000_mean']:6.3f}")

    # --------------------------------------------------- leave-one-camera-out
    print("\n=== leave-one-camera-out (reference-patch estimation) ===")
    loco: dict = {}
    for cam in sorted(ref.camera.unique()):
        r = ref.reset_index(drop=True)
        tr = np.where(r.camera != cam)[0]
        te = np.where(r.camera == cam)[0]
        loco[cam] = evaluate_reference_method(r, tr, te)
        line = " | ".join(f"{k.split('/')[-1]}: {v['mean']:.3f}deg"
                          for k, v in sorted(loco[cam].items()))
        print(f"  held out {cam:24s} {line}")
    results["protocols"]["leave_one_camera_out"] = loco

    loco_pooled: dict[str, dict] = {}
    for method in sorted({k for c in loco.values() for k in c}):
        vals = [c[method] for c in loco.values() if method in c]
        loco_pooled[method] = {
            m: float(np.mean([v[m] for v in vals]))
            for m in ("mean", "median", "trimean", "best25", "worst25", "deltaE2000_mean")
        }
    results["protocols"]["leave_one_camera_out_pooled"] = loco_pooled

    # ------------------------------------------------------------- classical
    print("\n=== classical baselines (checker masked out) ===")
    t0 = time.time()
    classical: dict = {}
    for cam, g in man.groupby("camera"):
        ids = g.image_id.tolist()
        if quick:
            ids = ids[:25]
        classical[cam] = evaluate_classical(man, ids)
        line = " | ".join(f"{k.split('/')[-1]}={v['mean']:.2f}"
                          for k, v in sorted(classical[cam].items()))
        print(f"  {cam:24s} {line}  ({time.time()-t0:.0f}s)")
    results["protocols"]["classical_per_camera"] = classical

    cls_pooled: dict[str, dict] = {}
    for method in sorted({k for c in classical.values() for k in c}):
        vals = [c[method] for c in classical.values() if method in c]
        cls_pooled[method] = {
            m: float(np.mean([v[m] for v in vals]))
            for m in ("mean", "median", "trimean", "best25", "worst25", "deltaE2000_mean")
        }
    results["protocols"]["classical_pooled"] = cls_pooled

    # ------------------------------------------------------------- verdict
    print("\n=== N1a SUMMARY (pooled, per-camera 3-fold for reference methods) ===")
    everything = {**pooled, **cls_pooled}
    for k, v in sorted(everything.items(), key=lambda kv: kv[1]["mean"]):
        print(f"  {k:42s} mean={v['mean']:7.3f}  median={v['median']:7.3f}  "
              f"worst25={v['worst25']:7.3f}")
    results["pooled_all_methods"] = everything

    neutral = pooled.get("reference_patch/neutral", {}).get("mean", float("nan"))
    fixed = pooled.get("reference_patch/fixed_population", {}).get("mean", float("nan"))
    oracle = pooled.get("reference_patch/oracle_per_image", {}).get("mean", float("nan"))
    best_cls = min((v["mean"] for v in cls_pooled.values()), default=float("nan"))
    results["ablation"] = {
        "neutral_prior_mean_deg": neutral,
        "fixed_population_prior_mean_deg": fixed,
        "oracle_per_image_prior_mean_deg": oracle,
        "prior_gain_deg": neutral - fixed,
        "prior_gain_pct": 100 * (neutral - fixed) / neutral if neutral else None,
        "fraction_of_oracle_gain_captured":
            (neutral - fixed) / (neutral - oracle) if (neutral - oracle) else None,
        "best_classical_mean_deg": best_cls,
    }
    print("\n  PRIOR ABLATION (the number that predicts the sclera requirement):")
    print(f"    assumed neutral        : {neutral:.3f} deg")
    print(f"    fixed population prior : {fixed:.3f} deg   (gain {neutral-fixed:+.3f})")
    print(f"    oracle per-image prior : {oracle:.3f} deg   (ceiling)")
    print(f"    best classical baseline: {best_cls:.3f} deg")

    (OUT / "n1a_nus8_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nresults -> {OUT / 'n1a_nus8_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
