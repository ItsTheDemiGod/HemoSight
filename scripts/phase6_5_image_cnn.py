"""Phase 6.5 Task 2 - the missing image CNN baseline, on Eyes-Defy-Anemia.

Section 3 of CLAUDE.md requires a conventional CNN comparison arm for every claim. The
PPG arm had one (Phase 4.5); the imaging arm never did. This closes it.

LIMITATION, STATED FIRST: 217 subjects with Hb, one image each, one Samsung Galaxy S6
in two regional variants (SM-G920F / SM-G920I), two sites (India 95, Italy 123), Hb
7.0-17.4 g/dL, no severe cases. **A pilot comparison arm, not a validation.**

Protocol (identical in spirit to Phase 4 Gate B and Phase 4.5):
  - existing subject-level splits; one image per subject so subject K-fold IS
    leave-subject-out; asserted in code;
  - baselines on identical folds: population mean, sex alone, demographics (age, sex -
    Eyes-Defy has no height/weight), demographics PLUS SITE, and a colour-feature
    baseline (mean palpebral Lab + Ridge, the shallow model the original Phase 5 plan
    asked for). SITE IS A DEMOGRAPHIC HERE: Italy's mean Hb is 13.8 g/dL and India's
    11.5, and the sites are two device variants, so a model that recognises the site
    from the image inherits 2.4 g/dL of separation for free. A first run of this script
    omitted site from the baseline and the CNN appeared to beat demographics; it beat
    sex alone by reading the site. The site-inclusive baseline is the one that counts;
  - pre-declared bands: < 1.0 g/dL viable, 1.0-2.0 marginal, > 2.0 not viable;
  - India vs Italy cross-site in both directions (the only cross-site axis available);
  - scrutiny: train-test gap, three seeds, and IF the CNN beats the demographic
    baseline: a sex probe on its penultimate features and a permutation test.
Expected outcome is failure. If it succeeds, that is reported prominently and the
imaging verdict is revisited - not quietly.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from hemosight.baseline import image_cnn as icnn          # noqa: E402
from hemosight.io.manifests import trusted_hb            # noqa: E402
from phase3_empirical_signal import (linear_to_lab, mask_region,  # noqa: E402
                                     palpebral_mask_path, srgb_to_linear)

MANIFEST = ROOT / "data" / "interim" / "manifests" / "eyes_defy.csv"
OUT = ROOT / "data" / "interim" / "phase6_5"
CACHE = OUT / "eyes_defy_crops.npz"
SEED = icnn.SEED
N_SPLITS = icnn.N_SPLITS
SEEDS = 3
MARGIN = 0.15
N_PERM = 30


def band(mae: float) -> str:
    return "VIABLE" if mae < 1.0 else "MARGINAL" if mae <= 2.0 else "NOT VIABLE"


def metrics(preds: np.ndarray, y: np.ndarray) -> dict:
    err = preds - y
    mae = float(np.mean(np.abs(err)))
    return {"mae_g_dl": mae, "rmse_g_dl": float(np.sqrt(np.mean(err ** 2))),
            "bias_g_dl": float(np.mean(err)),
            "r2": float(1.0 - np.sum(err ** 2) / np.sum((y - y.mean()) ** 2)),
            "pearson_r": float(np.corrcoef(preds, y)[0, 1]) if np.std(preds) > 0 else 0.0,
            "band": band(mae)}


def build_crops() -> dict:
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=True)
        return {k: z[k] for k in z.files}
    df = trusted_hb(pd.read_csv(MANIFEST))
    X, lab, meta = [], [], []
    for _, r in df.iterrows():
        mp = palpebral_mask_path(r)
        if mp is None:   # two subjects lack a palpebral-only mask; use the combined one
            mp = next((Path(p) for p in str(r["mask_paths"]).split("|")
                       if p.endswith("_forniceal_palpebral.png")), None)
        if mp is None or not mp.exists():
            continue
        mask = cv2.imread(str(mp), cv2.IMREAD_UNCHANGED)
        img = cv2.imread(str(r["file_path"]), cv2.IMREAD_COLOR)
        if mask is None or img is None:
            continue
        region, _ = mask_region(mask)
        if region.sum() < 50 or region.mean() > 0.6:
            continue
        ys, xs = np.where(region)
        sy, sx = img.shape[0] / mask.shape[0], img.shape[1] / mask.shape[1]
        y0, y1 = int(ys.min() * sy), int(ys.max() * sy)
        x0, x1 = int(xs.min() * sx), int(xs.max() * sx)
        dy, dx = int((y1 - y0) * MARGIN), int((x1 - x0) * MARGIN)
        crop = img[max(0, y0 - dy):y1 + dy + 1, max(0, x0 - dx):x1 + dx + 1][..., ::-1]
        X.append(cv2.resize(crop, (icnn.IMG, icnn.IMG), interpolation=cv2.INTER_AREA))
        # colour-feature baseline input: mean linear-sRGB inside the mask -> Lab
        small = cv2.resize(img, (mask.shape[1], mask.shape[0]), interpolation=cv2.INTER_AREA)[..., ::-1]
        lab.append(linear_to_lab(srgb_to_linear(small)[region].mean(axis=0)))
        meta.append((r["image_id"], r["subject_id"], r["site"], float(r["hb_g_dl"]),
                     float(str(r["sex"]).strip().upper() == "M"), float(r["age"])))
    out = {"X": np.stack(X).astype(np.uint8), "lab": np.stack(lab).astype(np.float32),
           "image_id": np.array([m[0] for m in meta]), "subject": np.array([m[1] for m in meta]),
           "site": np.array([m[2] for m in meta]), "y": np.array([m[3] for m in meta]),
           "male": np.array([m[4] for m in meta]), "age": np.array([m[5] for m in meta])}
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE, **out)
    return out


def ridge_cv(F: np.ndarray, y: np.ndarray) -> np.ndarray:
    kf = KFold(N_SPLITS, shuffle=True, random_state=SEED)
    preds = np.full(len(y), np.nan)
    for tr, te in kf.split(F):
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          RidgeCV(alphas=np.logspace(-3, 3, 25)))
        m.fit(F[tr], y[tr])
        preds[te] = m.predict(F[te])
    return preds


def mean_cv(y: np.ndarray) -> np.ndarray:
    kf = KFold(N_SPLITS, shuffle=True, random_state=SEED)
    preds = np.full(len(y), np.nan)
    for tr, te in kf.split(y):
        preds[te] = y[tr].mean()
    return preds


def main() -> int:
    t0 = time.time()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    d = build_crops()
    X, y, subs, site = d["X"], d["y"], d["subject"], d["site"]
    male, age, lab = d["male"], d["age"], d["lab"]
    n = len(y)
    print(f"device {dev}; n={n} subjects; sites {dict(zip(*np.unique(site, return_counts=True)))}; "
          f"Hb {y.min():.1f}-{y.max():.1f}; male {int(male.sum())}")
    res: dict = {"n_subjects": int(n), "sites": {s: int((site == s).sum()) for s in set(site)},
                 "limitation": "217 subjects with Hb, 1 image each, one Galaxy S6 in two "
                               "regional variants, 2 sites, Hb 7.0-17.4, no severe cases. "
                               "Pilot comparison arm, not a validation.",
                 "epochs": icnn.EPOCHS, "folds": N_SPLITS, "seeds": SEEDS,
                 "bands": "<1.0 viable, 1.0-2.0 marginal, >2.0 not viable"}

    # ------------------------------------------------------------ baselines
    print("\n=== baselines (identical 10-fold subject-disjoint splits) ===")
    B = {}
    B["population_mean"] = metrics(mean_cv(y), y)
    B["sex_only"] = metrics(ridge_cv(male[:, None], y), y)
    B["demographics_age_sex"] = metrics(ridge_cv(np.stack([age, male], 1), y), y)
    is_italy = (site == "eyes_defy:Italy").astype(float)
    demo3 = np.stack([is_italy, age, male], 1)
    B["site_only"] = metrics(ridge_cv(is_italy[:, None], y), y)
    B["demographics_site_sex_age"] = metrics(ridge_cv(demo3, y), y)
    B["colour_features_lab"] = metrics(ridge_cv(lab, y), y)
    B["colour_features_lab_plus_demographics"] = metrics(
        ridge_cv(np.concatenate([lab, np.stack([age, male], 1)], 1), y), y)
    B["colour_features_lab_plus_site_sex_age"] = metrics(
        ridge_cv(np.concatenate([lab, demo3], 1), y), y)
    for k, v in B.items():
        print(f"  {k:40s} MAE={v['mae_g_dl']:.3f}  r={v['pearson_r']:+.3f}  R2={v['r2']:+.3f}  {v['band']}")
    res["baselines"] = B
    res["site_hb"] = {s: {"mean": float(y[site == s].mean()), "sd": float(y[site == s].std()),
                          "n": int((site == s).sum())} for s in sorted(set(site))}
    best_demo = min(B["sex_only"]["mae_g_dl"], B["demographics_age_sex"]["mae_g_dl"],
                    B["demographics_site_sex_age"]["mae_g_dl"])

    # ------------------------------------------------------------ CNN, pooled CV
    print(f"\n=== CNN (ResNet-18, ImageNet init), {SEEDS} seeds x {N_SPLITS}-fold ===")
    seed_runs, all_preds = [], []
    feats = None
    for s in range(SEEDS):
        t1 = time.time()
        r = icnn.cv_predict(X, y, subs, dev, seed=SEED + s, want_features=(s == 0))
        m = metrics(r["preds"], y)
        m["train_mae"] = r["train_mae"]
        m["train_test_gap"] = m["mae_g_dl"] - r["train_mae"]
        seed_runs.append(m)
        all_preds.append(r["preds"])
        if s == 0:
            feats = r["features"]
        print(f"  seed {s}: MAE={m['mae_g_dl']:.3f} train={r['train_mae']:.3f} "
              f"gap={m['train_test_gap']:+.3f} r={m['pearson_r']:+.3f} R2={m['r2']:+.3f} "
              f"({time.time()-t1:.0f}s)")
    maes = np.array([m["mae_g_dl"] for m in seed_runs])
    mean_pred = np.mean(np.stack(all_preds), 0)
    cnn = metrics(mean_pred, y)
    cnn.update({"per_seed": seed_runs, "seed_mae_mean": float(maes.mean()),
                "seed_mae_sd": float(maes.std()), "seed_mae_range": [float(maes.min()), float(maes.max())],
                "train_mae_mean": float(np.mean([m["train_mae"] for m in seed_runs])),
                "train_test_gap_mean": float(np.mean([m["train_test_gap"] for m in seed_runs]))})
    res["cnn_pooled"] = cnn
    print(f"  seed-averaged prediction: MAE={cnn['mae_g_dl']:.3f} r={cnn['pearson_r']:+.3f} "
          f"R2={cnn['r2']:+.3f} {cnn['band']} | seed SD {maes.std():.4f} | gap {cnn['train_test_gap_mean']:+.3f}")

    # CNN + demographics: does the image add anything over site, age and sex?
    res["cnn_plus_demographics"] = metrics(ridge_cv(np.stack([mean_pred, age, male], 1), y), y)
    res["cnn_plus_site_sex_age"] = metrics(ridge_cv(np.stack([mean_pred, is_italy, age, male], 1), y), y)
    res["image_increment_over_site_sex_age_g_dl"] = (
        B["demographics_site_sex_age"]["mae_g_dl"] - res["cnn_plus_site_sex_age"]["mae_g_dl"])
    print(f"  CNN + demographics (age, sex): MAE={res['cnn_plus_demographics']['mae_g_dl']:.3f}; "
          f"CNN + site+sex+age: {res['cnn_plus_site_sex_age']['mae_g_dl']:.3f} "
          f"(image adds {res['image_increment_over_site_sex_age_g_dl']:+.3f} g/dL over site+sex+age)")
    # Per-site view of the pooled model, and the WHO anaemia band (12 F / 13 M) as AUROC.
    from sklearn.metrics import roc_auc_score
    res["cnn_pooled_by_site"] = {
        s: {"mae_g_dl": float(np.mean(np.abs(mean_pred[site == s] - y[site == s]))),
            "pearson_r": float(np.corrcoef(mean_pred[site == s], y[site == s])[0, 1]),
            "site_sex_age_mae_g_dl": float(np.mean(np.abs(ridge_cv(demo3, y)[site == s] - y[site == s]))),
            "population_mean_of_site_mae": float(np.mean(np.abs(y[site == s] - y[site == s].mean())))}
        for s in sorted(set(site))}
    thr = np.where(male == 1, 13.0, 12.0)
    anaemic = (y < thr).astype(int)
    res["who_anaemia_auroc"] = {
        "prevalence": float(anaemic.mean()),
        "cnn": float(roc_auc_score(anaemic, -mean_pred)),
        "colour_features_lab": float(roc_auc_score(anaemic, -ridge_cv(lab, y))),
        "site_sex_age": float(roc_auc_score(anaemic, -ridge_cv(demo3, y))),
        "cnn_plus_site_sex_age": float(roc_auc_score(anaemic, -ridge_cv(np.stack([mean_pred, is_italy, age, male], 1), y)))}
    for s, v in res["cnn_pooled_by_site"].items():
        print(f"  {s}: CNN {v['mae_g_dl']:.3f} (r={v['pearson_r']:+.3f}) | site+sex+age {v['site_sex_age_mae_g_dl']:.3f} | site mean {v['population_mean_of_site_mae']:.3f}")
    print(f"  WHO-band AUROC: CNN {res['who_anaemia_auroc']['cnn']:.3f} | colour {res['who_anaemia_auroc']['colour_features_lab']:.3f} | "
          f"site+sex+age {res['who_anaemia_auroc']['site_sex_age']:.3f} | CNN+site+sex+age {res['who_anaemia_auroc']['cnn_plus_site_sex_age']:.3f}")

    # ------------------------------------------------------------ scrutiny
    beats = cnn["mae_g_dl"] < best_demo
    res["beats_demographics"] = bool(beats)
    res["beats_population_mean"] = bool(cnn["mae_g_dl"] < B["population_mean"]["mae_g_dl"])
    # Sex probe on the learned representation - run regardless, it is cheap and
    # informative; it COUNTS as a finding only if the CNN beats demographics.
    probe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.1))
    kf = KFold(N_SPLITS, shuffle=True, random_state=SEED)
    sex_hat = cross_val_predict(probe, feats, male, cv=kf)
    res["sex_probe"] = {"accuracy": float((sex_hat == male).mean()),
                        "base_rate": float(max(male.mean(), 1 - male.mean())),
                        "note": "logistic probe on held-out 512-d penultimate features "
                                "(seed 0), 10-fold; counts as evidence only if the CNN "
                                "beats the demographic baseline"}
    print(f"  sex probe on features: {res['sex_probe']['accuracy']:.3f} vs base rate "
          f"{res['sex_probe']['base_rate']:.3f}")
    # Correlation of the CNN's prediction with sex: how much of what it learned IS sex.
    res["cnn_pred_vs_sex_r"] = float(np.corrcoef(mean_pred, male)[0, 1])
    res["hb_vs_sex_r"] = float(np.corrcoef(y, male)[0, 1])
    print(f"  r(CNN pred, male) = {res['cnn_pred_vs_sex_r']:+.3f}; r(Hb, male) = {res['hb_vs_sex_r']:+.3f}")

    if beats or res["beats_population_mean"]:
        print(f"\n=== permutation test, n={N_PERM} (CNN beat {'demographics' if beats else 'the population mean'}) ===")
        rng = np.random.default_rng(770000)
        null = []
        for i in range(N_PERM):
            yp = rng.permutation(y)
            r = icnn.cv_predict(X, yp, subs, dev, seed=SEED)
            null.append(float(np.mean(np.abs(r["preds"] - yp))))
            print(f"  perm {i}: {null[-1]:.4f}")
        null = np.array(null)
        real = seed_runs[0]["mae_g_dl"]
        res["permutation"] = {"n": N_PERM, "real_mae_seed0": real, "null_mean": float(null.mean()),
                              "null_sd": float(null.std()),
                              "p_empirical": float((np.sum(null <= real) + 1) / (N_PERM + 1)),
                              "p_floor": 1.0 / (N_PERM + 1),
                              "z": float((real - null.mean()) / (null.std() + 1e-12))}
        print(f"  real {real:.4f} null {null.mean():.4f}+/-{null.std():.4f} "
              f"p={res['permutation']['p_empirical']:.4f} z={res['permutation']['z']:+.2f}")

    # ------------------------------------------------------------ cross-site
    print("\n=== cross-site (the only cross-site axis the imaging data supports) ===")
    IN, IT = "eyes_defy:India", "eyes_defy:Italy"
    CS = {}
    for trs, tes in ((IT, IN), (IN, IT)):
        key = f"{trs.split(':')[1].lower()}_to_{tes.split(':')[1].lower()}"
        tr, te = np.where(site == trs)[0], np.where(site == tes)[0]
        yt = y[te]
        entry = {"n_train": int(len(tr)), "n_test": int(len(te)),
                 "population_mean_of_train_site": metrics(np.full(len(te), y[tr].mean()), yt)}
        for nm, F in (("sex_only", male[:, None]), ("demographics_age_sex", np.stack([age, male], 1)),
                      ("colour_features_lab", lab)):
            m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                              RidgeCV(alphas=np.logspace(-3, 3, 25))).fit(F[tr], y[tr])
            entry[nm] = metrics(m.predict(F[te]), yt)
        cs_preds = []
        for s in range(SEEDS):
            r = icnn.cross_site(X, y, site, trs, tes, dev, seed=SEED + s)
            cs_preds.append(r["preds"])
            mm = metrics(r["preds"], yt)
            mm["train_mae"] = r["train_mae"]
            entry.setdefault("cnn_per_seed", []).append(mm)
        entry["cnn"] = metrics(np.mean(np.stack(cs_preds), 0), yt)
        entry["cnn"]["train_test_gap_mean"] = float(np.mean(
            [m_["mae_g_dl"] - m_["train_mae"] for m_ in entry["cnn_per_seed"]]))
        CS[key] = entry
        print(f"  {key}: pop-mean {entry['population_mean_of_train_site']['mae_g_dl']:.3f} | "
              f"sex {entry['sex_only']['mae_g_dl']:.3f} | demo {entry['demographics_age_sex']['mae_g_dl']:.3f} | "
              f"colour {entry['colour_features_lab']['mae_g_dl']:.3f} | "
              f"CNN {entry['cnn']['mae_g_dl']:.3f} ({entry['cnn']['band']}, r={entry['cnn']['pearson_r']:+.3f}, "
              f"bias {entry['cnn']['bias_g_dl']:+.2f}, gap {entry['cnn']['train_test_gap_mean']:+.2f})")
    res["cross_site"] = CS

    # ------------------------------------------------------------ verdict
    res["verdict"] = {
        "cnn_pooled_band": cnn["band"],
        "cnn_beats_sex_alone": bool(cnn["mae_g_dl"] < B["sex_only"]["mae_g_dl"]),
        "cnn_beats_demographics_age_sex": bool(cnn["mae_g_dl"] < B["demographics_age_sex"]["mae_g_dl"]),
        "cnn_beats_demographics_site_sex_age": bool(cnn["mae_g_dl"] < B["demographics_site_sex_age"]["mae_g_dl"]),
        "cnn_beats_demographics": bool(beats),
        "image_increment_over_site_sex_age_g_dl": res["image_increment_over_site_sex_age_g_dl"],
        "who_auroc_cnn_vs_site_sex_age": [res["who_anaemia_auroc"]["cnn"], res["who_anaemia_auroc"]["site_sex_age"]],
        "cnn_beats_population_mean": res["beats_population_mean"],
        "cross_site_bands": {k: v["cnn"]["band"] for k, v in CS.items()},
        "cross_site_cnn_beats_train_site_mean": {
            k: bool(v["cnn"]["mae_g_dl"] < v["population_mean_of_train_site"]["mae_g_dl"])
            for k, v in CS.items()},
    }
    res["elapsed_s"] = time.time() - t0
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "image_cnn.json").write_text(json.dumps(res, indent=2, default=float), encoding="utf-8")
    pd.DataFrame({"subject_id": subs, "site": site, "y_true": y, "y_pred": mean_pred,
                  **{f"y_pred_seed__{i}": p for i, p in enumerate(all_preds)},
                  "sex": np.where(male == 1, "M", "F"), "age": age}).to_csv(
        OUT / "image_cnn_predictions.csv", index=False)
    print(f"\nverdict: {json.dumps(res['verdict'])}")
    print(f"wrote {OUT / 'image_cnn.json'}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
