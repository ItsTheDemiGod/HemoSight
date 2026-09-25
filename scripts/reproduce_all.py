"""Single entry point: reproduce the entire HemoSight result set from raw data.

    .\\.venv\\Scripts\\python.exe scripts\\reproduce_all.py            # everything
    .\\.venv\\Scripts\\python.exe scripts\\reproduce_all.py --fast     # skip slow stages
    .\\.venv\\Scripts\\python.exe scripts\\reproduce_all.py --list     # show the plan

Every stage is deterministic given the frozen seed in `configs/phase1_splits.yaml`
(20260911), with two documented exceptions noted in the STAGES table below.

RUNTIME on the reference machine (RTX 4060 8 GB, Python 3.12):
    fast subset   ~10 minutes   (MEASURED: 22/22 stages in 10.3 min)
    full          ~12 hours, dominated by the Phase 5 permutation tests (270 CV runs)

REPRODUCTION FIDELITY, verified after a clean --fast run:
    Phase 3 gate MAE          3.893  exact
    Phase 4 four-wavelength   1.190  exact
    Phase 4 sex-alone         0.831  exact
    Phase 4.5 permutation p   0.978  exact
    Phase 2 yellowing 10%     4.40   exact
    Phase 4.5 best deep MAE   1.111 vs 1.113 reported - within the measured seed SD
                              (0.0069), the only stage that does not reproduce bit-exact

Nothing here writes to `data/raw/`, which is read-only throughout.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass

from hemosight.io import paths


@dataclass
class Stage:
    name: str
    script: str
    minutes: float          # approximate, reference machine
    slow: bool = False
    note: str = ""


STAGES = [
    Stage("Phase 1  manifests", "dataset_manifests_phase1.py", 1.5,
          note="reads data/raw only; deterministic"),
    Stage("Phase 1  overlap check", "participant_overlap_check_phase1.py", 12, slow=True,
          note="MD5/pHash/dHash + GPU embeddings; caches to data/interim/overlap"),
    Stage("Phase 1  splits", "patient_level_splits_phase1.py", 0.2,
          note="seed 20260911; leak check fails the script on violation"),
    Stage("Phase 1.5 label arbitration", "ghana_label_arbitration_phase1_5.py", 0.3,
          note="writes hb_label_trusted into every manifest"),
    Stage("Phase 1.5 original search", "search_uncropped_originals_phase1_5.py", 6, slow=True,
          note="full scan of 9,450 images + RAR5 header parse"),
    Stage("Phase 1  audit report", "data_audit_report_phase1.py", 1.5),
    Stage("Phase 1  summary report", "data_summary_report_phase1.py", 0.2),
    Stage("Phase 1  figures", "data_audit_figures_phase1.py", 0.5,
          note="writes reports/figures (gitignored: dataset-derived pixels)"),
    Stage("Phase 1.5 remediation report", "remediation_report_phase1_5.py", 0.1),
    Stage("Phase 2  segmentation training", "train_sclera_segmentation_phase2.py", 160, slow=True,
          note="NON-DETERMINISTIC: cuDNN autotune. Sclera IoU reproduces to ~0.005"),
    Stage("Phase 2  N1a nus8", "illuminant_estimation_nus8_phase2.py", 90, slow=True,
          note="deterministic; classical baselines over 1,265 16-bit PNGs"),
    Stage("Phase 2  N1b self-consistency", "sclera_reference_selfconsistency_phase2.py", 50, slow=True),
    Stage("Phase 2  segmentation eval", "eval_sclera_segmentation_phase2.py", 25, slow=True),
    Stage("Phase 2  sensitivity", "sclera_reference_sensitivity_phase2.py", 5),
    Stage("Phase 2  report + figures", "illuminant_calibration_report_phase2.py", 0.2),
    Stage("Phase 2  figures", "illuminant_calibration_figures_phase2.py", 0.3),
    Stage("Phase 2.5 census", "specular_highlight_census_phase2_5.py", 12, slow=True),
    Stage("Phase 2.5 evaluation", "specular_illuminant_evaluation_phase2_5.py", 67, slow=True),
    Stage("Phase 2.5 report", "specular_rescue_report_phase2_5.py", 0.1),
    Stage("Phase 2.5 figures", "specular_rescue_figures_phase2_5.py", 0.2),
    Stage("Phase 3  Task 0 gate", "tissue_simulator_gate_phase3.py", 3,
          note="deterministic; uses sourced optical constants"),
    Stage("Phase 3  empirical signal", "empirical_colour_hb_signal_phase3.py", 1.5,
          note="MEASURES the colour-per-g/dL signal from 215 Eyes-Defy subjects; deterministic (seed 20260911); replaces a hard-coded 0.70 (Phase 6.5)"),
    Stage("Phase 3  report", "tissue_simulator_gate_report_phase3.py", 0.1),
    Stage("Phase 3.5 cancellation", "illuminant_ratio_cancellation_phase3_5.py", 34, slow=True),
    Stage("Phase 3.5 stability", "sclera_reference_stability_phase3_5.py", 20, slow=True),
    Stage("Phase 3.5 report", "ratio_reformulation_report_phase3_5.py", 0.1),
    Stage("Phase 4  Gate A", "ppg_acdc_cancellation_gate_phase4.py", 0.5,
          note="caches data/interim/phase4/features.csv"),
    Stage("Phase 4  Gate B + baselines", "ppg_hb_estimation_gate_phase4.py", 0.5),
    Stage("Phase 4  report", "ppg_gate_report_phase4.py", 0.1),
    Stage("Phase 4.5 deep sweep", "ppg_deep_models_phase4_5.py", 3,
          note="NON-DETERMINISTIC: cuDNN. MAE reproduces to ~0.01 (seed SD measured)"),
    Stage("Phase 4.5 ceiling", "ppg_ceiling_analysis_phase4_5.py", 4),
    Stage("Phase 4.5 report", "deep_ppg_report_phase4_5.py", 0.1),
    Stage("Phase 5  hardening", "permutation_hardening_phase5.py", 220, slow=True,
          note="260 permutation runs; the dominant cost of a full reproduction"),
    Stage("Phase 5  final results", "final_results_report_phase5.py", 0.2),
    # Phase 6 is CPU and disk only. The harness validation is included because it is a
    # RESULT - the harness's own sensitivity and false-positive rate - and results in
    # this project are reproducible or they are not reported. The extended Phase 5
    # permutation run is deliberately NOT a stage: it is a ~10 h GPU job whose figure
    # has not been consolidated, and adding it before then would misrepresent the plan.
    Stage("Phase 6  sample submissions", "make_sample_submissions_phase6.py", 0.6,
          note="regenerates app/backend/sample_data (tracked, synthetic) and the "
               "real-data known-truth inputs under data/ (not tracked)"),
    Stage("Phase 6  audit harness validation", "validate_audit_harness_phase6.py", 1.2,
          note="MEASURED 58 s: hashes 9,232 images, injects 7 known faults, runs 20 "
               "clean replicates; CPU and disk only"),
    Stage("Phase 6  audit harness report", "audit_harness_report_phase6.py", 0.2),
    # Phase 6.5 - closure. The deep-prediction dump must precede the harness validation
    # for its A8 section to run; it is listed here after it so a --fast run stays CPU-only,
    # and the validation script skips A8 cleanly when the file is absent.
    Stage("Phase 6.5 deep-model predictions", "deep_ppg_predictions_dump_phase6_5.py", 10, slow=True,
          note="GPU; 10 seeds + 6 candidates with the Phase 5 driver; re-run the harness "
               "validation afterwards for section A8 (19/19 known-truth cases)"),
    Stage("Phase 6.5 image CNN baseline", "image_cnn_baseline_phase6_5.py", 76, slow=True,
          note="GPU, MEASURED 4,578 s: ResNet-18 on Eyes-Defy, 3 seeds, 30 permutations, "
               "cross-site; NON-DETERMINISTIC (cuDNN), seed SD 0.048"),
    Stage("Phase 6.5 Eyes-Defy illuminant", "eyes_defy_illuminant_apply_phase6_5.py", 1.5,
          note="GPU inference only; Phase 2 estimator applied to all 218 images"),
    Stage("Phase 6.5 closure report", "closure_report_phase6_5.py", 0.1),
    Stage("Phase 7  controlled capture", "controlled_capture_gate_phase7.py", 44, slow=True,
          note="GPU, MEASURED 2,614 s: segments 5,186 MOBIUS/SBVPI frames; gate re-run at "
               "measured residuals; thresholds declared in CLAUDE.md before running"),
    Stage("Phase 7  statistical vs clinical", "statistical_vs_clinical_analysis_phase7.py", 0.5,
          note="needs the Phase 6.5 deep-model and CNN prediction tables"),
    Stage("Phase 7  reports", "capture_and_clinical_report_phase7.py", 0.1),
    # The external RUN (external_model_run_phase7.py) needs a third-party clone and its own
    # environment outside this repository and is not a stage; its record is committed to
    # the register and the report regenerates from it.
    Stage("Phase 7  external audit reports", "external_audit_report_phase7.py", 0.1,
          note="from configs/external_audit_register.json and the run record"),
    Stage("Phase 8A content review", "audit_content_review_phase8a.py", 1.0,
          note="plain and technical layers side by side; runs the harness on the shipped samples"),
    Stage("Phase 8B contrast + tokens", "design_tokens_contrast_phase8b.py", 0.1,
          note="writes app/frontend/src/tokens.css and measures every contrast pair"),
    Stage("Phase 8B visual assets", "design_visual_assets_phase8b.py", 0.2,
          note="OMLC spectra, CIE band, and the project's own aggregate figures -> front-end JSON"),
    # Lighthouse and the 48-state browser verification need node + Chrome and are run from
    # app/frontend (tools/verify_8b.mjs); their outputs are read by the report stage.
    Stage("Phase 8B design report", "design_review_report_phase8b.py", 0.1),
    Stage("Phase 9A cross-site predictions", "cross_site_cnn_predictions_phase9a.py", 0.8,
          note="GPU; regenerates what Phase 6.5 never saved. NOT deterministic: two "
               "runs differ by 0.05-0.10 g/dL on the seed average, up to 0.17 per seed "
               "(single-site training, no fold averaging). No verdict depends on it"),
    Stage("Phase 9A screening metrics", "screening_reframe_metrics_phase9a.py", 6, slow=True,
          note="CPU; 2,000-resample subject-level bootstraps. Thresholds, operating "
               "point and margin pre-declared in CLAUDE.md and committed before it ran"),
    Stage("Phase 9A report", "screening_reframe_report_phase9a.py", 0.1),
    Stage("Phase 9B literature audit", "literature_methodology_audit_phase9b.py", 0.1,
          note="CPU; scoring is data in hemosight.audit.literature (7 full texts in "
               "data/raw/literature/, read 2026-09-20); regenerates literature_gap.md"),
    Stage("Phase 9C parameter uncertainty", "parameter_uncertainty_propagation_phase9c.py", 25, slow=True,
          note="CPU, MEASURED 1,070 s for 16,384 Saltelli evaluations x 3 residuals plus "
               "290 s of banks and mismatch. DETERMINISTIC: nominal theta must reproduce "
               "3.892987 / 3.470951 / 1.039592 to 1e-12 or the run aborts. --reuse-design "
               "reruns the summaries from the cached design in ~3 min"),
    Stage("Phase 9C report", "parameter_uncertainty_report_phase9c.py", 0.1),
    Stage("Phase 9D power analysis", "power_analysis_phase9d.py", 4,
          note="CPU; rebuilds Phase 9A's own model scores and folds and asserts it "
               "reproduces the recorded differences before computing any MDE. "
               "Deterministic (bootstrap seed 20260911)"),
    Stage("Phase 9D report", "power_analysis_report_phase9d.py", 0.1),
    Stage("Phase 9E cross-site intervals", "cross_site_interval_estimation_phase9e.py", 0.1,
          note="CPU; the cross-site specificity/PPV/referral CIs Phase 9A never "
               "stored. Rebuilds Phase 9A's calls from the recorded operating point "
               "and asserts it reproduces its confusion matrices and sensitivity "
               "intervals exactly before adding anything. Deterministic"),
    Stage("Phase 9E required n", "required_sample_size_phase9e.py", 5, slow=True,
          note="CPU, MEASURED ~290 s. Asserts Phase 9D's MDEs reproduce, then "
               "MEASURES the SE scaling by subsampling (25 subsamples x 2,000-"
               "resample paired bootstraps per comparison) before computing any "
               "required n. Deterministic (seeds 20260911 / 20260921)"),
    Stage("Phase 9E guided capture", "guided_capture_interpolation_phase9e.py", 3,
          note="CPU, MEASURED ~155 s. Needs phase9c/design.npz for the prior draws. "
               "Draws FRESH perturbation banks (seed 20260921) because no original "
               "RNG order exists at an unmeasured residual, and re-runs the two "
               "measured anchors on them as a check. INTERPOLATION, not a "
               "measurement - see the report. Deterministic"),
    Stage("Phase 9E report", "boundaries_report_phase9e.py", 0.1),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="skip stages marked slow")
    ap.add_argument("--list", action="store_true", help="print the plan and exit")
    ap.add_argument("--from", dest="start", default=None, help="resume at this stage name")
    args = ap.parse_args()

    stages = [s for s in STAGES if not (args.fast and s.slow)]
    if args.start:
        idx = next((i for i, s in enumerate(stages) if args.start.lower() in s.name.lower()), 0)
        stages = stages[idx:]

    total = sum(s.minutes for s in stages)
    print(f"HemoSight reproduction: {len(stages)} stages, ~{total:.0f} min "
          f"({total/60:.1f} h) on the reference machine")
    print(f"repo root : {paths.ROOT}")
    print(f"raw data  : {paths.RAW}  (READ-ONLY)\n")
    if args.list:
        for s in stages:
            print(f"  {'[slow] ' if s.slow else '       '}{s.name:34s} "
                  f"{s.minutes:6.1f} min  {s.note}")
        return 0

    t0 = time.time()
    failed = []
    for i, s in enumerate(stages, 1):
        print(f"[{i}/{len(stages)}] {s.name} ... ", end="", flush=True)
        st = time.time()
        r = subprocess.run([sys.executable, str(paths.ROOT / "scripts" / s.script)],
                           capture_output=True, text=True)
        el = time.time() - st
        if r.returncode == 0:
            print(f"ok ({el/60:.1f} min)")
        else:
            print(f"FAILED ({el/60:.1f} min)")
            print("   " + (r.stderr.strip().splitlines() or ["<no stderr>"])[-1])
            failed.append(s.name)
    print(f"\ntotal {(time.time()-t0)/60:.1f} min; "
          f"{len(stages)-len(failed)}/{len(stages)} stages ok")
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
