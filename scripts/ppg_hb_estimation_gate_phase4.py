"""Phase 4, TASK 1 / GATE B + TASK 3: can Hb be predicted, and does PPG beat demographics?

Three conditions, each judged separately against the same bands as the Phase 3 gate:
  1. all four wavelengths      - the physics ceiling for this dataset
  2. 660 nm only               - the single channel a phone shares with it
  3. simulated phone-RGB       - what is actually deployable

Condition 3 is not a guess. The Jiang camspec database covers 400-720 nm, and the mean
sensitivity of 28 cameras at each PPG wavelength is: 660 nm -> R 0.179, G 0.016,
B 0.007; 730/850/940 nm -> outside the characterised range entirely, and behind the
IR-cut filter every phone carries. So a phone sees ONE of the four wavelengths, in ONE
channel. Condition 3 uses the 660 nm signal weighted by real R/G/B responses, with the
other three wavelengths set to zero because that is what the hardware does.

TASK 3 baselines on identical folds, because a demographic baseline frequently matches
an apparently sophisticated model on small clinical data:
  - population mean
  - demographics only (age, sex, height, weight)
  - PPG only
  - PPG + demographics

    .\\.venv\\Scripts\\python.exe scripts\\ppg_hb_estimation_gate_phase4.py
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from hemosight.io import paths
from hemosight.ppg.features import WAVELENGTHS
from hemosight.simulation.optical_data import camspec_database

OUT = paths.INTERIM / "phase4"
SEED = 20260911
N_SPLITS = 10
WHO = {"moderate/mild": 10.0, "mild/normal(F)": 12.0, "mild/normal(M)": 13.0}


def phone_channel_weights() -> dict:
    """Mean R/G/B sensitivity at each PPG wavelength, from real camera data."""
    db = camspec_database()
    wl = db["wavelength_nm"]
    w = {}
    for lam in WAVELENGTHS:
        if lam <= wl[-1]:
            v = np.array([[np.interp(lam, wl, db["cameras"][c][:, i]) for i in range(3)]
                          for c in db["cameras"]]).mean(axis=0)
        else:
            v = np.zeros(3)      # beyond the characterised range AND the IR-cut filter
        w[lam] = v
    return w


def build_conditions(d: pd.DataFrame) -> dict:
    """Feature matrices for each of the three wavelength conditions."""
    per_wl = ["ac_dc", "perfusion_index", "dc", "ac", "ac_rms", "beat_cv",
              "spectral_purity", "snr_db"]
    four = [f"{p}_{w}" for w in WAVELENGTHS for p in per_wl]
    four += [c for c in d.columns if c.startswith("R_")]
    four += ["hr_consistency", "mean_purity", "mean_beat_cv"]

    only660 = [f"{p}_660" for p in per_wl] + ["hr_consistency"]

    # Phone-RGB: the 660 nm signal seen through real R/G/B responses. The other three
    # wavelengths contribute nothing because the hardware cannot sense them.
    wts = phone_channel_weights()
    phone = d[["subject_id"]].copy()
    for ci, cname in enumerate("RGB"):
        for p in ("ac_dc", "perfusion_index", "ac", "dc"):
            acc = np.zeros(len(d), dtype=float)
            for lam in WAVELENGTHS:
                col = f"{p}_{lam}"
                if col in d.columns and wts[lam][ci] > 0:
                    acc = acc + wts[lam][ci] * pd.to_numeric(d[col], errors="coerce").to_numpy()
            phone[f"phone_{cname}_{p}"] = acc
    # A phone's own AC/DC per channel, plus the only usable cross-channel ratio.
    phone["phone_R_over_G_acdc"] = phone["phone_R_ac_dc"] / np.clip(
        phone["phone_G_ac_dc"].to_numpy(), 1e-12, None)
    phone_cols = [c for c in phone.columns if c.startswith("phone_")]
    for c in phone_cols:
        d[c] = phone[c].to_numpy()

    return {"1_four_wavelength": [c for c in four if c in d.columns],
            "2_660nm_only": [c for c in only660 if c in d.columns],
            "3_phone_rgb_simulated": phone_cols}


def evaluate(X: np.ndarray, y: np.ndarray, name: str) -> dict:
    """Grouped K-fold. Each subject contributes exactly one record, so a subject-level
    K-fold IS leave-subject-out grouping - no within-subject split is possible."""
    kf = KFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    preds = np.full(len(y), np.nan)
    for tr, te in kf.split(X):
        model = make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(),
            RidgeCV(alphas=np.logspace(-3, 3, 25)))
        model.fit(X[tr], y[tr])
        preds[te] = model.predict(X[te])
    err = preds - y
    mae = float(np.mean(np.abs(err)))
    band = "VIABLE" if mae < 1.0 else "MARGINAL" if mae <= 2.0 else "NOT VIABLE"
    ss = 1.0 - np.sum(err ** 2) / np.sum((y - y.mean()) ** 2)
    return {"name": name, "n_features": X.shape[1], "mae_g_dl": mae,
            "rmse_g_dl": float(np.sqrt(np.mean(err ** 2))),
            "bias_g_dl": float(np.mean(err)), "r2": float(ss),
            "pearson_r": float(np.corrcoef(preds, y)[0, 1]),
            "band": band, "preds": preds.tolist()}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(OUT / "features.csv")
    d = d[np.isfinite(d.hb_g_dl)].reset_index(drop=True)
    y = d.hb_g_dl.to_numpy()
    print(f"{len(d)} subjects, Hb {y.min():.1f}-{y.max():.1f} g/dL, SD {y.std():.3f}")

    print("\n=== what a phone can sense at each PPG wavelength (camspec, 28 cameras) ===")
    for lam, v in phone_channel_weights().items():
        tag = "" if v.sum() > 0 else "   <- beyond 720 nm and behind the IR-cut filter"
        print(f"   {lam:4d} nm: R={v[0]:.4f} G={v[1]:.4f} B={v[2]:.4f}{tag}")

    conds = build_conditions(d)
    results: dict = {"n_subjects": int(len(d)), "hb_sd": float(y.std()),
                     "conditions": {}, "baselines": {}}

    # ---------------------------------------------------------- TASK 3 baselines
    print("\n=== TASK 3: honest baselines, identical folds ===")
    mean_mae = float(np.mean(np.abs(y - y.mean())))
    results["baselines"]["population_mean"] = {
        "mae_g_dl": mean_mae, "r2": 0.0,
        "band": "VIABLE" if mean_mae < 1.0 else "MARGINAL" if mean_mae <= 2.0 else "NOT VIABLE"}
    print(f"  {'population mean':28s} MAE={mean_mae:.3f} g/dL")

    demo_cols = ["age", "sex", "height", "weight"]
    demo = evaluate(d[demo_cols].to_numpy(dtype=float), y, "demographics")
    results["baselines"]["demographics"] = {k: v for k, v in demo.items() if k != "preds"}
    print(f"  {'demographics (age/sex/h/w)':28s} MAE={demo['mae_g_dl']:.3f} g/dL  "
          f"r={demo['pearson_r']:.3f}  R2={demo['r2']:.3f}")

    sex_only = evaluate(d[["sex"]].to_numpy(dtype=float), y, "sex_only")
    results["baselines"]["sex_only"] = {k: v for k, v in sex_only.items() if k != "preds"}
    print(f"  {'sex alone':28s} MAE={sex_only['mae_g_dl']:.3f} g/dL  "
          f"r={sex_only['pearson_r']:.3f}")

    # ------------------------------------------------------------- GATE B
    print("\n=== GATE B: PPG-only, by wavelength condition ===")
    for cname, cols in conds.items():
        if not cols:
            continue
        X = d[cols].to_numpy(dtype=float)
        r = evaluate(X, y, cname)
        results["conditions"][cname] = {k: v for k, v in r.items() if k != "preds"}
        print(f"  {cname:26s} n_feat={r['n_features']:3d}  MAE={r['mae_g_dl']:.3f}  "
              f"r={r['pearson_r']:+.3f}  R2={r['r2']:+.3f}  -> {r['band']}")

        # PPG + demographics, to see whether PPG adds anything to demographics.
        Xd = np.column_stack([X, d[demo_cols].to_numpy(dtype=float)])
        rd = evaluate(Xd, y, cname + "_plus_demographics")
        results["conditions"][cname + "_plus_demographics"] = {
            k: v for k, v in rd.items() if k != "preds"}
        print(f"  {cname + ' + demographics':26s} n_feat={rd['n_features']:3d}  "
              f"MAE={rd['mae_g_dl']:.3f}  r={rd['pearson_r']:+.3f}  -> {rd['band']}")

    # Non-linear check: does a tree model find structure Ridge misses?
    print("\n=== non-linear check (gradient boosting, 4-wavelength) ===")
    X = d[conds["1_four_wavelength"]].to_numpy(dtype=float)
    kf = KFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    preds = np.full(len(y), np.nan)
    for tr, te in kf.split(X):
        m = make_pipeline(SimpleImputer(strategy="median"),
                          GradientBoostingRegressor(random_state=SEED))
        m.fit(X[tr], y[tr])
        preds[te] = m.predict(X[te])
    gb_mae = float(np.mean(np.abs(preds - y)))
    results["gbr_four_wavelength"] = {
        "mae_g_dl": gb_mae, "pearson_r": float(np.corrcoef(preds, y)[0, 1]),
        "band": "VIABLE" if gb_mae < 1.0 else "MARGINAL" if gb_mae <= 2.0 else "NOT VIABLE"}
    print(f"  gradient boosting MAE={gb_mae:.3f} g/dL  "
          f"r={results['gbr_four_wavelength']['pearson_r']:+.3f}")

    # ---------------------------------------------------------- verdict
    four = results["conditions"]["1_four_wavelength"]
    phone = results["conditions"]["3_phone_rgb_simulated"]
    results["verdict"] = {
        "four_wavelength": four["band"],
        "phone_rgb": phone["band"],
        "ppg_beats_demographics": bool(four["mae_g_dl"] < demo["mae_g_dl"]),
        "ppg_beats_population_mean": bool(four["mae_g_dl"] < mean_mae),
    }
    print("\n" + "=" * 70)
    print("GATE B VERDICT")
    print(f"  condition 1, four wavelengths : MAE {four['mae_g_dl']:.3f} -> **{four['band']}**")
    print(f"  condition 3, phone-RGB        : MAE {phone['mae_g_dl']:.3f} -> **{phone['band']}**")
    print(f"  PPG beats demographics?       : "
          f"{results['verdict']['ppg_beats_demographics']} "
          f"({four['mae_g_dl']:.3f} vs {demo['mae_g_dl']:.3f})")
    print(f"  PPG beats population mean?    : "
          f"{results['verdict']['ppg_beats_population_mean']} "
          f"({four['mae_g_dl']:.3f} vs {mean_mae:.3f})")
    print("=" * 70)

    (OUT / "gate_b.json").write_text(json.dumps(results, indent=2, default=float),
                                     encoding="utf-8")
    print(f"\nresults -> {OUT / 'gate_b.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
