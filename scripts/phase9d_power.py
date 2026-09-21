"""Phase 9D - power analysis: what this study could have detected.

Pre-declared in CLAUDE.md (Phase 9D, 2026-09-20) before any number here was computed:
the MDE formula, one deciding comparison per arm, the paired SE methods, the clinical
yardsticks (all of them already declared by earlier phases) and the verdict rule.

**Observed / retrospective power is not computed.** See `hemosight.evaluation.power`.

Model scores and folds are rebuilt by importing Phase 9A's own construction functions, so
the comparisons here are the comparisons that decided the arms, not re-derived ones; the
script asserts it reproduces Phase 9A's recorded point differences before reporting.

    .\\.venv\\Scripts\\python.exe scripts\\phase9d_power.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hemosight.evaluation import power as pw            # noqa: E402
from hemosight.evaluation import screening as scr       # noqa: E402
from hemosight.io import paths                          # noqa: E402
from phase9a_screening import (IMG_CROPS, IMG_PRED, PPG_DEEP, PPG_FEAT,  # noqa: E402
                               XS_PRED, folds_for, mean_cv, ridge_cv)

OUT = paths.INTERIM / "phase9d"
P9A = paths.INTERIM / "phase9a" / "screening.json"
TOL = 5e-3          # tolerance when reproducing Phase 9A's recorded differences


# --------------------------------------------------------------------------- #
# bootstrap replicate distributions - the identical scheme Phase 9A used,
# returning the replicates so their SD can be taken
# --------------------------------------------------------------------------- #
def paired_metric_replicates(truth, call_a, call_b, metric) -> np.ndarray:
    truth = np.asarray(truth).astype(bool)
    call_a = np.asarray(call_a).astype(bool)
    call_b = np.asarray(call_b).astype(bool)
    out = []
    for idx in scr._resamples(len(truth)):
        t = truth[idx]
        if t.sum() == 0 or (~t).sum() == 0:
            continue
        a = scr.screening_metrics(t, call_a[idx])[metric]
        b = scr.screening_metrics(t, call_b[idx])[metric]
        if np.isfinite(a) and np.isfinite(b):
            out.append(a - b)
    return np.array(out)


def paired_auroc_replicates(truth, score_a, score_b) -> np.ndarray:
    truth = np.asarray(truth).astype(bool)
    s = np.stack([np.asarray(score_a, float), np.asarray(score_b, float)], 1)
    out = []
    for idx in scr._resamples(len(truth)):
        t = truth[idx]
        if len(np.unique(t.astype(int))) < 2:
            continue
        v = (scr.ranking_metrics(t, s[idx, 0])["auroc"]
             - scr.ranking_metrics(t, s[idx, 1])["auroc"])
        if np.isfinite(v):
            out.append(v)
    return np.array(out)


def block(name, se, yardstick, yardstick_label, extra=None) -> dict:
    d = {"se": float(se), **pw.mde_table(se),
         "clinical_yardstick": float(yardstick), "yardstick_source": yardstick_label,
         "power_at_the_yardstick": pw.power_at(yardstick, se)}
    d["verdict"] = pw.verdict(d["mde_80"], yardstick)
    if extra:
        d.update(extra)
    return d


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    p9a = json.loads(P9A.read_text(encoding="utf-8"))
    R: dict = {"method": {
        "quantity": "minimum detectable effect (MDE) at alpha 0.05, two-sided",
        "formula": "MDE = (z_0.975 + z_power) * SE(paired difference)",
        "multiplier_80": pw.multiplier(0.80), "multiplier_90": pw.multiplier(0.90),
        "retrospective_power": "NOT COMPUTED - a known statistical error; see "
                              "hemosight.evaluation.power and the Phase 9D report",
        "bootstrap": {"n_boot": scr.N_BOOT, "seed": scr.SEED,
                      "scheme": "subject-level paired resampling, identical to Phase 9A"},
        "caveats": ["SE is estimated from this sample and carries its own sampling "
                    "uncertainty",
                    "for sensitivity and specificity the SE depends mildly on the true "
                    "effect size; no correction is applied"]},
        "arms": {}}

    # ================================================================= imaging
    d = pd.read_csv(IMG_PRED)
    z = np.load(IMG_CROPS, allow_pickle=False)
    y = d["y_true"].to_numpy(float)
    male = (d["sex"].astype(str).str.strip().str.upper() == "M").to_numpy()
    age = d["age"].to_numpy(float)
    site = d["site"].to_numpy(str)
    lab = z["lab"]
    truth = y < scr.who_threshold(male, age)
    folds = folds_for(len(y))
    is_italy = (site == "eyes_defy:Italy").astype(float)
    demo3 = np.stack([is_italy, age, male.astype(float)], 1)
    cnn = d["y_pred"].to_numpy(float)
    base = ridge_cv(demo3, y, folds)
    colour = ridge_cv(lab, y, folds)

    print("=== IMAGING REGRESSION: image-CNN MAE vs site + sex + age ===")
    ae_cnn, ae_base = np.abs(cnn - y), np.abs(base - y)
    pm = pw.paired_mean_se(ae_cnn, ae_base)
    rec_cnn = p9a["imaging"]["models"]["image_cnn"]["mae_g_dl"]
    rec_base = p9a["imaging"]["models"]["demographics_site_sex_age"]["mae_g_dl"]
    assert abs(pm["mean_a"] - rec_cnn) < TOL, (pm["mean_a"], rec_cnn)
    assert abs(pm["mean_b"] - rec_base) < TOL, (pm["mean_b"], rec_base)
    print(f"  reproduced Phase 9A MAEs: CNN {pm['mean_a']:.4f} (recorded {rec_cnn:.4f}), "
          f"baseline {pm['mean_b']:.4f} (recorded {rec_base:.4f})")
    boot_ae = np.array([np.mean(ae_cnn[i]) - np.mean(ae_base[i])
                        for i in scr._resamples(len(y))])
    reg = block("imaging_regression", pm["se_paired"], pw.NARROWEST_WHO_BAND_G_DL,
                "narrowest WHO severity band = 1.0 g/dL (Phase 9D pre-declaration; "
                "bands from Phase 3 / WHO)",
                {"paired": pm, "se_bootstrap_for_reference": pw.bootstrap_se(boot_ae),
                 "observed_difference_note": "reported for context only; the MDE does not "
                                             "use it",
                 "moves_a_who_boundary_at_80": pw.moves_a_who_boundary(
                     pw.mde(pm["se_paired"], 0.80))})
    print(f"  n={pm['n']}  paired SE {pm['se_paired']:.4f} (unpaired would be "
          f"{pm['se_unpaired_for_reference']:.4f}; error r={pm['error_correlation']:.3f}, "
          f"pairing saves {pm['pairing_variance_saving'] * 100:.0f}% of the SE)")
    print(f"  MDE 80% {reg['mde_80']:.3f} g/dL, 90% {reg['mde_90']:.3f} g/dL -> "
          f"{reg['verdict']}")
    R["arms"]["imaging_regression"] = reg

    # ---- imaging screening: specificity at matched sensitivity, and AUROC
    print("\n=== IMAGING SCREENING (within site, pooled): vs site + sex + age ===")
    scr_arm = {}
    for nm, score in (("image_cnn", cnn), ("colour_features_lab", colour)):
        m_sens = scr.nested_calls_matched_sensitivity(score, truth, folds, base)
        base_call = scr.nested_calls(base, truth, folds)["call"]
        rep = paired_metric_replicates(truth, m_sens["call"], base_call, "specificity")
        se = pw.bootstrap_se(rep)
        obs = (scr.screening_metrics(truth, m_sens["call"])["specificity"]
               - scr.screening_metrics(truth, base_call)["specificity"])
        rec = p9a["imaging"]["comparisons"][nm]["matched_sensitivity"]["specificity_difference"]
        assert abs(obs - rec) < TOL, (nm, obs, rec)
        a_rep = paired_auroc_replicates(truth, score, base)
        a_se = pw.bootstrap_se(a_rep)
        rec_a = p9a["imaging"]["comparisons"][nm]["auroc_difference"]
        obs_a = (scr.ranking_metrics(truth, score)["auroc"]
                 - scr.ranking_metrics(truth, base)["auroc"])
        assert abs(obs_a - rec_a) < TOL, (nm, obs_a, rec_a)
        n_non = int((~truth).sum())
        n_an = int(truth.sum())
        spec = block(nm, se, scr.MARGIN,
                     "0.10 = the clinically meaningful margin pre-declared in Phase 9A",
                     {"metric": "specificity gain at matched sensitivity",
                      "observed_difference_note": obs,
                      "n_non_anaemic": n_non,
                      "referrals_avoided_at_mde_80": pw.subjects_moved(
                          pw.mde(se, 0.80), n_non)})
        au = block(nm + "_auroc", a_se, scr.MARGIN,
                   "0.10 AUROC, the same pre-declared margin scale (stated as a "
                   "scale comparison, not a clinical equivalence)",
                   {"metric": "AUROC difference", "observed_difference_note": obs_a})
        scr_arm[nm] = {"specificity_at_matched_sensitivity": spec, "auroc": au,
                       "n": int(len(y)), "n_anaemic": n_an, "n_non_anaemic": n_non}
        print(f"  {nm}: spec-gain SE {se:.4f} -> MDE80 {spec['mde_80']:.3f} "
              f"({spec['mde_90']:.3f} at 90%) -> {spec['verdict']}")
        print(f"      = {spec['referrals_avoided_at_mde_80']:.0f} of {n_non} "
              f"non-anaemic subjects spared a needless referral")
        print(f"  {nm}: AUROC SE {a_se:.4f} -> MDE80 {au['mde_80']:.3f} "
              f"({au['mde_90']:.3f} at 90%)")
    R["arms"]["imaging_screening"] = scr_arm

    # ---- sensitivity at matched specificity, for completeness of the pre-declared pair
    m_spec = scr.nested_calls_matched_specificity(cnn, truth, folds, base)
    base_call = scr.nested_calls(base, truth, folds)["call"]
    rep = paired_metric_replicates(truth, m_spec["call"], base_call, "sensitivity")
    se = pw.bootstrap_se(rep)
    n_an = int(truth.sum())
    R["arms"]["imaging_screening"]["image_cnn"]["sensitivity_at_matched_specificity"] = block(
        "image_cnn_sensitivity", se, scr.MARGIN,
        "0.10 = the clinically meaningful margin pre-declared in Phase 9A",
        {"metric": "sensitivity gain at matched specificity", "n_anaemic": n_an,
         "additional_anaemic_detected_at_mde_80": pw.subjects_moved(pw.mde(se, 0.80), n_an)})
    s2 = R["arms"]["imaging_screening"]["image_cnn"]["sensitivity_at_matched_specificity"]
    print(f"  image_cnn: sens-gain SE {se:.4f} -> MDE80 {s2['mde_80']:.3f} = "
          f"{s2['additional_anaemic_detected_at_mde_80']:.0f} of {n_an} anaemic subjects "
          f"-> {s2['verdict']}")

    # ========================================================= cross-site
    print("\n=== IMAGING CROSS-SITE, PER DIRECTION (the load-bearing finding) ===")
    xs = pd.read_csv(XS_PRED)
    cs: dict = {}
    for direction, part in xs.groupby("direction"):
        part = part[part["split"] == "test"].reset_index(drop=True)
        yy = part["y_true"].to_numpy(float)
        mm = (part["sex"].astype(str).str.strip().str.upper() == "M").to_numpy()
        aa = part["age"].to_numpy(float)
        tt = yy < scr.who_threshold(mm, aa)
        pred = part["y_pred"].to_numpy(float)
        ff = folds_for(len(yy))
        demo = ridge_cv(np.stack([aa, mm.astype(float)], 1), yy, ff)   # single-site: no site term
        m_sens = scr.nested_calls_matched_sensitivity(pred, tt, ff, demo)
        b_call = scr.nested_calls(demo, tt, ff)["call"]
        rep = paired_metric_replicates(tt, m_sens["call"], b_call, "specificity")
        se = pw.bootstrap_se(rep)
        a_rep = paired_auroc_replicates(tt, pred, demo)
        a_se = pw.bootstrap_se(a_rep)
        n_an, n_non = int(tt.sum()), int((~tt).sum())
        spec = block(direction, se, scr.MARGIN,
                     "0.10 = the clinically meaningful margin pre-declared in Phase 9A",
                     {"metric": "specificity gain at matched sensitivity",
                      "n": int(len(yy)), "n_anaemic": n_an, "n_non_anaemic": n_non,
                      "referrals_avoided_at_mde_80": pw.subjects_moved(
                          pw.mde(se, 0.80), n_non)})
        au = block(direction + "_auroc", a_se, scr.MARGIN,
                   "0.10 AUROC, the same pre-declared margin scale",
                   {"metric": "AUROC difference", "n": int(len(yy))})
        # regression MAE in the same direction, vs the same demographic baseline
        pmx = pw.paired_mean_se(np.abs(pred - yy), np.abs(demo - yy))
        mae_blk = block(direction + "_mae", pmx["se_paired"], pw.NARROWEST_WHO_BAND_G_DL,
                        "narrowest WHO severity band = 1.0 g/dL",
                        {"paired": pmx, "metric": "MAE difference"})
        cs[direction] = {"n": int(len(yy)), "n_anaemic": n_an, "n_non_anaemic": n_non,
                         "specificity_at_matched_sensitivity": spec, "auroc": au,
                         "mae": mae_blk}
        print(f"  {direction}: n={len(yy)} ({n_an} anaemic, {n_non} not)")
        print(f"      spec-gain SE {se:.4f} -> MDE80 {spec['mde_80']:.3f} "
              f"({spec['mde_90']:.3f} at 90%) -> {spec['verdict']}")
        print(f"      AUROC   SE {a_se:.4f} -> MDE80 {au['mde_80']:.3f} -> {au['verdict']}")
        print(f"      MAE     SE {pmx['se_paired']:.4f} -> MDE80 {mae_blk['mde_80']:.3f} g/dL")
    R["arms"]["imaging_cross_site"] = cs

    # ================================================================= PPG
    print("\n=== PPG: deep model vs sex alone (MAE) and vs demographics (AUROC) ===")
    deep = pd.read_csv(PPG_DEEP)
    feat = pd.read_csv(PPG_FEAT)
    feat = feat[np.isfinite(feat.hb_g_dl)].reset_index(drop=True)
    yp = deep["y_true"].to_numpy(float)
    mp = (deep["sex"].astype(str).str.strip().str.upper() == "M").to_numpy()
    ap = deep["age"].to_numpy(float)
    tp = yp < scr.who_threshold(mp, ap)
    fp = folds_for(len(yp))
    sex_only = ridge_cv(feat[["sex"]].to_numpy(float), yp, fp)
    demo4 = ridge_cv(feat[["age", "sex", "height", "weight"]].to_numpy(float), yp, fp)
    dpred = deep["y_pred"].to_numpy(float)

    pmp = pw.paired_mean_se(np.abs(dpred - yp), np.abs(sex_only - yp))
    rec_sex = p9a["ppg"]["models"]["sex_only"]["mae_g_dl"]
    rec_deep = p9a["ppg"]["models"]["ppg_deep_speccnn_660_selected"]["mae_g_dl"]
    assert abs(pmp["mean_b"] - rec_sex) < TOL, (pmp["mean_b"], rec_sex)
    assert abs(pmp["mean_a"] - rec_deep) < TOL, (pmp["mean_a"], rec_deep)
    print(f"  reproduced Phase 9A MAEs: deep {pmp['mean_a']:.4f} (recorded {rec_deep:.4f}), "
          f"sex alone {pmp['mean_b']:.4f} (recorded {rec_sex:.4f})")
    ppg_mae = block("ppg_mae", pmp["se_paired"], pw.NARROWEST_WHO_BAND_G_DL,
                    "narrowest WHO severity band = 1.0 g/dL",
                    {"paired": pmp, "metric": "MAE difference vs sex alone",
                     "moves_a_who_boundary_at_80": pw.moves_a_who_boundary(
                         pw.mde(pmp["se_paired"], 0.80))})
    print(f"  n={pmp['n']}  paired SE {pmp['se_paired']:.4f} (error r="
          f"{pmp['error_correlation']:.3f}) -> MDE80 {ppg_mae['mde_80']:.3f} g/dL, "
          f"90% {ppg_mae['mde_90']:.3f} -> {ppg_mae['verdict']}")

    best_demo = p9a["ppg"]["best_demographic_baseline_by_auroc"]
    demo_score = {"sex_only": sex_only,
                  "demographics_age_sex_height_weight": demo4}.get(best_demo)
    assert demo_score is not None, f"unexpected PPG baseline {best_demo}"
    a_rep = paired_auroc_replicates(tp, dpred, demo_score)
    a_se = pw.bootstrap_se(a_rep)
    rec_a = p9a["ppg"]["comparisons"]["ppg_deep_speccnn_660_selected"]["auroc_difference"]
    obs_a = (scr.ranking_metrics(tp, dpred)["auroc"]
             - scr.ranking_metrics(tp, demo_score)["auroc"])
    assert abs(obs_a - rec_a) < TOL, (obs_a, rec_a)
    ppg_au = block("ppg_auroc", a_se, scr.MARGIN,
                   "0.10 AUROC, the same pre-declared margin scale",
                   {"metric": f"AUROC difference vs {best_demo}",
                    "observed_difference_note": obs_a})
    m_sens = scr.nested_calls_matched_sensitivity(dpred, tp, fp, demo_score)
    b_call = scr.nested_calls(demo_score, tp, fp)["call"]
    rep = paired_metric_replicates(tp, m_sens["call"], b_call, "specificity")
    se = pw.bootstrap_se(rep)
    n_an, n_non = int(tp.sum()), int((~tp).sum())
    ppg_spec = block("ppg_spec", se, scr.MARGIN,
                     "0.10 = the clinically meaningful margin pre-declared in Phase 9A",
                     {"metric": "specificity gain at matched sensitivity",
                      "n_non_anaemic": n_non,
                      "referrals_avoided_at_mde_80": pw.subjects_moved(
                          pw.mde(se, 0.80), n_non)})
    print(f"  AUROC vs {best_demo}: SE {a_se:.4f} -> MDE80 {ppg_au['mde_80']:.3f} "
          f"({ppg_au['mde_90']:.3f} at 90%) -> {ppg_au['verdict']}")
    print(f"  spec-gain SE {se:.4f} -> MDE80 {ppg_spec['mde_80']:.3f} -> {ppg_spec['verdict']}")
    R["arms"]["ppg"] = {"n": int(len(yp)), "n_anaemic": n_an, "n_non_anaemic": n_non,
                        "prevalence": float(tp.mean()), "mae_vs_sex_alone": ppg_mae,
                        "auroc": ppg_au, "specificity_at_matched_sensitivity": ppg_spec}

    (OUT / "power.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
    print(f"\nresults -> {OUT / 'power.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
