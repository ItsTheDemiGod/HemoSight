# CLAUDE.md completeness audit — 2026-09-12

**Scope.** Every checkbox in section 6 of `CLAUDE.md` (160 boxes: 92 ticked, 68 unticked),
checked against what is on disk. Nothing was fixed before this report was written; the
phase-plan restructure (Task 4) was applied after it, and is described in section 6.

**Method.** Each unticked box was classified from the artefacts, the DECISION LOG and the
gate results already on record. Each ticked box was spot-checked for the script, output
file, report, figure or test it implies. Verified in this session, not read from the
file: the test suite (`133 passed in 9.67 s`), the front-end build (`tsc -b && vite
build`, 2.15 s), the GPU (`nvidia-smi`: 1,636 MiB of 8,188 used, no permutation process
alive), the audit database, network reachability (`pip download reportlab` succeeded)
and the git history.

---

## 1. Headline

| | count |
| --- | --- |
| unticked boxes | **68** |
| — SUPERSEDED by a failed gate or a closed arm | **57** |
| — BLOCKED | **1** |
| — OUTSTANDING | **2** |
| — DONE BUT UNTICKED | **8** |
| ticked boxes | **92** |
| — with a missing or reduced artefact | **3** (none with *no* artefact; details in section 3) |

**Of 68 open boxes, two are real work**: the deferred Phase 6 end-to-end validation
(now unblocked, ~15 min of GPU) and making the Phase 3 empirical-signal figure
reproducible (its computation is not on disk). Everything else is either dead by a
pre-declared gate, already done, or impossible in this environment.

---

## 2. TASK 1 — classification of every unticked box

Legend: **SUPERSEDED** = should not be done, a preceding gate failed; **BLOCKED** =
cannot be done here; **OUTSTANDING** = still to do and worth doing; **DONE BUT UNTICKED**
= done, box never ticked.

### Phase 0

| item | class | evidence / reason |
| --- | --- | --- |
| Initialise the git repository and make the first commit | **DONE BUT UNTICKED** | 4 commits exist: `06aa682`, `9f55c1e` (2026-09-10), `2888583`, `4e6eff7` (2026-09-11). 81 files tracked. **Caveat:** nothing from Phase 4 onward is committed — 32 paths untracked or modified (`app/`, `src/hemosight/audit/`, `src/hemosight/ppg/`, every Phase 4–6 script, report and test, and `CLAUDE.md` itself). |

### Phase 3 — task list

| item | class | evidence / reason |
| --- | --- | --- |
| Task 1: layered conjunctival optical model with every constant cited *(PARTIAL)* | **SUPERSEDED** | Task 0 gate: **3.893 g/dL** MAE at the measured 3.935 dE2000 residual (sourced constants; 3.417 on transcribed) against a >2.0 NOT RECOVERABLE threshold. The partial deliverable exists: `src/hemosight/simulation/constants.py` (3 cited layers), `optical_data.py`. The full layered MC was correctly not built. |
| Task 1: radiative transfer validated against published benchmark cases | **SUPERSEDED** | Same gate. A diffusion forward model (`forward.py`) was enough to produce the gate result; photon transport would not change it. |
| Task 2: validate simulated spectra against published conjunctival/eyelid reflectance | **SUPERSEDED** | Same gate. (Would also be BLOCKED: no published conjunctival spectra are on disk.) |
| Task 3: generate the synthetic corpus | **SUPERSEDED** | Same gate. `data/synthetic/` is empty, correctly — the inversion the corpus would train cannot survive the calibration residual. |

### Phase 3 — original eight-item list

| item | class | evidence / reason |
| --- | --- | --- |
| Assemble chromophore absorption spectra (HbO2, Hb, melanin, water) and scattering with cited sources | **DONE BUT UNTICKED** | `data/raw/optical_constants/` (Prahl haemoglobin, spectralLIB water/scattering/melanin); loaded by `optical_data.py`; Phase 3.5 Task 0 compared them against the transcription (18.8% of points >10% off). Melanin is a fitted power law, flagged sweep-never-fix. |
| Define the layered eyelid/conjunctiva optical model (layers, thickness, BVF, oxygenation) | **DONE BUT UNTICKED** | `constants.DEFAULT_LAYERS` (epithelium / vascular stroma / tarsal plate, cited [5][6][2]); `HB_RANGE`, `OXYGENATION_RANGE`, `BVF_RANGE`, `MELANIN_RANGE`. **Caveat:** thicknesses and BVF still carry the VERIFICATION REQUIRED banner (see section 4). |
| Implement the Monte Carlo photon-transport forward model | **SUPERSEDED** | Task 0 gate. A layered diffusion model was built instead (`forward.py`) and was sufficient to fail the gate. |
| Validate the simulator against published spectra or an analytic limiting case | **SUPERSEDED** | Task 0 gate. The only check made is inversion self-consistency (max 0.0001 g/dL), which is not a validation. |
| Sample Hb 4–18 g/dL and export a synthetic spectral library to `data/synthetic/` | **SUPERSEDED** | Task 0 gate; `data/synthetic/` empty. |
| Collect or fit camera SSFs and illuminant SPDs; project spectra to synthetic RGB | **DONE BUT UNTICKED (reduced)** | camspec database on disk (`data/raw/camera_sensitivities/`, 28 cameras, 400–720 nm) and parsed by `optical_data.py`; used in Phase 4 Gate B. Projection in `forward.py` is through D65 and the **CIE 1931 observer as a camera proxy** — only 2 of 6 nus8 cameras have measured SSFs (DECISION LOG 2026-09-11). |
| Compare synthetic RGB against real conjunctiva pixels; document the sim-to-real gap | **OUTSTANDING (reproducibility)** | The comparison was made and reported — **0.70 dE2000/g/dL empirical on 216 Eyes-Defy subjects vs 0.452 simulated** — but **no script and no output file produce it**. The figure is hard-coded in `scripts/tissue_simulator_gate_report_phase3.py:81`. See section 3. The outstanding work is preserving the computation, not redoing the science. |
| Log the severe-anemia coverage the simulator adds | **SUPERSEDED** | No corpus was generated. |

### Phase 3.5

| item | class | evidence / reason |
| --- | --- | --- |
| Task 2: re-run the Phase 3 gate on ratio features | **SUPERSEDED** | Task 1: best ratio feature (iris/sclera) **10.04 g/dL equivalent** against a >2.0 threshold, 5x over; every ratio worse than the uncorrected sclera. `data/interim/phase3_5/task1_cancellation.json`. |

### Phase 4 (original plan): spectral reconstruction and Hb estimation (N3) — 8 items

| item | class | evidence / reason |
| --- | --- | --- |
| All eight (reconstruction, unmixing, concentration maps, per-image Hb, real-data evaluation, leave-one-site/device-out, N1 ablation, reconstruction residual) | **SUPERSEDED** | The imaging arm is **CLOSED, FINAL** (DECISION LOG 2026-09-11, Phase 4): Phase 3 gate 3.893 g/dL and Phase 3.5 ratio 10.04 g/dL. Each item presupposes the synthetic library (never built) and an inversion the gate showed cannot survive the calibration residual. |

### Phase 5 (original plan): CNN baseline comparison arm — 6 items

| item | class | evidence / reason |
| --- | --- | --- |
| Define / train / evaluate the CNN baseline; colour-feature baseline; comparison table; keep-current protocol | **SUPERSEDED** | Every item is a comparison arm *for the physical model*, which was never built because the Phase 3 gate failed. For the one surviving claim (PPG waveform), Phase 4.5 ran three deep architectures under identical subject-disjoint folds and Phase 4 Task 3 ran the demographic baseline — that is the conventional arm for that claim. |

> ⚠️ **Flag, not a classification.** Section 3 of CLAUDE.md makes "a conventional CNN
> baseline must be built and maintained as the comparison arm for every claim" a HARD
> CONSTRAINT. **No image CNN was ever trained**, and the write-up must say so. Whether a
> cross-site CNN on Eyes-Defy (217 subjects, Italy→India and back, sex and age available
> for all 218) is worth running as a reviewer-proofing step is a judgement for the
> author; it is cheap (GPU free, one phone model, hours not days) but it is not required
> by any surviving claim. Recorded here so the decision is made rather than defaulted.

### Phase 6 (audit harness)

| item | class | evidence / reason |
| --- | --- | --- |
| Task 3: read `/mnt/skills/public/frontend-design/SKILL.md` before writing components | **BLOCKED** | The path does not exist on this machine (Windows; the path is a Linux mount from a different environment) and there is no copy to obtain. The components have since been written, so the step *cannot* now be done "before". It should be closed as not-applicable, not left open. |
| Task 4: end-to-end validation of the three Phase 5 checks against the Phase 4.5 deep model | **OUTSTANDING — now UNBLOCKED** | Deferred because per-subject predictions were never written and the GPU was held. The GPU is free (permutation run 240/240, `perm_extended.pid` process gone, 1,636 MiB in use by the desktop). What it takes is in section 4. |

### Phase 6 (original plan): conformal prediction and abstention (N4) — 8 items

| item | class | evidence / reason |
| --- | --- | --- |
| All eight | **SUPERSEDED** | No estimator to wrap: imaging arm closed (Phase 3/3.5 gates), PPG arm NOT VIABLE (Gate B, best MAE 1.113 vs sex alone 0.831). DECISION LOG 2026-09-12. Already marked NOT APPLICABLE in the file. |

### Phase 7: fairness audit (N5) — 7 items

| item | class | evidence / reason |
| --- | --- | --- |
| Attach skin-tone labels using SCIN | **SUPERSEDED** | Twice over: SCIN was deleted and N5 rebuilt on ITA (DECISION LOG 2026-09-11, Phase 1.5); and there is no estimator whose performance could be stratified. |
| Stratify every headline metric by skin tone and device | **SUPERSEDED** | No estimator. The negative results *are* already stratified by device and lighting where it mattered (segmentation IoU by phone/lighting; Phase 2.5 census by phone; variance decompositions). |
| Report abstention rate by stratum | **SUPERSEDED** | No N4 abstention exists. |
| Decompose any gap into melanin vs illuminant error | **SUPERSEDED (mechanism half done)** | No gap to decompose, but the *mechanism* was measured: Phase 3 Task 4, melanin fraction 0.005 shifts recovered Hb by **+9.6 g/dL** with the illuminant held perfect (`task4_prior_sensitivity.json`). The write-up should carry this as the N5 finding. |
| Use the simulator to test the decomposition where melanin is known | **SUPERSEDED (partially served)** | Same artefact — melanin known by construction, illuminant perfect. Only the melanin half; the illuminant-error half needs an estimator. |
| Compare the gap profile against the CNN baseline | **SUPERSEDED** | Neither exists. |
| Write the audit with skin-tone labelling limits stated | **SUPERSEDED** | Folds into the paper: the three N5 limitations already in section 2 plus the melanin finding. |

### Phase 8: multimodal fusion (N6) — 8 items

| item | class | evidence / reason |
| --- | --- | --- |
| Build the PPG pipeline: load, filter, extract four-wavelength features, per-subject Hb estimate | **DONE BUT UNTICKED** | `src/hemosight/ppg/features.py`, `scripts/ppg_acdc_cancellation_gate_phase4.py` / `ppg_hb_estimation_gate_phase4.py`; `data/interim/phase4/features.csv` (252 subjects, 41+ features incl. per-channel SNR and heart rate); `gate_b.json` holds the per-subject-CV estimates. The estimate is NOT VIABLE, but the pipeline the box asks for exists and ran. |
| Build the nail and palm pipelines | **SUPERSEDED** | No estimator to feed. Also partly BLOCKED: **no palm dataset exists anywhere in the inventory** — the claim text names a modality the project never had data for. Nail data is binary-label-only. |
| Fusion model into one physical estimate | **SUPERSEDED** | Nothing to fuse; no g/dL estimate from any modality. |
| Modality dropout / evaluate every subset | **SUPERSEDED** | As above. |
| Per-modality quality gating | **SUPERSEDED** | Two SQIs were built anyway (Phase 2 image score, AUROC 0.816, rejects 0 of 17; Phase 4 PPG SQI, rejects 17.5% but r with error −0.033) and both were found unusable — recorded as negatives. |
| Demonstrate graceful degradation | **SUPERSEDED** | As above. |
| Propagate uncertainty through fusion; re-verify conformal coverage | **SUPERSEDED** | No N4. |
| Document which subjects have which modalities and the evaluation limits | **DONE BUT UNTICKED** | Phase 1 overlap: conjunctiva/nail roster Jaccard 1.000 (204/204), ~454 paired, binary only; Hb_PPG shares no subject with any image set (`data/interim/overlap/overlap_results.json`; DECISION LOG 2026-09-11 "N6 scoped"). |

### Phase 9: web application — 8 items

| item | class | evidence / reason |
| --- | --- | --- |
| Scaffold the FastAPI backend with SQLite and a PostgreSQL-ready data layer | **DONE BUT UNTICKED** | `app/backend/{main,db,models,schemas,jobs}.py`; `HEMOSIGHT_AUDIT_DB` connection-string override; `SafeJSON` column type. **Built for the audit tool, not the inference app** — ticked with that caveat. |
| Define the inference API: image upload, optional PPG, three-state result | **SUPERSEDED** | No estimator. |
| Scaffold React + TypeScript + Vite + Tailwind | **DONE BUT UNTICKED** | `app/frontend/`, 7 routed pages, builds in 2.15 s, `npm run lint` clean. Same caveat. |
| Capture/upload flow with input quality feedback | **SUPERSEDED** | The audit app uploads CSVs, which is a different thing from image capture with quality feedback. |
| Results view: Hb value, interval, three-state decision, chromophore map | **SUPERSEDED** | No estimator. |
| Three.js / react-three-fiber + Framer Motion | **SUPERSEDED** | Framer Motion is in use in the audit app; Three.js is not in `package.json` and nothing in the surviving product needs 3D. |
| Screening-not-diagnosis framing everywhere a result appears | **SUPERSEDED** | The item is about estimator results. The audit app already carries "Nothing here is a clinical validation" on every page shell (`App.tsx:67`, `Landing.tsx:139`). |
| End-to-end tests covering abstention and missing-modality paths | **SUPERSEDED** | Neither path exists. |

### Phase 10: Flutter mobile application — 7 items

| item | class | evidence / reason |
| --- | --- | --- |
| All seven | **SUPERSEDED** | Everything ports an estimator's capture and results flow that does not exist. Not blocked on tooling: `C:\src\flutter\bin\flutter` is present. `mobile/README.md` is a placeholder. |

---

## 3. TASK 2 — ticked boxes checked against their artefacts

All 92 ticked boxes were mapped to a script, output, report, figure or test. **No ticked
box has nothing behind it.** Three have less behind them than the box implies:

| phase / item | what is on disk | gap |
| --- | --- | --- |
| **Phase 3, Task 2:** "compare simulated RGB against real Eyes-Defy images at matched Hb; report the gap honestly *(DONE in reduced form: empirical 0.70 vs simulated 0.452)*" | The figure appears in `reports/phase3_simulation.md` and is hard-coded as a string in `scripts/tissue_simulator_gate_report_phase3.py:81–101`. | **No script computes it and no file stores it.** No Phase 3 script references Eyes-Defy or palpebral masks; `task0_gate.json` has no empirical key; `reproduce_all.py` has no stage for it. The detail in the report (216 subjects, an n=3 bin at 5.26 excluded) says it was genuinely computed — but in code that was not preserved. This is the load-bearing "signal" number in the 5.6x noise/signal ratio, and it is currently unreproducible. **Worst finding of this audit.** |
| **Phase 2:** "Apply the estimator to the conjunctiva datasets and inspect stability within and across sites" | `data/interim/phase2/eyes_defy_segmentation_quality.csv`; `segmentation_eval.json["eyes_defy"]` (quality 0.811 India / 0.816 Italy, 0% failure). | What is stored is **segmentation quality**, not the illuminant estimate. No per-image illuminant estimate for Eyes-Defy exists on disk, so "stability of the estimator across sites" was never measured — the RESULTS LOG entry already says "this is a confidence measure, not accuracy". Reduced delivery, honestly logged, but the box text overstates it. |
| **Phase 6, Task 2:** "FastAPI backend — upload, run, retrieve, export" | All four endpoints exist; Markdown export works end to end (tested). | **PDF export returns HTTP 501** (`main.py:281–292`) because `reportlab` is not installed. Half of "export". See section 4 — the blocker has lapsed. |

Minor and not defects: Phase 6 Task 1 says "121 passing" — the suite is now **133 passing**
(verified). The Phase 5 Task 1 box says ">=200 permutations of the selected model" —
`harden.json` has n=200 for the selected model and n=240 selection-aware; satisfied.

**A structural defect found while checking, outside the phase plan:** the last three
RESULTS LOG entries (Phase 6 validation; Phase 5 extended run in-progress; Phase 5
extended run complete, all dated 2026-09-12) sit **after section 9 WORKING PROTOCOL**,
not inside section 8 RESULTS LOG. They are findable by search but not by reading the
log. Not moved in this pass; recommended.

---

## 4. TASK 3 — named items

### 4.1 Phase 6 Task 4: end-to-end validation of the three Phase 5 checks against the deep model

**Status: OUTSTANDING and now UNBLOCKED. Closeable.**

*Verified this session:* the extended run is complete (240/240, `perm_extended.log`
ends "elapsed 10.65 h"; PID 11608 is not running; GPU at 1,636 of 8,188 MiB with no
project process). The blocker stated in `reports/phase6_audit_harness.md` lines 160 and
176 no longer holds.

*What is missing:* `scripts/permutation_hardening_phase5.py` computes the 10 per-seed prediction
vectors (`all_preds`) and the seed-averaged `mean_pred` in memory (lines 75–93) and
writes only their summary statistics to `harden.json`. The six candidate models' per-
subject predictions from the selection step are likewise discarded. The harness's
contract (`hemosight.audit.contract`) needs `subject_id, y_true, y_pred`, plus
`y_pred_seed__<k>` for the seed check (minimum 3) and `y_pred__<name>` for selection-
aware permutation, plus `sex`/`age` for the baseline.

*What it takes:*
1. A ~40-line script (or a `--dump-predictions` flag on `permutation_hardening_phase5.py`) that calls
   `hemosight.ppg.cv.fit_predict` for the 10 seeds of `speccnn_660` and once for each
   of the six candidates, and writes one CSV in the contract format to
   `data/interim/phase6/known_truth/phase5_deep_model.csv` (untracked — real Hb).
   **Cost: ~16 CV runs at ~26 s each ≈ 7 min of GPU** (measured: 60 CV runs per
   permutation at ~158 s). Same seeds as `permutation_hardening_phase5.py` (`SEED + s`), so the
   per-seed MAEs should reproduce to the cuDNN tolerance (~0.01).
2. Run `permutation`, `seed_stability`, `subgroup_robustness` (and the demographic
   baseline) over that file through the harness; add it as a known-truth case in
   `validate_audit_harness_phase6.py` so it becomes 16/16.
3. Compare: seed SD ≈ 0.0069 and effect/SD ≈ 11.9 should reproduce; retained-advantage
   fraction should PASS as Phase 5 did. **The permutation p will NOT match 0.0041** —
   the harness permutes labels against fixed predictions, a different null from the
   refitting construction (DECISION LOG 2026-09-12, deviation 3). The verdict is what
   is compared; the report must say so, as it already does for the Phase 4 case.
4. Tick the box; amend the two "deferred" sentences in `phase6_audit_harness.md`.

### 4.2 PDF export returns HTTP 501 (reportlab absent)

**Status: confirmed, and the stated blocker has LAPSED.** `import reportlab` fails in
`.venv`. The code comment says "reportlab is not installed in this environment and there
is no network". **Network is reachable now:** `pip download reportlab --no-deps`
fetched `reportlab-5.0.1-py3-none-any.whl` in seconds (to a temp directory; nothing
was installed, per the report-first instruction). Closing it is `pip install reportlab`,
adding it to `pyproject.toml`, and exercising `to_pdf` once through the endpoint. Note
reportlab 5.x is a major version; `hemosight.audit.report.to_pdf` was written blind
against it and may need a small adjustment.

### 4.3 VERIFICATION REQUIRED banner on layer thicknesses and blood volume fractions

**Status: still standing, correctly.** `constants.py` lines 13–17: haemoglobin, water,
scattering and camera SSFs are sourced from files; **layer thicknesses and BVF (Efron
2009, Zhivov 2006, Jacques 2013) remain hand-transcribed** with no file behind them.
`DEFAULT_LAYERS` = epithelium 32 µm / BVF 0.002; vascular stroma 200 µm / BVF 0.060;
tarsal plate 800 µm / BVF 0.010.

Two things determine how much this matters: (a) Phase 3 Task 4 measured the model's
tolerance — thickness scale 0.8–2.0 and BVF ±30% both stay under 1.0 g/dL error, so a
transcription error in these would have to be large to move any recorded verdict; and
(b) the gate failed by 1.9x, so no plausible correction flips it. **It is a publication
hygiene item, not a scientific risk.** Closing it means re-reading the two primary papers
and recording the page/table each number came from — a network task, which is now
possible. It is not closeable from disk.

### 4.4 Dataset licences: 8 of 10 UNVERIFIED

**Status: confirmed, unchanged.** `reports/dataset_manifest.md` line 5 and the table at
lines 9–16; `reports/phase1_dataset_licences.md` lines 29–36. Verified: optical
constants (OMLC) and camspec. Unverified: nus8, SBVPI, MOBIUS, CP-AnemiC, both Ghana
Mendeley sets, Eyes-Defy, Hb_PPG. None ships a licence file. **Now closeable** — each
needs its landing page read (Mendeley DOIs `nt7r8hv2pz` and `2xx4j3kjg2` are likely
CC BY 4.0; SBVPI/MOBIUS are typically research-agreement; nus8 research-use). This is a
network task that was impossible before and is possible now. It gates publication (the
paper must state terms) but does not gate any result. No dataset-derived file is tracked
in git (test-enforced), so there is no current exposure.

### 4.5 Junk pre-registration rows titled "t"

**Status: confirmed — and there are three test rows, not two.**
`data/interim/phase6/service/audit.db`, table `preregistrations`, 6 rows:

| id | title | declared_at |
| --- | --- | --- |
| `cae40bcaf1224515` | `t` | 2026-09-12 03:40:56 |
| `13216591daf3430d` | `t` | 2026-09-12 03:41:17 |
| `6647d126d843425f` | `e2e` | 2026-09-12 05:42:18 |
| three rows | `HemoSight PPG audit — mixed fault sample` | 05:33, 05:37, 05:48 |

The two `t` rows and the `e2e` row are smoke-test artefacts (thresholds
`{"permutation": {"alpha": 0.05}}` only). The three real rows are themselves near-
duplicates differing only in `min_effect_to_seed_sd_ratio` (5 / 3 / 5). The database is
untracked development state under `data/interim/`, so nothing is published; cleaning it
is a `DELETE` of three rows or a fresh `audit.db`. Also 23 submissions and 13 runs.
Closeable in a minute. **The endpoint has no title validation** — a one-character title
was accepted; worth a minimum-length check if the tool is ever used by anyone else.

### 4.6 The frontend-design SKILL.md checkbox

**Status: BLOCKED, permanently, and now moot.** The path is a Linux mount from another
environment and does not exist here; there is no source to obtain it from. The
components it was meant to precede have been written, built and lint-checked. Leaving it
open implies it might be done; it should be marked closed-as-not-applicable, with the
existing DECISION LOG entry (2026-09-12) as the record. **This audit marks it that way
in the restructure; it is not ticked** because the work was not done.

---

## 5. TASK 5 — what remains, in priority order

**The answer is: the write-up, plus a short list of hygiene items — and nothing else of
substance.** No open box in the plan represents modelling work that a pre-declared gate
left alive.

1. **Make the Phase 3 empirical signal reproducible** (0.70 dE2000/g/dL on 216
   Eyes-Defy subjects). It is the numerator of the project's central noise/signal
   ratio and currently exists only as prose. ~1 hour: a script writing
   `data/interim/phase3/empirical_signal.json`, a stage in `reproduce_all.py`, and the
   report reading the number from the file. If the recomputed figure differs, the
   RESULTS LOG gets a correction entry.
2. **Close Phase 6 Task 4** (deep-model end-to-end validation). ~7 min GPU + ~1 hour.
   Section 4.1.
3. **Commit.** Everything after Phase 3.5 is uncommitted — Phases 4, 4.5, 5, 6, the
   audit package, the web app, and CLAUDE.md. A disk failure loses the project's actual
   contribution.
4. **Publication hygiene, all now network-possible:** verify the 8 licences (4.4);
   re-read Efron 2009 / Zhivov 2006 and lift the banner or record what was found (4.3);
   install reportlab and close the 501 (4.2); delete the three test pre-registration
   rows (4.5); move the three stray RESULTS LOG entries into section 8.
5. **The write-up.** `reports/final_results.md` already holds the master table, nine
   mechanisms, limitations and a corrections table; the paper is an editorial task over
   material that exists. It must state that no image CNN was trained (section 3 hard
   constraint unmet for the imaging arm) and that the Phase 2 diagnosis is incomplete
   (specular vs sclera p = 0.29).
6. **Optional, author's call, not required by any claim:** a cross-site CNN baseline on
   Eyes-Defy with sex/age beside it, purely to pre-empt the reviewer question. Cheap;
   listed last deliberately.

---

## 6. What the restructure (Task 4) changed in CLAUDE.md

Applied after this report was written. Section 6 of CLAUDE.md now has:

- A **state-at-a-glance table** at the top of the phase plan: one row per phase, its
  status (COMPLETE / CLOSED AT GATE / SUPERSEDED / OPEN), the gate that closed it, and
  the count of genuinely open items.
- A **legend** for the inline markers: `🔴 SUPERSEDED —`, `⛔ BLOCKED —`,
  `🟡 OUTSTANDING —`, each followed by the gate/blocker in one line.
- Every unticked box annotated inline with its class and reason. **No box was deleted
  and no text was removed;** the annotations are appended in italics after the original
  wording, matching the convention already used in Phase 3 and 6.
- The **8 DONE BUT UNTICKED boxes ticked**, each with its evidence appended.
- The three reduced-artefact ticked boxes (section 3) annotated `⚠️`, left ticked.
- A DECISION LOG entry dated 2026-09-12 recording the restructure, per the WORKING
  PROTOCOL rule that no plan item is changed silently.
