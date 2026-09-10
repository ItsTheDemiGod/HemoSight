# CLAUDE.md — HemoSight

**This document governs all work in this repository.** It is the source of truth for
scope, claims, constraints, and sequencing. Read it fully before starting any task.
If a request conflicts with this document, say so before acting.

---

## 1. PROJECT IDENTITY

HemoSight is a non-invasive anemia screening system that estimates blood hemoglobin
from ordinary photographs (palpebral conjunctiva, palm, fingernail) and optionally
fingertip PPG. It is a **research project first and a deployable product second**.
Web application first, Flutter mobile app second.

### The core scientific bet

Treat the photograph as a **SPECTROSCOPIC MEASUREMENT, not as pixels for a CNN**.
Recover a reflectance spectrum from RGB, unmix it into chromophore concentrations
(hemoglobin, oxyhemoglobin, melanin), and report hemoglobin in g/dL with a calibrated
uncertainty interval.

Every design decision is answerable to that bet. If a proposed step cannot be traced
back to a physical quantity, it needs justification in the DECISION LOG.

---

## 2. THE SIX NOVELTY CLAIMS

These drive every design decision.

**N1. Calibration-free spectral super-resolution.** Use the sclera as an endogenous
white reference to estimate the scene illuminant, removing the per-camera spectral
profiling and per-use radiometric calibration that currently blocks
hyperspectral-reconstruction methods from field deployment. **THIS IS THE HEADLINE
CLAIM.**

**N2. Monte Carlo forward model** of layered eyelid tissue generates synthetic
reflectance spectra across Hb 4-18 g/dL, oxygenation, blood volume fraction, layer
thickness and melanin; projected through camera spectral sensitivity curves and
illuminant SPDs to synthetic RGB. Train on simulation, test on real. This supplies
severe-anemia cases that no public dataset contains.

**N3. Physical interpretability.** Output hemoglobin concentration in g/dL and
oxygenation, not a class probability. Explanations are chromophore concentration maps,
not saliency heatmaps.

**N4. Conformal prediction with selective abstention over a physical quantity.**
Three-state output: screen negative / screen positive-refer / cannot decide. Spectral
reconstruction residual provides a principled non-conformity signal.

**N5. Mechanistic fairness audit.** Report performance stratified by skin tone and
source device, and DECOMPOSE any gap into melanin absorption versus illuminant
estimation error.

**N6. Multimodal fusion with graceful degradation.** Conjunctiva, palm, nail and PPG
are all measurements of the same molecule through different optical paths. Fuse into
one physical estimate. Train with modality dropout so missing or low-quality inputs
degrade gracefully rather than failing.

---

## 3. HARD CONSTRAINTS

These are not negotiable and not subject to convenience.

- **Public datasets ONLY. No new data will ever be collected. No human subjects.**
- **All evaluation is retrospective. The project must NEVER claim clinical validation.
  All user-facing output must be framed as screening, not diagnosis.**
- **Cross-site and cross-device generalization must be reported honestly, including
  negative results. Single-site accuracy numbers are considered worthless.**
- **A conventional CNN baseline must be built and maintained as the comparison arm for
  every claim.**

### Operating rules that follow from the constraints

- `data/raw/` is **READ-ONLY**. Never write, rename, move or delete inside it. All
  derived data goes to `data/interim/`, `data/processed/` or `data/synthetic/`.
- Splits are **patient-level and site-aware**, never image-level. An image-level split
  on these datasets is a leak, because subjects contribute multiple images.
- No result is reportable until it has been produced on a held-out site or device.
- Negative results are recorded in the RESULTS LOG with the same weight as positive ones.

---

## 4. DATASET INVENTORY

All under `data/raw/`. Contents below reflect a shallow scaffold-time inspection; the
authoritative audit is Phase 1.

| Folder | What it is | Role |
| --- | --- | --- |
| `nus8` | NUS 8-camera color constancy benchmark. Linear PNGs, colorchecker masks, ground-truth illuminant `.mat` per camera. | Validates N1 |
| `SBVPI` | High-resolution periocular sclera segmentation dataset. No Hb labels. | Sclera segmentation |
| `MOBIUS` | Mobile-captured sclera segmentation under varied conditions. No Hb labels. | Stress-tests sclera segmentation |
| `CP-AnemiC dataset` | Conjunctival pallor, Ghana, children, with Hb values. | Hb labels, conjunctiva |
| `Application of Machine Learning in Detecting Iron Deficiency Anemia Using Conjunctiva image Dataset from Ghana` | Ghana conjunctiva dataset (Mendeley `nt7r8hv2pz`). | Hb / anemia labels, conjunctiva |
| `Detection of Anemia using Colour of the Fingernails Image Datasets from Ghana` | Ghana fingernails dataset (Mendeley `2xx4j3kjg2`). | Nail modality (N6) |
| `dataset anemia` | Contents to be identified during the data audit. | TBD — see below |
| `Hb_PPG_Dataset` | 252 subjects, four-wavelength PPG (660/730/850/940 nm), 200 Hz, 60 s, venous-blood Hb reference via HemoCue. CSV per subject plus `subject information.xlsx`. | PPG modality (N6) |
| `scin-main` | SCIN dermatology dataset repo. Skin tone labels: self-reported Fitzpatrick, dermatologist-estimated Fitzpatrick, Monk Skin Tone. | Fairness (N5) |
| Eyes-Defy-Anemia | Expected but may not yet be present under that name; check for it. | Conjunctiva, multi-site |

### 🔴 KNOWN RISK — participant overlap (highest-priority Phase 1 item)

**CP-AnemiC and the Ghana conjunctiva dataset share authors and collection hospitals
and may contain overlapping participants. Any cross-site claim built on treating them
as independent is invalid until overlap is ruled out.**

Until an overlap check has been run and logged, these two sources are treated as **one
site**. No paper text, figure or table may describe them as independent. Any result
computed across them before the check is provisional and must be labelled as such in
the RESULTS LOG.

### Scaffold-time observations (to confirm or overturn in Phase 1)

- `dataset anemia` contains `India/` and `Italy/` subject folders whose files follow
  the pattern `<id>_palpebral.png` and `<id>_forniceal.png` alongside a source `.jpg`.
  This strongly suggests it **is** the Eyes-Defy-Anemia dataset under a different
  folder name. Confirm in Phase 1 before relying on it; if confirmed, it supplies the
  second and third sites and is the main lever for honest cross-site evaluation.
- `nus8` currently has three extracted cameras (`Canon600D`, `NikonD5200`,
  `SamsungNX2000`), each with `png/`, `mask/` and `groundtruth.mat`, plus a
  `raw_downloads/` folder of archives. The remaining cameras of the 8-camera benchmark
  appear not to be extracted. Confirm coverage in Phase 1 — the N1 cross-device
  argument is weaker with three cameras than with eight.
- SBVPI and MOBIUS carry no Hb labels; they are segmentation-only resources.

---

## 5. TECH STACK

- **Core:** Python 3.12, PyTorch, NumPy, SciPy, scikit-learn, OpenCV, rawpy, pandas,
  matplotlib, colour-science
- **Backend:** FastAPI. Database: SQLite for development, PostgreSQL-ready.
- **Frontend:** React + TypeScript + Vite, Tailwind CSS, Framer Motion for animation,
  Three.js / react-three-fiber for 3D. Target a polished, modern, animated interface.
- **Mobile (later phase):** Flutter, located at `C:\src\flutter`
- **Experiment tracking:** local, file-based. No cloud services requiring accounts.
- **Platform:** Windows. Use Windows-compatible paths and commands throughout.

---

## 6. PHASE PLAN

Every task starts unchecked. Tick a checkbox only when the task is actually complete
and its output exists on disk.

### Phase 0: Scaffold
- [ ] Create the repository directory structure
- [ ] Write `pyproject.toml` pinning Python 3.12 and the core dependencies
- [ ] Write `.gitignore` excluding `data/`, caches, model artefacts and `node_modules`
- [ ] Write `README.md` pointing to CLAUDE.md as the source of truth
- [ ] Write this CLAUDE.md with claims, constraints, inventory, phase plan and logs
- [ ] Create and populate the Python virtual environment
- [ ] Verify the environment imports the package and passes the smoke test
- [ ] Initialise the git repository and make the first commit

### Phase 1: Data audit, manifests, overlap check, patient-level splits
- [ ] Inventory every dataset: file counts, formats, resolutions, colour encoding, EXIF and device metadata
- [ ] Identify the contents of `dataset anemia` and confirm or refute that it is Eyes-Defy-Anemia
- [ ] Parse every Hb label source into one tidy `labels` table (subject, site, Hb g/dL, age, sex, device, modality)
- [ ] Build a per-dataset image manifest in `data/interim/manifests/` with a stable subject ID and provenance for every file
- [ ] **Run the CP-AnemiC / Ghana-conjunctiva overlap check** (perceptual hashing, EXIF timestamps, filename structure, subject metadata) and log the verdict
- [ ] Define and freeze patient-level, site-aware train/calibration/test splits; write them to `data/processed/splits/`
- [ ] Characterise label distributions per site: Hb range, anemia prevalence, severe-anemia count, class balance
- [ ] Record dataset licences and redistribution terms; confirm no data is committed to git

### Phase 2: Sclera segmentation and illuminant estimation (N1)
- [ ] Build loaders for SBVPI and MOBIUS with their segmentation masks
- [ ] Train or adapt a sclera segmentation model; report IoU on SBVPI and on MOBIUS separately
- [ ] Implement sclera-as-white-reference illuminant estimation from a segmented region
- [ ] Validate illuminant estimation on `nus8` against ground-truth illuminants (angular error), per camera
- [ ] Compare against standard colour-constancy baselines (grey-world, max-RGB, grey-edge) on the same split
- [ ] Quantify sensitivity to mask error, specular highlights, scleral yellowing and vessel coverage
- [ ] Apply the estimator to the conjunctiva datasets and inspect stability within and across sites
- [ ] Write up the calibration-free argument with its failure modes stated explicitly

### Phase 3: Monte Carlo tissue simulator (N2)
- [ ] Assemble chromophore absorption spectra (HbO2, Hb, melanin, water) and tissue scattering parameters with cited sources
- [ ] Define the layered eyelid/conjunctiva optical model (layer count, thickness ranges, blood volume fraction, oxygenation)
- [ ] Implement the Monte Carlo photon-transport forward model producing diffuse reflectance spectra
- [ ] Validate the simulator against published reflectance spectra or an analytic limiting case
- [ ] Sample the parameter space across Hb 4-18 g/dL and export a synthetic spectral library to `data/synthetic/`
- [ ] Collect or fit camera spectral sensitivity curves and illuminant SPDs; project spectra to synthetic RGB
- [ ] Compare the synthetic RGB distribution against real conjunctiva pixels and document the sim-to-real gap
- [ ] Log the severe-anemia coverage the simulator adds relative to the real data

### Phase 4: Spectral reconstruction and Hb estimation (N3)
- [ ] Implement RGB-to-reflectance-spectrum reconstruction trained on the synthetic library
- [ ] Implement chromophore unmixing from the reconstructed spectrum to Hb, HbO2 and melanin
- [ ] Produce per-pixel chromophore concentration maps as the explanation artefact
- [ ] Aggregate pixel-level estimates to a per-image Hb value in g/dL with an uncertainty estimate
- [ ] Evaluate on real data with MAE, bias, Bland-Altman limits of agreement and correlation, per site
- [ ] Run leave-one-site-out and leave-one-device-out evaluation; report the drop honestly
- [ ] Ablate the N1 illuminant estimation to show what calibration-free costs or buys
- [ ] Record the spectral reconstruction residual per image for downstream use in N4

### Phase 5: CNN baseline comparison arm
- [ ] Define the baseline: standard backbone, conjunctiva crop input, Hb regression head
- [ ] Train the baseline under identical splits, preprocessing and augmentation budget
- [ ] Evaluate with the identical metric suite, including leave-one-site-out
- [ ] Add a colour-feature baseline (mean/percentile RGB or HSV statistics plus a shallow regressor)
- [ ] Build a single comparison table that every subsequent claim must cite
- [ ] Establish the protocol for keeping the baseline current whenever the physical model changes

### Phase 6: Conformal prediction and abstention (N4)
- [ ] Carve a dedicated calibration split, disjoint from training and test at patient level
- [ ] Implement split conformal prediction intervals over the Hb estimate
- [ ] Verify empirical coverage against the nominal level, overall and per site
- [ ] Define the non-conformity signal from the spectral reconstruction residual and justify it
- [ ] Implement the three-state decision rule: screen negative / screen positive-refer / cannot decide
- [ ] Plot accuracy versus abstention rate and choose an operating point with a stated rationale
- [ ] Test coverage under distribution shift (unseen site, unseen device) and report the degradation
- [ ] Compare against the CNN baseline equipped with the same conformal wrapper

### Phase 7: Fairness audit (N5)
- [ ] Attach skin tone labels using SCIN (self-reported Fitzpatrick, dermatologist Fitzpatrick, Monk Skin Tone); document how labels transfer to the anemia datasets and where they cannot
- [ ] Stratify every headline metric by skin tone and by source device
- [ ] Report abstention rate by stratum, not only accuracy
- [ ] Decompose any performance gap into a melanin-absorption component and an illuminant-estimation-error component
- [ ] Use the simulator to test the decomposition on synthetic data where true melanin is known
- [ ] Compare the gap profile of the physical model against the CNN baseline
- [ ] Write the audit with the limits of the skin-tone labelling stated plainly

### Phase 8: Multimodal fusion (N6)
- [ ] Build the PPG pipeline: load `Hb_PPG_Dataset`, filter, extract four-wavelength features, produce a per-subject Hb estimate
- [ ] Build the nail and palm pipelines against their datasets
- [ ] Define the fusion model that combines modalities into one physical Hb estimate rather than an ensemble average
- [ ] Train with modality dropout and evaluate every subset of available modalities
- [ ] Add per-modality quality gating so low-quality inputs are down-weighted rather than trusted
- [ ] Demonstrate graceful degradation: performance versus number of available modalities
- [ ] Propagate uncertainty through fusion and re-verify conformal coverage
- [ ] Document which subjects have which modalities and the resulting evaluation limits

### Phase 9: Web application
- [ ] Scaffold the FastAPI backend with SQLite and a PostgreSQL-ready data layer
- [ ] Define the inference API: image upload, optional PPG, three-state result with interval
- [ ] Scaffold the React + TypeScript + Vite frontend with Tailwind
- [ ] Build the capture and upload flow with input quality feedback
- [ ] Build the results view: Hb value, uncertainty interval, three-state decision, chromophore map
- [ ] Add the Three.js / react-three-fiber visualisation and Framer Motion transitions
- [ ] Enforce screening-not-diagnosis framing and the no-clinical-validation disclaimer everywhere a result appears
- [ ] Add end-to-end tests covering the abstention path and the missing-modality path

### Phase 10: Flutter mobile application
- [ ] Verify the Flutter toolchain at `C:\src\flutter` and scaffold the project in `mobile/`
- [ ] Implement camera capture with on-device quality checks (focus, exposure, sclera visibility)
- [ ] Integrate with the backend API, including offline and failure states
- [ ] Port the results view with parity to the web three-state output
- [ ] Evaluate on-device versus server-side inference and record the decision
- [ ] Test across a range of phone cameras and log the cross-device behaviour
- [ ] Carry the screening-not-diagnosis framing into every mobile surface

---

## 7. DECISION LOG

Dated entries recording any design decision, deviation from this plan, or changed
assumption. Append only. Never delete an entry; supersede it with a newer one that
says what changed and why.

Format: `### YYYY-MM-DD — Title`, then **Decision**, **Rationale**, **Alternatives
considered**, **Consequences**.

### 2026-09-10 — Repository scaffolded
**Decision.** Created the directory structure, `pyproject.toml`, `.gitignore`,
`README.md` and this CLAUDE.md. One `src/hemosight/` submodule per novelty claim, plus
`io`, `baseline` and `evaluation`.
**Rationale.** Mapping submodules onto claims keeps the code answerable to the claims,
and makes an empty module a visible signal that a claim is unsupported.
**Alternatives considered.** A flat `src/` layout; rejected because it hides which
claim a piece of code serves.
**Consequences.** `hemosight.io` shadows the stdlib `io` name inside the package.
Python 3 absolute imports make this safe, but code inside `hemosight/` must not rely on
implicit relative imports.

### 2026-09-10 — `dataset anemia` provisionally identified as Eyes-Defy-Anemia
**Decision.** Recorded the folder as *probably* Eyes-Defy-Anemia rather than renaming
it or treating the identification as settled.
**Rationale.** It contains `India/` and `Italy/` subject folders with `_palpebral` and
`_forniceal` mask files, matching the published structure. But `data/raw/` is
read-only and the identification is inferred from folder shape alone.
**Alternatives considered.** Treating it as confirmed; rejected because a
mis-identified site would corrupt every cross-site claim downstream.
**Consequences.** Phase 1 must confirm it before any cross-site result uses it.

### 2026-09-10 — CP-AnemiC and Ghana conjunctiva treated as one site until proven otherwise
**Decision.** Until the overlap check runs, the two Ghana sources count as a single
site for every split and every metric.
**Rationale.** The failure mode of wrongly assuming independence (an invalid cross-site
claim, discovered late) is far worse than the failure mode of wrongly assuming
dependence (a conservative result that improves when the check clears them).
**Alternatives considered.** Proceeding as independent and checking later; rejected
because results computed under a wrong assumption tend to survive into write-ups.
**Consequences.** Cross-site evaluation depends on Eyes-Defy-Anemia being usable until
the overlap check completes.

---

## 8. RESULTS LOG

Dated entries recording **every** metric produced, including failures and negative
results. A run that produced a bad number is a result. A run that crashed after
consuming a day is a result. Append only; never delete an entry.

Format: `### YYYY-MM-DD — Experiment name`, then **Config** (script, config file,
commit), **Data** (split, sites, n), **Metric(s)**, **Interpretation**, **Status**
(provisional / confirmed / superseded).

*No results yet. Phase 0 produces no metrics.*

---

## 9. WORKING PROTOCOL

After completing any task:

1. **Tick its checkbox in CLAUDE.md.** A task is complete when its output exists on
   disk, not when the code is written.
2. **Record any deviation in the DECISION LOG**, dated, with the rationale.
3. **Record any metric in the RESULTS LOG**, dated, including failures and negative
   results.
4. **Never delete a log entry.** Supersede it with a newer entry instead.
5. **Never silently change a phase plan item.** Editing or removing a task requires a
   DECISION LOG entry saying what changed and why.

Additional standing rules:

- Never write to `data/raw/`.
- Never split at image level; splits are patient-level and site-aware.
- Never report a single-site number as a headline result.
- Never describe any output as diagnostic, validated, or clinically approved.
- Keep the CNN baseline current: if the physical model changes, the comparison arm is
  re-run before the new number is reported.
- When a result is worse than the baseline, log it and say so plainly. That is the
  point of having a baseline.
