"""Phase 7 Task 2 - the statistically-real / clinically-useless pattern, on comparable axes.

Two results found independently in two modalities have the same shape:
  PPG raw waveform (Phases 4.5/5): distinguishable from chance, ~0.06 g/dL better than a
      constant, six times worse than sex alone, separates no WHO band.
  Conjunctival colour (Phase 6.5): within-site r 0.5-0.6, permutation z = -10, worth
      +0.08 g/dL over site + sex + age.
This script puts both on the same axes, from the artefacts, and writes
`data/interim/phase7/statistical_vs_clinical.json` for the report.

Axes:
  DETECTABILITY   effect vs its null: permutation z, empirical p (with its floor).
  UTILITY         (a) improvement over predicting a constant;
                  (b) improvement over the best CHEAP baseline on identical folds;
                  (c) fraction of the cheap baseline's own advantage that the model adds;
                  (d) whether a WHO decision boundary moves: AUROC for the WHO anaemia
                      band (12 g/dL F / 13 M) of the model vs the cheap baseline, and the
                      change in screening sensitivity/specificity at that threshold.
Retrospective: every other quantitative result in the project is placed in the same
2x2 (statistically real? / clinically useful?) so the pattern's reach is measured
rather than asserted.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from hemosight.io import paths

I = paths.INTERIM
OUT = I / "phase7"
SEED = 20260911


def load(rel):
    return json.loads((I / rel).read_text(encoding="utf-8"))


def ridge_cv(F, y):
    kf = KFold(10, shuffle=True, random_state=SEED)
    p = np.full(len(y), np.nan)
    for tr, te in kf.split(F):
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          RidgeCV(alphas=np.logspace(-3, 3, 25))).fit(F[tr], y[tr])
        p[te] = m.predict(F[te])
    return p


def who_threshold(male: np.ndarray) -> np.ndarray:
    return np.where(male == 1, 13.0, 12.0)


def screening(pred, y, male):
    """Screen positive if the prediction is below the WHO threshold for the subject's sex."""
    thr = who_threshold(male)
    truth = (y < thr).astype(int)
    call = (pred < thr).astype(int)
    tp = int(((call == 1) & (truth == 1)).sum()); fn = int(((call == 0) & (truth == 1)).sum())
    tn = int(((call == 0) & (truth == 0)).sum()); fp = int(((call == 1) & (truth == 0)).sum())
    return {"prevalence": float(truth.mean()), "sensitivity": tp / max(1, tp + fn),
            "specificity": tn / max(1, tn + fp), "n": int(len(y)),
            "auroc": float(roc_auc_score(truth, -pred)) if 0 < truth.mean() < 1 else None}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"axes": ["detectability: z vs null, empirical p and its floor",
                    "utility: gain over constant; gain over best cheap baseline; fraction of "
                    "baseline advantage; WHO-band AUROC and screening sens/spec vs baseline"]}

    # ------------------------------------------------------------ PPG waveform
    h = load("phase5/harden.json"); ext = h["permutation_selection_aware_extended"]
    gb = load("phase4/gate_b.json")
    deep = pd.read_csv(I / "phase6" / "known_truth" / "phase5_deep_model.csv")
    y = deep.y_true.to_numpy(); pred = deep.y_pred.to_numpy()
    male = (deep.sex == "M").astype(float).to_numpy()
    age = deep.age.to_numpy(float)
    base_sex = ridge_cv(male[:, None], y)
    const = np.full(len(y), np.nan)
    for tr, te in KFold(10, shuffle=True, random_state=SEED).split(y):
        const[te] = y[tr].mean()
    mae = lambda p: float(np.mean(np.abs(p - y)))
    stack = ridge_cv(np.stack([pred, male, age], 1), y)
    ppg = {
        "modality": "PPG raw waveform, spectrogram CNN, 660 nm (Phases 4.5 / 5)",
        "n_subjects": int(len(y)),
        "detectability": {"real_mae": ext["real_mae"], "null_mean": ext["null_mean"],
                          "null_sd": ext["null_sd"], "z": ext["z_parametric"],
                          "p_empirical": ext["p_empirical"], "p_is_floor": ext["at_floor"],
                          "n_perm": ext["n"], "construction": "selection-aware, model refit inside each permutation"},
        "utility": {
            "constant_mae": mae(const), "model_mae": mae(pred),
            "gain_over_constant": mae(const) - mae(pred),
            "cheap_baseline": "sex alone", "cheap_baseline_mae": mae(base_sex),
            "gain_over_cheap_baseline": mae(base_sex) - mae(pred),
            "model_plus_baseline_mae": mae(stack),
            "increment_when_added_to_baseline": mae(base_sex) - mae(stack),
            "fraction_of_baseline_advantage": (mae(const) - mae(pred)) / (mae(const) - mae(base_sex)),
            "who_screening_model": screening(pred, y, male),
            "who_screening_cheap_baseline": screening(base_sex, y, male),
            "who_screening_model_plus_baseline": screening(stack, y, male),
        },
    }
    res["ppg_waveform"] = ppg

    # ------------------------------------------------------------ conjunctival colour
    cnn = load("phase6_5/image_cnn.json"); emp = load("phase3/empirical_signal.json")
    cp = pd.read_csv(I / "phase6_5" / "image_cnn_predictions.csv")
    z = np.load(I / "phase6_5" / "eyes_defy_crops.npz", allow_pickle=True)
    yc = cp.y_true.to_numpy(); pc = cp.y_pred.to_numpy()
    malec = (cp.sex == "M").astype(float).to_numpy(); agec = cp.age.to_numpy(float)
    italy = (cp.site == "eyes_defy:Italy").astype(float).to_numpy()
    lab = z["lab"]
    demo3 = np.stack([italy, malec, agec], 1)
    base3 = ridge_cv(demo3, yc)
    constc = np.full(len(yc), np.nan)
    for tr, te in KFold(10, shuffle=True, random_state=SEED).split(yc):
        constc[te] = yc[tr].mean()
    maec = lambda p: float(np.mean(np.abs(p - yc)))
    colour = ridge_cv(lab, yc)
    colour_plus = ridge_cv(np.concatenate([lab, demo3], 1), yc)
    cnn_plus = ridge_cv(np.stack([pc, italy, malec, agec], 1), yc)
    pm = cnn.get("permutation", {})
    pn = emp["permutation_null"]["regression_site_sex_age"]
    conj = {
        "modality": "conjunctival colour, Eyes-Defy under a fixed LED (Phase 6.5)",
        "n_subjects": int(len(yc)),
        "detectability": {
            "cnn_permutation": {"real_mae": pm.get("real_mae_seed0"), "null_mean": pm.get("null_mean"),
                                "null_sd": pm.get("null_sd"), "z": pm.get("z"),
                                "p_empirical": pm.get("p_empirical"), "p_is_floor": pm.get("p_empirical") == pm.get("p_floor"),
                                "n_perm": pm.get("n"), "construction": "model refit inside each permutation"},
            "colour_slope": {"signal_dE_per_g_dl": emp["headline"]["de_per_g_dl"],
                             "ci95": emp["headline"]["ci95"], "null_mean": pn["null_mean"],
                             "null_sd": pn["null_sd"], "p_empirical": pn["p_empirical"],
                             "z": (emp["headline"]["de_per_g_dl"] - pn["null_mean"]) / pn["null_sd"]},
        },
        "utility": {
            "constant_mae": maec(constc), "model_mae": maec(pc), "colour_features_mae": maec(colour),
            "gain_over_constant": maec(constc) - maec(pc),
            "cheap_baseline": "site + sex + age", "cheap_baseline_mae": maec(base3),
            "gain_over_cheap_baseline": maec(base3) - maec(pc),
            "model_plus_baseline_mae": maec(cnn_plus),
            "increment_when_added_to_baseline": maec(base3) - maec(cnn_plus),
            "colour_plus_baseline_mae": maec(colour_plus),
            "fraction_of_baseline_advantage": (maec(constc) - maec(pc)) / (maec(constc) - maec(base3)),
            "who_screening_model": screening(pc, yc, malec),
            "who_screening_cheap_baseline": screening(base3, yc, malec),
            "who_screening_model_plus_baseline": screening(cnn_plus, yc, malec),
            "who_screening_colour_plus_baseline": screening(colour_plus, yc, malec),
        },
    }
    res["conjunctival_colour"] = conj

    # ------------------------------------------------------------ retrospective 2x2
    ceil = load("phase4_5/ceiling.json")
    n1b = load("phase2/n1b_selfconsistency.json") if (I / "phase2/n1b_selfconsistency.json").exists() else None
    res["retrospective_2x2"] = [
        {"result": "PPG raw waveform (spectrogram CNN)", "statistically_real": True,
         "clinically_useful": False, "cell": "real & useless",
         "evidence": f"z {ext['z_parametric']:.2f}, p <= {ext['p_empirical']:.4f} (floor); {ppg['utility']['gain_over_cheap_baseline']:+.3f} g/dL vs sex alone"},
        {"result": "Conjunctival colour (CNN / mean Lab), controlled LED", "statistically_real": True,
         "clinically_useful": False, "cell": "real & useless",
         "evidence": f"z {pm.get('z', float('nan')):.1f}; {conj['utility']['increment_when_added_to_baseline']:+.3f} g/dL added to site+sex+age; MARGINAL band"},
        {"result": "PPG hand-engineered AC/DC features", "statistically_real": False,
         "clinically_useful": False, "cell": "not real & useless",
         "evidence": f"permutation p = {ceil['permutation']['p_value']:.3f}, z = {ceil['permutation']['z_score']:+.2f} (wrong direction); 0 of 51 features above the MI null"},
        {"result": "PPG features + demographics (MAE 0.824, inside the VIABLE band)", "statistically_real": False,
         "clinically_useful": "apparent only", "cell": "apparent utility, no signal beyond the baseline",
         "evidence": "0.824 vs demographics alone 0.831 - the whole score is the sex covariate (Phase 4 Task 3)"},
        {"result": "Image CNN, first run, baseline without site (MAE 1.309 'beats' demographics 1.607)", "statistically_real": True,
         "clinically_useful": "apparent only", "cell": "apparent utility, no signal beyond the (correct) baseline",
         "evidence": "site + sex + age alone 1.273 (Phase 6.5 correction) - the score was the site"},
        {"result": "Sclera as white reference (N1, Phase 2)", "statistically_real": True,
         "clinically_useful": False, "cell": "real & worse than the cheap baseline",
         "evidence": "significantly WORSE than grey-world (p = 3.1e-8); reduces spread vs no correction (p = 2.4e-8)"},
        {"result": "Corneal specular reference (Phase 2.5)", "statistically_real": True,
         "clinically_useful": False, "cell": "real & worse than the cheap baseline",
         "evidence": "beats no-correction (p = 2.3e-4), loses to grey-world (p = 4.5e-6), indistinguishable from sclera (p = 0.29)"},
        {"result": "Illuminant-free within-image ratio (Phase 3.5)", "statistically_real": False,
         "clinically_useful": False, "cell": "not real & useless",
         "evidence": "every ratio feature worse than no correction; 10.04 g/dL equivalent"},
        {"result": "Sex alone as an Hb predictor (both modalities)", "statistically_real": True,
         "clinically_useful": "partly", "cell": "real & the cheap baseline itself",
         "evidence": "PPG MAE 0.831 (R2 0.415); Eyes-Defy 1.631 - the yardstick every model must beat"},
    ]
    res["pattern_reach"] = {
        "results_in_the_real_and_useless_cell": 2,
        "results_placed": len(res["retrospective_2x2"]),
        "note": "The specific cell has exactly two members. What generalises is the 2x2 itself: "
                "three results sit in the 'apparent utility' cell that a cheap-baseline "
                "comparison on identical folds exposed, and two sit in 'real but worse than the "
                "cheap baseline'. Detectability and utility were separable in 7 of 9 results.",
    }
    (OUT / "statistical_vs_clinical.json").write_text(json.dumps(res, indent=2, default=float), encoding="utf-8")
    for k in ("ppg_waveform", "conjunctival_colour"):
        u = res[k]["utility"]
        print(f"{k}: gain over constant {u['gain_over_constant']:+.3f}; over cheap baseline {u['gain_over_cheap_baseline']:+.3f}; "
              f"added to baseline {u['increment_when_added_to_baseline']:+.3f}; frac of baseline advantage {u['fraction_of_baseline_advantage']:.2f}; "
              f"AUROC model {u['who_screening_model']['auroc']:.3f} vs baseline {u['who_screening_cheap_baseline']['auroc']:.3f} "
              f"vs model+baseline {u['who_screening_model_plus_baseline']['auroc']:.3f}; sens/spec model "
              f"{u['who_screening_model']['sensitivity']:.2f}/{u['who_screening_model']['specificity']:.2f} baseline "
              f"{u['who_screening_cheap_baseline']['sensitivity']:.2f}/{u['who_screening_cheap_baseline']['specificity']:.2f}")
    print(f"wrote {OUT / 'statistical_vs_clinical.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
