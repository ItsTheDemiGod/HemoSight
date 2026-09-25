# Code map

Written 2026-09-25, during a rename-and-documentation pass that touched no result.
Two problems motivated it: files were named by project phase (`phase3_report.py`,
`phase9a_*.py`), so nothing about a filename said what the file computes, and the
code behind the web app's eight checks could not be located at all — it lived inside
plainly-named modules (`duplicates.py`, `baselines.py`, ...) with no link from the
check number the UI shows to the file on disk. Both are fixed here: every audit check
is now its own file named for the check, every analysis script leads with what it
computes, and this document is the map from either back to the other.

**Nothing in `docs/archive/` was renamed or edited.** Those files are the append-only
historical record; they cite scripts by the names that were current when each entry
was written, and rewriting them to match new names would falsify the record. This map
is the translation layer instead — see the "old name -> new name" table below.

## Where do I start reading

1. **`CLAUDE.md`** — the project's claims, constraints, data inventory and phase plan.
   Read it before anything else; it says what is proven, refuted, or still open.
2. **This file** — for "where does check N live" or "what script produced this
   number", the two questions that motivated writing it.
3. **`src/hemosight/audit/registry.py`** — the single place that lists the eight
   checks, their order, and their default thresholds. The web app's check picker and
   this document's check table both come from it; nothing hard-codes a list of eight
   anywhere else.
4. **`scripts/reproduce_all.py`** — the single entry point that reproduces every
   number in every report from raw data, in dependency order, with the runtime of
   each stage measured on the reference machine.
5. **`app/backend/main.py`** and **`app/frontend/src/pages/`** — the web application
   that runs the eight checks against an uploaded predictions file.

## Directory tree

```
CLAUDE.md                  project charter: claims, constraints, data, phase plan
README.md                  entry point for a first-time visitor; points here and at CLAUDE.md
docs/
  CODE_MAP.md               this file
  archive/                  append-only historical record (decisions, results, corrections,
                             superseded claims, pre-declarations) - never renamed, never edited
configs/                    frozen seeds, thresholds, the external-audit register
data/
  raw/                      the ten source datasets - READ-ONLY, never written to
  interim/                  every script's intermediate JSON/CSV output, one folder per
                             project phase (data, not code - these folder names were not
                             renamed; see "why data/interim keeps its phase folders" below)
  processed/, synthetic/    downstream derived data (patient-level splits, synthetic corpora)
src/hemosight/
  audit/                    the audit harness: the eight checks plus the runner, the input
                             contract, the plain/technical content model, and the report
                             renderer. See "the eight checks" below.
  baseline/                 the conventional CNN comparison arm (ResNet-18 on Eyes-Defy)
  calibration/              N1/N1a/N1b: sclera segmentation, illuminant estimation, the
                            specular-highlight rescue attempt
  simulation/               N2: the Monte Carlo layered-tissue forward model, its cited
                            optical constants, and the Phase 9C parameter-uncertainty sweep
  ppg/                      the four-wavelength PPG pipeline: features, deep models, CV splits
  evaluation/               the screening-metrics (Phase 9A) and power-analysis (Phase 9D)
                            math, kept separate from any one phase's driver script
  io/                       paths, manifests, splits, hashing - shared low-level utilities
  conformal/, fairness/, fusion/, spectral/   scoped-but-unbuilt N4/N5/N6 packages (empty
                            beyond __init__.py; see CLAUDE.md phases 6(orig)/7/8 for why)
scripts/                    one script per analysis or report; see the tables below.
                            reproduce_all.py is the entry point that runs all of them in order.
tests/                      one test file per project phase, named to match (test_phase9c.py
                            tests parameter_uncertainty_propagation_phase9c.py, etc.)
app/
  backend/                  FastAPI service for the audit harness: upload, run, report, export
  frontend/                 React + TypeScript + Vite UI: upload, pre-registration, results,
                            report, case study, glossary
reports/                    every generated report (*.md) and the figures/ directory
                            (gitignored - dataset-derived pixels are never committed)
notebooks/, web/, mobile/   scratch space, an early static mockup, and a placeholder for the
                            (superseded, never started) Flutter app - see CLAUDE.md phase plan
```

### Why `data/interim/` keeps its phase folders

Only `scripts/*.py` and `src/hemosight/audit/*.py` were renamed. `data/interim/phase9c/`,
`app/backend/main.py`'s `paths.INTERIM / "phase5" / "harden.json"`, and similar are
**data locations**, hard-coded as output paths in dozens of scripts and read by the web
backend at runtime. Renaming them would mean re-running every stage that writes there
(hours of GPU time) to move real results, for a cosmetic gain — the task this document
supports was to make code legible, not to relabel data nobody was failing to find. They
were left exactly as they were.

## The eight checks

`src/hemosight/audit/registry.py` is the source of truth for the list, the order, and
the default thresholds; this table mirrors it. `question_plain` is quoted verbatim from
`src/hemosight/audit/content.py`, which is the exact wording the web app's results page
shows a user.

| # | question (as shown to a user) | file | check id | from phase |
| - | --- | --- | --- | --- |
| 1 | Are the same pictures in both the training set and the test set? | `check1_leakage_duplicates.py` | `duplicates` | Phase 1 |
| 2 | Was the model tested on people it never saw during training? | `check2_split_integrity.py` | `split_integrity` | Phase 1 |
| 3 | Does the model do better than simply knowing the subject's sex, age, device or site? | `check3_demographic_baseline.py` | `demographic_baseline` | Phase 4 |
| 4 | Is the model's skill really a demographic variable wearing a model's clothes? | `check4_demographic_proxy_probe.py` | `proxy_probe` | Phase 4 / 4.5 |
| 5 | Is the model's score better than what pure chance would produce on this data? | `check5_permutation_test.py` | `permutation` | Phase 4.5 / 5 |
| 6 | If you trained the same model again with a different random start, would the result hold? | `check6_seed_stability.py` | `seed_stability` | Phase 5 |
| 7 | Does the result rest on a handful of people the model happens to do well on? | `check7_subgroup_robustness.py` | `subgroup_robustness` | Phase 5 |
| 8 | Do the inputs contain any information about the outcome, before any model is built? | `check8_ceiling_analysis.py` | `ceiling` | Phase 4.5 |

All eight files live in `src/hemosight/audit/`. The runner (`registry.py`), the shared
verdict vocabulary (`verdict.py`), the input contract (`contract.py`), the plain/technical
wording (`content.py`), and the Markdown/PDF renderer (`report.py`) are the other modules
in that directory — none of them is a ninth check.

## Headline results -> producing script -> report

The left-hand column is the number CLAUDE.md and `reports/final_results.md` treat as
load-bearing; the script is what to re-run to reproduce it (`reproduce_all.py` runs all
of them in the right order); the report is where it is written up in prose.

| headline result | script | report |
| --- | --- | --- |
| Grey-world beats sclera/specular colour constancy (N1 refuted) | `specular_illuminant_evaluation_phase2_5.py` | `reports/phase2_5_specular.md` |
| Phase 3 gate: 3.893 g/dL at the measured 3.935 dE2000 residual | `tissue_simulator_gate_phase3.py` | `reports/phase3_simulation.md` |
| Empirical colour-per-Hb signal, 0.84 dE2000/g/dL (CI 0.57-1.17) | `empirical_colour_hb_signal_phase3.py` | `reports/phase3_simulation.md` |
| Ratio reformulation does not rescue N1 (10.04 g/dL equivalent) | `illuminant_ratio_cancellation_phase3_5.py` | `reports/phase3_5_ratio.md` |
| PPG Gate A/B: not viable, sex alone (0.831) beats 4-wavelength PPG (1.190) | `ppg_hb_estimation_gate_phase4.py` | `reports/phase4_ppg_gate.md` |
| Deep PPG: best MAE 1.113, one real-but-useless spectrogram signal | `ppg_deep_models_phase4_5.py` | `reports/phase4_5_deep.md` |
| Ceiling analysis: 0 of 51 hand-engineered PPG features above the MI null | `ppg_ceiling_analysis_phase4_5.py` | `reports/phase4_5_deep.md` |
| The surviving positive claim hardened: empirical p <= 0.0041 at n=240 | `permutation_hardening_phase5.py` | `reports/final_results.md` |
| Conventional CNN baseline: MAE 1.301 vs site+sex+age 1.273 (Phase 6.5) | `image_cnn_baseline_phase6_5.py` | `reports/phase6_5_closure.md` |
| Audit harness self-validation: false-positive rate on clean replicates | `validate_audit_harness_phase6.py` | `reports/phase6_audit_harness.md` |
| Controlled-capture gate: studio 1.040 g/dL MARGINAL vs uncontrolled 3.471 | `controlled_capture_gate_phase7.py` | `reports/phase7.md` |
| Screening reframe: imaging weakened within site, confirmed cross-site | `screening_reframe_metrics_phase9a.py` | `reports/phase9a_screening_metrics.md` |
| Literature audit: 0 of 7 read papers report a demographic baseline | `literature_methodology_audit_phase9b.py` | `reports/literature_gap.md` |
| Parameter-uncertainty propagation: gate result robust, studio result fragile | `parameter_uncertainty_propagation_phase9c.py` | `reports/phase9c_uncertainty.md` |
| Power analysis: 2 arms adequately powered, 3 comparisons underpowered | `power_analysis_phase9d.py` | `reports/phase9d_power.md` |
| The guided-capture gap, interpolated: 1.44 g/dL MARGINAL, 95% [0.83, 5.73] | `guided_capture_interpolation_phase9e.py` | `reports/phase9e_boundaries.md` |
| Required sample sizes for every underpowered comparison | `required_sample_size_phase9e.py` | `reports/phase9e_boundaries.md` |
| Every number in one place | `final_results_report_phase5.py` | `reports/final_results.md` |

## Old name -> new name

All 66 `scripts/phase*.py` files and all 8 audit-check modules under
`src/hemosight/audit/`, `git mv`'d in one pass so history survives (`git log --follow`).

### Audit checks (`src/hemosight/audit/`)

| old | new |
| --- | --- |
| `duplicates.py` | `check1_leakage_duplicates.py` |
| `split_integrity.py` | `check2_split_integrity.py` |
| `baselines.py` | `check3_demographic_baseline.py` |
| `proxy.py` | `check4_demographic_proxy_probe.py` |
| `permutation.py` | `check5_permutation_test.py` |
| `seeds.py` | `check6_seed_stability.py` |
| `subgroups.py` | `check7_subgroup_robustness.py` |
| `ceiling.py` | `check8_ceiling_analysis.py` |

### Scripts (`scripts/`)

| old | new |
| --- | --- |
| `phase1_manifests.py` | `dataset_manifests_phase1.py` |
| `phase1_overlap.py` | `participant_overlap_check_phase1.py` |
| `phase1_splits.py` | `patient_level_splits_phase1.py` |
| `phase1_audit.py` | `data_audit_report_phase1.py` |
| `phase1_summary.py` | `data_summary_report_phase1.py` |
| `phase1_figures.py` | `data_audit_figures_phase1.py` |
| `phase1_5_label_arbitration.py` | `ghana_label_arbitration_phase1_5.py` |
| `phase1_5_remediation_report.py` | `remediation_report_phase1_5.py` |
| `phase1_5_search_originals.py` | `search_uncropped_originals_phase1_5.py` |
| `phase2_train_segmentation.py` | `train_sclera_segmentation_phase2.py` |
| `phase2_eval_segmentation.py` | `eval_sclera_segmentation_phase2.py` |
| `phase2_nus8_n1a.py` | `illuminant_estimation_nus8_phase2.py` |
| `phase2_n1b_selfconsistency.py` | `sclera_reference_selfconsistency_phase2.py` |
| `phase2_sensitivity.py` | `sclera_reference_sensitivity_phase2.py` |
| `phase2_report.py` | `illuminant_calibration_report_phase2.py` |
| `phase2_figures.py` | `illuminant_calibration_figures_phase2.py` |
| `phase2_5_census.py` | `specular_highlight_census_phase2_5.py` |
| `phase2_5_evaluate.py` | `specular_illuminant_evaluation_phase2_5.py` |
| `phase2_5_report.py` | `specular_rescue_report_phase2_5.py` |
| `phase2_5_figures.py` | `specular_rescue_figures_phase2_5.py` |
| `phase3_task0_gate.py` | `tissue_simulator_gate_phase3.py` |
| `phase3_empirical_signal.py` | `empirical_colour_hb_signal_phase3.py` |
| `phase3_report.py` | `tissue_simulator_gate_report_phase3.py` |
| `phase3_5_task1_cancellation.py` | `illuminant_ratio_cancellation_phase3_5.py` |
| `phase3_5_task3_stability.py` | `sclera_reference_stability_phase3_5.py` |
| `phase3_5_report.py` | `ratio_reformulation_report_phase3_5.py` |
| `phase4_gate_a.py` | `ppg_acdc_cancellation_gate_phase4.py` |
| `phase4_gate_b.py` | `ppg_hb_estimation_gate_phase4.py` |
| `phase4_report.py` | `ppg_gate_report_phase4.py` |
| `phase4_5_deep.py` | `ppg_deep_models_phase4_5.py` |
| `phase4_5_ceiling.py` | `ppg_ceiling_analysis_phase4_5.py` |
| `phase4_5_report.py` | `deep_ppg_report_phase4_5.py` |
| `phase5_harden.py` | `permutation_hardening_phase5.py` |
| `phase5_perm_extended.py` | `permutation_extended_run_phase5.py` |
| `phase5_perm_status.py` | `permutation_run_status_phase5.py` |
| `phase5_consolidate_extended.py` | `permutation_consolidate_phase5.py` |
| `phase5_manifest_and_lit.py` | `dataset_manifest_and_literature_phase5.py` |
| `phase5_final_report.py` | `final_results_report_phase5.py` |
| `phase6_make_sample_data.py` | `make_sample_submissions_phase6.py` |
| `phase6_validate_harness.py` | `validate_audit_harness_phase6.py` |
| `phase6_report.py` | `audit_harness_report_phase6.py` |
| `phase6_5_deep_predictions.py` | `deep_ppg_predictions_dump_phase6_5.py` |
| `phase6_5_eyes_defy_illuminant.py` | `eyes_defy_illuminant_apply_phase6_5.py` |
| `phase6_5_image_cnn.py` | `image_cnn_baseline_phase6_5.py` |
| `phase6_5_report.py` | `closure_report_phase6_5.py` |
| `phase7_controlled_capture.py` | `controlled_capture_gate_phase7.py` |
| `phase7_statistical_vs_clinical.py` | `statistical_vs_clinical_analysis_phase7.py` |
| `phase7_external_run.py` | `external_model_run_phase7.py` |
| `phase7_external_report.py` | `external_audit_report_phase7.py` |
| `phase7_report.py` | `capture_and_clinical_report_phase7.py` |
| `phase8a_content_review.py` | `audit_content_review_phase8a.py` |
| `phase8b_contrast.py` | `design_tokens_contrast_phase8b.py` |
| `phase8b_assets.py` | `design_visual_assets_phase8b.py` |
| `phase8b_report.py` | `design_review_report_phase8b.py` |
| `phase9a_cross_site_preds.py` | `cross_site_cnn_predictions_phase9a.py` |
| `phase9a_screening.py` | `screening_reframe_metrics_phase9a.py` |
| `phase9a_report.py` | `screening_reframe_report_phase9a.py` |
| `phase9b_literature_audit.py` | `literature_methodology_audit_phase9b.py` |
| `phase9c_uncertainty.py` | `parameter_uncertainty_propagation_phase9c.py` |
| `phase9c_report.py` | `parameter_uncertainty_report_phase9c.py` |
| `phase9d_power.py` | `power_analysis_phase9d.py` |
| `phase9d_report.py` | `power_analysis_report_phase9d.py` |
| `phase9e_guided_capture.py` | `guided_capture_interpolation_phase9e.py` |
| `phase9e_intervals.py` | `cross_site_interval_estimation_phase9e.py` |
| `phase9e_required_n.py` | `required_sample_size_phase9e.py` |
| `phase9e_report.py` | `boundaries_report_phase9e.py` |

`docs/archive/*.md` cite scripts and checks by their old names throughout, because that
was the name in force when each entry was written. That is correct and is left alone;
this table is the only translation between the two.
