"""Phase 9E Part B - the sample a confirmatory study would need.

Phase 9D found three comparisons UNDERPOWERED and stopped there. An UNDERPOWERED verdict
without a required n is a complaint; with one it is a specification. This script turns
each into a number a study designer can act on.

Pre-declared in CLAUDE.md (Phase 9E, 2026-09-21) before this ran:

  * the target is the pre-declared 0.10 margin, at 80% and 90% power;
  * required group size = observed group size x (observed MDE / 0.10) ** (1 / slope);
  * **the slope is MEASURED, not assumed** - this project's own data is subsampled at
    several fractions, the whole nested-operating-point and paired-bootstrap pipeline is
    re-run at each, and log SE is fitted against log n;
  * required n is reported FIRST as a minimum count in the group that carries the metric
    (non-anaemic for a specificity, anaemic for a sensitivity), because Phase 9D
    established that the cross-site failure is a composition problem, not a raw-n one;
  * Phase 9D's MDEs must reproduce before any new number is computed.

    .\\.venv\\Scripts\\python.exe scripts\\required_sample_size_phase9e.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hemosight.evaluation import power as pw            # noqa: E402
from hemosight.evaluation import screening as scr       # noqa: E402
from hemosight.io import paths                          # noqa: E402
from screening_reframe_metrics_phase9a import (IMG_PRED, PPG_DEEP, PPG_FEAT,  # noqa: E402
                               XS_PRED, folds_for, ridge_cv)
from power_analysis_phase9d import (paired_auroc_replicates,      # noqa: E402
                           paired_metric_replicates)

OUT = paths.INTERIM / "phase9e"
P9D = paths.INTERIM / "phase9d" / "power.json"
TOL = 5e-3
TARGET = scr.MARGIN                      # 0.10, pre-declared in Phase 9A
SUB_FRACTIONS = (0.40, 0.55, 0.70, 0.85, 1.00)
SUB_REPEATS = 6
SUB_SEED = 20260921
REFERENCE_SLOPE = 0.5       # the ordinary 1/sqrt(n) rate
FIT_R2_FLOOR = 0.50         # below this the measured slope is not itself well measured


# --------------------------------------------------------------------------- #
# one comparison, reduced to the three things Part B needs
# --------------------------------------------------------------------------- #
def spec_se(score: np.ndarray, base: np.ndarray, truth: np.ndarray) -> float:
    """Bootstrap SE of the specificity gain at matched sensitivity, on these subjects."""
    folds = folds_for(len(truth))
    m = scr.nested_calls_matched_sensitivity(score, truth, folds, base)
    b = scr.nested_calls(base, truth, folds)["call"]
    return pw.bootstrap_se(paired_metric_replicates(truth, m["call"], b, "specificity"))


def sens_se(score: np.ndarray, base: np.ndarray, truth: np.ndarray) -> float:
    """Bootstrap SE of the sensitivity gain at matched specificity."""
    folds = folds_for(len(truth))
    m = scr.nested_calls_matched_specificity(score, truth, folds, base)
    b = scr.nested_calls(base, truth, folds)["call"]
    return pw.bootstrap_se(paired_metric_replicates(truth, m["call"], b, "sensitivity"))


def auroc_se(score: np.ndarray, base: np.ndarray, truth: np.ndarray) -> float:
    return pw.bootstrap_se(paired_auroc_replicates(truth, score, base))


def measure_scaling(se_fn, score, base, truth, carrier: str, label: str) -> dict:
    """Subsample subjects, re-run the whole pipeline, fit log SE against log n.

    Subsampling is stratified on the anaemia label so prevalence is held fixed and the
    fitted slope describes n, not composition. The per-subject model scores are held
    fixed - the question is the sampling variability of the metric difference given the
    models, which is what the MDE uses.
    """
    rng = np.random.default_rng(SUB_SEED)
    an, non = np.flatnonzero(truth), np.flatnonzero(~truth)
    ns, ses = [], []
    for f in SUB_FRACTIONS:
        for _ in range(1 if f == 1.0 else SUB_REPEATS):
            if f == 1.0:
                idx = np.arange(len(truth))
            else:
                k_a = max(4, int(round(f * an.size)))
                k_n = max(4, int(round(f * non.size)))
                idx = np.sort(np.concatenate([rng.choice(an, k_a, replace=False),
                                              rng.choice(non, k_n, replace=False)]))
            t = truth[idx]
            if t.sum() < 4 or (~t).sum() < 4:
                continue
            se = se_fn(score[idx], base[idx], t)
            if not np.isfinite(se) or se <= 0:
                continue
            ns.append(int(t.sum() if carrier == "anaemic" else (~t).sum()))
            ses.append(se)
    fit = pw.scaling_slope(np.array(ns), np.array(ses))
    fit.update({"carrier_group": carrier, "label": label,
                "points": [{"n_carrier": int(n), "se": float(s)} for n, s in zip(ns, ses)]})
    print(f"  scaling [{label}] on {carrier}: slope {fit['slope']:.3f} "
          f"(R2 {fit['r2']:.3f}, {fit['n_points']} points, n {min(ns)}-{max(ns)})")
    return fit


def required_block(name: str, mde80: float, mde90: float, n_carrier: int, carrier: str,
                   prevalence: float, fit: dict, extra: dict | None = None) -> dict:
    """Required group size at the 0.10 margin, and the cohorts that deliver it.

    Both the MEASURED-slope figure and the ordinary 1/sqrt(n) reference are reported,
    always. Where the subsample fit is itself weak - which happens exactly where the
    carrier group is smallest, and is a second symptom of the same problem - the
    reference figure is the headline and the measured one is kept beside it. That rule
    is applied by R2, not by which answer is preferred.
    """
    slope, r2 = fit["slope"], fit["r2"]
    trusted = bool(np.isfinite(r2) and r2 >= FIT_R2_FLOOR)
    out = {"comparison": name, "carrier_group": carrier, "n_carrier_observed": n_carrier,
           "mde_80_observed": mde80, "mde_90_observed": mde90, "target": TARGET,
           "prevalence_observed": prevalence,
           "slope_measured": slope, "slope_fit_r2": r2,
           "slope_fit_is_trustworthy": trusted,
           "headline_slope": slope if trusted else REFERENCE_SLOPE,
           "headline_basis": ("measured slope" if trusted else
                              f"1/sqrt(n) reference - the measured slope's fit is weak "
                              f"(R2 {r2:.2f} on {fit['n_points']} points spanning "
                              f"n {min(p['n_carrier'] for p in fit['points'])}-"
                              f"{max(p['n_carrier'] for p in fit['points'])})")}
    for tag, s in (("measured", slope), ("reference", REFERENCE_SLOPE)):
        for p, m in (("80", mde80), ("90", mde90)):
            req = pw.required_group_n(n_carrier, m, TARGET, s)
            out[f"{tag}_required_carrier_{p}"] = req
            out[f"{tag}_required_total_at_observed_prevalence_{p}"] = pw.total_n_for_group(
                req, prevalence, carrier)
            out[f"{tag}_required_total_at_balanced_prevalence_{p}"] = pw.total_n_for_group(
                req, 0.50, carrier)
            out[f"{tag}_multiple_of_observed_{p}"] = (float(req / n_carrier) if n_carrier
                                                      else float("nan"))
    head = "measured" if trusted else "reference"
    for p in ("80", "90"):
        out[f"headline_required_carrier_{p}"] = out[f"{head}_required_carrier_{p}"]
        out[f"headline_required_total_at_observed_prevalence_{p}"] = out[
            f"{head}_required_total_at_observed_prevalence_{p}"]
        out[f"headline_required_total_at_balanced_prevalence_{p}"] = out[
            f"{head}_required_total_at_balanced_prevalence_{p}"]
    if extra:
        out.update(extra)
    print(f"  {name}\n    {carrier} {n_carrier} -> "
          f"{out['headline_required_carrier_80']:.0f} at 80% "
          f"({out['headline_required_carrier_90']:.0f} at 90%) [{out['headline_basis']}]; "
          f"cohort at the observed prevalence "
          f"{out['headline_required_total_at_observed_prevalence_80']:.0f}, balanced "
          f"{out['headline_required_total_at_balanced_prevalence_80']:.0f}")
    if not trusted:
        print(f"    measured-slope figure kept beside it: "
              f"{out['measured_required_carrier_80']:.0f} at 80%")
    return out


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    p9d = json.loads(P9D.read_text(encoding="utf-8"))["arms"]
    R: dict = {"declared_in": "CLAUDE.md Phase 9E section, committed before this ran",
               "target_margin": TARGET,
               "method": {"required_group_n": "n_obs * (MDE_obs / 0.10) ** (1 / slope)",
                          "slope": "MEASURED by subsampling, not assumed",
                          "subsample_fractions": list(SUB_FRACTIONS),
                          "subsample_repeats": SUB_REPEATS, "subsample_seed": SUB_SEED,
                          "stratified": "on the anaemia label, so prevalence is held fixed",
                          "reference_slope": REFERENCE_SLOPE,
                          "fit_r2_floor": FIT_R2_FLOOR,
                          "caveats": [
                              "the per-subject model scores are held fixed while subjects "
                              "are subsampled; a real smaller study would also retrain, and "
                              "its model would be worse, so these are LOWER bounds on n",
                              "the SE of a proportion depends mildly on the true effect "
                              "size, which is not corrected for (Phase 9D caveat, carried)",
                              "a larger study drawn from more sites would have a different "
                              "per-subject variance; this extrapolates THIS cohort"]},
               "reproduction": {}, "scaling": {}, "required": {}}

    # ------------------------------------------------------- imaging, within site
    d = pd.read_csv(IMG_PRED)
    y = d["y_true"].to_numpy(float)
    male = (d["sex"].astype(str).str.strip().str.upper() == "M").to_numpy()
    age = d["age"].to_numpy(float)
    site = d["site"].to_numpy(str)
    truth = y < scr.who_threshold(male, age)
    folds = folds_for(len(y))
    demo3 = np.stack([(site == "eyes_defy:Italy").astype(float), age,
                      male.astype(float)], 1)
    base = ridge_cv(demo3, y, folds)
    cnn = d["y_pred"].to_numpy(float)

    print("=== 0. Reproducing Phase 9D's MDEs before computing anything new ===")
    rec = p9d["imaging_screening"]["image_cnn"]
    checks = [("imaging_screening_specificity", pw.mde(spec_se(cnn, base, truth), 0.80),
               rec["specificity_at_matched_sensitivity"]["mde_80"]),
              ("imaging_screening_sensitivity", pw.mde(sens_se(cnn, base, truth), 0.80),
               rec["sensitivity_at_matched_specificity"]["mde_80"])]
    for k, got, ref in checks:
        assert abs(got - ref) < TOL, (k, got, ref)
        R["reproduction"][k] = {"recorded": ref, "reproduced": float(got), "ok": True}
        print(f"  {k:36s} recorded {ref:.4f}  reproduced {got:.4f}")

    print("\n=== 1. Measuring the SE scaling (subsampling this project's own data) ===")
    R["scaling"]["imaging_screening_specificity"] = measure_scaling(
        spec_se, cnn, base, truth, "non_anaemic", "imaging within site, specificity")
    R["scaling"]["imaging_screening_sensitivity"] = measure_scaling(
        sens_se, cnn, base, truth, "anaemic", "imaging within site, sensitivity")

    print("\n=== 2. Required sample size at the 0.10 margin ===")
    prev = float(truth.mean())
    R["required"]["imaging_screening_specificity"] = required_block(
        "imaging screening within site - specificity at matched sensitivity",
        rec["specificity_at_matched_sensitivity"]["mde_80"],
        rec["specificity_at_matched_sensitivity"]["mde_90"],
        int((~truth).sum()), "non_anaemic", prev,
        R["scaling"]["imaging_screening_specificity"],
        {"power_at_the_margin_now":
         rec["specificity_at_matched_sensitivity"]["power_at_the_yardstick"]})
    R["required"]["imaging_screening_sensitivity"] = required_block(
        "imaging screening within site - sensitivity at matched specificity",
        rec["sensitivity_at_matched_specificity"]["mde_80"],
        rec["sensitivity_at_matched_specificity"]["mde_90"],
        int(truth.sum()), "anaemic", prev,
        R["scaling"]["imaging_screening_sensitivity"],
        {"power_at_the_margin_now":
         rec["sensitivity_at_matched_specificity"]["power_at_the_yardstick"]})

    # ------------------------------------------------------------ cross-site
    print("\n=== 3. Cross-site, per direction - the composition problem ===")
    xs = pd.read_csv(XS_PRED)
    for direction, part in xs.groupby("direction"):
        part = part[part["split"] == "test"].reset_index(drop=True)
        yy = part["y_true"].to_numpy(float)
        mm = (part["sex"].astype(str).str.strip().str.upper() == "M").to_numpy()
        aa = part["age"].to_numpy(float)
        tt = yy < scr.who_threshold(mm, aa)
        pred = part["y_pred"].to_numpy(float)
        demo = ridge_cv(np.stack([aa, mm.astype(float)], 1), yy, folds_for(len(yy)))
        recd = p9d["imaging_cross_site"][direction]["specificity_at_matched_sensitivity"]
        got = pw.mde(spec_se(pred, demo, tt), 0.80)
        assert abs(got - recd["mde_80"]) < TOL, (direction, got, recd["mde_80"])
        R["reproduction"][f"cross_site_{direction}"] = {
            "recorded": recd["mde_80"], "reproduced": float(got), "ok": True}
        print(f"  {direction}: recorded {recd['mde_80']:.4f}  reproduced {got:.4f}")
        R["scaling"][f"cross_site_{direction}"] = measure_scaling(
            spec_se, pred, demo, tt, "non_anaemic", f"cross-site {direction}")
        R["required"][f"cross_site_{direction}"] = required_block(
            f"cross-site {direction} - specificity at matched sensitivity",
            recd["mde_80"], recd["mde_90"], int((~tt).sum()), "non_anaemic",
            float(tt.mean()), R["scaling"][f"cross_site_{direction}"],
            {"n_test_observed": int(len(yy)), "n_anaemic_observed": int(tt.sum()),
             "power_at_the_margin_now": recd["power_at_the_yardstick"]})

    # ------------------------------------------------------------ PPG AUROC
    print("\n=== 4. PPG AUROC - the other uninformative comparison ===")
    deep = pd.read_csv(PPG_DEEP)
    feat = pd.read_csv(PPG_FEAT)
    feat = feat[np.isfinite(feat.hb_g_dl)].reset_index(drop=True)
    yp = deep["y_true"].to_numpy(float)
    mp = (deep["sex"].astype(str).str.strip().str.upper() == "M").to_numpy()
    tp = yp < scr.who_threshold(mp, deep["age"].to_numpy(float))
    fp = folds_for(len(yp))
    best = p9d["ppg"]["auroc"]["metric"].split("vs ")[-1]
    demo_x = (feat[["sex"]].to_numpy(float) if best == "sex_only"
              else feat[["age", "sex", "height", "weight"]].to_numpy(float))
    demo_score = ridge_cv(demo_x, yp, fp)
    dpred = deep["y_pred"].to_numpy(float)
    recp = p9d["ppg"]["auroc"]
    got = pw.mde(auroc_se(dpred, demo_score, tp), 0.80)
    assert abs(got - recp["mde_80"]) < TOL, (got, recp["mde_80"])
    R["reproduction"]["ppg_auroc"] = {"recorded": recp["mde_80"],
                                      "reproduced": float(got), "ok": True}
    print(f"  ppg_auroc: recorded {recp['mde_80']:.4f}  reproduced {got:.4f}")
    R["scaling"]["ppg_auroc"] = measure_scaling(auroc_se, dpred, demo_score, tp,
                                                "anaemic", "PPG AUROC")
    R["required"]["ppg_auroc"] = required_block(
        "PPG screening - AUROC difference vs the best demographic baseline",
        recp["mde_80"], recp["mde_90"], int(tp.sum()), "anaemic", float(tp.mean()),
        R["scaling"]["ppg_auroc"],
        {"power_at_the_margin_now": recp["power_at_the_yardstick"],
         "note": "AUROC is carried by the smaller class: 18 anaemic against 234 not"})

    R["elapsed_s"] = time.time() - t0
    (OUT / "required_n.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
    print(f"\nresults -> {OUT / 'required_n.json'} ({R['elapsed_s']:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
