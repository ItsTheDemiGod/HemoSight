# Graph Report - HemoSight  (2026-09-17)

## Corpus Check
- 213 files · ~254,344 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 16 file(s) not represented in the graph (top: .csv 9, (none) 6, .css 1)

## Summary
- 1956 nodes · 4156 edges · 118 communities (102 shown, 16 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 195 edges (avg confidence: 0.89)
- Token cost: 409,948 input · 0 output

## Community Hubs (Navigation)
- Audit Checks and Contract
- Phase Report Generators
- PPG Gate B and Ceiling
- Phase 1-2.5 Scripts
- Specular Illuminant Estimation
- Audit Plain-Language Content
- Sclera Segmentation Training
- Frontend Perf Measurement
- Package Import Tests
- External Audit Ingestion
- FastAPI Backend Routes
- Screening Metrics Library
- Phase 6 Harness Tests
- Frontend API Types
- Empirical Colour Signal
- Reflectance Priors
- Audit Runner and Report
- Backend DB and Jobs
- Sclera Self-Consistency
- Dataset Manifest Builders
- PPG Feature Extraction
- Datasets and Novelty Claims
- Leak-Proof Splits
- Frontend Motion Layer
- CNN Baseline and Phase 9A Corrections
- Classical Colour Constancy
- Harness Validation Cases
- Phase 5 Tests
- Image Hashing for Checks
- Image CNN Baseline
- Optical Constants
- Deep PPG Cross-Validation
- NUS-8 Experiment
- Generated Visuals
- Phase 1.5 Remediation
- Label Arbitration Scripts
- Figure Scripts
- Master Table and N1 Refutation
- Phase 3 Forward Model Tests
- Frontend Package Config
- Licences and Stability Results
- Participant Overlap Check
- Deep PPG Architectures
- Sample Submissions and Phases
- Frontend Dev Dependencies
- Core Bet and N1 Claims
- Audit Package and Prereg
- Final Results Hardening
- NUS-8 Reader and Paths
- Extended Permutation Test
- External Audit and Literature Gap
- Illuminant Estimation Tests
- Ghana Naming Tests
- Web App and Superseded Phases
- Results and Report Pages
- TypeScript Config
- Phase 9A Screening Verdicts
- Pre-Registration Model
- Illuminant Error Metrics
- Gate and Controlled Capture Scripts
- Job Polling
- The One Positive Claim
- External Run and Reproduce
- Utility Scripts
- Deep PPG Preprocessing
- Forward Model Projection
- Documentation Invariant Tests
- JSON Safety
- Upload and Prereg Pages
- Eyes-Defy and External Availability
- Corrections and Simulator Findings
- Phase 4.5 Deep Script
- Backend Schemas
- Original Image Search
- Illuminant Perturbation Gate
- Grouped Evaluation Builders
- Upload Routes
- App Shell and Routing
- Archive and Working Protocol
- Image Metadata
- Diffuse Reflectance
- Ghana Filename Parsing
- Ratio Cancellation
- PPG Gate A
- Phase 7 Report
- Simulate RGB Guards
- Phase 1 Audit Script
- Phase 2 Report
- Permutation Labels
- Sample Data Manifest
- Frontend Runtime Dependencies
- NPM Scripts
- Phase 2.5 Report
- Contrast Ratios
- Phase 9A Report
- Phase 1 Summary
- Phase 4.5 Report
- Phase 4 Report
- Phase 5 Final Report
- Phase 6 Report
- Phase 8B Report
- U-Net Decoder Block
- Case Study Loader
- Vite Config
- Contract Error
- Calibration Package
- Conformal Package
- Fairness Package
- Fusion Package
- HemoSight Package
- Spectral Package
- Phase 0 Scaffold
- Hemosight Root

## God Nodes (most connected - your core abstractions)
1. `AuditInput` - 36 edges
2. `load_predictions()` - 33 edges
3. `run_audit()` - 28 edges
4. `CheckResult` - 23 edges
5. `main()` - 22 edges
6. `main()` - 20 edges
7. `Timer` - 19 edges
8. `PreRegistration` - 18 edges
9. `angular_error()` - 18 edges
10. `react` - 17 edges

## Surprising Connections (you probably didn't know these)
- `test_untrusted_rows_carry_a_reason()` --calls--> `_finalise()`  [INFERRED]
  tests/test_phase1.py → src/hemosight/io/manifests.py
- `test_camspec_parses_all_28_cameras()` --calls--> `camspec_database()`  [INFERRED]
  tests/test_phase3.py → src/hemosight/simulation/optical_data.py
- `INSUFFICIENT DATA as a first-class verdict` --semantically_similar_to--> `N4: Conformal prediction with selective abstention`  [INFERRED] [semantically similar]
  reports/external_audit_procedure.md → CLAUDE.md
- `Retired phrase: 'moves no clinical threshold'` --semantically_similar_to--> `Audit check: demographic_baseline (beating the obvious guess)`  [INFERRED] [semantically similar]
  CLAUDE.md → reports/content_review.md
- `execute()` --calls--> `load_predictions()`  [INFERRED]
  app/backend/jobs.py → src/hemosight/audit/contract.py

## Import Cycles
- 3-file cycle: `src/hemosight/audit/__init__.py -> src/hemosight/audit/report.py -> src/hemosight/audit/registry.py -> src/hemosight/audit/__init__.py`

## Hyperedges (group relationships)
- **Imaging arm: four representations refuted to pre-declared gates** — claude_phase_2_sclera_illuminant, claude_phase_2_5_specular_rescue, claude_phase_3_simulator_gate, claude_phase_3_5_ratio_reformulation, claude_imaging_arm_closed_final [EXTRACTED 1.00]
- **PPG arm: gates, deep models, hardening and the one useless positive** — claude_dataset_hb_ppg, claude_phase_4_ppg_gates, claude_phase_4_5_deep_ppg, claude_phase_5_harden_consolidate, claude_one_positive_claim_spectrogram_cnn, claude_sex_alone_benchmark, claude_ppg_arm_not_viable [EXTRACTED 1.00]
- **HemoSight Audit: the eight checks generalised from Phases 1-5** — claude_phase_6_audit_harness, reports_content_review_check_duplicates, reports_content_review_check_split_integrity, reports_content_review_check_demographic_baseline, reports_content_review_check_proxy_probe, reports_content_review_check_permutation, reports_content_review_check_seed_stability, reports_content_review_check_subgroup_robustness, reports_content_review_check_ceiling [EXTRACTED 1.00]
- **Imaging Arm Refutation Chain (Phases 2 to 3.5)** — reports_phase2_calibration_n1b_partially_supported, reports_phase2_5_specular_dichromatic_specular_estimation, reports_phase3_simulation_task0_gate, reports_phase3_5_ratio_ratio_reformulation, reports_phase2_5_specular_n1_refuted [EXTRACTED 1.00]
- **Demographic Covariate Masquerading as Signal** — reports_phase4_ppg_gate_ppg_demographics_trap, reports_phase6_5_closure_site_omission_correction, reports_phase4_5_deep_sex_probe, reports_final_results_sex_alone_baseline, reports_statistical_vs_clinical_reporting_standard [INFERRED 0.85]
- **Audit Harness Checks Derived From Project Phases** — reports_phase6_audit_harness_hemosight_audit, reports_phase1_data_audit_leakproof_groups, reports_phase4_5_deep_ceiling_analysis, reports_final_results_selection_aware_permutation, reports_phase7_external_audit_ingest [EXTRACTED 1.00]

## Communities (118 total, 16 thin omitted)

### Community 0 - "Audit Checks and Contract"
Cohesion: 0.06
Nodes (65): dataclasses, pandas, Check 3 - demographic baseline comparison. PROVENANCE. Phase 4, Task 3…, run(), Check 8 - ceiling analysis: can this signal contain the target at all?…, run(), AuditInput, encode_design() (+57 more)

### Community 1 - "Phase Report Generators"
Cohesion: 0.05
Nodes (67): functools, load(), main(), Phase 3.5, Task 5: generate reports/phase3_5_ratio.md. Task 1's result is…, row(), load(), main(), Phase 3, Task 5: generate reports/phase3_simulation.md. The gate result is… (+59 more)

### Community 2 - "PPG Gate B and Ceiling"
Cohesion: 0.08
Nodes (45): cv_mae(), main(), Phase 4.5, TASK 2: how much Hb information can this signal contain at all? "Our…, build_conditions(), main(), phone_channel_weights(), DataFrame, Phase 4, TASK 1 / GATE B + TASK 3: can Hb be predicted, and does PPG beat… (+37 more)

### Community 3 - "Phase 1-2.5 Scripts"
Cohesion: 0.10
Nodes (28): argparse, collections, cv2, numpy, Phase 1, Task 3: build one manifest per dataset plus a master manifest. Writes…, Phase 2.5, Task 1: corneal-highlight feasibility census. RUN THIS FIRST. Gate…, Phase 2.5, Tasks 3 and 4: specular illuminant estimation, evaluated on the…, Phase 2, Task 1 (evaluation) + Task 4: segmentation quality, broken down.… (+20 more)

### Community 4 - "Specular Illuminant Estimation"
Cohesion: 0.08
Nodes (44): count_chroma_clusters(), degenerate_direction(), detect_highlights(), dichromatic_plane_normal(), estimate_specular_illuminant(), Highlight, illuminant_from_dichromatic(), ndarray (+36 more)

### Community 5 - "Audit Plain-Language Content"
Cohesion: 0.08
Nodes (37): _base_headline(), _base_todo(), catalogue(), _ceil_headline(), _ceil_todo(), CheckContent, _dup_headline(), _dup_todo() (+29 more)

### Community 6 - "Sclera Segmentation Training"
Cohesion: 0.08
Nodes (38): Dataset, main(), eval_subset(), main(), main(), main(), main(), confusion() (+30 more)

### Community 7 - "Frontend Perf Measurement"
Cohesion: 0.05
Nodes (31): evalStart, idleRequests, requests, t0, fd, idx, polls, rejections (+23 more)

### Community 8 - "Package Import Tests"
Cohesion: 0.06
Nodes (29): importlib, pytest, Metrics, patient-level and cross-site splits, report/figure generation., parametrize, Smoke test: the package and every submodule import cleanly., test_submodule_imports(), Tests for Phase 9A, the screening reframe. Two jobs: keep the screening…, Phase 7 recorded sensitivity 0.00. Every PPG model must still show it. (+21 more)

### Community 9 - "External Audit Ingestion"
Cohesion: 0.11
Nodes (28): Exception, cmd_ingest(), cmd_register(), cmd_run(), main(), External-audit path: ingest a third party's released predictions, run the…, ingest(), ingest_file() (+20 more)

### Community 10 - "FastAPI Backend Routes"
Cohesion: 0.14
Nodes (32): _availability(), content(), create_run(), get_prereg(), get_run(), get_submission(), health(), _iso() (+24 more)

### Community 11 - "Screening Metrics Library"
Cohesion: 0.11
Nodes (33): bootstrap_ci(), choose_cut_for_sensitivity(), choose_cut_for_specificity(), confusion(), _cut_candidates(), margin_cleared(), nested_calls(), nested_calls_matched_sensitivity() (+25 more)

### Community 12 - "Phase 6 Harness Tests"
Cohesion: 0.07
Nodes (33): _app_module(), _frontend(), Tests for Phase 6 - the HemoSight Audit harness. The tool judges other people's…, p = 0.0164 at n=60 was 1/(60+1), the smallest number the sample size allowed., Re-homed, not duplicated: two copies of a correction drift invisibly., data/raw is READ-ONLY. The harness reads pixels from it and nothing more., If the validation has been run, it must still agree with the project's record., p = 0.0164 stands until the extended run is consolidated by hand. (+25 more)

### Community 13 - "Frontend API Types"
Cohesion: 0.13
Nodes (24): api, AuditReport, CheckResult, CheckSpec, ContentCatalogue, PlainLayer, PreReg, TodoCategory (+16 more)

### Community 14 - "Empirical Colour Signal"
Cohesion: 0.12
Nodes (25): binned_signal(), de2000(), linear_to_lab(), main(), mask_region(), palpebral_mask_path(), ndarray, Path (+17 more)

### Community 15 - "Reflectance Priors"
Cohesion: 0.11
Nodes (16): main(), Per subject, take up to `per_cell` frames from each (phone, lighting) cell., select_grid(), FixedPopulationPrior, NeutralPrior, OraclePrior, PerKeyPrior, ndarray (+8 more)

### Community 16 - "Audit Runner and Report"
Cohesion: 0.12
Nodes (27): main(), load_predictions(), Path, Load and validate a submission. Raises ContractError on a blocking problem., Run the selected checks and collect their verdicts. A check that raises is…, run_audit(), _frame(), DataFrame (+19 more)

### Community 17 - "Backend DB and Jobs"
Cohesion: 0.13
Nodes (24): Base, get_session(), init_db(), Database session handling. SQLite for development, PostgreSQL-ready.…, A JSON column that coerces NumPy scalars, arrays, NaN and Inf on the way in.…, SafeJSON, execute(), progress() (+16 more)

### Community 18 - "Sclera Self-Consistency"
Cohesion: 0.12
Nodes (26): est_from_mask(), main(), measure(), centre_crop(), main(), ndarray, spread(), Summarise a reference patch's pixels to one RGB triple. Uses an inter-… (+18 more)

### Community 19 - "Dataset Manifest Builders"
Cohesion: 0.15
Nodes (25): probe(), Path, Read one image's properties without decoding pixel data., build_cp_anemic(), build_eyes_defy(), _build_ghana(), build_ghana_conj(), build_ghana_nail() (+17 more)

### Community 20 - "PPG Feature Extraction"
Cohesion: 0.12
Nodes (23): _butter(), ChannelFeatures, extract_channel(), extract_subject(), load_subject(), ndarray, PPG AC/DC extraction and ratio-of-ratios features. EXTRACTION METHOD - stated…, All channels plus every ratio-of-ratios. `signals` is (n_samples, 4). (+15 more)

### Community 21 - "Datasets and Novelty Claims"
Cohesion: 0.13
Nodes (25): CP-AnemiC (Ghana conjunctival pallor), Ghana conjunctiva (Mendeley nt7r8hv2pz), Ghana fingernails (Mendeley 2xx4j3kjg2), MOBIUS mobile sclera dataset, SBVPI sclera dataset, N1b: Sclera as endogenous white reference across devices, N2: Monte Carlo forward model of layered eyelid tissue, N5: Mechanistic fairness audit (ITA, melanin vs illuminant) (+17 more)

### Community 22 - "Leak-Proof Splits"
Cohesion: 0.13
Nodes (20): load_hashes(), main(), DataFrame, Phase 1, Task 4: reproducible splits under data/interim/splits/. Every split is…, Series, grouped_split(), kfold_by_group(), leakproof_groups() (+12 more)

### Community 23 - "Frontend Motion Layer"
Cohesion: 0.14
Nodes (18): Cursor(), P, Particles(), Ctx, MotionProvider(), MotionState, MotionToggle(), readUser() (+10 more)

### Community 24 - "CNN Baseline and Phase 9A Corrections"
Cohesion: 0.13
Nodes (23): Conventional CNN baseline (ResNet-18 on Eyes-Defy, MAE 1.301), Hard constraints (public data only, retrospective, cross-site honesty, CNN baseline), Mean palpebral CIELAB + ridge (strongest within-site screening model), Retired phrase: 'moves no clinical threshold', Phase 6.5: Closure of outstanding audit items, Phase 9A: Screening reframe (triage task), Plug-in operating point artefact (PPG sensitivity 0.00), Baseline: site + sex + age (MAE 1.273, AUROC 0.816) (+15 more)

### Community 25 - "Classical Colour Constancy"
Cohesion: 0.17
Nodes (22): centre_crop(), main(), ndarray, grey_edge(), grey_world(), load_linear_png(), _masked_pixels(), max_rgb() (+14 more)

### Community 26 - "Harness Validation Cases"
Cohesion: 0.16
Nodes (22): a_phase1_images(), a_phase4_tabular(), a_phase5_deep_end_to_end(), a_phase5_statistics(), b_injected(), c_clean(), case_seed(), line() (+14 more)

### Community 27 - "Phase 5 Tests"
Cohesion: 0.10
Nodes (20): _perm_module(), Tests for the Phase 5 consolidation and reproducibility package., Every stage in the entry point must point at a script that exists., A process killed mid-write leaves a partial line; it must not block resume., An empirical p equal to 1/(n+1) is a bound. It must be labelled as one., The standing p = 0.0164 stands until the extended run is consolidated by hand.…, The project's standing rule: nothing from data/ ever enters version control., The literature counts must carry their own caveat, since the sample is tiny. (+12 more)

### Community 28 - "Image Hashing for Checks"
Cohesion: 0.15
Nodes (19): scipy_fft, hash_frame(), DataFrame, Attaching pixels to rows, once, for every check that needs them. Two checks…, Attach a file path to every row it can be attached to, honestly. Two routes. An…, Rows with md5/phash/dhash attached. Empty frame if no pixels are reachable., resolve_paths(), dhash() (+11 more)

### Community 29 - "Image CNN Baseline"
Cohesion: 0.19
Nodes (21): _augment(), build_model(), cross_site(), cv_predict(), features(), fit_one(), free(), _predict() (+13 more)

### Community 30 - "Optical Constants"
Cohesion: 0.17
Nodes (21): eps_hb(), eps_hbo2(), _interp(), Layer, layer_mu_a(), mu_a_blood(), mu_a_melanin(), mu_a_water() (+13 more)

### Community 31 - "Deep PPG Cross-Validation"
Cohesion: 0.13
Nodes (17): gc, main(), main(), sklearn_model_selection, build_windows(), fit_predict(), free(), load_data() (+9 more)

### Community 32 - "NUS-8 Experiment"
Cohesion: 0.15
Nodes (20): main(), build_reference_table(), checker_bbox(), evaluate_classical(), evaluate_reference_method(), fit_oracle(), parse_checker_mask(), DataFrame (+12 more)

### Community 33 - "Generated Visuals"
Cohesion: 0.15
Nodes (17): Breakeven(), Grid(), HbSpectra(), NoiseSignal(), NullDistribution(), path(), Reticle(), SpectralBand() (+9 more)

### Community 34 - "Phase 1.5 Remediation"
Cohesion: 0.17
Nodes (20): Ghana Pool BINARY_LABEL_ONLY Verdict, hb_label_trusted manifest flag, N1 Split into N1a / N1b / N1c, N2 Justification: Label Trustworthiness, N5 Rebuilt on Individual Typology Angle, N6 Fixed Scope Limits, Phase 1.5 Remediation, Conjunctiva-Nail Shared Participant Roster (+12 more)

### Community 35 - "Label Arbitration Scripts"
Cohesion: 0.12
Nodes (11): json, Phase 1.5, Task 3: arbitrate the haemoglobin labels of the Ghana pool. The task…, Phase 1.5, Task 8: generate reports/phase1_5_remediation.md. Reads the machine-…, Phase 5, TASK 3 (manifest) and TASK 4 (literature positioning). The dataset…, load(), main(), Phase 6.5 closure report: reports/phase6_5_closure.md. Every number is read…, row() (+3 more)

### Community 36 - "Figure Scripts"
Cohesion: 0.16
Nodes (16): matplotlib, matplotlib_pyplot, fig_cross_set_pairs(), fig_hb_distributions(), fig_label_conflict(), main(), Phase 1 figures for reports/figures/. 1. Cross-set duplicate pairs (CP-AnemiC…, fig_crop() (+8 more)

### Community 37 - "Master Table and N1 Refutation"
Cohesion: 0.18
Nodes (19): Master Table of Six Tested Representations, MOBIUS dataset, NUS-8 colour constancy benchmark, Dichromatic Specular Illuminant Estimation, Grey-World on Tight Periocular Crop (3.935 dE2000), Multiple Chromatic Highlight Clusters Counted Not Averaged, N1 Refuted: Endogenous Ocular White References Fail, Phase 2.5 Specular Rescue (+11 more)

### Community 38 - "Phase 3 Forward Model Tests"
Cohesion: 0.12
Nodes (17): parametrize, Tests for the Phase 3 forward model. The important one is…, Guards the warning in constants.py: if this ever stops being an exact power law…, Every estimator in the file reports what it returns under shuffled labels. The…, All six haemoglobin isosbestic points must land where the literature puts them., The basis of every colour- and PPG-based haemoglobin method., mu_s' falls monotonically across the visible for a Mie+Rayleigh mixture., _root() (+9 more)

### Community 39 - "Frontend Package Config"
Cohesion: 0.11
Nodes (17): name, private, type, version, autoprefixer, eslint, eslint-plugin-react-hooks, eslint-plugin-react-refresh (+9 more)

### Community 40 - "Licences and Stability Results"
Cohesion: 0.16
Nodes (18): Hb_PPG_Dataset, SBVPI dataset, Licence Verification (8 of 8 resolved), Phase 1 Dataset Licences, Sclera Segmentation U-Net (IoU 0.875), Sclera Within/Between-Subject Stability 1.447, PPG Signal Quality Index, Between-Subject Colour at Fixed Hb 4.55 dE2000 (+10 more)

### Community 41 - "Participant Overlap Check"
Cohesion: 0.17
Nodes (14): compute_hashes(), embed(), intra_duplicates(), load_manifests(), main(), pair_report(), DataFrame, ndarray (+6 more)

### Community 42 - "Deep PPG Architectures"
Cohesion: 0.13
Nodes (7): CNN1D, GRUNet, Tensor, 2D CNN over a per-channel spectrogram., Small dilated 1D CNN. Kept small on purpose: 252 subjects cannot support more., Bidirectional GRU over a lightly strided waveform., SpecCNN

### Community 43 - "Sample Submissions and Phases"
Cohesion: 0.18
Nodes (17): Known-truth submissions (phase1 overlap, phase4 PPG), Sample submissions for HemoSight Audit, Hb_PPG_Dataset (four-wavelength PPG, 252 subjects), Ghana pool participant overlap verdict (CP-AnemiC inside Ghana conjunctiva), Phase 3.5: Within-image ratio reformulation, Phase 4.5: Deep models on raw PPG, Phase 4: PPG arm, Gate A and Gate B, Verdict: PPG arm NOT VIABLE (+9 more)

### Community 44 - "Frontend Dev Dependencies"
Cohesion: 0.12
Nodes (17): devDependencies, autoprefixer, eslint, eslint-plugin-react-hooks, eslint-plugin-react-refresh, lighthouse, postcss, puppeteer-core (+9 more)

### Community 45 - "Core Bet and N1 Claims"
Cohesion: 0.18
Nodes (17): Core bet: photograph as spectroscopic measurement, NUS-8 colour constancy benchmark, Grey-world on a tight periocular crop (recommended normalisation), HemoSight project, Verdict: imaging arm CLOSED, FINAL, N1: Calibration-free spectral super-resolution (sclera white reference), N1a: Illuminant estimation accuracy across sensors, N3: Physical interpretability (Hb in g/dL, chromophore maps) (+9 more)

### Community 46 - "Audit Package and Prereg"
Cohesion: 0.21
Nodes (13): hashlib, HemoSight Audit - the methodological checks of Phases 1-5, generalised. This…, Pre-registration: thresholds declared before the results are seen. WHY THIS IS…, AuditReport, fingerprint(), _fmt_measured(), Path, Rendering an audit report. Markdown always; PDF when reportlab is installed,… (+5 more)

### Community 47 - "Final Results Hardening"
Cohesion: 0.18
Nodes (17): Final Results, Selection-Aware Permutation Test, Sex-Alone Baseline MAE 0.831 g/dL, Leak-Proof Split Groups (subject_id, md5), Ceiling Analysis (MI, FDR, permutation p=0.978), Phase 4.5 Deep PPG, Sex Probe on Learned Representation, Spectrogram CNN 660 nm (z=-4.72, real but useless) (+9 more)

### Community 48 - "NUS-8 Reader and Paths"
Cohesion: 0.15
Nodes (15): scipy_io, build_nus8_manifest(), DataFrame, NUS 8-camera colour-constancy benchmark reader. This module is the ONLY place…, Return one row per image for a single NUS camera., All six extracted cameras, concatenated., read_camera(), assert_raw_readonly() (+7 more)

### Community 49 - "Extended Permutation Test"
Cohesion: 0.20
Nodes (13): platform, psutil, append(), main(), permuted_labels(), ndarray, Phase 5, TASK 1 (extended): drive the selection-aware permutation null to n >=…, Permutation i's shuffled haemoglobin vector. A pure function of (y, i). (+5 more)

### Community 50 - "External Audit and Literature Gap"
Cohesion: 0.19
Nodes (16): mbedmutha/anemia-detection repository, BPANet (Lin et al. 2025), External Audit Register, Hemo-ConViT (unlocated), Literature Gap Table, UNKNOWN Is Not Evidence of Absence, Eyes-Defy-Anemia dataset, HemoSight Audit (src/hemosight/audit) (+8 more)

### Community 51 - "Illuminant Estimation Tests"
Cohesion: 0.17
Nodes (15): angular_error(), Angle in degrees between estimated and ground-truth illuminant vectors. Accepts…, estimate_illuminant(), Invert the measurement model: illuminant = measured / reflectance. Returns a…, Tests for the Phase 2 calibration code. The important ones here are not the…, Documents WHY the iris is the primary region. Correcting by an illuminant…, An illuminant is defined only up to scale; the metric must not see brightness., measured = illuminant * reflectance, so dividing by reflectance must recover it. (+7 more)

### Community 52 - "Ghana Naming Tests"
Cohesion: 0.14
Nodes (15): parse_ghana_name(), Parse a Ghana filename stem. Returns None if it does not match at all., parametrize, Tests for the Phase 1 pieces where a silent bug would corrupt every downstream…, The Ghana pool must never produce a trusted Hb value, even if a row somehow…, Non-Anrmic' must never be read as anemic., Two different subject ids sharing one md5 must land in a single group., a~b via hash H1 and b~c via H2 must put a, b and c in one group. (+7 more)

### Community 53 - "Web App and Superseded Phases"
Cohesion: 0.19
Nodes (15): HemoSight Audit front-end entry page, N4: Conformal prediction with selective abstention, Phase 10: Flutter mobile - SUPERSEDED, Phase 6: HemoSight Audit harness (software deliverable), Phase 6 (original): Conformal prediction - SUPERSEDED, Phase 8B: Visual redesign (dark instrument), Phase 9: Web application - SUPERSEDED, Decision 2026-09-12: Phase 6 is an audit harness, not conformal prediction (+7 more)

### Community 54 - "Results and Report Pages"
Cohesion: 0.23
Nodes (10): Run, formatValue(), KeyValue(), VerdictMark(), ReportPage(), ORDER, ResultsPage(), SortKey (+2 more)

### Community 55 - "TypeScript Config"
Cohesion: 0.13
Nodes (14): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+6 more)

### Community 56 - "Phase 9A Screening Verdicts"
Cohesion: 0.25
Nodes (15): Mean Palpebral CIELAB Colour Features + Ridge, Image CNN Baseline ResNet-18 (MAE 1.301), Site Omitted From Baseline Correction, Pre-declared Clinically Meaningful Margin (>= 0.10, CI > 0), Cross-Site Collapse (sensitivity 0.397), Correction: 'Moves No Clinical Threshold' Retired, Pre-declared Operating Point (sens >= 0.90, nested), Phase 9A Screening Reframe (+7 more)

### Community 57 - "Pre-Registration Model"
Cohesion: 0.18
Nodes (6): PreRegistration, Path, Thresholds and their declaration time., Return (thresholds, declared_in_advance) for one check., Whether the declaration predates the results it judges., test_an_edited_preregistration_is_detectable()

### Community 58 - "Illuminant Error Metrics"
Cohesion: 0.20
Nodes (13): delta_e2000_illuminant(), delta_e2000_pairwise_spread(), error_summary(), ndarray, Illuminant-estimation error metrics. Angular error is the standard colour-…, Spread of a set of Lab colours: mean and max pairwise CIEDE2000. This is the…, CIEDE2000 between a neutral surface corrected by `est` versus by `gt`. An…, The standard NUS reporting set. (+5 more)

### Community 59 - "Gate and Controlled Capture Scripts"
Cohesion: 0.21
Nodes (10): Phase 3, TASK 0: THE GATE. Run and report this before anything else. Question:…, eye_centre_crop(), grey_world_gain(), main(), measure(), ndarray, Phase 7 Task 1 - is the refutation about PHOTOGRAPHS or about UNCONTROLLED…, Per sample: sclera colour (Lab) under each correction. Grouped by subject key. (+2 more)

### Community 60 - "Job Polling"
Cohesion: 0.22
Nodes (8): RunPage(), isSettled(), JobStatus, Pollable, PollHandle, PollOptions, pollUntilSettled(), vitest

### Community 61 - "The One Positive Claim"
Cohesion: 0.22
Nodes (13): The one positive claim: raw-PPG spectrogram CNN (real, useless), Phase 5: Harden the positive claim and consolidate, Phase 8A: Audit tool language for a dual audience, Decision 2026-09-11: the positive claim survives hardening, Result 2026-09-11: raw PPG waveform carries a real but useless signal, Result 2026-09-12: Phase 5 extended permutation n=240, p <= 0.0041 still a bound, Audit check: permutation (better than shuffled labels), Audit check: seed_stability (same model, different luck) (+5 more)

### Community 62 - "External Run and Reproduce"
Cohesion: 0.19
Nodes (10): os, execute(), main(), prepare(), Path, Phase 7 Task 3B - attempt to run the one external repository with released…, Run with nbclient in the isolated env; return first error and where it happened., Single entry point: reproduce the entire HemoSight result set from raw data.… (+2 more)

### Community 63 - "Utility Scripts"
Cohesion: 0.17
Nodes (9): pathlib, Verify that PyTorch is the CUDA build and can actually compute on the GPU. Run…, Path, Phase 6: materialise the Task 4 validation inputs as CSV files. The validation…, write_readme(), Phase 8A - reports/content_review.md: every check, plain and technical side by…, shutil, sys (+1 more)

### Community 64 - "Deep PPG Preprocessing"
Cohesion: 0.18
Nodes (12): scipy, make_windows(), preprocess(), ndarray, Deep models over raw PPG waveforms. Phase 4 tested hand-engineered AC/DC…, (n, 4) raw at 200 Hz -> (m, 4) at 50 Hz, band-limited., Fixed windows, each channel z-scored within the window., Every window must carry its subject id, or leakage control is impossible. (+4 more)

### Community 65 - "Forward Model Projection"
Cohesion: 0.23
Nodes (12): camera_sensitivities(), cie_1931_sensitivities(), illuminant_spd(), ndarray, Forward model: tissue parameters -> reflectance spectrum -> camera RGB. Two…, (len(wl), 3) sensitivity curves. Falls back to the CIE observer., Relative spectral power distribution of a named or blackbody illuminant.…, Integrate reflectance * illuminant * sensitivity over wavelength. (+4 more)

### Community 66 - "Documentation Invariant Tests"
Cohesion: 0.21
Nodes (12): _claude_md(), Tests for the project's own documentation invariants. CLAUDE.md is loaded into…, CLAUDE.md must stay small enough to load in full, never truncated. If this…, Every archive file must exist, and CLAUDE.md must point at each one., The counts recorded at the split. These only ever go up., The logs live in the archive; CLAUDE.md carries pointers, not entries., Future sessions must be told where to append., test_claude_md_fits_in_context() (+4 more)

### Community 67 - "JSON Safety"
Cohesion: 0.18
Nodes (9): decimal, math, _clean_float(), Any, Coercion of analysis payloads into things JSON can actually hold. WHY THIS…, NaN and +/-Inf become None; every other float passes through., Return a structure built only from str, int, float, bool, None, list and dict.…, to_jsonable() (+1 more)

### Community 68 - "Upload and Prereg Pages"
Cohesion: 0.29
Nodes (9): Submission, PreRegPage(), submit(), start(), CONTRACT, SAMPLES, UploadPage(), send() (+1 more)

### Community 69 - "Eyes-Defy and External Availability"
Cohesion: 0.31
Nodes (10): Eyes-Defy-Anemia (dataset anemia, India + Italy), N1c: Sclera-referenced correction improves Hb end to end, Decision 2026-09-13: external audit run; availability is the result, External audit availability record, 'Available upon request' as its own availability category, Candidate: mbedmutha/anemia-detection (student repo), Candidate: BPANet (Lin et al. 2025), Candidate: Hemo-ConViT (unlocated) (+2 more)

### Community 70 - "Corrections and Simulator Findings"
Cohesion: 0.33
Nodes (10): Twelve Project Corrections, Self-Consistency Is Blind to the Reflectance Prior, Optical Constants Transcription Correction (max 252%), Layered Forward Model (N2), Isosbestic Self-Check (consistency, not verification), Error Is Better at Low Hb (0.57x), Melanin Catastrophic Confounder (+9.6 g/dL at 0.005), Phase 3 Simulation Gate (+2 more)

### Community 71 - "Phase 4.5 Deep Script"
Cohesion: 0.29
Nodes (9): aggregate(), build_windows(), main(), Phase 4.5, TASK 1: deep models over raw PPG waveforms. Closes the one…, Cache windows for all subjects. `channels` selects wavelength indices., Train one fold. The target is standardised using TRAIN statistics only. Without…, Window predictions -> one prediction per subject (median)., run_condition() (+1 more)

### Community 72 - "Backend Schemas"
Cohesion: 0.28
Nodes (7): PreRegIn, Request and response shapes., RunIn, SubmissionOut, BaseModel, field_validator, pydantic

### Community 73 - "Original Image Search"
Cohesion: 0.33
Nodes (8): black_fraction(), list_rar5(), main(), Path, Phase 1.5, Task 2: exhaustive search for uncropped / full-eye source images. If…, RAR5 variable-length integer: 7 bits per byte, high bit = continue., Return [{name, unpacked_size, is_dir}] for a RAR5 archive., _vint()

### Community 74 - "Illuminant Perturbation Gate"
Cohesion: 0.36
Nodes (8): chroma(), main(), perturbation_for_delta_e(), ndarray, Random illuminant perturbation calibrated to a target dE2000. Returns the…, build_gate(), invert(), run()

### Community 75 - "Grouped Evaluation Builders"
Cohesion: 0.25
Nodes (9): evaluate(), ndarray, Grouped K-fold. Each subject contributes exactly one record, so a subject-level…, build_known_truth(), build_mixed(), main(), DataFrame, The two real-data submissions whose verdicts are already on the record. (+1 more)

### Community 76 - "Upload Routes"
Cohesion: 0.25
Nodes (8): create_prereg(), Upload a predictions CSV, optionally with images. Images arrive either as a zip…, Declare thresholds. Do this BEFORE uploading results, or the report says so., upload(), new_id(), Ids are generated eagerly, not at flush: the upload route needs the id to name…, post, UploadFile

### Community 77 - "App Shell and Routing"
Cohesion: 0.32
Nodes (6): App(), NAV, app_frontend_src_index, CaseStudy(), ref_react_dom_client, react-router-dom

### Community 78 - "Archive and Working Protocol"
Cohesion: 0.32
Nodes (8): docs/archive evidentiary record, Working protocol (append-only logs, tick on artefact), Decision 2026-09-17: CLAUDE.md split into header plus docs/archive, DECISION LOG (section 7), Decision 2026-09-11: imaging arm CLOSED, not to be reopened, docs/archive README: index and split verification, Result 2026-09-11: N1 OVERALL REFUTED, RESULTS LOG (section 8)

### Community 79 - "Image Metadata"
Cohesion: 0.25
Nodes (6): Image, pil, _estimate_jpeg_quality(), ImageMeta, Cheap per-image property extraction. Uses PIL header reads (no full decode) so…, Rough JPEG quality from the luminance quantisation table. Compares the table…

### Community 80 - "Diffuse Reflectance"
Cohesion: 0.25
Nodes (8): Layer, diffuse_reflectance(), layered_reflectance(), Total diffuse reflectance of a semi-infinite turbid medium. Standard diffusion-…, Reflectance of the layered conjunctiva. Layers are combined by an attenuation-…, Pallor: more haemoglobin, less light returned., test_diffuse_reflectance_bounds_and_monotonicity(), test_reflectance_falls_monotonically_with_haemoglobin()

### Community 81 - "Ghana Filename Parsing"
Cohesion: 0.29
Nodes (6): re, ghana_subject_id(), GhanaName, Filename parsing for the Ghana datasets, where the subject identifier is…, Structured view of one Ghana filename., Build the subject key. `merge_series` controls whether e.g. "Anemic-001" and…

### Community 82 - "Ratio Cancellation"
Cohesion: 0.25
Nodes (8): sim_ratio(), ndarray, ratio_feature(), Per-channel ratio, normalised to unit sum. The illuminant cancels in a/b., The Phase 3.5 premise. With a plain mean the illuminant cancels to machine…, A channel-mixing transform (overlapping sensitivities) is NOT cancelled - which…, test_ratio_cancels_a_diagonal_illuminant_exactly(), test_ratio_does_not_cancel_a_non_diagonal_transform()

### Community 83 - "PPG Gate A"
Cohesion: 0.32
Nodes (7): build_feature_table(), main(), DataFrame, ndarray, Phase 4, TASK 0 / GATE A: does the AC/DC normalisation actually cancel? Run and…, Split between-subject variance into Hb-explained and nuisance parts. Uses a…, variance_split()

### Community 84 - "Phase 7 Report"
Cohesion: 0.46
Nodes (7): load(), main(), pct(), Phase 7 reports: reports/statistical_vs_clinical.md and reports/phase7.md.…, row(), write_phase7(), write_statistical_vs_clinical()

### Community 85 - "Simulate RGB Guards"
Cohesion: 0.25
Nodes (8): Convenience wrapper: parameters -> (reflectance spectrum, RGB)., simulate_rgb(), Task 4's two headline sensitivities, pinned as regression guards., Higher Hb means relatively more red - the signal the whole project rests on., Guards the gate result itself. The Phase 3 conclusion is that the colour change…, test_oxygenation_barely_changes_rgb_but_melanin_wrecks_it(), test_rgb_red_ratio_increases_with_haemoglobin(), test_the_haemoglobin_signal_is_small()

### Community 86 - "Phase 1 Audit Script"
Cohesion: 0.43
Nodes (6): human(), main(), md_table(), DataFrame, Phase 1, Task 1 + Task 5: generate reports/phase1_data_audit.md and…, scan_dir()

### Community 87 - "Phase 2 Report"
Cohesion: 0.38
Nodes (4): load(), main(), md_row(), Phase 2, Task 5: generate reports/phase2_calibration.md. Reads every Phase 2…

### Community 88 - "Permutation Labels"
Cohesion: 0.29
Nodes (7): permuted_labels(), ndarray, Permutation i's shuffled labels, as a pure function of (y, subjects, i).…, Reproducibility of permutation i is what makes any resumable or re-runnable…, A subject contributing many rows must move as one, or the null is wrong., test_permutation_labels_depend_only_on_the_index(), test_permutation_shuffles_across_subjects_not_rows()

### Community 89 - "Sample Data Manifest"
Cohesion: 0.33
Nodes (5): files, generated_by, image_dir, image_zip, n_subjects

### Community 90 - "Frontend Runtime Dependencies"
Cohesion: 0.33
Nodes (6): dependencies, framer-motion, gsap, react, react-dom, react-router-dom

### Community 91 - "NPM Scripts"
Cohesion: 0.33
Nodes (6): scripts, build, dev, lint, preview, test

### Community 92 - "Phase 2.5 Report"
Cohesion: 0.47
Nodes (4): load(), main(), Phase 2.5, Task 5: generate reports/phase2_5_specular.md. Verdict thresholds…, row()

### Community 93 - "Contrast Ratios"
Cohesion: 0.53
Nodes (5): _lin(), luminance(), main(), ratio(), Phase 8B - the palette and its measured WCAG contrast ratios. The tokens below…

### Community 94 - "Phase 9A Report"
Cohesion: 0.60
Nodes (5): ci(), f(), main(), Generate `reports/phase9a_screening_metrics.md` from `phase9a/screening.json`.…, signed()

### Community 95 - "Phase 1 Summary"
Cohesion: 0.50
Nodes (4): main(), md_table(), DataFrame, Phase 1, Task 5: reports/phase1_summary.md. Per-dataset sanity tables, the…

### Community 96 - "Phase 4.5 Report"
Cohesion: 0.60
Nodes (4): load(), main(), Phase 4.5, TASK 3: generate reports/phase4_5_deep.md.…, row()

### Community 97 - "Phase 4 Report"
Cohesion: 0.60
Nodes (4): load(), main(), Phase 4, Task 4: generate reports/phase4_ppg_gate.md. Both gate results are…, row()

### Community 98 - "Phase 5 Final Report"
Cohesion: 0.60
Nodes (4): load(), main(), Phase 5, TASK 2: consolidate every result into reports/final_results.md.…, row()

### Community 99 - "Phase 6 Report"
Cohesion: 0.50
Nodes (4): main(), Path, Phase 6, TASK 5: write reports/phase6_audit_harness.md from the artefacts.…, _read()

### Community 100 - "Phase 8B Report"
Cohesion: 0.60
Nodes (4): lh(), main(), Phase 8B report: reports/phase8b_design.md. Palette and contrast from…, row()

### Community 104 - "Contract Error"
Cohesion: 0.67
Nodes (3): ContractError, The submission cannot be audited at all, as opposed to a check declining., ValueError

## Knowledge Gaps
- **136 isolated node(s):** `generated_by`, `n_subjects`, `image_dir`, `image_zip`, `files` (+131 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 748 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AuditInput` connect `Audit Checks and Contract` to `Audit Runner and Report`, `Image Hashing for Checks`, `Audit Package and Prereg`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `load_predictions()` connect `Audit Runner and Report` to `Audit Checks and Contract`, `Contract Error`, `External Audit Ingestion`, `FastAPI Backend Routes`, `Grouped Evaluation Builders`, `Upload Routes`, `Audit Package and Prereg`, `Backend DB and Jobs`, `Harness Validation Cases`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `probe()` connect `Dataset Manifest Builders` to `Image Metadata`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `AuditInput` (e.g. with `run()` and `run()`) actually correct?**
  _`AuditInput` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `load_predictions()` (e.g. with `execute()` and `get_submission()`) actually correct?**
  _`load_predictions()` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `generated_by`, `n_subjects`, `image_dir` to the rest of the system?**
  _136 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Audit Checks and Contract` be split into smaller, more focused modules?**
  _Cohesion score 0.05733397037744864 - nodes in this community are weakly interconnected._