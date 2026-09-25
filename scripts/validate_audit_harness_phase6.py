"""Phase 6, TASK 4: audit the audit tool.

A tool that judges other people's evidence has to be held to the standard it applies.
This script runs HemoSight Audit against inputs whose correct verdict is already known
and reports, as numbers, how often it is right.

Three sources of known truth:

  A. THIS PROJECT'S OWN DATA. Every verdict here is already on the record in CLAUDE.md
     and reports/final_results.md - the 419 shared MD5 hashes, the 1,708 -> 1,067
     group collapse, sex alone at MAE 0.831 beating the PPG model at 1.190, 0 of 51
     features above the mutual-information null, permutation p = 0.978. The harness
     must return the verdict the phase returned.
  B. SYNTHETIC FAULT INJECTION. Inputs built with one known defect each: duplicates
     across a split, a model that is secretly a demographic classifier, a model with no
     signal, a model with genuine signal, a seed-unstable model, an effect carried by a
     handful of subjects, and a subject leaking across a split. Each must be caught by
     the check that exists to catch it. This gives the sensitivity.
  C. CLEAN REPLICATES. Inputs with no injected fault at all, repeated under independent
     seeds. Any FAIL here is a false positive, and the rate is reported whatever it is.

    .\\.venv\\Scripts\\python.exe scripts\\validate_audit_harness_phase6.py
    .\\.venv\\Scripts\\python.exe scripts\\validate_audit_harness_phase6.py --fast

GPU NOTE. The Phase 4.5 deep models are not re-run here and their per-subject
predictions were never written to disk, so the three Phase 5 checks that judge them
(permutation, seed stability, subgroup robustness) are validated at the statistic level
against the numbers recorded in harden.json rather than end to end. The end-to-end run
needs the GPU, which is currently held by the extended permutation job. The gap is
reported rather than papered over; see reports/phase6_audit_harness.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from hemosight.audit import load_predictions, run_audit
from hemosight.audit.registry import BY_ID
from hemosight.audit.stats import empirical_p, mae
from hemosight.io import paths

sys.path.insert(0, str(paths.ROOT / "scripts"))

OUT = paths.INTERIM / "phase6"
SEED = 20260911


def case_seed(name: str) -> int:
    """A stable seed per named case.

    NOT hash(name): Python salts string hashing per process, so a seed derived from it
    changes between runs and the injected faults would not be reproducible - which
    would quietly break the claim in scripts/reproduce_all.py that every stage is
    deterministic given the frozen seed. crc32 is stable across processes and versions.
    """
    return (SEED + zlib.crc32(name.encode("utf-8"))) % (2 ** 31)

# Verdicts already on the record. Sourced from CLAUDE.md RESULTS LOG entries dated
# 2026-09-11 and reports/final_results.md.
RECORDED = {
    "phase1_overlap": dict(
        check="duplicates", verdict="FAIL",
        source="RESULTS LOG 2026-09-11, Phase 1 overlap check: 419 shared MD5",
        note="cp_anemic is contained inside ghana_conj; they are one site"),
    "phase1_groups": dict(
        check="split_integrity", verdict="FAIL",
        source="RESULTS LOG 2026-09-11, Phase 1 splits: 1,708 ids -> 1,067 groups",
        note="a subject-level split would have leaked"),
    "phase4_baseline": dict(
        check="demographic_baseline", verdict="FAIL",
        source="RESULTS LOG 2026-09-11, Phase 4 Task 3: sex alone 0.831 vs PPG 1.190",
        note="sex alone beats the model by 30%"),
    "phase4_proxy": dict(
        check="proxy_probe", verdict="FAIL",
        source="DECISION LOG 2026-09-11: PPG+demographics 0.824 vs demographics 0.831",
        note="the apparent PPG model is a sex classifier"),
    "phase4_5_ceiling": dict(
        check="ceiling", verdict="FAIL",
        source="RESULTS LOG 2026-09-11, Phase 4.5 ceiling: 0 of 51 above the MI null",
        note="the signal is absent from the features, not merely unfound"),
    "phase4_5_permutation": dict(
        check="permutation", verdict="FAIL",
        source="RESULTS LOG 2026-09-11, Phase 4.5 ceiling: permutation p = 0.978",
        note="worse than 97.8% of shuffled-label models"),
    # Phase 6.5 Task 3: the deep model, END TO END on its regenerated predictions.
    "phase5_deep_permutation": dict(
        check="permutation", verdict="PASS",
        source="RESULTS LOG 2026-09-12, Phase 5 extended: p = 0.0041 (floor) at n=240",
        note="distinguishable from chance. The harness permutes labels against FIXED "
             "predictions, a different null from the refitting construction, so its p "
             "is NOT a reproduction of 0.0041; only the verdict is compared"),
    "phase5_deep_seed_stability": dict(
        check="seed_stability", verdict="PASS",
        source="RESULTS LOG 2026-09-11, Phase 5 Task 1: seed SD 0.0069, effect 11.9x",
        note="ten seeds of the selected model, regenerated with the Phase 5 driver"),
    "phase5_deep_subgroup": dict(
        check="subgroup_robustness", verdict="PASS",
        source="RESULTS LOG 2026-09-11, Phase 5 Task 1: 1.1124 -> 1.2258 dropping the best decile",
        note="advantage over the baseline retained on the reduced set"),
    "phase5_deep_baseline": dict(
        check="demographic_baseline", verdict="FAIL",
        source="RESULTS LOG 2026-09-11, Phase 4.5: best deep 1.113 vs sex alone 0.831",
        note="the surviving positive claim still loses to sex alone"),
}


# --------------------------------------------------------------------------- utils
def verdict_of(report, check_id: str) -> tuple[str, str, dict]:
    for r in report.results:
        if r["check_id"] == check_id:
            return r["verdict"], r["headline"], r["measured"]
    return "MISSING", "", {}


def line(tag, expected, got, headline, extra=""):
    ok = "OK " if expected == got else "MISMATCH"
    print(f"  [{ok}] {tag:26s} expected {expected:17s} got {got:17s} {extra}")
    print(f"           {headline[:110]}")
    return expected == got


# ------------------------------------------------------------- A. the project's data
def a_phase1_images(results: list, fast: bool) -> None:
    """Checks 1 and 2 against the Phase 1 overlap and split findings."""
    print("\n=== A1/A2  Phase 1: CP-AnemiC inside Ghana, and the group collapse ===")
    sets = ["cp_anemic", "ghana_conj", "ghana_nail"]
    frames = []
    for s in sets:
        m = pd.read_csv(paths.MANIFESTS / f"{s}.csv")
        if fast:
            m = m.sample(min(len(m), 400), random_state=SEED)
        frames.append(pd.DataFrame({
            "subject_id": s + "::" + m.subject_id.astype(str),
            "y_true": np.arange(len(m), dtype=float) % 7 + 8.0,   # placeholder target
            "y_pred": np.arange(len(m), dtype=float) % 7 + 8.0,
            "split": np.where(m.dataset == "cp_anemic", "test", "train"),
            "image_path": m.file_path,
        }))
    df = pd.concat(frames, ignore_index=True)
    print(f"  {len(df)} images over {df.subject_id.nunique()} nominal subject ids"
          + ("   (--fast subsample)" if fast else ""))

    t0 = time.time()
    inp = load_predictions(df)
    rep = run_audit(inp, checks=["duplicates", "split_integrity"])
    print(f"  hashed and compared in {time.time() - t0:.0f}s")

    v, h, m = verdict_of(rep, "duplicates")
    ok = line("phase1_overlap", "FAIL", v, h,
              f"(cross-split exact groups: {m.get('n_exact_duplicate_groups_crossing_a_split')})")
    results.append({**RECORDED["phase1_overlap"], "case": "phase1_overlap", "ok": ok,
                    "verdict": v, "expected": "FAIL", "measured": m, "headline": h})

    v, h, m = verdict_of(rep, "split_integrity")
    collapse = (f"({m.get('nominal_subject_ids')} ids -> "
                f"{m.get('leakproof_groups')} groups)")
    ok = line("phase1_groups", "FAIL", v, h, collapse)
    results.append({**RECORDED["phase1_groups"], "case": "phase1_groups", "ok": ok,
                    "verdict": v, "expected": "FAIL", "measured": m, "headline": h})


def a_phase4_tabular(results: list) -> None:
    """Checks 3, 4, 5 and 8 against the Phase 4 / 4.5 feature-model findings.

    The predictions are regenerated with Phase 4's own estimator, imported from
    scripts/ppg_hb_estimation_gate_phase4.py rather than reimplemented, so the submission the harness
    audits is the model the phase actually reported on.
    """
    print("\n=== A3-A6  Phase 4 / 4.5: the PPG feature model ===")
    from ppg_hb_estimation_gate_phase4 import build_conditions, evaluate

    d = pd.read_csv(paths.INTERIM / "phase4" / "features.csv")
    d = d[np.isfinite(d.hb_g_dl)].reset_index(drop=True)
    y = d.hb_g_dl.to_numpy()
    conds = build_conditions(d)
    cname, cols = next(iter(conds.items()))
    X = d[cols].to_numpy(dtype=float)
    r = evaluate(X, y, cname)
    print(f"  regenerated {cname}: MAE {r['mae_g_dl']:.3f} g/dL "
          f"(Phase 4 recorded 1.190)")

    feat = d[cols].copy()
    sub = pd.DataFrame({
        "subject_id": d.subject_id.astype(str),
        "y_true": y,
        "y_pred": np.array(r["preds"], dtype=float),
        "age": d.age, "sex": np.where(d.sex.to_numpy() > 0.5, "M", "F"),
    })
    sub = pd.concat([sub, feat], axis=1)

    inp = load_predictions(sub)
    rep = run_audit(inp, checks=["demographic_baseline", "ceiling", "permutation"],
                    options={"permutation": {"n_permutations": 1000}})

    # The proxy finding Phase 4 recorded is about PPG + DEMOGRAPHICS at MAE 0.824,
    # not about PPG alone at 1.190 - the whole point was that adding PPG to
    # demographics did not improve on demographics. That is the submission the proxy
    # check has to be shown against, so it is built separately here.
    demo_cols = ["age", "sex", "height", "weight"]
    Xd = np.hstack([X, d[demo_cols].to_numpy(dtype=float)])
    rd = evaluate(Xd, y, cname + "_plus_demographics")
    print(f"  regenerated {cname}+demographics: MAE {rd['mae_g_dl']:.3f} g/dL "
          f"(Phase 4 recorded 0.824)")
    sub_d = sub.copy()
    sub_d["y_pred"] = np.array(rd["preds"], dtype=float)
    rep_d = run_audit(load_predictions(sub_d), checks=["proxy_probe"])
    v, h, m = verdict_of(rep_d, "proxy_probe")
    ok = line("phase4_proxy", RECORDED["phase4_proxy"]["verdict"], v, h)
    results.append({**RECORDED["phase4_proxy"], "case": "phase4_proxy", "ok": ok,
                    "verdict": v, "expected": RECORDED["phase4_proxy"]["verdict"],
                    "measured": m, "headline": h})

    for case, cid in (("phase4_baseline", "demographic_baseline"),
                      ("phase4_5_ceiling", "ceiling"),
                      ("phase4_5_permutation", "permutation")):
        v, h, m = verdict_of(rep, cid)
        ok = line(case, RECORDED[case]["verdict"], v, h)
        results.append({**RECORDED[case], "case": case, "ok": ok, "verdict": v,
                        "expected": RECORDED[case]["verdict"], "measured": m,
                        "headline": h})


def a_phase5_statistics(results: list) -> None:
    """The Phase 5 numbers, reproduced at statistic level.

    The deep model's per-subject predictions were never written to disk and
    regenerating them needs the GPU, which is reserved. What can be checked without it
    is that the harness's own statistics reproduce the recorded figures exactly.
    """
    print("\n=== A7  Phase 5 hardening statistics (no GPU) ===")
    h = json.loads((paths.INTERIM / "phase5" / "harden.json").read_text(
        encoding="utf-8"))
    pa = h["permutation_selection_aware"]
    real = h["real_mae_seed_averaged"]

    # Recorded: n=60, zero draws at or below the real value, p = 0.01639 = 1/61.
    draws = np.full(pa["n"], pa["null_mean"])            # all above the real value
    s = empirical_p(draws, real)
    ok_p = (abs(s["p_empirical"] - pa["p_empirical"]) < 1e-6 and s["at_floor"])
    print(f"  [{'OK ' if ok_p else 'MISMATCH'}] empirical p at n={pa['n']}: harness "
          f"{s['p_empirical']:.5f} vs recorded {pa['p_empirical']:.5f}, "
          f"at_floor={s['at_floor']}")
    results.append({"case": "phase5_empirical_p_floor", "ok": bool(ok_p),
                    "verdict": "reproduced" if ok_p else "mismatch",
                    "expected": "reproduced",
                    "check": "permutation (statistic)",
                    "source": "RESULTS LOG 2026-09-11, Phase 5 Task 1: p = 0.01639 at n=60",
                    "note": "the reported p is the floor 1/(n+1), not a measurement",
                    "measured": {k: s[k] for k in ("p_empirical", "p_floor",
                                                   "at_floor", "n")},
                    "headline": f"p = {s['p_empirical']:.5f}, floor {s['p_floor']:.5f}"})

    ss = h["seed_stability"]
    gap = pa["null_mean"] - real
    ratio = gap / ss["sd"]
    ok_r = abs(ratio - 11.9) < 0.6
    print(f"  [{'OK ' if ok_r else 'MISMATCH'}] seed ratio: harness {ratio:.1f}x vs "
          f"recorded 11.9x (gap {gap:.4f}, SD {ss['sd']:.4f})")
    results.append({"case": "phase5_seed_ratio", "ok": bool(ok_r),
                    "verdict": "reproduced" if ok_r else "mismatch",
                    "expected": "reproduced", "check": "seed_stability (statistic)",
                    "source": "RESULTS LOG 2026-09-11: SD 0.0069, gap 0.0815, 11.9x",
                    "note": "the effect must be large against seed noise",
                    "measured": {"ratio": round(ratio, 2), "seed_sd": ss["sd"],
                                 "gap": round(gap, 5)},
                    "headline": f"effect is {ratio:.1f}x the seed SD"})


def a_phase5_deep_end_to_end(results: list) -> bool:
    """Phase 6.5 Task 3. The Phase 4.5/5 deep model's per-subject predictions,
    regenerated by scripts/deep_ppg_predictions_dump_phase6_5.py (10 seeds + 6 candidates),
    driven through the three Phase 5 checks and the demographic baseline. Returns
    False (and records nothing) if the file is absent, so the CPU-only path of this
    script still runs."""
    p = paths.INTERIM / "phase6" / "known_truth" / "phase5_deep_model.csv"
    if not p.exists():
        print("\n=== A8  Phase 5 deep model end to end: SKIPPED (run "
              "scripts/deep_ppg_predictions_dump_phase6_5.py) ===")
        return False
    print("\n=== A8  Phase 5 deep model, END TO END on regenerated predictions ===")
    df = pd.read_csv(p)
    inp = load_predictions(df)
    rep = run_audit(inp, checks=["demographic_baseline", "permutation", "seed_stability",
                                 "subgroup_robustness"],
                    options={"permutation": {"n_permutations": 2000}})
    for case, cid in (("phase5_deep_baseline", "demographic_baseline"),
                      ("phase5_deep_permutation", "permutation"),
                      ("phase5_deep_seed_stability", "seed_stability"),
                      ("phase5_deep_subgroup", "subgroup_robustness")):
        v, h, m = verdict_of(rep, cid)
        ok = line(case, RECORDED[case]["verdict"], v, h)
        results.append({**RECORDED[case], "case": case, "ok": ok, "verdict": v,
                        "expected": RECORDED[case]["verdict"], "measured": m,
                        "headline": h})
    return True


# ------------------------------------------------------------ B. injected faults
def _tiny_image(path: Path, rng, size: int = 32) -> None:
    from PIL import Image
    a = rng.integers(0, 255, (size, size, 3), dtype=np.uint8)
    Image.fromarray(a).save(path)


def synth(n: int, rng, kind: str, image_dir: Path | None = None) -> pd.DataFrame:
    """A submission with exactly one known defect, or none for kind='clean'."""
    sex = rng.integers(0, 2, n)
    signal = rng.normal(0, 1, n)
    y = 13.0 + 1.2 * sex + 0.8 * signal + rng.normal(0, 0.6, n)
    sid = [f"s{i:04d}" for i in range(n)]
    split = np.where(np.arange(n) < int(0.7 * n), "train", "test")

    if kind == "no_signal":
        pred = np.full(n, y.mean()) + rng.normal(0, 0.9, n)
    elif kind == "demographic_proxy":
        pred = 13.0 + 1.2 * sex + rng.normal(0, 0.25, n)
    elif kind == "few_subjects":
        # The advantage lives in 8% of subjects; everyone else gets the mean.
        pred = np.full(n, y.mean())
        lucky = rng.choice(n, size=max(3, int(0.08 * n)), replace=False)
        pred[lucky] = y[lucky]
        pred = pred + rng.normal(0, 0.05, n)
    else:                                    # clean / genuine_signal / duplicates
        pred = 13.0 + 0.9 * sex + 0.7 * signal + rng.normal(0, 0.7, n)

    df = pd.DataFrame({
        "subject_id": sid, "y_true": y, "y_pred": pred, "split": split,
        "sex": np.where(sex == 1, "M", "F"),
        "age": rng.integers(18, 75, n),
        "signal_feature": signal + rng.normal(0, 0.4, n),
        "noise_feature": rng.normal(0, 1, n),
    })

    # A seed changes a whole training run, so it moves every prediction together. Adding
    # independent per-row noise instead barely moves the MAE at all - an average over
    # hundreds of subjects absorbs it - and an earlier version of this generator failed
    # to produce an unstable model for that reason.
    shift_sd = 0.30 if kind == "seed_unstable" else 0.0
    for k in range(5):
        df[f"y_pred_seed__{k}"] = (df.y_pred + rng.normal(0, shift_sd)
                                   + rng.normal(0, 0.01, n))
    if kind == "seed_unstable":
        df["y_pred"] = df["y_pred_seed__0"]

    if image_dir is not None:
        image_dir.mkdir(parents=True, exist_ok=True)
        rel = []
        for i, s in enumerate(sid):
            p = image_dir / f"{s}.png"
            if not p.exists():
                _tiny_image(p, rng)
            rel.append(p.name)
        df["image_path"] = rel
        if kind == "duplicates_across_split":
            # Copy three TRAIN images into the TEST side under new subject ids: the
            # Phase 1 failure mode, byte-identical content on both sides of a split.
            extra = []
            for i in range(3):
                src = image_dir / f"{sid[i]}.png"
                dst = image_dir / f"leak{i}.png"
                dst.write_bytes(src.read_bytes())
                extra.append({**df.iloc[i].to_dict(),
                              "subject_id": f"leak{i}", "split": "test",
                              "image_path": dst.name})
            df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)
        elif kind == "subject_across_split":
            extra = [{**df.iloc[i].to_dict(), "split": "test"} for i in range(5)]
            df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)
    return df


FAULTS = {
    "duplicates_across_split": ("duplicates",
                                "byte-identical images on both sides of the split"),
    "subject_across_split": ("split_integrity",
                             "the same subject_id in train and test"),
    "demographic_proxy": ("proxy_probe",
                          "a model that is a sex classifier with a decoration"),
    "no_signal": ("permutation", "a model with no association to the target"),
    "seed_unstable": ("seed_stability",
                      "a model whose score moves with the seed by more than its effect"),
    "few_subjects": ("subgroup_robustness",
                     "an advantage carried by 8% of subjects"),
}


def b_injected(results: list, n: int, perms: int) -> None:
    print("\n=== B  injected faults: does the right check catch each one? ===")
    img = OUT / "synthetic_images"
    for kind, (target, desc) in FAULTS.items():
        rng = np.random.default_rng(case_seed(kind))
        df = synth(n, rng, kind, image_dir=img)
        inp = load_predictions(df, image_dir=img)
        rep = run_audit(inp, checks=[target],
                        options={"permutation": {"n_permutations": perms}})
        v, h, m = verdict_of(rep, target)
        ok = line(kind, "FAIL", v, h)
        results.append({"case": f"inject::{kind}", "ok": ok, "verdict": v,
                        "expected": "FAIL", "check": target, "note": desc,
                        "source": "synthetic fault injection", "measured": m,
                        "headline": h})

    # A model with genuine signal must NOT be called out by the permutation test.
    rng = np.random.default_rng(case_seed("genuine_signal"))
    df = synth(n, rng, "genuine_signal")
    rep = run_audit(load_predictions(df), checks=["permutation"],
                    options={"permutation": {"n_permutations": perms}})
    v, h, m = verdict_of(rep, "permutation")
    ok = line("genuine_signal", "PASS", v, h)
    results.append({"case": "inject::genuine_signal", "ok": ok, "verdict": v,
                    "expected": "PASS", "check": "permutation",
                    "note": "a real effect must survive the permutation test",
                    "source": "synthetic positive control", "measured": m,
                    "headline": h})


# ------------------------------------------------------------- C. clean replicates
def c_clean(results: list, n: int, replicates: int, perms: int) -> dict:
    print(f"\n=== C  {replicates} clean replicates: how often does the tool cry wolf? ===")
    img = OUT / "clean_images"
    false_fail: dict[str, int] = {}
    runs = 0
    for rep_i in range(replicates):
        rng = np.random.default_rng(4000 + rep_i)
        df = synth(n, rng, "clean", image_dir=img)
        inp = load_predictions(df, image_dir=img)
        rep = run_audit(inp, options={"permutation": {"n_permutations": perms}})
        for r in rep.results:
            runs += 1
            if r["verdict"] == "FAIL":
                false_fail[r["check_id"]] = false_fail.get(r["check_id"], 0) + 1
        print(f"  replicate {rep_i + 1}/{replicates}: "
              f"{rep.counts['FAIL']} FAIL, {rep.counts['INSUFFICIENT_DATA']} "
              f"INSUFFICIENT, {rep.counts['PASS']} PASS", flush=True)
    total_fp = sum(false_fail.values())
    print(f"  false FAILs: {total_fp} of {runs} check-runs "
          f"({total_fp / max(1, runs):.1%})")
    for k, v in sorted(false_fail.items()):
        print(f"    {k}: {v}/{replicates}")
    results.append({"case": "clean_replicates", "ok": total_fp == 0,
                    "verdict": f"{total_fp} false FAIL of {runs} check-runs",
                    "expected": "0 false FAIL", "check": "all",
                    "note": "no fault was injected in any of these",
                    "source": "synthetic clean control",
                    "measured": {"replicates": replicates, "check_runs": runs,
                                 "false_fail_total": total_fp,
                                 "false_fail_by_check": false_fail},
                    "headline": f"{total_fp / max(1, runs):.2%} false-positive rate"})
    return {"replicates": replicates, "check_runs": runs, "false_fail_total": total_fp,
            "false_fail_by_check": false_fail,
            "false_positive_rate": total_fp / max(1, runs)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true",
                    help="subsample the image corpora and cut the replicate count")
    ap.add_argument("--n", type=int, default=240)
    ap.add_argument("--replicates", type=int, default=20)
    ap.add_argument("--perms", type=int, default=1000)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    t0 = time.time()
    a_phase1_images(results, args.fast)
    a_phase4_tabular(results)
    a_phase5_statistics(results)
    deep_e2e = a_phase5_deep_end_to_end(results)
    b_injected(results, args.n, args.perms)
    reps = 5 if args.fast else args.replicates
    fp = c_clean(results, args.n, reps, args.perms)

    known = [r for r in results if r["case"] != "clean_replicates"]
    n_ok = sum(1 for r in known if r["ok"])
    sensitivity_cases = [r for r in known if r["expected"] == "FAIL"]
    n_caught = sum(1 for r in sensitivity_cases if r["ok"])

    summary = {
        "known_truth_cases": len(known),
        "reproduced": n_ok,
        "agreement_rate": n_ok / max(1, len(known)),
        "fault_cases": len(sensitivity_cases),
        "faults_caught": n_caught,
        "sensitivity": n_caught / max(1, len(sensitivity_cases)),
        "false_positive": fp,
        "not_validated_end_to_end": [] if deep_e2e else [
            "permutation, seed stability and subgroup robustness against the Phase 4.5 "
            "DEEP model: data/interim/phase6/known_truth/phase5_deep_model.csv is absent; "
            "run scripts/deep_ppg_predictions_dump_phase6_5.py (GPU, ~7 min) and re-run this."],
        "deep_model_validated_end_to_end": deep_e2e,
        "seconds": round(time.time() - t0, 1),
    }
    print("\n=== SUMMARY ===")
    print(f"  known-truth cases reproduced : {n_ok}/{len(known)} "
          f"({summary['agreement_rate']:.0%})")
    print(f"  sensitivity to injected faults: {n_caught}/{len(sensitivity_cases)} "
          f"({summary['sensitivity']:.0%})")
    print(f"  false-positive rate           : {fp['false_positive_rate']:.2%} "
          f"({fp['false_fail_total']} of {fp['check_runs']} check-runs)")
    for miss in [r for r in known if not r["ok"]]:
        print(f"  MISMATCH: {miss['case']} expected {miss['expected']} got "
              f"{miss['verdict']}")

    (OUT / "harness_validation.json").write_text(
        json.dumps({"summary": summary, "cases": results}, indent=2, default=str),
        encoding="utf-8")
    print(f"\nresults -> {OUT / 'harness_validation.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
