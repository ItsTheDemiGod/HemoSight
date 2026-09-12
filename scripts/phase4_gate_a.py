"""Phase 4, TASK 0 / GATE A: does the AC/DC normalisation actually cancel?

Run and report before anything else in the phase.

The claim is that AC/DC cancels source intensity, sensor gain, static tissue and skin
tone, because all appear in both AC and DC. Phase 3.5 is the cautionary precedent: a
spatial ratio cancelled the illuminant EXACTLY on synthetic data and still failed on
real captures by a factor of 139. So cancellation is tested on the real recordings, and
the synthetic check is treated as an implementation test only.

METHOD. For each feature, split its between-subject variance into the part explained by
haemoglobin and the part not. The nuisance term is the part NOT explained by Hb. If the
normalisation works, normalised features should carry markedly less non-Hb variance,
relative to their own scale, than the raw DC they were built from.

Thresholds declared in CLAUDE.md before running:
    >= 50% nuisance reduction AND signal > non-Hb variation  -> PASS
    reduction present but signal ~ noise                     -> MARGINAL, stop
    no meaningful reduction                                  -> FAIL, stop

    .\\.venv\\Scripts\\python.exe scripts\\phase4_gate_a.py
"""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from hemosight.io import paths
from hemosight.ppg.features import WAVELENGTHS, extract_subject, load_subject

OUT = paths.INTERIM / "phase4"


def build_feature_table() -> pd.DataFrame:
    cache = OUT / "features.csv"
    if cache.exists():
        return pd.read_csv(cache)
    OUT.mkdir(parents=True, exist_ok=True)
    info = pd.read_excel(paths.HB_PPG_SHEET).rename(
        columns={"Hemoglobin (g/L)": "hb_g_l", "Age (year)": "age",
                 "Height (cm)": "height", "Weight (kg)": "weight",
                 "Signal length (second)": "siglen"})
    rows, t0 = [], time.time()
    for r in info.to_dict("records"):
        sid = int(r["ID"])
        if len(rows) % 50 == 0:
            print(f"  {len(rows)}/{len(info)}  {time.time()-t0:.0f}s", end="\r", flush=True)
        sig = load_subject(paths.HB_PPG / "data_csv" / f"{sid}.csv")
        if sig is None:
            continue
        f = extract_subject(sig)
        if f is None:
            continue
        hb = pd.to_numeric(r["hb_g_l"], errors="coerce")
        f.update({
            "subject_id": sid,
            "hb_g_dl": float(hb) / 10.0 if pd.notna(hb) else np.nan,  # g/L -> g/dL
            "age": pd.to_numeric(r["age"], errors="coerce"),
            "sex": 1.0 if str(r["Gender"]).strip().lower() == "male" else 0.0,
            "height": pd.to_numeric(r["height"], errors="coerce"),
            "weight": pd.to_numeric(r["weight"], errors="coerce"),
            "siglen": pd.to_numeric(r["siglen"], errors="coerce"),
            "n_samples": len(sig),
        })
        rows.append(f)
    print()
    d = pd.DataFrame(rows)
    d.to_csv(cache, index=False)
    return d


def variance_split(values: np.ndarray, hb: np.ndarray) -> dict:
    """Split between-subject variance into Hb-explained and nuisance parts.

    Uses a linear fit in Hb. Reported as a COEFFICIENT OF VARIATION so features on
    wildly different scales (raw DC in ADC counts, AC/DC ~1e-2) are comparable.
    """
    m = np.isfinite(values) & np.isfinite(hb)
    v, h = values[m], hb[m]
    if len(v) < 20 or np.std(v) == 0:
        return {}
    slope, intercept = np.polyfit(h, v, 1)
    pred = slope * h + intercept
    resid = v - pred
    total_var = float(np.var(v))
    nuis_var = float(np.var(resid))
    scale = float(np.mean(np.abs(v)))
    return {
        "n": int(len(v)),
        "mean": float(np.mean(v)),
        "total_cv": float(np.sqrt(total_var) / max(scale, 1e-12)),
        "nuisance_cv": float(np.sqrt(nuis_var) / max(scale, 1e-12)),
        "r2_hb": float(1.0 - nuis_var / max(total_var, 1e-12)),
        "slope_per_g_dl": float(slope),
        "signal_per_g_dl_rel": float(abs(slope) / max(scale, 1e-12)),
        "residual_sd": float(np.sqrt(nuis_var)),
        # The project's standard framing: how many g/dL of Hb is the noise worth?
        "equivalent_hb_noise_g_dl": float(np.sqrt(nuis_var) / max(abs(slope), 1e-12)),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("=== extracting PPG features ===")
    d = build_feature_table()
    d = d[np.isfinite(d.hb_g_dl)]
    print(f"  {len(d)} subjects with features and Hb; "
          f"Hb {d.hb_g_dl.min():.1f}-{d.hb_g_dl.max():.1f} g/dL")

    hb = d.hb_g_dl.to_numpy()
    groups = {
        "RAW DC (carries every nuisance)": [f"dc_{w}" for w in WAVELENGTHS],
        "RAW AC": [f"ac_{w}" for w in WAVELENGTHS],
        "NORMALISED AC/DC": [f"ac_dc_{w}" for w in WAVELENGTHS],
        "RATIO-OF-RATIOS R": [c for c in d.columns if c.startswith("R_")],
    }

    results: dict = {"n_subjects": int(len(d)), "groups": {}}
    print("\n=== GATE A: variance split, real data ===")
    print(f"  {'feature':22s} {'total CV':>9s} {'nuisance CV':>12s} {'R2(Hb)':>8s} "
          f"{'equiv Hb noise':>15s}")
    for gname, cols in groups.items():
        print(f"\n  -- {gname}")
        per = {}
        for c in cols:
            if c not in d.columns:
                continue
            s = variance_split(d[c].to_numpy(dtype=float), hb)
            if not s:
                continue
            per[c] = s
            print(f"  {c:22s} {s['total_cv']:9.4f} {s['nuisance_cv']:12.4f} "
                  f"{s['r2_hb']:8.4f} {s['equivalent_hb_noise_g_dl']:14.2f} g/dL")
        if per:
            results["groups"][gname] = {
                "per_feature": per,
                "median_nuisance_cv": float(np.median([v["nuisance_cv"] for v in per.values()])),
                "median_r2_hb": float(np.median([v["r2_hb"] for v in per.values()])),
                "best_equivalent_hb_noise": float(min(
                    v["equivalent_hb_noise_g_dl"] for v in per.values())),
            }

    # ---- the cancellation test -------------------------------------------
    raw_dc = results["groups"]["RAW DC (carries every nuisance)"]["median_nuisance_cv"]
    norm = results["groups"]["NORMALISED AC/DC"]["median_nuisance_cv"]
    ratio = results["groups"].get("RATIO-OF-RATIOS R", {}).get("median_nuisance_cv", np.nan)
    red_norm = 1.0 - norm / raw_dc
    red_ratio = 1.0 - ratio / raw_dc if np.isfinite(ratio) else np.nan

    print("\n=== nuisance variance reduction (the cancellation claim) ===")
    print(f"  raw DC       median nuisance CV = {raw_dc:.4f}")
    print(f"  AC/DC        median nuisance CV = {norm:.4f}   reduction = {red_norm*100:+6.1f}%")
    print(f"  R (ratio)    median nuisance CV = {ratio:.4f}   reduction = {red_ratio*100:+6.1f}%")

    best = min(g["best_equivalent_hb_noise"] for g in results["groups"].values())
    best_feat = min(
        ((c, v["equivalent_hb_noise_g_dl"])
         for g in results["groups"].values() for c, v in g["per_feature"].items()),
        key=lambda kv: kv[1])
    hb_sd = float(np.std(hb))
    print("\n=== signal vs non-Hb variation ===")
    print(f"  population Hb SD                : {hb_sd:.3f} g/dL")
    print(f"  best single-feature equiv noise : {best:.2f} g/dL  ({best_feat[0]})")
    print(f"  -> signal exceeds noise? {'YES' if best < hb_sd else 'NO'} "
          f"(a feature is only informative if its equivalent noise is below the "
          f"population spread it must resolve)")

    passed_reduction = red_norm >= 0.50 or (np.isfinite(red_ratio) and red_ratio >= 0.50)
    signal_ok = best < hb_sd
    band = ("PASS" if (passed_reduction and signal_ok)
            else "MARGINAL" if passed_reduction or signal_ok else "FAIL")
    results.update({
        "raw_dc_nuisance_cv": raw_dc, "normalised_nuisance_cv": norm,
        "ratio_nuisance_cv": ratio,
        "reduction_acdc": red_norm, "reduction_ratio": red_ratio,
        "population_hb_sd": hb_sd, "best_equivalent_hb_noise_g_dl": best,
        "best_feature": best_feat[0],
        "passed_reduction_threshold": bool(passed_reduction),
        "signal_exceeds_noise": bool(signal_ok), "gate_a": band,
    })

    print("\n" + "=" * 68)
    print(f"GATE A: **{band}**")
    print(f"  nuisance reduction >= 50%: {passed_reduction}  "
          f"(AC/DC {red_norm*100:.1f}%, R {red_ratio*100:.1f}%)")
    print(f"  signal exceeds non-Hb variation: {signal_ok}")
    print("=" * 68)

    (OUT / "gate_a.json").write_text(json.dumps(results, indent=2, default=float),
                                     encoding="utf-8")
    print(f"\nresults -> {OUT / 'gate_a.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
