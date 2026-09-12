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

## 2. THE NOVELTY CLAIMS

These drive every design decision.

> **Revised 2026-09-11 (Phase 1.5).** N1 was split into three sub-claims, N2's
> justification was corrected, N5 was rebuilt without SCIN, and N6 was scoped to what
> the data actually supports. The **original wording of every changed claim is preserved
> verbatim in the DECISION LOG** — nothing was deleted. Each revision cites the Phase 1
> finding that forced it.

### CLAIM HIERARCHY (restructured 2026-09-11 after Phase 2.5 refuted N1)

| rank | claim | status |
| --- | --- | --- |
| ~~**CO-PRIMARY (imaging arm)**~~ | N3 + N4 from photographs | 🔴 **CLOSED, FINAL (Phase 3.5)** — four approaches refuted, each with a mechanism |
| ~~**CO-PRIMARY (PPG arm)**~~ | N3 + N4 from four-wavelength PPG | 🔴 **NOT VIABLE (Phase 4)** — negative R², loses to the population mean; sex alone beats it by 30% |
| **SECONDARY** | **N1** — as a **negative result plus a practical recommendation** | REFUTED as a method; the diagnosis stands |
| supporting | **N2** — Monte Carlo forward model | unchanged in substance (Phase 3) |
| supporting | **N5** — mechanistic fairness audit | unchanged in substance |
| supporting | **N6** — multimodal fusion, scoped | unchanged in substance |

> ## 🔴 FINAL STATUS — EVERY REPRESENTATION TESTED (2026-09-11, after Phase 4.5)
>
> **Both modalities have been tested to pre-declared gates. Neither yields a usable
> haemoglobin estimator. The deep-learning hole is now closed with evidence.**
>
> | # | modality | representation | phase | verdict | key number |
> | --- | --- | --- | --- | --- | --- |
> | 1 | Imaging | Sclera as absolute white reference | 2 | **REFUTED** | loses to grey-world, p~3e-8 |
> | 2 | Imaging | Corneal specular highlight | 2.5 | **REFUTED** | no better than sclera, p=0.29 |
> | 3 | Imaging | Absolute colorimetric Hb inversion | 3 | **NOT RECOVERABLE** | signal 0.45 (sim) / **0.84** (measured, CI 0.57-1.17) vs 3.9 dE2000 noise = 4.7x *(corrected 2026-09-12; was "0.45-0.70")* |
> | 4 | Imaging | Illuminant-free within-image ratio | 3.5 | **REFUTED** | reference within/between = 1.447 |
> | 5 | PPG | AC/DC + ratio-of-ratios features | 4 | **NOT VIABLE** | R² **-0.025**; permutation **p=0.978** |
> | 6 | PPG | Raw waveform, 3 deep architectures | 4.5 | **NOT VIABLE** | best MAE 1.113; **sex alone 0.831** |
> | 7 | Imaging | **Conventional CNN baseline** (ResNet-18, Eyes-Defy, the §3 comparison arm) | 6.5 | **MARGINAL** | MAE 1.301; site+sex+age alone 1.273; image adds +0.08; cross-site italy_to_india 1.96, india_to_italy 1.99 |
> | 8 | Imaging | **Controlled capture** (studio residual 1.06 dE2000 vs 3.94 uncontrolled) | 7 | **MARGINAL** | gate MAE 1.04 g/dL at the measured studio residual; VIABLE needs < 0.99; Eyes-Defy (fixed LED) colour model 1.34 - refutation restated in two parts |
>
> **The one positive claim survived Phase 5 hardening** (selection-aware permutation, **empirical p <= 0.0041 at n=240**, z=-4.96, 11.9x the seed SD) and remains clinically useless: ~0.05 g/dL better than a constant. The p is still the FLOOR 1/(n+1) - zero of 240 permutations reached the real value - so it is a bound, not a measurement.
>
> **The benchmark that beats everything: sex alone, MAE 0.831 g/dL.** No method in six
> attempts across two modalities beats a single binary demographic variable.
>
> **One genuine positive, precisely bounded.** The raw PPG waveform *does* carry
> haemoglobin-correlated information that AC/DC features discard — a spectrogram CNN is
> distinguishable from chance at **z = -4.72**. It improves on predicting a constant by
> **0.054 g/dL** and separates no WHO severity band. Real, significant, useless. Writing
> "deep learning found nothing" would be false; writing "deep learning worked" would be
> far more false.
>
> **The project's contribution is the body of negative results and their mechanisms** —
> six refutations, thresholds declared before every experiment, cross-device and
> cross-subject validation throughout, and a demographic baseline that exposes how
> easily an apparently working estimator is really a sex classifier. That last point
> alone is a contribution to a literature that frequently omits it.
>
> **Nothing further should be built. What remains is the write-up.**

**Why the PPG arm was promoted to co-primary (2026-09-11, Phase 3.5 Task 4).**
`Hb_PPG_Dataset` is **not subject to the Phase 3 failure**, and the reason is
structural rather than incidental:

* **Four narrow wavelengths (660/730/850/940 nm), not three broad overlapping RGB
  channels** — the measurement is closer to spectroscopy than to photography.
* **A controlled source.** The LEDs are the illuminant. There is no ambient illuminant
  to estimate, so the entire error term that defeated Phases 2, 2.5 and 3 — recovering
  an unknown illuminant from the scene — **does not exist** in this modality.
* **It is the project's best-labelled data:** 252 subjects with venous-blood HemoCue
  reference, against 217 usable Eyes-Defy images. It is also, after the Phase 1.5
  arbitration rejected the entire Ghana pool, one of only two trustworthy Hb sources
  in the project (the other being Eyes-Defy, 217 rows).

The Phase 3 gate result is specific to **ambient-light RGB photography**, not to
non-invasive haemoglobin estimation in general. That distinction is the reason this
project still has a viable primary claim.

Scope change only — **no PPG model has been built yet**.

**Why the headline moved.** N1 was the headline claim. Phase 2.5 refuted it: two
independent endogenous ocular references (sclera, corneal specular highlight) were
tested rigorously on the same held-out-iris protocol and **both lose to grey-world**, a
whole-image statistic needing no segmentation, reference surface or anatomy. The
project's remaining and now primary contribution is the physical estimation pipeline
itself — reporting haemoglobin as a physical quantity with an honest uncertainty
interval and a principled abstention, rather than a class probability.

**N1's secondary contribution, stated positively:**
1. A rigorous negative result — endogenous ocular white references do not support
   calibration-free colour correction on mobile captures, measured on 100 subjects
   across 3 devices and 3 lighting conditions.
2. A practical recommendation — **grey-world on a tight periocular crop**, which
   *improves* as the field of view narrows (**6.076 → 3.935 ΔE2000 at 25% FOV**),
   because a wide frame is skin-dominated while a periocular crop is better balanced.
   This is the normalisation every later phase uses.

> ⚠️ **The Phase 2 diagnosis is INCOMPLETE and must not be presented as settled.**
> Phase 2 attributed the sclera's failure to inter-individual reflectance variance.
> Phase 2.5 then removed that term entirely by using a specular reference — and the
> result did not improve: **specular vs sclera p = 0.29, no significant difference.**
> Inter-individual reflectance variance is therefore **not the sole limiting factor**.
> Something else contributes and has not been identified. Any write-up must say so.

### N1 — Calibration-free spectral super-resolution (~~THE HEADLINE CLAIM~~ — **REFUTED**)

> 🔴 **REFUTED 2026-09-11 (Phase 2.5). The claim below is retained verbatim as the
> hypothesis that was tested; it is NOT a description of a working method.**
>
> Two independent endogenous ocular references were tested on the same held-out-iris
> protocol. Neither beats grey-world, a whole-image statistic needing no segmentation,
> no reference surface and no anatomy: grey-world **6.076** dE2000, specular+sclera
> 7.047, sclera 7.427, specular 7.821, no correction 9.530. Specular and sclera are
> statistically indistinguishable (p = 0.29), so removing the per-subject reflectance
> term — the bottleneck Phase 2 identified — did not help. Grey-world's margin *widens*
> under the tight crops deployment implies (3.935 dE2000 at 25% field of view).
>
> **The contribution of N1 is now the DIAGNOSIS, not the method:** a quantified account
> of why endogenous ocular white references fail, with the failure attributed to
> inter-individual reflectance variance (10% scleral yellowing = 4.40 deg) rather than
> to segmentation (31 px mask perturbation = 0.40 deg) or estimation mathematics
> (0.666 deg given a known reflectance, six sensors). **N1a survives intact.** See
> `reports/phase2_5_specular.md` and the DECISION LOG.
>
> Downstream colour normalisation uses **grey-world on a tight periocular crop**.

Use the sclera as an endogenous white reference to estimate the scene illuminant,
removing the per-camera spectral profiling and per-use radiometric calibration that
currently blocks hyperspectral-reconstruction methods from field deployment.

Phase 1 found that the two largest conjunctiva datasets are pre-segmented cutouts with
the sclera removed. That does **not** invalidate N1; it invalidates treating N1 as a
single end-to-end claim. N1 is therefore three sub-claims, each with its own dataset and
its own metric:

**N1a — Illuminant estimation accuracy across sensors.**
Validated on `nus8`: 6 cameras, 1,265 images, ground-truth illuminants.
*Metric:* angular error and ΔE2000 against the colorchecker-derived illuminant.
The colorchecker must be masked out of the input using `cc_coords`, or the answer leaks
into the estimate.

**N1b — The sclera is a valid endogenous white reference across devices and lighting.**
Validated on `MOBIUS` (3 phones × 3 lighting conditions × 100 subjects) and `SBVPI`.
**No haemoglobin labels are required for this test**, which is why it can use the only
datasets that have real device diversity.
*Protocol — self-consistency.* For one subject, images captured under different phones
and lighting conditions depict the same tissue, so a valid white reference should make
their corrected colour agree. Report the **ΔE2000 spread across conditions, per subject,
before versus after sclera-referenced correction**, on conjunctival/scleral colour.
*Controls:* grey-world, white-patch, and a no-correction baseline. The claim holds only
if sclera-referenced correction reduces spread by more than those.

**N1c — Sclera-referenced correction improves haemoglobin estimation end to end.**
Validated on **Eyes-Defy-Anemia only**.
*Metric:* Hb MAE, bias, and Bland-Altman limits, with and without the correction.
**Hard limitation, to be stated in every claim built on N1c: 218 subjects, 2 sites, and
2 regional variants of a single Samsung Galaxy S6 (`SM-G920F`, `SM-G920I`). No severe
cases (minimum 7.0 g/dL).** N1c is the narrowest of the three and must never be reported
without those numbers attached.

### N2 — Monte Carlo forward model of layered eyelid tissue

Generates synthetic reflectance spectra across Hb 4-18 g/dL, oxygenation, blood volume
fraction, layer thickness and melanin; projected through camera spectral sensitivity
curves and illuminant SPDs to synthetic RGB. Train on simulation, test on real.

**Justification (corrected 2026-09-11).** The only real severe-anemia cases available
(n=48, single site) carry mutually contradictory haemoglobin labels, as established in
Phase 1. The Monte Carlo forward model is therefore the only source of reliably
labelled severe anemia in this project. **Its purpose is label trustworthiness, not
merely data quantity.**

### N3 — Physical interpretability

Output hemoglobin concentration in g/dL and oxygenation, not a class probability.
Explanations are chromophore concentration maps, not saliency heatmaps.

### N4 — Conformal prediction with selective abstention over a physical quantity

Three-state output: screen negative / screen positive-refer / cannot decide. Spectral
reconstruction residual provides a principled non-conformity signal.

### N5 — Mechanistic fairness audit

Report performance stratified by skin tone and source device, and DECOMPOSE any gap
into melanin absorption versus illuminant estimation error.

**Method (rebuilt 2026-09-11, SCIN removed).**

- **Skin tone:** estimated by **Individual Typology Angle (ITA)**, computed in closed
  form from CIELAB on periocular skin regions, applied to **N1-calibrated images**.
  Reusing the N1 pipeline is what makes the decomposition *mechanistic* rather than
  descriptive: the same illuminant estimate that N1 produces is what makes ITA
  comparable across captures.
- **Population axis:** the India versus Italy sites within Eyes-Defy-Anemia.
- **Device axis:** MOBIUS, 3 phones × 3 lighting conditions.
- **Decomposition:** melanin versus illuminant-estimation error, testable in simulation
  (N2) where melanin is known by construction.

**Limitations, to be carried verbatim into the paper:** *there are no ground-truth skin
tone labels in this project; ITA is a proxy, not a measurement; and the tone axis is
confounded with site.*

### N6 — Multimodal fusion with graceful degradation

Conjunctiva, palm, nail and PPG are all measurements of the same molecule through
different optical paths. Fuse into one physical estimate. Train with modality dropout so
missing or low-quality inputs degrade gracefully rather than failing.

**Scope (fixed 2026-09-11). These are limits, not open problems to be solved later.**

- **Real multimodal fusion is conjunctiva + nail, CLASSIFICATION ONLY, never
  regression.** The ~454 participants with paired body sites come from the Ghana pool,
  which is BINARY-LABEL-ONLY (see N2's justification and the DECISION LOG). No fused,
  calibrated Hb estimate in g/dL can be validated on paired modalities.
- **Image + PPG fusion is simulation-only, permanently.** `Hb_PPG_Dataset` shares no
  participants with any image dataset and never will, because no new data will be
  collected. Any image+PPG result is a simulation result and must be labelled as one.

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

All under `data/raw/`. **Audited 2026-09-11**; full detail in `reports/phase1_data_audit.md`
and `reports/phase1_summary.md`.

| Folder | What it is | Role |
| --- | --- | --- |
| `nus8` | NUS 8-camera color constancy benchmark. Linear PNGs, colorchecker masks, ground-truth illuminant `.mat` per camera. | Validates N1 |
| `SBVPI` | High-resolution periocular sclera segmentation dataset. No Hb labels. | Sclera segmentation |
| `MOBIUS` | Mobile sclera segmentation. **3 phones × 3 lighting × 100 subjects**, recoverable from filenames. No Hb. | **N1b** and N5 device axis |
| `CP-AnemiC dataset` | Conjunctival pallor, Ghana, children 6–60 months. Hb present but **REJECTED** (Phase 1.5). Contained inside the Ghana conjunctiva set. | Binary label only |
| `Application of Machine Learning ... Conjunctiva image Dataset from Ghana` | Ghana conjunctiva (Mendeley `nt7r8hv2pz`). Superset of CP-AnemiC. No Hb. | Binary label only |
| `Detection of Anemia using Colour of the Fingernails Image Datasets from Ghana` | Ghana fingernails (Mendeley `2xx4j3kjg2`). Shares a participant roster with the conjunctiva set. No Hb. | Nail modality (N6), binary only |
| `dataset anemia` | **CONFIRMED Eyes-Defy-Anemia** (Phase 1). 218 subjects across India (95) and Italy (123); full photographs plus palpebral/forniceal masks; Hb in per-site `.xlsx`. | Conjunctiva, the ONLY cross-site Hb data (N1) |
| `Hb_PPG_Dataset` | 252 subjects, four-wavelength PPG (660/730/850/940 nm), 200 Hz, 60 s, venous-blood Hb reference via HemoCue. CSV per subject plus `subject information.xlsx`. | PPG modality (N6) |
| ~~Eyes-Defy-Anemia (expected separately)~~ | Present on disk as `dataset anemia`; see the row above. No separate folder exists. | — |

**DELETED 2026-09-11:** `scin-main` was removed from `data/raw/` in Phase 1.5. It held
no data (5 documentation files), and SCIN is dermatology imagery with no conjunctiva, no
Hb and no participant overlap, so its skin-tone labels could not be attached to any
subject here. N5 no longer depends on it. Recoverable from
`github.com/google-research-datasets/scin` if ever needed.

### 🔴 KNOWN RISK — participant overlap (highest-priority Phase 1 item)

**CP-AnemiC and the Ghana conjunctiva dataset share authors and collection hospitals
and may contain overlapping participants. Any cross-site claim built on treating them
as independent is invalid until overlap is ruled out.**

**VERDICT (2026-09-11): CONFIRMED AND WORSE THAN FEARED.** CP-AnemiC is not merely
overlapping with the Ghana conjunctiva set — it is largely *contained inside* it. 419
distinct MD5 hashes are shared; 87.3% of CP-AnemiC files are byte-identical to a Ghana
file; 98.2% fall within pHash Hamming 10. They are permanently **one site**.

No paper text, figure or table may describe them as independent, and no split may place
one in train and the other in test. A second, independent problem was found in the same
check: **CP-AnemiC's haemoglobin labels conflict on its duplicated images** (see the
DECISION LOG, 2026-09-11).

### Phase 1 findings (2026-09-11) — these SUPERSEDE the scaffold-time guesses

- ✅ **`dataset anemia` IS Eyes-Defy-Anemia.** Confirmed by Italian sheet metadata
  (`Foglio1`, annotator notes "da segmentare la forniceale"), India+Italy sites, and
  95+123=218 subjects with Hgb. It is the project's only source of full photographs
  paired with haemoglobin.
- ✅ **`nus8` now has SIX extracted cameras**: Canon EOS-1Ds Mark III, Canon600D,
  Fujifilm X-M1, NikonD5200, Olympus E-PL6, SamsungNX2000. 1265 images, all parsed,
  zero missing PNGs or colorchecker masks. **The extraction item is CLOSED.** Two of the
  benchmark's eight (SonyA57, PanasonicGX1) remain unextracted — say "six sensors", not
  eight. `SamsungNX2000/groundtruth.mat/` is empty; its ground truth is read from
  `raw_downloads/` by `paths.resolve_nus8_gt()`.
- 🔴 **CP-AnemiC and the Ghana conjunctiva set are ONE dataset**, not two sites. See the
  overlap verdict above and the DECISION LOG.
- 🔴 **CP-AnemiC and Ghana conjunctiva images have NO SCLERA.** Both are pre-segmented
  conjunctiva cutouts on black backgrounds (>50% black in 100% of sampled images). N1's
  white reference is absent from them, so the headline claim can only be validated
  end-to-end on Eyes-Defy's 218 subjects.
- 🔴 **CP-AnemiC Hb labels conflict on duplicated images**: 710 files, 498 unique images,
  and 90 of 91 exact-duplicate groups carry more than one Hb value.
- 🟢 **Ghana conjunctiva and fingernail sets share a participant roster** (non-anemic
  numbers match 204/204, Jaccard 1.000). ~454 subjects with paired body sites — an N6
  opportunity, though with binary labels only, no Hb.
- 🟢 **MOBIUS carries real device diversity**: 3 phones x 3 lighting conditions x 100
  subjects, recoverable from its filename grammar. No Hb.
- 🔴 **`scin-main` contains NO DATA** — 5 files, all documentation. SCIN's images and
  skin-tone labels live in a GCS bucket, and SCIN is dermatology imagery with no
  participant correspondence to any anemia dataset. N5 is materially weakened.
- SBVPI and MOBIUS carry no Hb labels; they are segmentation-only resources.

Full detail: `reports/phase1_data_audit.md`, `reports/phase1_summary.md`.

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
- **GPU:** NVIDIA GeForce RTX 4060 Laptop GPU, **8 GB VRAM** (8188 MiB), driver 610.62.
  PyTorch must be installed from the CUDA index
  (`--index-url https://download.pytorch.org/whl/cu126`); the default PyPI index
  serves a CPU-only wheel on Windows and must never be used here.
  **The 8 GB ceiling is a design constraint, not a footnote.** It caps batch size
  and backbone choice in Phase 5 (CNN baseline) and Phase 8 (multimodal fusion,
  where several modality encoders may be resident at once). Plan for gradient
  accumulation and mixed precision rather than discovering the limit at train time.

---

## 6. PHASE PLAN

Every task starts unchecked. Tick a checkbox only when the task is actually complete
and its output exists on disk.

> ### STATE AT A GLANCE (audit 2026-09-12 — `reports/claude_md_audit.md`)
>
> **Legend for unticked boxes.** `🔴 SUPERSEDED —` not to be done: a pre-declared gate
> that preceded it failed, cited inline. `⛔ BLOCKED —` cannot be done here, blocker cited.
> `🟡 OUTSTANDING —` genuinely still to do. Ticked boxes annotated `⚠️` have a reduced or
> missing artefact behind them. Original wording is never removed; annotations are appended.
>
> | phase | status | closed by | open items |
> | --- | --- | --- | --- |
> | 0 Scaffold | ✅ COMPLETE | — | 0 |
> | 1 Data audit | ✅ COMPLETE | — | 0 |
> | 1.5 Remediation | ✅ COMPLETE | — | 0 |
> | 2 Sclera / illuminant (N1) | ✅ COMPLETE — N1 **REFUTED** | — | 0 (one ⚠️ reduced artefact) |
> | 2.5 Specular rescue | ✅ COMPLETE — **REFUTED** | — | 0 |
> | 3 Simulator (N2) | 🔴 CLOSED AT GATE | Task 0: 3.893 g/dL vs >2.0 | 0 (empirical signal now measured, Phase 6.5) |
> | 3.5 Ratio reformulation | 🔴 CLOSED AT GATE | Task 1: 10.04 g/dL vs >2.0 | 0 |
> | 4 Imaging (N3) | 🔴 SUPERSEDED | imaging arm CLOSED, FINAL | 0 |
> | 4 PPG gates | ✅ COMPLETE — **NOT VIABLE** | — | 0 |
> | 4.5 Deep PPG | ✅ COMPLETE — **NOT VIABLE** (one real, useless signal) | — | 0 |
> | 5 Harden + consolidate | ✅ COMPLETE | — | 0 |
> | 5 (orig) CNN baseline | ✅ BUILT in Phase 6.5 | — | 0 (MAE 1.301, MARGINAL; site+sex+age alone 1.273) |
> | 6 Audit harness | ✅ COMPLETE | — | 0 (deep-model validation closed in Phase 6.5) + 1 ⛔ closed-not-applicable |
> | 6.5 Closure | ✅ COMPLETE | — | 0 |
> | 7 Additions | ✅ COMPLETE | Task 1 outcome B; external audit: 0 of 3 candidates auditable | 0 |
> | 8A Language for a dual audience | ✅ COMPLETE | — | 0 |
> | 8B Visual redesign | ✅ COMPLETE | — | 0 (Lighthouse 97-100 / 100 / 100; 48 page states verified) |
> | 6 (orig) Conformal (N4) | 🔴 SUPERSEDED | no estimator | 0 |
> | 7 Fairness (N5) | 🔴 SUPERSEDED | no estimator; mechanism measured in Phase 3 Task 4 | 0 |
> | 8 Fusion (N6) | 🔴 SUPERSEDED | no g/dL estimate from any modality | 0 (2 items found done, ticked) |
> | 9 Web app | 🔴 SUPERSEDED | replaced by Phase 6 audit app | 0 (2 scaffold items ticked, with caveat) |
> | 10 Flutter | 🔴 SUPERSEDED | no estimator | 0 |
>
> **Open work in the whole plan: none (Phase 6.5, 2026-09-12).** What remains is the write-up.
### Phase 0: Scaffold
- [x] Create the repository directory structure
- [x] Write `pyproject.toml` pinning Python 3.12 and the core dependencies
- [x] Write `.gitignore` excluding `data/`, caches, model artefacts and `node_modules`
- [x] Write `README.md` pointing to CLAUDE.md as the source of truth
- [x] Write this CLAUDE.md with claims, constraints, inventory, phase plan and logs
- [x] Create and populate the Python virtual environment
- [x] Verify the environment imports the package and passes the smoke test
- [x] Initialise the git repository and make the first commit *(ticked 2026-09-12 audit: 4 commits, 06aa682 → 4e6eff7, 81 files tracked. ⚠️ Nothing from Phase 4 onward is committed — 32 paths untracked/modified on 2026-09-12; see `reports/claude_md_audit.md`)*

### Phase 1: Data audit, manifests, overlap check, patient-level splits
- [x] Inventory every dataset: file counts, formats, resolutions, colour encoding, EXIF and device metadata
- [x] Identify the contents of `dataset anemia` and confirm or refute that it is Eyes-Defy-Anemia
- [x] Parse every Hb label source into one tidy `labels` table (subject, site, Hb g/dL, age, sex, device, modality)
- [x] Build a per-dataset image manifest in `data/interim/manifests/` with a stable subject ID and provenance for every file
- [x] **Run the CP-AnemiC / Ghana-conjunctiva overlap check** (perceptual hashing, EXIF timestamps, filename structure, subject metadata) and log the verdict
- [x] Define and freeze patient-level, site-aware train/calibration/test splits; write them to `data/interim/splits/` *(path amended from `data/processed/splits/`; see DECISION LOG 2026-09-11)*
- [x] Characterise label distributions per site: Hb range, anemia prevalence, severe-anemia count, class balance
- [x] Record dataset licences and redistribution terms; confirm no data is committed to git

### Phase 1.5: Remediation of the Phase 1 findings
- [x] Restructure N1 into N1a (sensor accuracy), N1b (sclera as white reference), N1c (end-to-end Hb)
- [x] Search exhaustively for uncropped / full-eye originals and record the result conclusively
- [x] Arbitrate the Ghana-pool haemoglobin labels and implement `hb_label_trusted` as a hard manifest flag
- [x] Correct N2's justification from "no public dataset contains severe anemia" to the label-trustworthiness argument
- [x] Rebuild N5 without SCIN: ITA on N1-calibrated periocular skin; delete `data/raw/scin-main`
- [x] Fix the figures licence exposure: gitignore `reports/figures/`, untrack it, document regeneration
- [x] Fix N6's scope: conjunctiva+nail classification only; image+PPG simulation-only, permanently
- [x] Write `reports/phase1_5_remediation.md` and update the "CANNOT support" list

### Phase 2: Sclera segmentation and illuminant estimation (N1)
- [x] Build loaders for SBVPI and MOBIUS with their segmentation masks
- [x] Train or adapt a sclera segmentation model; report IoU on SBVPI and on MOBIUS separately
- [x] Implement sclera-as-white-reference illuminant estimation from a segmented region
- [x] Validate illuminant estimation on `nus8` against ground-truth illuminants (angular error), per camera
- [x] Compare against standard colour-constancy baselines (grey-world, max-RGB, grey-edge) on the same split
- [x] Quantify sensitivity to mask error, specular highlights, scleral yellowing and vessel coverage
- [x] Apply the estimator to the conjunctiva datasets and inspect stability within and across sites *(scope amended: the Ghana conjunctiva pool has no sclera (Phase 1.5), so this ran on Eyes-Defy-Anemia only — see DECISION LOG 2026-09-11)* *(⚠️ reduced artefact RESOLVED 2026-09-12: per-image illuminant estimates now stored by `scripts/phase6_5_eyes_defy_illuminant.py`; within-subject stability recorded as not measurable, one image per subject)*
- [x] Write up the calibration-free argument with its failure modes stated explicitly
- [x] N1b self-consistency on MOBIUS (3 phones x 3 lighting x 100 subjects), evaluated on a held-out region
- [x] Per-image segmentation quality score, validated against MOBIUS's deliberately-bad frames
- [x] Vasculature exclusion inside the sclera, checked against SBVPI's ground-truth vessel masks

### Phase 2.5: Specular (corneal highlight) rescue attempt for N1 — TIME-BOXED
**Hypothesis.** Under the dichromatic reflection model, specular reflection from a
dielectric preserves the illuminant's SPD. A corneal highlight is therefore close to a
direct sample of the scene illuminant and carries **no per-subject reflectance term** —
precisely the variance that defeated the sclera in Phase 2. This is a hypothesis to
test, not a claim to confirm.

**Thresholds declared BEFORE running (2026-09-11):**
- **Feasibility gate:** if fewer than **30%** of images yield a detectable AND
  unsaturated corneal highlight, STOP at Task 1 and report non-viability.
- **SUPPORTED:** specular beats grey-world on held-out-iris within-subject dE2000
  spread, paired Wilcoxon p < 0.05.
- **PARTIALLY SUPPORTED:** specular beats no-correction (p < 0.05) but not grey-world.
- **REFUTED:** specular fails to beat no-correction.

- [x] Task 1: feasibility census — highlight detection rate, saturation distribution, area, by phone and lighting
- [x] Apply the 30% feasibility gate and report the number before proceeding
- [x] Task 2: dichromatic specular illuminant estimation (not a mean of bright pixels)
- [x] Task 2: report the number of distinct chromatic clusters rather than forcing one estimate
- [x] Task 3: evaluate on the identical MOBIUS protocol, held-out iris, circularity guard intact
- [x] Task 3: paired statistics against grey-world specifically, plus per-subject win rates and variance decomposition
- [x] Task 4: deployment-realism — how grey-world degrades as the field of view narrows to a tight crop
- [x] Task 5: `reports/phase2_5_specular.md` with a verdict against the pre-declared thresholds

### Phase 3: Monte Carlo tissue simulator (N2)

**TASK 0 GATE — interpretation thresholds declared BEFORE running (2026-09-11):**
Propagate the residual colour error that grey-world actually leaves through the
forward model and measure the resulting haemoglobin error.
- **Under +/-1.0 g/dL** -> the approach is VIABLE; proceed.
- **1.0 to 2.0 g/dL** -> MARGINAL; viable only for coarse screening bands, not point
  estimates. Report which WHO severity boundaries remain distinguishable.
- **Over +/-2.0 g/dL** -> the colour-to-haemoglobin inversion is NOT RECOVERABLE under
  realistic calibration error. STOP and report as a major finding.
Residual errors tested: **3.935** dE2000 (grey-world at 25% FOV, the recommended
normalisation), **6.076** (grey-world full frame), and **1.0** (best case).
The result is reported before any further work, whatever it shows.

- [x] Task 0: minimal forward model plus error propagation; report the gate result first
- [x] Task 0: report whether Hb error is uniform or worse at low Hb, where screening decisions are made
- [ ] 🔴 SUPERSEDED — Task 1: layered conjunctival optical model with EVERY constant cited in one documented module *(PARTIAL: constants module built and cited; full layered MC NOT built — gate failed, see DECISION LOG 2026-09-11)* *(gate: Phase 3 Task 0, 3.893 g/dL at the measured 3.935 dE2000 residual vs >2.0 NOT RECOVERABLE)*
- [ ] 🔴 SUPERSEDED — Task 1: radiative transfer, validated against published benchmark cases before any output is trusted *(NOT BUILT — stopped at the Task 0 gate)* *(gate: Phase 3 Task 0, 3.893 g/dL at the measured 3.935 dE2000 residual vs >2.0 NOT RECOVERABLE)*
- [ ] 🔴 SUPERSEDED — Task 2: validate simulated spectra against published conjunctival/eyelid reflectance measurements *(NOT DONE — stopped at the gate; simulated colour WAS checked against 216 real Eyes-Defy subjects instead)* *(gate: Phase 3 Task 0, 3.893 g/dL at the measured 3.935 dE2000 residual vs >2.0 NOT RECOVERABLE)*
- [x] Task 2: compare simulated RGB against real Eyes-Defy images at matched Hb; report the gap honestly *(DONE in reduced form: empirical 0.70 vs simulated 0.452 dE2000 per g/dL)* *(⚠️ artefact gap RESOLVED 2026-09-12: the 0.70 constant is withdrawn; measured 0.84 (CI 0.57-1.17) by `phase3_empirical_signal.py`)*
- [x] Task 2: state plainly what the model does NOT capture
- [ ] 🔴 SUPERSEDED — Task 3: generate the synthetic corpus, storing spectra AND RGB with full generating parameters *(NOT BUILT — stopped at the gate; the inversion the corpus would serve cannot survive realistic calibration error)* *(gate: Phase 3 Task 0, 3.893 g/dL at the measured 3.935 dE2000 residual vs >2.0 NOT RECOVERABLE)*
- [x] Task 4: quantify how much reflectance-prior error is tolerable (closes the question Phase 2 could not answer)
- [x] Task 5: `reports/phase3_simulation.md` with the gate result first and an N2 verdict

- [x] Assemble chromophore absorption spectra (HbO2, Hb, melanin, water) and tissue scattering parameters with cited sources *(ticked 2026-09-12 audit: `data/raw/optical_constants/` (Prahl Hb, spectralLIB water/scattering/melanin) loaded by `simulation/optical_data.py`; Phase 3.5 Task 0 compared them against the transcription. Melanin is a fitted power law, sweep-never-fix)*
- [x] Define the layered eyelid/conjunctiva optical model (layer count, thickness ranges, blood volume fraction, oxygenation) *(ticked 2026-09-12 audit: `constants.DEFAULT_LAYERS` (3 cited layers) plus HB/OXYGENATION/BVF/MELANIN ranges. ⚠️ Thicknesses and BVF still carry the VERIFICATION REQUIRED banner)*
- [ ] 🔴 SUPERSEDED — Implement the Monte Carlo photon-transport forward model producing diffuse reflectance spectra *(gate: Phase 3 Task 0, 3.893 g/dL at the measured 3.935 dE2000 residual vs >2.0 NOT RECOVERABLE; a layered diffusion model (`forward.py`) was sufficient to fail it)*
- [ ] 🔴 SUPERSEDED — Validate the simulator against published reflectance spectra or an analytic limiting case *(gate: Phase 3 Task 0, 3.893 g/dL at the measured 3.935 dE2000 residual vs >2.0 NOT RECOVERABLE; only inversion self-consistency (0.0001 g/dL) was checked, which is not validation)*
- [ ] 🔴 SUPERSEDED — Sample the parameter space across Hb 4-18 g/dL and export a synthetic spectral library to `data/synthetic/` *(gate: Phase 3 Task 0, 3.893 g/dL at the measured 3.935 dE2000 residual vs >2.0 NOT RECOVERABLE; `data/synthetic/` is empty)*
- [x] Collect or fit camera spectral sensitivity curves and illuminant SPDs; project spectra to synthetic RGB *(ticked 2026-09-12 audit: REDUCED — camspec (28 cameras, 400-720 nm) on disk and parsed; projection in `forward.py` is via D65 + CIE 1931 observer as camera proxy; only 2 of 6 nus8 cameras have measured SSFs (DECISION LOG 2026-09-11))*
- [x] Compare the synthetic RGB distribution against real conjunctiva pixels and document the sim-to-real gap *(ticked 2026-09-12, Phase 6.5 Task 1: `scripts/phase3_empirical_signal.py` -> `empirical_signal.json`; measured 0.84 dE2000/g/dL (CI 0.57-1.17) vs simulated 0.452, gap 1.9x; the earlier 0.70 constant is withdrawn)*
- [ ] 🔴 SUPERSEDED — Log the severe-anemia coverage the simulator adds relative to the real data *(gate: Phase 3 Task 0, 3.893 g/dL at the measured 3.935 dE2000 residual vs >2.0 NOT RECOVERABLE; no corpus exists)*

### Phase 3.5: Ratio reformulation — TIME-BOXED test of a possible rescue

**Rationale.** Every method tested so far (sclera-referenced, specular, grey-world)
tries to RECOVER THE ABSOLUTE ILLUMINANT, and that is the specific thing that failed.
Under a von Kries diagonal model, observed = reflectance x illuminant, so a ratio of
two regions in the SAME image cancels the illuminant algebraically, per channel:

    conjunctiva_observed / sclera_observed  =  R_conj / R_sclera

No estimation step, therefore no estimation error. This REFRAMES N1 rather than
abandoning it: the premise that the eye carries its own reference was right; the error
was demanding the reference yield the ABSOLUTE illuminant, which needs its reflectance
known. A ratio needs only that the reference be STABLE PER SUBJECT, which Phase 2
demonstrated it is. **This is a hypothesis to test, not to confirm.**

**Thresholds declared BEFORE running (2026-09-11), in the equivalent-Hb units of the
Phase 3 gate so the comparison is direct:**
- **Equivalent residual < 1.0 g/dL** -> the illuminant cancels; proceed to Task 2.
- **1.0 to 2.0 g/dL** -> partial cancellation; MARGINAL.
- **> 2.0 g/dL** -> von Kries diagonality or region stability is failing; the
  reformulation does NOT rescue the claim. STOP, do not proceed to Task 2.

- [x] Task 0: replace transcribed constants with the downloaded sourced files; report disagreements
- [x] Task 1: cancellation test on the unchanged MOBIUS protocol; report before proceeding
- [x] Task 1: decompose the ratio residual by phone, lighting and interaction
- [ ] 🔴 SUPERSEDED — Task 2: re-run the Phase 3 gate on ratio features *(NOT RUN — Task 1 failed at 10.04 g/dL equivalent, 5x the pre-declared threshold)* *(gate: Phase 3.5 Task 1, best ratio 10.04 g/dL equivalent vs >2.0, 5x over)*
- [x] Task 2: report ratio sensitivity in dE2000-equivalent per g/dL — a ratio may attenuate signal as well as noise
- [x] Task 3: within- versus between-subject sclera reference stability; state which regime the data is in
- [x] Task 3: test whether a per-subject offset helps, and whether it is obtainable in deployment
- [x] Task 4: record the PPG scope change — promoted to co-primary, not subject to the Phase 3 failure
- [x] Task 5: `reports/phase3_5_ratio.md` with the Task 1 result first and a verdict

### Phase 4: Spectral reconstruction and Hb estimation (N3)

> 🔴 **SUPERSEDED IN FULL (audit 2026-09-12).** The imaging arm is CLOSED, FINAL
> (DECISION LOG 2026-09-11): Phase 3 Task 0 gate 3.893 g/dL and Phase 3.5 Task 1 ratio
> 10.04 g/dL, both against a >2.0 threshold. Every item below presupposes the synthetic
> library (never built) and an inversion the gate showed cannot survive the calibration
> residual. Retained verbatim; not to be started.
- [ ] 🔴 SUPERSEDED — Implement RGB-to-reflectance-spectrum reconstruction trained on the synthetic library
- [ ] 🔴 SUPERSEDED — Implement chromophore unmixing from the reconstructed spectrum to Hb, HbO2 and melanin
- [ ] 🔴 SUPERSEDED — Produce per-pixel chromophore concentration maps as the explanation artefact
- [ ] 🔴 SUPERSEDED — Aggregate pixel-level estimates to a per-image Hb value in g/dL with an uncertainty estimate
- [ ] 🔴 SUPERSEDED — Evaluate on real data with MAE, bias, Bland-Altman limits of agreement and correlation, per site
- [ ] 🔴 SUPERSEDED — Run leave-one-site-out and leave-one-device-out evaluation; report the drop honestly
- [ ] 🔴 SUPERSEDED — Ablate the N1 illuminant estimation to show what calibration-free costs or buys
- [ ] 🔴 SUPERSEDED — Record the spectral reconstruction residual per image for downstream use in N4

### Phase 4: PPG arm — TWO GATES (imaging arm is CLOSED)

**Why PPG is not a fifth reformulation of a dead claim.** Every imaging failure traces
to one of two measured causes: the illuminant must be estimated and cannot be estimated
accurately enough (Phases 2, 2.5, 3), and the reference surface is less stable within a
subject than between subjects (Phase 3.5 Task 3, within/between = 1.447). Contact PPG is
structurally exempt from both — the LED in contact with tissue IS the illuminant, and
AC/DC normalisation cancels static tissue, skin tone, source intensity and sensor gain
by construction in the TIME domain, not the spatial domain that failed in Phase 3.5.
It is the principle under which pulse oximetry already works clinically without
per-subject calibration. **It must still be gated, not assumed.**

**GATE A thresholds, declared BEFORE running (2026-09-11):**
- Nuisance variance reduction **>= 50%** AND signal exceeding non-Hb variation -> PASS.
- Reduction present but signal comparable to noise -> MARGINAL, stop for a decision.
- No meaningful reduction -> FAIL, the normalisation does not cancel on real data.

**GATE B thresholds (same bands as the Phase 3 gate), applied SEPARATELY to each of
three conditions:**
- **< 1.0 g/dL MAE** -> viable. **1.0-2.0** -> marginal, screening bands only.
  **> 2.0** -> not viable.
- Conditions: (1) all four wavelengths = the physics ceiling; (2) 660 nm only = the one
  channel a phone shares; (3) simulated phone-RGB = what is actually deployable.
- If (1) passes and (3) fails, that is the honest finding and is reported as such.

⚠️ **Phase 3.5 showed exact algebraic cancellation on synthetic data and 139x that
residual on real captures. Cancellation is verified ON REAL DATA; any synthetic check is
an implementation test only.**

- [x] Task 0 / GATE A: AC-DC extraction documented precisely; cancellation verified on real data
- [x] Task 0 / GATE A: nuisance variance reduction and signal-to-noise in per-g/dL units; report before proceeding
- [x] Task 1 / GATE B: Hb estimators under 4-wavelength, 660-nm-only, and simulated phone-RGB conditions
- [x] Task 1 / GATE B: grouped leave-subject-out CV; never split within a subject
- [x] Task 2: signal quality index; check explicitly whether it rejects anything at the operating threshold
- [x] Task 2: verify the dataset's own SNR claims (940 nm worst, 850 nm cleanest) independently
- [x] Task 3: demographics-only and population-mean baselines on identical splits
- [x] Task 4: `reports/phase4_ppg_gate.md` with both gate results stated first

### Phase 4.5: Deep models on raw PPG — closing the last untested representation

**Not a rescue attempt.** Phase 4 tested hand-engineered features and found no skilled
model. A deep model over raw waveforms is the one representation not yet tried, and any
reader of a negative-results paper will ask whether it was. It is answered with evidence
rather than omission. **The expected outcome is failure, and failure is the useful
result.**

**Same pre-declared thresholds as Phase 4 Gate B:** <1.0 g/dL viable, 1.0-2.0 marginal,
>2.0 not viable. Same baselines: population mean, sex alone, full demographics. Same
grouped leave-subject-out splits.

⚠️ **With 252 subjects a deep model can trivially memorise.** Subject-disjoint folds are
verified explicitly, the train-test gap is reported, and **if any model beats the
demographic baseline a sex probe is run on its learned representation FIRST** — Phase 4
Task 3 showed how easily an apparent Hb model is really a sex classifier.

- [x] Task 1: 1D CNN and a sequence model over raw waveforms; 4-channel and 660-nm-only
- [x] Task 1: verify subject-disjoint folds explicitly; report train-test gap
- [x] Task 1: sex probe on the learned representation if any model beats demographics
- [x] Task 2: mutual information and ranked correlations with multiple-comparison correction
- [x] Task 2: permutation test — establish numerically what "no signal" looks like
- [x] Task 3: `reports/phase4_5_deep.md`, and a FINAL status table of every tested representation

### Phase 5: Harden the positive claim, and consolidate

Two objectives, no new modelling directions.

- [x] Task 1: >=200 permutations of the selected model; report EMPIRICAL p beside the parametric z
- [x] Task 1: account for selection — run the full best-of-six inside each permutation
- [x] Task 1: seed stability; retract if seed spread is comparable to the real-vs-null gap
- [x] Task 1: verify the effect is not carried by a small subset of subjects
- [x] Task 2: `reports/final_results.md` — master table, mechanisms, limitations, corrections
- [x] Task 3: single entry-point reproduction script with documented runtime
- [x] Task 3: dataset manifest with source, licence status and how to obtain
- [x] Task 3: confirm no data files and no dataset-derived figures are tracked in git
- [x] Task 4: `reports/literature_gap.md` — counts only, from papers already cited

### Phase 5 (original plan): CNN baseline comparison arm

> ✅ **BUILT 2026-09-12 (Phase 6.5 Task 2).** The audit found section 3's hard constraint unmet for the
> imaging arm. `scripts/phase6_5_image_cnn.py` closes it: ResNet-18 on Eyes-Defy, subject-disjoint
> folds, the Phase 4 baselines and bands, three seeds, sex probe, cross-site both ways. **MAE 1.301
> (MARGINAL) vs site + sex + age 1.273**; beats it: False. Pilot arm: 217
> subjects, one phone model, no severe cases. The comparison arm agrees with the refutation.

- [x] Define the baseline: standard backbone, conjunctiva crop input, Hb regression head *(ticked 2026-09-12, Phase 6.5 Task 2: `scripts/phase6_5_image_cnn.py`, `image_cnn.json`)*
- [x] Train the baseline under identical splits, preprocessing and augmentation budget *(ticked 2026-09-12, Phase 6.5 Task 2: `scripts/phase6_5_image_cnn.py`, `image_cnn.json`)*
- [x] Evaluate with the identical metric suite, including leave-one-site-out *(ticked 2026-09-12, Phase 6.5 Task 2: `scripts/phase6_5_image_cnn.py`, `image_cnn.json`)*
- [x] Add a colour-feature baseline (mean/percentile RGB or HSV statistics plus a shallow regressor) *(ticked 2026-09-12, Phase 6.5 Task 2: `scripts/phase6_5_image_cnn.py`, `image_cnn.json`)*
- [x] Build a single comparison table that every subsequent claim must cite *(ticked 2026-09-12, Phase 6.5 Task 2: `scripts/phase6_5_image_cnn.py`, `image_cnn.json`)*
- [ ] 🔴 SUPERSEDED — Establish the protocol for keeping the baseline current whenever the physical model changes *(there is no physical model left to change; re-running `phase6_5_image_cnn.py` is the protocol if one ever appears)*

### Phase 6: HemoSight Audit - the software deliverable (web application)

The project's shippable product is **not** a haemoglobin estimator; six representations
across two modalities failed their pre-declared gates. It is the methodological audit
pipeline those gates were run with, generalised so it operates on any claimed screening
model's predictions. **This section REPLACES the original Phase 6 for sequencing
purposes only; the original is retained verbatim below.** See the DECISION LOG,
2026-09-12.

- [x] Task 1: generalise Phases 1-5 into `src/hemosight/audit/`, wrapping the existing modules rather than rewriting them
- [x] Task 1: one generic input contract (subject_id, y_true, y_pred + optional split/age/sex/device/site/group/images)
- [x] Task 1: eight checks, each returning PASS / FAIL / INSUFFICIENT DATA with the measured quantity and a plain-language explanation
- [x] Task 1: INSUFFICIENT DATA is a first-class outcome; no verdict is ever inferred from what could not be measured
- [x] Task 1: existing tests continue to pass (121 passing, was 102)
- [x] Task 2: FastAPI backend - upload, run, retrieve, export, with long checks as background jobs reporting progress *(⚠️ RESOLVED 2026-09-12: reportlab installed and declared; PDF export verified end to end)*
- [x] Task 2: pre-registration endpoint recording thresholds and whether they predate the results
- [x] Task 2: SQLite for development, PostgreSQL-ready; no authentication in this phase
- [x] Task 3: React + TypeScript + Vite + Tailwind + Framer Motion front end, seven pages
- [ ] ⛔ BLOCKED — Task 3: read `/mnt/skills/public/frontend-design/SKILL.md` before writing components *(NOT DONE - the file does not exist on this machine; see the DECISION LOG, 2026-09-12)* *(blocker: the path is a Linux mount from another environment and has no source here; the components have since been written, built and linted, so the step can no longer precede them. CLOSED AS NOT APPLICABLE — not ticked because it was not done)*
- [x] Task 4: validate the harness against this project's own data, where every verdict is already on the record
- [x] Task 4: validate against synthetic inputs carrying one known injected fault each
- [x] Task 4: validate against clean inputs and report the false-positive rate whatever it is
- [x] Task 4: end-to-end validation of the three Phase 5 checks against the Phase 4.5 DEEP model *(ticked 2026-09-12, Phase 6.5 Task 3: predictions regenerated by `phase6_5_deep_predictions.py`, harness A8 19/19 known-truth cases; the harness p is a different null from 0.0041)*
- [x] Task 5: `reports/phase6_audit_harness.md` - architecture, catalogue with provenance, validation, limitations

### Phase 6.5: Closure of every outstanding audit item (2026-09-12)

Ordered by the brief: Task 1 first, its verdict checked before anything else was started.

- [x] Task 1: measure the empirical colour-per-g/dL signal; store it; reproduce stage; reports read it *(withdrew the 0.70 constant; measured 0.84, CI 0.57-1.17; noise/signal 4.7x; no verdict changed)*
- [x] Task 2: image CNN baseline on Eyes-Defy with the Phase 4 baselines, bands and scrutiny *(MAE 1.301, MARGINAL; site+sex+age alone 1.273; beats it: False; cross-site italy_to_india 1.96, india_to_italy 1.99; first run omitted site - corrected)*
- [x] Task 3: per-subject deep-model predictions written; the three Phase 5 checks run end to end *(19/19 known-truth cases)*
- [x] Task 4: Phase 2 estimator applied to Eyes-Defy and stored; PDF export working with reportlab declared
- [x] Task 5: 8 licences verified from source; constants banner narrowed (epithelium lifted, rest retained); test pre-registration rows deleted and title validated; stray log entries moved
- [x] Task 6: everything committed; no data, figures or binaries tracked (test-enforced)
- [x] Task 7: `reports/phase6_5_closure.md`; CLAUDE.md updated; every decision and correction logged


### Phase 7: Three additions before the write-up (2026-09-12)

**Task 1 - the controlled-capture hypothesis.** Two results point the same way: Phase 3.5
Task 3 (studio captures cut within-subject sclera variation 3.5x; within/between 1.447 on
phones, 0.924 in studio) and Phase 6.5 (under Eyes-Defy's controlled illuminant,
conjunctival colour correlates with Hb within site, r 0.54-0.63). The untested question is
whether the refutation is about PHOTOGRAPHS or about UNCONTROLLED photographs.

**Thresholds declared BEFORE running (2026-09-12).** The Phase 3 gate is re-run at
MEASURED residuals, never assumed ones: the within-subject sclera colour spread (dE2000)
under each capture condition, with the best of {no correction, grey-world full frame,
grey-world 25% crop} applied per condition. Conditions, from least to most controlled:
MOBIUS across 3 phones x 3 lighting (the Phase 3.5 figure); MOBIUS same phone, same
lighting, gaze varying (geometry only); SBVPI studio. Bands as Phase 3: **< 1.0 g/dL
VIABLE, 1.0-2.0 MARGINAL, > 2.0 NOT RECOVERABLE.** Outcomes:
- **A - closes the gap:** gate MAE at the studio residual < 1.0 AND the Eyes-Defy empirical
  colour model (Phase 6.5, measured under a fixed LED) < 1.0 -> the refutation is about
  uncontrolled capture specifically and is restated narrowly.
- **B - partial:** either lands in 1.0-2.0 -> controlled capture moves the inversion from
  NOT RECOVERABLE to MARGINAL only; the refutation is restated as two-part (not recoverable
  uncontrolled; screening bands at best controlled).
- **C - generalises:** both stay > 2.0 -> the refutation is stronger, not narrower.
The residual needed to reach VIABLE is read off the gate model and compared with every
measured condition. Eyes-Defy has one image per subject, so its within-subject residual
is NOT measurable and is reported as such; its empirical MAE is the controlled-capture
measurement it does support. Reported whichever way it falls.

- [x] Task 1: measure within-subject residuals per capture condition (MOBIUS across conditions, MOBIUS within condition, SBVPI studio), with and without grey-world *(ticked 2026-09-12: `scripts/phase7_controlled_capture.py`; best residuals MOBIUS across phones x lighting 3.46, MOBIUS same phone + lighting 1.98, SBVPI studio 1.06 dE2000)*
- [x] Task 1: re-run the Phase 3 gate at each measured residual; report MAE against the bands *(ticked 2026-09-12: studio residual -> MAE 1.04 g/dL, MARGINAL; across-phone 3.47, NOT RECOVERABLE)*
- [x] Task 1: state the residual required for VIABLE and whether any measured condition achieves it *(ticked 2026-09-12: VIABLE needs < 0.99 dE2000; achieved by NO measured condition)*
- [x] Task 1: restate the imaging refutation as the outcome dictates; log it *(ticked 2026-09-12: outcome B - partial - controlled capture reaches MARGINAL only; see the DECISION LOG)*
- [x] Task 2: `reports/statistical_vs_clinical.md` - the statistically-real / clinically-useless pattern, quantified on comparable axes in both modalities, with a reporting standard and a retrospective check *(ticked 2026-09-12: `scripts/phase7_statistical_vs_clinical.py` -> `statistical_vs_clinical.json` -> report; nine results placed in the 2x2)*
- [x] Task 3: external-audit ingestion path (`hemosight.audit.ingest`), documented conversion procedure, INSUFFICIENT DATA prominent, external report template, attempted-audit register - built, NOT run *(ticked 2026-09-12: `hemosight.audit.ingest`, `run_audit(unsupported=)`, `to_external_markdown`, `scripts/external_audit.py`, empty register, `reports/external_audit_procedure.md`; 6 tests; smoke-tested on a synthetic table only - NOT run on any external work)*
- [x] Task 3B: availability record for every external candidate examined - `reports/external_audit_availability.md`, register with "upon request" as its own category *(ticked 2026-09-13: 3 examined, **0 auditable**)*
- [x] Task 3B: run the one released codebase in an isolated environment, paths repointed only, stop at the first error *(ticked 2026-09-13: 0 of 7 notebooks ran; 0 predictions; the harness produced no verdict on any external model)*
- [x] Task 3B: methodology from paper text for the paper that cannot be run - `reports/literature_gap.md` extended with NOT REPORTED as a value distinct from UNKNOWN and from NO *(ticked 2026-09-13: BPANet; Hemo-ConViT unlocated and excluded)*
- [x] Task 3B: `reports/external_audit.md`, leading with the availability result *(ticked 2026-09-13)*
- [x] `reports/phase7.md`; CLAUDE.md updated; decisions and results logged *(ticked 2026-09-12)*

### Phase 8A: The audit tool's language, for a dual audience (2026-09-13)

A content and information-architecture phase, not a visual one (8B). Two audiences, equally:
a researcher who needs every number, caveat and bound intact, and a first-time visitor who
needs to know what the tool is and what a result means. **Layered disclosure: plain language
is the default; the technical statement is one click away and never removed. Simplify the
sentence, never the claim.**

- [x] Task 1: content model in ONE place - `hemosight.audit.content` - per check: plain headline (rendered from the measured values), what it means, mechanism (plain and computational), technical statement (the check's own wording, verbatim), what to do, provenance *(ticked 2026-09-13; attached to every result by `run_audit` as `plain`; served by `/api/content`)*
- [x] Task 2: what-to-do in exactly one of FIXABLE / REPORT IT / STOP, category always visible, never phrased as a way to make a failing check pass; this project as the STOP worked example *(ticked 2026-09-13; FAIL is FIXABLE only for the two split-construction checks; enforced by test)*
- [x] Task 3: pages rewritten for orientation - landing (the problem in plain terms, how it works in three steps, a live worked example from the PPG result), pre-registration (why, with the project's own gate as the example), upload (what a predictions file is, each column in plain words, downloadable samples), results (plain headline per check, technical statement one click away), report export (both layers in Markdown and PDF) *(ticked 2026-09-13)*
- [x] Task 4: every user-facing string audited; glossary (`/glossary`, 24 terms) linked from unavoidable terms; `reports/content_review.md` with both layers side by side and real sample outputs; tests that every field is populated and INSUFFICIENT DATA never carries pass styling *(ticked 2026-09-13; 151 tests passing)*


### Phase 8B: Visual redesign (2026-09-13)

Direction: the atmosphere of a dark, typographic, parallax landing page (MNTN, Kryston
Schwarze) translated to this subject - a precision instrument, not a document. The
frontend-design skill file does not exist on this machine (logged 2026-09-12); proceeded
without it. Hard constraint honoured: no stock photography and nothing derived from a
dataset image; every visual is generated from public tabulated physics or the project's
own aggregate results.

- [x] Task 1: colour system - deep near-black ground, three surface elevations, one accent, three verdict hues each with a distinct glyph and label; all tokens in ONE file generated by `scripts/phase8b_contrast.py`, which measures every text/ground pair *(ticked 2026-09-13: all required pairs AA, most AAA; INSUFFICIENT DATA is amber + dashed diamond, never a faded pass; a test forbids hex colours outside `tokens.css`)*
- [x] Task 2: imagery - oxy/deoxy-haemoglobin extinction curves (OMLC) as the glowing hero and story visual; spectral band (CIE -> sRGB) as divider; null distribution, noise-vs-signal ladder and breakeven curve from the project's own results; grid, reticle, synthetic trace and particles by code *(ticked 2026-09-13: `scripts/phase8b_assets.py` -> five JSON files; no raster image ships, test-enforced)*
- [x] Task 3: motion - GSAP + ScrollTrigger (lazy, motion-on only) for the pinned five-step scrollytelling, three-layer parallax and staggered reveals; canvas particle field (<= 70 points, 6 px/s, off-screen paused); glowing conic borders; hover lifts and drawn underlines; reticle cursor *(ticked 2026-09-13)*
- [x] Task 4: accessibility and performance - `prefers-reduced-motion` and an in-app toggle disable every decorative motion and the cursor; native cursor restored; reticle hides on keyboard; visible focus rings; skip link *(ticked 2026-09-13: Lighthouse landing 97/100/100 mobile, 100/100/100 desktop; upload and results 99-100/100/100; bar was 90/97; bundle main 118.4 kB gz + lazy GSAP 46 kB gz)*
- [x] Task 5: restraint - verdict cards calm and legible, numbers undecorated, disclaimer in the frame of every page *(ticked 2026-09-13; checked from screenshots of a real seven-check run)*
- [x] Task 6: verified at 1440 / 834 / 390 in both motion modes on every page - 48 page states, 0 with a problem - and `reports/phase8b_design.md` with palette, ratios, motion inventory, measurements and what was cut *(ticked 2026-09-13)*


### Phase 6 (original plan): Conformal prediction and abstention (N4)

> WARNING: **NOT APPLICABLE as written, and not started.** N4 wraps a haemoglobin
> estimator in conformal intervals and a three-state decision rule. There is no
> estimator to wrap: the imaging arm is closed and the PPG arm is not viable. The tasks
> are retained verbatim rather than deleted, per the WORKING PROTOCOL. See the DECISION
> LOG, 2026-09-12.

- [ ] 🔴 SUPERSEDED — Carve a dedicated calibration split, disjoint from training and test at patient level
- [ ] 🔴 SUPERSEDED — Implement split conformal prediction intervals over the Hb estimate
- [ ] 🔴 SUPERSEDED — Verify empirical coverage against the nominal level, overall and per site
- [ ] 🔴 SUPERSEDED — Define the non-conformity signal from the spectral reconstruction residual and justify it
- [ ] 🔴 SUPERSEDED — Implement the three-state decision rule: screen negative / screen positive-refer / cannot decide
- [ ] 🔴 SUPERSEDED — Plot accuracy versus abstention rate and choose an operating point with a stated rationale
- [ ] 🔴 SUPERSEDED — Test coverage under distribution shift (unseen site, unseen device) and report the degradation
- [ ] 🔴 SUPERSEDED — Compare against the CNN baseline equipped with the same conformal wrapper

### Phase 7: Fairness audit (N5)

> 🔴 **SUPERSEDED (audit 2026-09-12).** There is no estimator whose performance could
> be stratified: imaging arm closed (Phase 3/3.5 gates), PPG arm NOT VIABLE (Gate B).
> The first item was superseded a second time by the Phase 1.5 decision that deleted SCIN
> and rebuilt N5 on ITA. **The N5 *mechanism* WAS measured** — Phase 3 Task 4: melanin
> fraction 0.005 shifts recovered Hb by +9.6 g/dL with the illuminant held perfect — and
> the write-up carries it together with the three N5 limitations in section 2.
- [ ] 🔴 SUPERSEDED — Attach skin tone labels using SCIN (self-reported Fitzpatrick, dermatologist Fitzpatrick, Monk Skin Tone); document how labels transfer to the anemia datasets and where they cannot *(also superseded by DECISION LOG 2026-09-11: SCIN deleted, N5 rebuilt on ITA)*
- [ ] 🔴 SUPERSEDED — Stratify every headline metric by skin tone and by source device
- [ ] 🔴 SUPERSEDED — Report abstention rate by stratum, not only accuracy *(no N4 abstention exists)*
- [ ] 🔴 SUPERSEDED — Decompose any performance gap into a melanin-absorption component and an illuminant-estimation-error component *(no gap to decompose; the melanin mechanism itself was measured in Phase 3 Task 4)*
- [ ] 🔴 SUPERSEDED — Use the simulator to test the decomposition on synthetic data where true melanin is known *(the melanin half was done in Phase 3 Task 4 (`task4_prior_sensitivity.json`); the illuminant-error half needs an estimator)*
- [ ] 🔴 SUPERSEDED — Compare the gap profile of the physical model against the CNN baseline *(neither exists)*
- [ ] 🔴 SUPERSEDED — Write the audit with the limits of the skin-tone labelling stated plainly *(folds into the paper)*

### Phase 8: Multimodal fusion (N6)

> 🔴 **SUPERSEDED except two items (audit 2026-09-12).** No modality yields a g/dL
> estimate to fuse (Phase 3/3.5 gates; Phase 4 Gate B; Phase 4.5). Two items were in fact
> completed by earlier phases and are ticked below with their evidence. **No palm dataset
> exists anywhere in the inventory** — the claim names a modality the project never had.
- [x] Build the PPG pipeline: load `Hb_PPG_Dataset`, filter, extract four-wavelength features, produce a per-subject Hb estimate *(ticked 2026-09-12 audit: `src/hemosight/ppg/features.py`, `scripts/phase4_gate_a.py`/`phase4_gate_b.py`, `data/interim/phase4/features.csv` (252 subjects) and `gate_b.json` (per-subject CV estimates). The estimate is NOT VIABLE, but the pipeline the box asks for exists and ran)*
- [ ] 🔴 SUPERSEDED — Build the nail and palm pipelines against their datasets *(no estimator to feed; nail data is binary-only; NO palm dataset exists — also BLOCKED)*
- [ ] 🔴 SUPERSEDED — Define the fusion model that combines modalities into one physical Hb estimate rather than an ensemble average
- [ ] 🔴 SUPERSEDED — Train with modality dropout and evaluate every subset of available modalities
- [ ] 🔴 SUPERSEDED — Add per-modality quality gating so low-quality inputs are down-weighted rather than trusted *(two SQIs were built anyway and both found unusable: Phase 2 image score rejects 0 of 17 bad frames; Phase 4 PPG SQI r(SQI,|error|) = -0.033)*
- [ ] 🔴 SUPERSEDED — Demonstrate graceful degradation: performance versus number of available modalities
- [ ] 🔴 SUPERSEDED — Propagate uncertainty through fusion and re-verify conformal coverage *(no N4)*
- [x] Document which subjects have which modalities and the resulting evaluation limits *(ticked 2026-09-12 audit: Phase 1 overlap — conjunctiva/nail roster Jaccard 1.000 (204/204), ~454 paired subjects, binary labels only; Hb_PPG shares no subject with any image set (`data/interim/overlap/overlap_results.json`; DECISION LOG 2026-09-11, N6 scoped))*

### Phase 9: Web application

> 🔴 **SUPERSEDED except the two scaffold items (audit 2026-09-12).** This phase is the
> inference application around an estimator that does not exist. The software deliverable
> became the audit harness (Phase 6, DECISION LOG 2026-09-12). The two scaffold items are
> ticked because `app/backend/` and `app/frontend/` exist, build and are tested — **for the
> audit tool, not the inference app**; the caveat is part of the tick.
- [x] Scaffold the FastAPI backend with SQLite and a PostgreSQL-ready data layer *(ticked 2026-09-12 audit: `app/backend/{main,db,models,schemas,jobs}.py`, `HEMOSIGHT_AUDIT_DB` connection-string override, `SafeJSON` column type — built for the AUDIT tool, not the inference app)*
- [ ] 🔴 SUPERSEDED — Define the inference API: image upload, optional PPG, three-state result with interval *(no estimator)*
- [x] Scaffold the React + TypeScript + Vite frontend with Tailwind *(ticked 2026-09-12 audit: `app/frontend/`, 7 routed pages, `tsc -b && vite build` 2.15 s, lint clean — built for the AUDIT tool, not the inference app)*
- [ ] 🔴 SUPERSEDED — Build the capture and upload flow with input quality feedback *(the audit app uploads CSVs, which is not image capture with quality feedback)*
- [ ] 🔴 SUPERSEDED — Build the results view: Hb value, uncertainty interval, three-state decision, chromophore map *(no estimator)*
- [ ] 🔴 SUPERSEDED — Add the Three.js / react-three-fiber visualisation and Framer Motion transitions *(Framer Motion is in use in the audit app; Three.js is not in `package.json` and nothing in the surviving product needs 3D)*
- [ ] 🔴 SUPERSEDED — Enforce screening-not-diagnosis framing and the no-clinical-validation disclaimer everywhere a result appears *(the item is about estimator results; the audit app already carries "Nothing here is a clinical validation" on every page shell (`App.tsx`, `Landing.tsx`))*
- [ ] 🔴 SUPERSEDED — Add end-to-end tests covering the abstention path and the missing-modality path *(neither path exists)*

### Phase 10: Flutter mobile application

> 🔴 **SUPERSEDED IN FULL (audit 2026-09-12).** Every item ports an estimator's capture
> and results flow that does not exist. Not blocked on tooling: `C:\src\flutter` is
> present. `mobile/README.md` is a placeholder.
- [ ] 🔴 SUPERSEDED — Verify the Flutter toolchain at `C:\src\flutter` and scaffold the project in `mobile/`
- [ ] 🔴 SUPERSEDED — Implement camera capture with on-device quality checks (focus, exposure, sclera visibility)
- [ ] 🔴 SUPERSEDED — Integrate with the backend API, including offline and failure states
- [ ] 🔴 SUPERSEDED — Port the results view with parity to the web three-state output
- [ ] 🔴 SUPERSEDED — Evaluate on-device versus server-side inference and record the decision
- [ ] 🔴 SUPERSEDED — Test across a range of phone cameras and log the cross-device behaviour
- [ ] 🔴 SUPERSEDED — Carry the screening-not-diagnosis framing into every mobile surface

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

### 2026-09-10 — PyTorch installed CPU-only; no GPU available
> ⚠️ **SUPERSEDED and FACTUALLY WRONG — see the correction dated 2026-09-11 below.**

**Decision.** Installed the default `torch` wheel, which resolved to a CPU build
(`torch 2.14.0+cpu`, `cuda.is_available() == False`).
**Rationale.** No CUDA device was detected on this machine, so a CUDA wheel would have
added several GB for nothing.
**Alternatives considered.** Forcing a CUDA index URL; deferred until a GPU exists.
**Consequences.** Phase 3 (Monte Carlo simulation) and Phase 5 (CNN baseline) are the
compute-heavy phases and will be slow. Revisit before Phase 3: either obtain GPU access
and reinstall from the CUDA index, or design the simulator around vectorised NumPy and
a reduced photon count, and log which path was taken.

### 2026-09-11 — CORRECTION to the 2026-09-10 CPU-only entry: the machine has CUDA hardware
**Correction.** The entry above is wrong in its cause and its conclusion. This machine
has an **NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB (8 GB) VRAM, driver 610.62,
CUDA UMD 13.3**. `nvidia-smi` reports it.
**What actually happened.** `pip install` resolved `torch` from the default PyPI index,
which serves the CPU wheel on Windows. `torch.cuda.is_available() == False` was a
consequence of installing a CPU-only build, **not** evidence that no CUDA device was
present. The original entry inferred absent hardware from a package-resolution
artefact, which was an unfounded leap: that flag cannot distinguish "no GPU" from
"no CUDA runtime in this wheel", and nothing was run to tell the two apart.
**Action taken.** Uninstalled `torch`, `torchvision` and `torchaudio`, then reinstalled
from the CUDA index:
`pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu126`
Verified `cuda.is_available()`, device name, total memory, and a matmul on the device.
**Consequences.**
- **The Phase 3 compute revisit point is CLOSED.** The simulator and CNN baseline may
  assume GPU availability. The fallback plan in the superseded entry (vectorised NumPy
  with a reduced photon count) is no longer required on compute grounds, though it may
  still be worth having for reproducibility on CPU-only machines.
- **8 GB VRAM is now the binding constraint**, not compute availability. It caps batch
  size and model choice in Phase 5 (CNN baseline) and Phase 8 (multimodal fusion),
  where several modality encoders may need to be resident at once. Recorded in the
  TECH STACK section.
- **Standing rule:** never install `torch` from the default index in this project. See
  the comment in `pyproject.toml`.
**Lesson for future entries.** Do not record an inferred cause as a finding. State the
observation ("`cuda.is_available()` returned False") separately from the explanation,
and verify the explanation before logging it.

### 2026-09-10 — `data/` excluded from git in full, including its subdirectory markers
**Decision.** `.gitignore` excludes `data/` entirely, so the `.gitkeep` files in
`data/interim/`, `data/processed/` and `data/synthetic/` are ignored too.
**Rationale.** The hard constraint that no dataset is ever committed outweighs the
convenience of committed directory markers.
**Alternatives considered.** Negation patterns to keep the markers tracked; rejected as
an unnecessary hole in a rule that should be absolute.
**Consequences.** A fresh clone has no `data/` tree. Any script that writes to
`data/interim`, `data/processed` or `data/synthetic` must create its directory with
`mkdir(parents=True, exist_ok=True)` rather than assume it exists.

### 2026-09-11 — `dataset anemia` CONFIRMED as Eyes-Defy-Anemia
**Decision.** The provisional identification of 2026-09-10 is now confirmed and the
inventory updated. The folder is **not** renamed; `data/raw/` stays read-only and
`paths.EYES_DEFY` carries the mapping.
**Evidence.** Italian-language spreadsheet internals (sheet `Foglio1`, annotator notes
"da segmentare la forniceale", "Segmentato da Michele"), India and Italy site folders,
per-subject `_palpebral`/`_forniceal` masks beside a source `.jpg`, and 95 + 123 = 218
subjects with Hgb — matching the published dataset.
**Consequences.** Eyes-Defy is the project's **only** source of full photographs paired
with haemoglobin, and therefore the only end-to-end test bed for N1. Its Italy sheet
needed two repairs: 15 of 123 Hb values use a European decimal comma (`15,1`) and would
have been silently dropped to NaN by a naive parse; one row is `_` with the note "Hgb
not available" and stays genuinely missing (217 of 218 have Hb).

### 2026-09-11 — CP-AnemiC and Ghana conjunctiva are ONE site (overlap verdict)
**Decision.** The two are permanently merged into a single site `ghana`, together with
the Ghana fingernail set. No split, table or claim may treat them as independent.
**Evidence.** Four independent signals agree: 419 distinct MD5 hashes shared; 620/710
(87.3%) of CP-AnemiC files byte-identical to a Ghana conjunctiva file; 697/710 (98.2%)
within pHash Hamming 10 and 646 at distance **0**; 701/710 above 0.92 embedding cosine.
Only 14.2% of Ghana conjunctiva files are covered, so Ghana is the superset and
**CP-AnemiC is a labelled subset of it**.
**Alternatives considered.** Treating the non-matching ~2% of CP-AnemiC as an
independent site; rejected as too small to support any claim and impossible to
disentangle from the shared collection protocol.
**Consequences.** Cross-site evaluation now rests entirely on Eyes-Defy's India/Italy
pair. The metadata-correspondence signal could not be computed at all: the Ghana sets
ship no Hb, age or sex. That signal is *unavailable*, not negative.

### 2026-09-11 — CP-AnemiC haemoglobin labels are unreliable on duplicated images
**Decision.** CP-AnemiC is **not** treated as a trustworthy per-image Hb regression
target. Any use of it must first deduplicate by content hash and then either drop
conflicted groups or treat them as unlabelled; whichever is chosen must be stated with
the result.
**Evidence.** 710 files contain only 498 unique images. Of 91 exact-duplicate groups,
**90 carry more than one distinct Hb value**. The worst is one image appearing 10 times
with Hb recorded as 4.6, 5.1, 8.0, 8.7, 8.8, 8.9, 9.5, 9.7, 10.5 and 10.93 g/dL across
8 hospitals (`reports/figures/phase1_cp_anemic_label_conflict.png`). 303 of 710 files
(42.7%) sit in a conflicted group.
**Consequences.** This is independent of the overlap finding and worse for modelling.
All 48 severe cases (<7 g/dL) live in this dataset, so **no calibrated claim about
severe anemia is available from real data**. It strengthens the motivation for the N2
simulator while removing the means to validate the simulator's severe range.

### 2026-09-11 — N1 cannot be computed on the two largest conjunctiva datasets
**Decision.** N1's end-to-end validation is scoped to Eyes-Defy (218 subjects). nus8
validates illuminant accuracy; SBVPI/MOBIUS validate sclera segmentation. The Ghana
pool is excluded from any N1 result.
**Evidence.** CP-AnemiC and Ghana conjunctiva are pre-segmented cutouts: mean near-black
pixel fraction 0.70 and 0.72, with **100% of sampled images over 30% black**. The eye
surrounding the conjunctiva, including the sclera, has been removed. Eyes-Defy measures
0.000.
**Consequences.** The headline claim rests on 218 subjects, two sites, and two regional
variants of one phone (`SM-G920F`, `SM-G920I`) — not on the ~9,000 images the collection
appears to offer. This must be stated in the paper, not discovered by a reviewer.

### 2026-09-11 — Ghana conjunctiva and fingernail share participants (N6 opportunity)
**Decision.** Recorded as an **opportunity, not contamination**, and the paired subjects
are grouped together for splitting.
**Evidence.** Subject numbers parsed from filenames match across body sites: non-anemic
204/204 (Jaccard **1.000**) over a contiguous 1–204 range; anemic 250 shared of 271
(0.919). Image content does not overlap (0 shared MD5, minimum pHash 10), as expected
for different body parts — so this is inferred from the numbering scheme, not proven by
a participant ID column.
**Consequences.** ~454 participants have paired conjunctiva + nail images, which is what
N6 needs. But they carry **binary labels only, no Hb**, so fusion can be developed and
its graceful degradation demonstrated on classification only. Hb_PPG shares no subjects
with any image dataset, so image+PPG fusion is **simulation-only, permanently**.

### 2026-09-11 — Splits grouped by (subject_id, content hash), not subject_id alone
**Decision.** The grouping unit is the connected component of a graph joining subject
ids and MD5 hashes, implemented in `src/hemosight/io/splits.py`.
**Rationale.** Subject-level grouping is insufficient here: identical images appear
under different subject ids, and CP-AnemiC images recur inside the Ghana set. In the
Ghana pool, **1,708 nominal subject ids collapse to 1,067 leak-proof groups** — that gap
is exactly the leakage a plain subject-level split would have permitted.
**Consequences.** Every split carries an automated leak check that fails the script on
violation. Splits are frozen under seed `20260911` in `configs/phase1_splits.yaml`.

### 2026-09-11 — Split outputs written to `data/interim/splits/`, not `data/processed/`
**Decision.** Phase 1 plan item amended: splits live in `data/interim/splits/`.
**Rationale.** The Phase 1 instruction specified `data/interim/` for all outputs, and
splits are regenerable intermediate artefacts rather than a finished processed dataset.
**Consequences.** Logged rather than changed silently, per the WORKING PROTOCOL. If a
frozen `data/processed/splits/` copy is wanted later for release, it should be a
deliberate copy step with its own log entry.

### 2026-09-11 — N2's premise narrowed; N5 materially weakened
**Decision.** Two novelty claims need their wording changed before any write-up. The
claims themselves are NOT edited in section 2 — that text stays verbatim as the
original brief — but no paper text may repeat them as written.
**N2** says the simulator "supplies severe-anemia cases that no public dataset
contains". False as written: CP-AnemiC holds 48 images below 7 g/dL, minimum 3.1 g/dL.
The defensible version is that severe cases are *rare, confined to one site, and carry
unreliable labels*.
**N5** assumes SCIN skin-tone labels can be attached to the anemia datasets. They
cannot. `scin-main/` on disk holds **no data at all** (5 documentation files; the images
live in a GCS bucket), and SCIN is dermatology imagery with no conjunctiva photographs,
no Hb, and no participant correspondence to any dataset here. The only route is to train
a skin-tone estimator on SCIN and apply it, making every fairness stratum an *estimate
with its own error*. The mechanistic melanin-vs-illuminant decomposition is therefore
testable only in simulation, where melanin is known by construction.
**Consequences.** Both are recorded here so the gap between the original claim and what
the data supports is visible for the rest of the project.

## PHASE 1.5 DECISIONS (2026-09-11)

### 2026-09-11 — N1 restructured into N1a / N1b / N1c
**Decision.** N1 is now three sub-claims with separate datasets and metrics. See
section 2.
**Justification.** Phase 1 found CP-AnemiC and the Ghana conjunctiva set are
pre-segmented cutouts (mean near-black fraction 0.71/0.72; **the least-cropped image of
all 4,972 is still 49.7% black**), so the sclera N1 needs is absent. Treating N1 as one
end-to-end claim would have made it look refuted by a data limitation that in fact only
bounds its final stage. Splitting it lets N1a and N1b be validated at full strength on
`nus8` and `MOBIUS`, where no Hb labels are needed and real device diversity exists.
**Original wording, preserved.** *"N1. Calibration-free spectral super-resolution. Use
the sclera as an endogenous white reference to estimate the scene illuminant, removing
the per-camera spectral profiling and per-use radiometric calibration that currently
blocks hyperspectral-reconstruction methods from field deployment. THIS IS THE HEADLINE
CLAIM."*
**Consequences.** The headline survives, but N1c — the only sub-claim that touches
haemoglobin — is permanently bounded to 218 subjects, 2 sites, 2 variants of one phone,
no severe cases. That limitation is now written into the claim itself.

### 2026-09-11 — No uncropped originals exist anywhere on disk (CLOSED, do not re-litigate)
**Decision.** The search is closed. N1c's data base cannot be widened from local data.
**Evidence.** Exhaustive, not sampled (`scripts/phase1_5_search_originals.py`):
- Every one of 710 CP-AnemiC and 4,262 Ghana conjunctiva images scanned. **Minimum
  black fraction 0.497 and 0.496** — the least-cropped image in either set is still
  half black. **Zero images below 5% black. Zero images above 1 MP** (max 0.14 MP).
- `Fingernails.rar` (27 MB) listed via a pure-Python RAR5 header parse, no extraction:
  **4,260 PNGs with names identical to the extracted folder** — a compressed copy, not
  originals.
- All 12 nus8 archives are sensor data, not conjunctiva.
- `ghana_conj` has **no subdirectories and no non-image files**; CP-AnemiC has only
  `Anemic/`, `Non-anemic/` and its spreadsheet.
**Consequences.** The cutouts are the only form in which these data were ever
distributed. Nothing further to check locally; re-obtaining originals would require
contacting the original authors, which is outside this project's constraints.

### 2026-09-11 — Ghana pool is BINARY-LABEL-ONLY; `hb_label_trusted` enforced
**Decision.** All haemoglobin values from `cp_anemic`, `ghana_conj` and `ghana_nail` are
**rejected for every regression task**. Enforced by `hb_label_trusted`, set inside
`_finalise()` in `src/hemosight/io/manifests.py` so a manifest rebuild cannot silently
restore them, plus a `trusted_hb()` helper that downstream code must use.
**Evidence** (`scripts/phase1_5_label_arbitration.py`):
- The briefed comparison could not be run as stated: **the Ghana conjunctiva set ships
  no haemoglobin values at all** (0 of 4,262), only a class token in the filename. So
  "adopt Ghana as authoritative" was never available.
- CP-AnemiC Hb is **not** self-consistent: 90 of 91 exact-duplicate groups carry more
  than one Hb value; worst spread **7.10 g/dL within one byte-identical image**.
- Therefore neither collection is self-consistent on Hb, so the briefed fallback applies.
**Additional finding — the binary label has its own noise floor.** Ghana's binary label
*is* internally self-consistent (0 of 1,397 duplicate groups conflict). But on the 419
unique images present in both collections the two **disagree on 7 (1.67%)**. CP-AnemiC's
`anemia_label` is exactly `hb_g_dl < 11.0` and its severity bins are the exact WHO
bands, so it carries no information beyond Hb — meaning each disagreement is a genuine
mislabelling in one collection or the other. **No binary result on this pool may claim
accuracy above ~98.3% and attribute the gap to the model.** The rate is measurable on
419 images and unmeasurable on the remaining ~4,000.
**Consequences.** The project's entire trustworthy haemoglobin base is **469 rows**:
217 Eyes-Defy + 252 Hb_PPG. **It contains zero severe cases.**

### 2026-09-11 — N2's justification corrected
**Decision.** N2's justification is now the label-trustworthiness argument in section 2.
**Original wording, preserved.** *"This supplies severe-anemia cases that no public
dataset contains."*
**Why it was wrong.** CP-AnemiC contains 48 images below 7 g/dL, minimum 3.1 g/dL. The
statement was factually false and would not have survived review.
**Why the replacement is stronger.** Those 48 cases are exactly the ones whose labels
the arbitration rejected, so the simulator remains the only source of *reliably
labelled* severe anemia. The argument shifts from quantity to trustworthiness, which the
Phase 1 evidence supports directly.

### 2026-09-11 — N5 rebuilt without SCIN; `data/raw/scin-main` deleted
**Decision.** SCIN removed as a dependency and deleted from disk. N5 now estimates skin
tone by Individual Typology Angle on N1-calibrated periocular skin.
**Original wording, preserved.** *"N5. Mechanistic fairness audit. Report performance
stratified by skin tone and source device, and DECOMPOSE any gap into melanin absorption
versus illuminant estimation error."* (The claim stands; only its method changed.)
**Justification.** `scin-main/` held **no data** — 5 documentation files, 212 KB, zero
images or label tables; SCIN's data lives in a GCS bucket. Even downloaded it could not
serve N5: SCIN is dermatology imagery with no conjunctiva, no Hb, and no participant
correspondence to any dataset here, so attaching its labels would require an unvalidated
cross-domain transfer.
**Note on the READ-ONLY rule.** This is the only deliberate deletion inside `data/raw/`,
made on explicit instruction. It removed documentation, not data, and is recoverable
from `github.com/google-research-datasets/scin`. The READ-ONLY rule otherwise stands
unchanged.
**Why ITA is the better method.** It is computed in closed form from CIELAB, needs no
external dataset, and — because it runs on N1-calibrated images — makes the melanin
versus illuminant decomposition mechanistic rather than descriptive: the same illuminant
estimate under test is what makes ITA comparable across captures.
**Consequences.** N5 gains three stated limitations that must appear verbatim in the
paper: no ground-truth tone labels, ITA is a proxy, and the tone axis is confounded with
site.

### 2026-09-11 — N6 scoped to what the data supports
**Decision.** Two scope limits recorded in section 2 as permanent, not as open problems.
**Justification.** The ~454 paired conjunctiva+nail participants sit in the
BINARY-LABEL-ONLY pool, so fusion there cannot produce a validated g/dL estimate.
`Hb_PPG_Dataset` shares no participants with any image dataset, and the "no new data
ever" constraint means it never will.
**Consequences.** N6 is demonstrated as (a) real classification fusion on paired body
sites and (b) simulation-only fusion involving PPG. Any paper text implying a validated
multimodal Hb regression would be false.

### 2026-09-11 — `reports/figures/` removed from version control
**Decision.** `reports/figures/` added to `.gitignore` and removed from the git index
with `git rm -r --cached` (files kept on disk). `reports/README.md` documents exact
regeneration commands per figure.
**Justification.** Figures render dataset pixels, and 9 of 10 datasets ship no licence
file, so their redistribution terms are unverified. Committing them would redistribute
dataset imagery through the repository — the precise thing the "nothing committed" rule
exists to prevent.
**Verified.** `git ls-files reports/figures/` returns nothing; `git check-ignore`
confirms the rule matches. All figures regenerate from `data/raw/` with no manual steps.

## PHASE 2 DECISIONS (2026-09-11)

### 2026-09-11 — N1b's primary evaluation region is the IRIS, not the sclera
**Decision.** Self-consistency is measured on the iris, a surface never used to
estimate the illuminant. A sclera figure using a left/right spatial holdout is
reported as secondary and explicitly labelled partially circular.
**Rationale.** Estimating from the sclera and evaluating on the sclera is degenerate:
`corrected = measured / (measured / prior) = prior`, a constant, so the spread
collapses to exactly zero for every subject regardless of the data. That would have
looked like a spectacular confirmation of the headline claim and meant nothing.
**Evidence that this was not hypothetical.** On the secondary sclera-holdout region the
sclera methods appear to win comfortably (2.47 vs 3.33 dE2000 for shades-of-grey). On
the non-circular iris they lose to grey-world. **Measuring only on the sclera would have
produced a confident and wrong claim of success.**
**Consequences.** `tests/test_phase2.py::test_selfconsistency_is_circular_on_the_
reference_region` asserts the degeneracy exists, so any future "simplification" of the
protocol fails a test rather than silently producing a fake result.

### 2026-09-11 — Self-consistency cannot answer the reflectance-prior question
**Decision.** The prior comparison (neutral / fixed-population / per-subject) is
reported from N1b as instructed, together with a statement that the protocol is
structurally incapable of answering it. The question is answered by N1a instead.
**Rationale.** A prior is constant for a given subject, so it multiplies all of that
subject's captures by the same factor: it *shifts* the subject's colour cluster without
changing its *spread*. Within-subject spread is therefore blind to the prior by
construction.
**Evidence.** Predicted before running, then confirmed: neutral 7.31, fixed 7.43,
per-subject 7.43 dE2000; fixed vs neutral paired p = 0.25 (not significant); fixed and
per-subject are **bit-identical** (max per-subject difference 0.0).
**Second finding.** Per-subject and fixed-population coincide because a per-subject
prior can only be fitted from that subject's own ground truth, which a held-out subject
by definition lacks, so the estimator falls back to the population value. **A
per-subject prior is not evaluable in any deployable setting** — which answers whether
one could be shipped: it could not.
**Consequences.** N1a (nus8, ground-truth illuminants) carries the prior question:
knowing the reference reflectance halves the error, 1.266 -> 0.666 deg. N1c will test
it against haemoglobin.

### 2026-09-11 — N1b runs on all 100 MOBIUS subjects, not the 35 annotated ones
**Decision.** `index_mobius_all()` indexes all 16,717 frames; N1b uses the trained
model's masks rather than ground-truth masks.
**Rationale.** A first run selected only 35 subjects, because `index_mobius()` returns
only the 3,559 annotated frames — and those come from exactly the subjects the
segmentation model trained on. That would have evaluated the pipeline on its own
training subjects while discarding two thirds of the population. The run was stopped
and restarted.
**Consequences.** 100 subjects, 1,796 frames, 40 held out for evaluation. 71 of the 100
subjects were never seen in segmentation training; this is recorded in the results JSON
so the unseen subset can be reported separately if the distinction ever matters.

### 2026-09-11 — MOBIUS and SBVPI label spaces reconciled in the loss, not the labels
**Decision.** `merged_bg_cross_entropy` merges the background and periocular logits
for MOBIUS frames only.
**Rationale.** MOBIUS marks periocular skin black, identical to true background, while
SBVPI gives it its own class. Training naively on both teaches the model that skin is
simultaneously class 0 and class 4, and the periocular class collapses. Remapping the
labels instead would have thrown away either SBVPI's periocular supervision or
MOBIUS's negative supervision.
**Evidence it worked.** Epoch 1 shows background IoU 0.110 and periocular 0.357 while
the conventions were still in conflict; by epoch 3 they reach 0.953 and 0.957, ending
at 0.964 and 0.975.

### 2026-09-11 — 16-bit NUS PNGs must be read with cv2, never PIL
**Decision.** `load_linear_png` uses `cv2.IMREAD_UNCHANGED` and reverses BGR.
**Rationale.** The NUS PNGs are 16-bit (bit depth 16, colour type 2). PIL returns them
as 8-bit RGB **without raising**, collapsing ~1,848 distinct values to 11 on a typical
frame. Every downstream number would have been noise, and nothing would have failed
loudly.
**Related.** Dark-level subtraction is equally load-bearing and equally silent: on
Canon600D it moves mean angular error from 12.04 to 0.89 deg. Both are verified per
camera before use.

### 2026-09-11 — The MOBIUS sclera prior is contaminated by grey-world's bias
**Decision.** The fitted population sclera reflectance prior is reported with an
explicit warning that it is **not** interpretable as physical sclera reflectance.
**Evidence.** The fitted value is `[0.858, 1.020, 1.122]` — more blue than red, the
opposite of a yellowish sclera. MOBIUS ships no ground-truth illuminant, so the prior
had to be fitted against grey-world under a stated assumption; MOBIUS frames are
skin-dominated, grey-world therefore leans red, and the "reflectance" inherited the
inverse of that bias.
**Consequences.** This is why the fitted prior scores marginally *worse* than assuming
neutrality on MOBIUS. A physically meaningful sclera prior requires a dataset with
ground-truth illuminants or measured reflectance; neither exists in this project. Any
future sclera prior must be fitted where ground truth exists, or derived from the N2
simulator — not fitted against another estimator.

## PHASE 2.5 DECISIONS (2026-09-11)

### 2026-09-11 — N1 is REFUTED in its entirety; the contribution becomes the diagnosis
**Decision.** N1 — "the sclera as an endogenous white reference enables calibration-free
colour correction" — is recorded as a **negative result**. Two independent endogenous
ocular references (sclera, corneal specular highlight) have now been tested on the same
protocol and neither beats grey-world, a whole-image statistic requiring no
segmentation, no reference surface and no anatomy.
**Evidence** (held-out iris, within-subject dE2000, 40 subjects, paired Wilcoxon):
grey-world 6.076; specular+sclera 7.047 (p=4.5e-04 worse); sclera 7.427 (p=3.1e-08
worse); specular 7.821 (p=4.5e-06 worse); no correction 9.530.
**The rescue did not rescue.** Specular vs sclera: +0.394 dE2000, **p = 0.29, not
significant**. Removing the per-subject reflectance term — the exact quantity Phase 2
identified as the bottleneck — did not improve the result.
**The replacement contribution.** A quantified, mechanistic account of *why* endogenous
ocular white references fail: the sclera's diffuse reflectance varies between
individuals by more than the illuminant signal being estimated (10% yellowing = 4.40
deg, larger than grey-world's entire error), while segmentation (31 px mask
perturbation = 0.40 deg) and estimation mathematics (0.666 deg given a known
reflectance, six sensors) are both exonerated. The corneal highlight removes the
per-subject term and still fails, while adding its own failure modes.
**Consequences.** No paper text may present N1 as a working method. **N1a survives
intact** as a component result. The project's calibration recommendation downstream is
grey-world on a tight periocular crop.

### 2026-09-11 — Task 4 refuted its own hypothesis; reported as such
**Decision.** The deployment-realism check was expected to show grey-world degrading as
scene context vanished, favouring local references. It shows the opposite and is
reported that way.
**Evidence.** Grey-world mean dE2000 by field of view: 100% -> 6.076, 60% -> 5.790,
40% -> 5.416, **25% -> 3.935**, 15% -> 4.889. Its best result anywhere in Phase 2 or
2.5, and better than every endogenous method by ~3.1-3.9 dE2000.
**Mechanism.** A wide MOBIUS frame is dominated by facial skin, which is strongly and
consistently red, so the grey-world assumption is badly violated. A tight periocular
crop contains sclera, iris, pupil, lashes and a little skin — a far more balanced set of
reflectances, so the assumption is *better* satisfied on exactly the narrow crop a real
capture produces. The tightest crop (15%) worsens again, consistent with losing that
balance.
**Consequences.** Grey-world's advantage does not merely survive the deployment-realistic
regime, it **widens**. Caveat recorded against overstatement: these crops are centred on
the eye using the segmentation and are therefore idealised; hand-framing noise was not
simulated, though the effect size (-2.14 dE2000) makes it unlikely to be erased.

### 2026-09-11 — Highlight detection must be physics-based, not percentile-based
**Decision.** A specular pixel must exceed BOTH 3x the region's median luminance AND its
99th percentile.
**Rationale.** A percentile alone is not a detector. The top 1% of a 350,000-pixel
iris+pupil region is ~3,500 pixels whether or not any highlight exists, so a
percentile-only rule fires on every image by construction. The first census run reported
97.3% usable — an artefact of the detector never returning empty. The dichromatic model
supplies a real criterion: a specular pixel is much brighter than the same surface's
body reflectance.
**Consequences.** The honest rate is 71.7% on MOBIUS, not 97.3%.
`tests/test_phase2_5.py::test_uniform_region_yields_no_highlight` asserts a flat
synthetic iris yields zero detections.

### 2026-09-11 — Degenerate colour clouds are the signal, not a fit failure
**Decision.** `degenerate_direction()` was added as the PREFERRED decomposition route.
**Rationale.** The verification test failed on first run: the dichromatic plane fit
returned None for the pupil. Investigation showed why — with `D ~= 0` the pupil's pixels
satisfy `I ~= m_s * L` and collapse to a single direction (s1/s0 = 0.019), so a plane fit
correctly refuses them. But that refusal discards the cleanest reading available: the
principal direction recovers the true illuminant to within 2 degrees.
**Consequences.** The test caught a real defect rather than a test artefact. Both routes
are now verified against synthetic surfaces built from the dichromatic model with a known
illuminant.

### 2026-09-11 — SBVPI excluded from the feasibility gate denominator
**Decision.** SBVPI's 0% highlight rate is reported separately, not averaged into the
gate.
**Rationale.** The Phase 2 model outputs **zero** iris/pupil pixels on SBVPI, consistent
with its measured iris IoU of 0.000 there. The 0% measures segmentation transfer, not
highlight availability, and averaging it in would have dragged the headline number down
for the wrong reason (58.6% all-frames versus 71.7% MOBIUS).

## PHASE 3 DECISIONS (2026-09-11)

### 2026-09-11 — Claim hierarchy restructured: N3+N4 become PRIMARY, N1 becomes a secondary negative result
**Decision.** The claim hierarchy in section 2 now ranks N3+N4 as the primary
contribution and N1 as a secondary one consisting of a negative result plus a practical
recommendation. Substance of N2, N5 and N6 is unchanged. All original claim text is
retained verbatim under its refuted banner.
**Rationale.** N1 was the headline and Phase 2.5 refuted it on pre-declared criteria.
Continuing to present it as the headline would misrepresent the evidence. What the
project can still establish is the physical estimation pipeline: haemoglobin in g/dL
with a calibrated interval and a principled abstention, which is N3+N4.
**The negative result is stated positively.** Two independent endogenous references
tested on 100 subjects, 3 devices, 3 lighting conditions; both lose to grey-world; and
grey-world *improves* under tight crops (6.076 -> 3.935 dE2000 at 25% FOV), which is
both a useful practical recommendation and a counter-intuitive finding worth reporting.
**Consequences.** Grey-world on a tight periocular crop is the normalisation for all
later phases. Phase 3's gate (Task 0) now carries unusual weight: it asks whether the
colour-to-haemoglobin inversion survives the residual error that recommendation leaves.

### 2026-09-11 — The Phase 2 diagnosis is recorded as INCOMPLETE
**Decision.** A standing warning is attached to the claim hierarchy: the Phase 2
explanation for why the sclera fails is not settled and may not be presented as such.
**Evidence.** Phase 2 attributed the failure to inter-individual reflectance variance
(10% scleral yellowing moves the estimate 4.40 deg). Phase 2.5 removed that term
outright by using a corneal specular reference, which carries no per-subject
reflectance component at all. The result did not improve: **specular vs sclera
+0.394 dE2000, p = 0.29**.
**Interpretation.** If inter-individual reflectance variance were the sole limiting
factor, eliminating it should have helped. It did not. Either another error source
dominates both methods, or the specular route introduces compensating errors of its own
(availability on 78% of frames, 41% multi-source frames, 39 pp device spread).
**Consequences.** The diagnosis remains the project's contribution from N1, but it is a
*partial* diagnosis. Honest framing: segmentation and estimation mathematics are
exonerated with measured bounds; inter-individual reflectance variance is demonstrated
to be large but is NOT sufficient to explain the whole gap. Identifying the remainder is
open work, not a claimed result.

### 2026-09-11 — TASK 0 GATE FAILED: work stopped before Tasks 1-3
**Decision.** The full layered Monte Carlo simulator, its literature validation, and the
synthetic corpus (Tasks 1-3) were **not built**. Work stopped at the gate, as the
pre-declared protocol required.
**Evidence.** Haemoglobin MAE at the residual colour error this project's own
recommended normalisation leaves (3.935 dE2000, grey-world @25% FOV, measured in
Phase 2.5) is **3.417 g/dL** — 1.7x the >2.0 g/dL "NOT RECOVERABLE" threshold declared
in CLAUDE.md before running. At full-frame grey-world (6.076) it is 5.096 g/dL. Only at
a residual of 1.0 dE2000 — better than any method measured anywhere in this project —
does it become viable (0.864 g/dL).
**Rationale for stopping.** The corpus exists to train an RGB-to-haemoglobin inversion.
The gate shows that inversion cannot survive the available calibration error, so more
or better training data does not address the limit. Building it anyway would be the
exact waste the gate was designed to prevent.
**Consequences.** N2's purpose changes from *data generator* to *analysis instrument*:
the minimal forward model produced the gate result, the signal-to-noise framing, the
low-Hb sensitivity finding and the melanin confounder without any photon transport.

### 2026-09-11 — The failure is a signal-to-noise limit, not a modelling artefact
> ⚠️ **CORRECTED 2026-09-12 (Phase 6.5 Task 1).** The "~0.70 (measured on 216 subjects)" figure below is WITHDRAWN: it had no producing script, and the binned method it was attributed to has a null of ~2.1 dE2000/g/dL. Measured value: **0.84 dE2000/g/dL (CI 0.57-1.17)**, noise/signal **4.7x**, not 5.6x. Verdict unchanged. See the 2026-09-12 entry "The empirical signal was a constant".
**Decision.** The result is stated as a signal-versus-noise comparison, which needs no
inversion machinery and is therefore harder to dismiss.
**Evidence.** Haemoglobin changes conjunctival colour by **0.452 dE2000 per g/dL**
(simulated) or **~0.70** (measured on 216 real Eyes-Defy subjects using the dataset's own
palpebral masks). The best calibration available leaves **3.935 dE2000**. Noise exceeds
signal by **5.6x (empirical) to 8.7x (simulated)** — equivalent to 5.6-8.7 g/dL of
haemoglobin error against a clinically meaningful range only 14 g/dL wide.
**Robustness.** Five tissue-assumption variants (BVF 0.02-0.15, StO2 0.60-1.00) all give
7.5-12.2 g/dL equivalent error. The conclusion does not depend on one parameter choice.
**The gate is OPTIMISTIC**, which strengthens it: oxygenation, blood volume fraction,
melanin and layer thickness were all held fixed AND known. Real per-subject variation in
those adds error on top.
**Consequences.** The failure is specific to *ambient-light RGB photography*, not to
non-invasive haemoglobin estimation in general. The PPG modality uses four narrow
wavelengths with a controlled source and no ambient illuminant to estimate, and is not
subject to this particular limit.

### 2026-09-11 — Melanin is a catastrophic confounder (an N5 finding found in Phase 3)
**Decision.** Recorded here and flagged forward to N5 rather than left to be
rediscovered.
**Evidence** (Task 4, illuminant held perfect, only the tissue prior perturbed):
a melanin volume fraction of **0.005 — half of one percent — shifts recovered
haemoglobin by +9.6 g/dL**. At 0.01 and above the estimate rails to the top of the
search range, i.e. total failure. By contrast oxygenation is **benign across its entire
physiological range** (0.60-1.00 all within +/-1.0 g/dL), blood volume fraction is
tolerable to about +/-30%, and layer thickness to -20%/+100%.
**Interpretation.** Conjunctival melanin is low but nonzero and conjunctival melanosis
is more prevalent in darker-skinned populations. This is a direct, quantified mechanism
by which a colour-based haemoglobin estimator would be **severely biased by skin tone** —
exactly what N5 exists to audit.
**Qualifications recorded against overstatement.** The epithelial melanin layer in this
model is thin, so the sensitivity may be overstated by the layered approximation; and
above 0.01 the estimate rails, so only the fact of failure is meaningful, not the
magnitude. Neither changes the direction.

### 2026-09-11 — Optical constants are TRANSCRIBED and require verification
**Decision.** `constants.py` carries a prominent VERIFICATION REQUIRED banner and a
`validate_constants()` self-check; every downstream number is provisional.
**Rationale.** This environment has no network access and no installed package ships
haemoglobin optical data, so the spectral tables were transcribed from the cited
published compilations rather than read from primary files.
**The self-check earned its place.** It FAILED on first run: the 500 nm isosbestic
landed at 515 nm, and the 529/545 pair had collapsed because HbO2's 542 nm alpha peak
was not rising above deoxy-Hb between them. Both were real transcription errors. After
correction all six isosbestic points land within 0.5 nm, the HbO2 visible peak is at
576 nm, and the deoxy/oxy red ratio is 8.4x.
**Consequences.** Internal consistency is not verification. Before publication the
primary sources must be re-read and `validate_constants()` re-run.

### 2026-09-11 — The six nus8 camera spectral sensitivities are NOT available
**Decision.** The CIE 1931 2-degree observer is used as a camera proxy; Task 3's
"project through the six nus8 cameras" could not be done as specified.
**Evidence.** NUS ships ground-truth illuminants and colorchecker coordinates, not
spectral sensitivity functions. `colour-science` ships measured SSFs for exactly two
cameras (Nikon 5100, Sigma SDMerill), neither of them a nus8 camera.
**Consequences.** Any camera-specific claim in later phases needs SSFs this project does
not have. Recorded as a data limitation, not worked around silently.

## PHASE 3.5 DECISIONS (2026-09-11)

### 2026-09-11 — The ratio reformulation is REFUTED; the imaging arm is definitively a negative result
**Decision.** Phase 3.5 Task 1 failed against its pre-declared threshold and work
stopped; Task 2 was not run. **Both formulations of the imaging claim — absolute
illuminant recovery and the illuminant-free ratio — have now failed.** The project's
imaging contribution is recorded as a negative result, not a method.
**Evidence.** Best ratio feature `iris_over_sclera`: within-subject spread 6.399
dE2000, ratio sensitivity 0.637 dE2000/g/dL, **equivalent residual 10.04 g/dL** against
a >2.0 failing threshold — 5x over. Every ratio feature is **worse than the uncorrected
sclera** (5.682): iris/sclera 6.399, pupil/iris 7.541, pupil/sclera 9.091. Grey-world
remains best at 3.330.
**The implementation was verified before the conclusion was accepted.** On a synthetic
diagonal illuminant change the ratio cancels **exactly, 0.000000 dE2000** with a plain
mean (0.046 with the percentile-trimmed summariser actually used). The observed spread
on real captures is **139x larger** than the implementation's own residual. The algebra
works; the data does not.
**Consequences.** No third reformulation is proposed. The imaging arm's status is
settled. Phases 4-8 must not be run as an imaging pipeline on the assumption that
colour-to-haemoglobin works.

### 2026-09-11 — Why the ratio fails: the reference is noisier within-subject than between
**Finding.** The ratio method needs the sclera stable across captures **of one person**,
not across people. Measured separately (Task 3):
- MOBIUS (phone captures): within-subject **5.860** dE2000 vs between-subject **4.050**
  — ratio **1.447**, the wrong side of 1.
- SBVPI (studio): within **1.685** vs between **1.825** — ratio **0.924**.
**Interpretation.** On phone captures the sclera varies MORE across captures of the same
person than between different people. Dividing by a reference noisier than the
population it normalises against adds variance rather than removing it, which is exactly
what Task 1 measured. Controlled studio conditions cut within-subject variation **3.5x**,
so the instability is dominated by capture conditions (geometry, gaze, specular
contamination, focus), not by tissue change — but even in a studio the ratio is 0.92,
still short of the << 1 regime required.
**Second mechanism.** von Kries diagonality is breaking down: the ratio should cancel
the camera's per-channel gains as well as the illuminant, yet the phone variance
fraction stays at **0.177**, against 0.202 uncorrected. Real sensitivities overlap
enough that an illuminant change is not a per-channel gain.
**Third.** The ratio raises the signal 1.4x (0.452 -> 0.637 dE2000/g/dL) but raises the
noise 1.9x. Reporting only the signal gain would have been the easy error.

### 2026-09-11 — A per-subject offset would not help, and is not obtainable
**Decision.** Per-subject calibration is recorded as unavailable and is not to be used
in any reported figure.
**Evidence.** An offset removes the BETWEEN-subject term and leaves the WITHIN-subject
term. On MOBIUS that removes 4.050 dE2000 and leaves **5.860** — it removes the smaller
term and leaves the larger one. It addresses the wrong problem.
**And it cannot be obtained.** A per-subject offset needs one capture of that subject
with a known answer: a reference haemoglobin measurement or a calibrated target in
frame. A screening deployment has neither — the premise is a first, uncalibrated capture
of a person whose haemoglobin is unknown. Any performance figure assuming an offset is
reporting an oracle, not a method.

### 2026-09-11 — Task 0: the downloaded constants disagree materially with the transcription
**Decision.** All spectral constants now load from `data/raw/optical_constants/`;
`constants_transcribed.py` is retained only for this comparison. The VERIFICATION
REQUIRED banner is lifted for haemoglobin, water, scattering and camera sensitivities,
and **remains** for layer thicknesses and blood volume fractions, which no downloaded
file backs.
**Evidence.** Median relative error 1.30%, but **18.8% of points differ by >10%**, max
**252%**. Worst: deoxy-Hb at 470 nm (16,156 sourced vs 56,880 transcribed), 1000 nm
(207 vs 726), 460 nm (23,389 vs 75,326). The transcription had deoxy-haemoglobin far
too high across the blue and the far red.
**Important caveat about the Phase 3 self-check.** The isosbestic check **PASSED on the
bad data** — it verified where the two curves cross, which was correct, while the values
between the crossings were wrong. A consistency check is not a verification, as was
flagged at the time.
**Effect on Phase 3.** Re-running the gate on sourced data gives **3.893 g/dL** (was
3.417) at the measured residual: the verdict is unchanged and marginally stronger, and
the 2.0 dE2000 case moves from MARGINAL to NOT RECOVERABLE.

### 2026-09-11 — Melanin confirmed to be a fitted power law; flagged as sweep-never-fix
**Evidence.** Fitting `mu_a = A*lambda^-k` to the spectralLIB melanin curve gives
A = 6.6e11, k = 3.330, with a maximum log-residual of **0.000000** — it is *exactly* a
power law with no measured structure in it.
**Consequences.** Combined with the Phase 3 finding that a melanin volume fraction of
0.005 shifts recovered Hb by **+9.6 g/dL**, this is the model's single most consequential
assumption: extreme sensitivity, large inter-individual variation, known only through a
smooth fit. `constants.py` now flags it to be SWEPT, never fixed, and
`melanin_powerlaw_fit()` exposes the exponent so the sensitivity can be propagated. It
is also the mechanism by which this method would be biased by skin tone (N5).

### 2026-09-11 — PPG arm promoted to CO-PRIMARY (Task 4, scope change only)
**Decision.** The claim hierarchy now carries two co-primary arms: imaging (contingent,
now refuted) and PPG (promoted). **No PPG model has been built.**
**Rationale.** `Hb_PPG_Dataset` is not subject to the Phase 3 failure for a structural
reason: four narrow wavelengths rather than three broad overlapping RGB channels, and a
**controlled source** — the LEDs are the illuminant, so there is no ambient illuminant to
estimate and the entire error term that defeated Phases 2, 2.5, 3 and 3.5 does not
exist. It is also the project's best-labelled data: 252 subjects with venous HemoCue
reference, against 217 usable Eyes-Defy images, and one of only two trustworthy Hb
sources left after the Phase 1.5 arbitration.
**Consequences.** The Phase 3/3.5 failures are specific to ambient-light RGB
photography, not to non-invasive haemoglobin estimation. That distinction is why the
project still has a viable primary claim.

### 2026-09-11 — Only 2 of 6 nus8 cameras have spectral sensitivities
**Evidence.** 28 cameras parsed from the Jiang camspec database (400-720 nm at 10 nm;
an initial parser assumed 400-700 and returned zero). Canon 600D matches exactly;
Canon 1DMarkIII is a different body from the nus8 1Ds Mark III. **Fujifilm X-M1 and
Samsung NX2000 are absent entirely.** An average mobile-phone SSF is also available and
is more representative of this project's inputs than any DSLR.
**Consequences.** Any camera-specific claim over all six nus8 sensors remains
unsupported by measured SSFs.

## PHASE 4 DECISIONS (2026-09-11)

### 2026-09-11 — The imaging arm is CLOSED. Final. Not to be reopened.
**Decision.** The imaging arm of this project is a closed negative result. No further
reformulation will be attempted or proposed.
**Record.** Four approaches tested, each with pre-declared thresholds, on 100 subjects
across 3 devices and 3 lighting conditions:
absolute illuminant from sclera (Phase 2, REFUTED, p~3e-8 vs grey-world);
absolute illuminant from corneal specular (Phase 2.5, REFUTED, no better than sclera
p=0.29); absolute colorimetric Hb inversion (Phase 3, NOT RECOVERABLE, signal
0.45-0.70 dE2000/g/dL vs 3.9 noise); illuminant-free within-image ratio (Phase 3.5,
REFUTED, reference noisier within-subject than between at 1.447).
**Consequences.** Any future work citing this project must cite the imaging arm as a
negative result with mechanism, never as a method.

### 2026-09-11 — GATE A FAILED: AC/DC does not cancel nuisance variance on real data
**Decision.** Gate A fails against its pre-declared threshold (>=50% nuisance variance
reduction).
**Evidence.** Median nuisance CV: raw DC **0.5633**; AC/DC **1.5299** (**-171.6%**, i.e.
worse); ratio-of-ratios **1.1152** (-98.0%). Best single feature's equivalent Hb noise
is **9.75 g/dL** against a population SD of **1.470** — noise is 6.6x the signal it must
resolve. Median R^2 with Hb across all feature groups <= 0.021.
**Honest limitation of the gate as designed.** Half the cancellation claim is NOT
testable here: all 252 subjects used ONE device, so there is no source-intensity or
sensor-gain variation for AC/DC to cancel. Between-subject DC variation (CV 0.39-0.63)
reflects finger thickness, perfusion and skin tone. What Gate A *does* establish is the
other half — AC/DC also claims to cancel static tissue absorption, and it demonstrably
does not: normalised features are MORE subject-variable than the raw DC they came from.
**Consequences.** Gate A is weak on device-invariance and decisive on tissue-invariance.

### 2026-09-11 — GATE B: PPG carries no recoverable Hb signal; three of four wavelengths are invisible to a phone
**Decision.** The PPG arm is NOT VIABLE on this dataset, in all three conditions.
**Evidence.** Grouped 10-fold CV, 252 subjects (one record each, so subject-level
K-fold IS leave-subject-out):
four wavelengths MAE **1.190**, R^2 **-0.025**; 660 nm only MAE 1.209, R^2 -0.037;
phone-RGB MAE 1.175, R^2 +0.007. **Two of three have NEGATIVE R^2 — worse than
predicting the population mean (MAE 1.175).** Gradient boosting finds nothing either
(MAE 1.193, r=+0.121). Best univariate |r| between any PPG feature and Hb is 0.149.
**The hardware fact.** Measured camspec sensitivities (28 cameras, 400-720 nm): at
660 nm R=0.179, G=0.016, B=0.007; at **730/850/940 nm all three channels are zero** —
beyond the characterised range and behind the IR-cut filter every phone carries. **A
phone senses one of the four wavelengths, in one channel.** Even a working
four-wavelength method could not transfer to the target hardware.

### 2026-09-11 — TASK 3 decided the phase: the best predictor of Hb is SEX
**Decision.** No PPG result may be reported without the demographic baseline beside it.
**Evidence.** Sex alone MAE **0.831** g/dL, R^2 0.415. Full demographics (age, sex,
height, weight) MAE **0.831** — age, height and weight add exactly nothing. Population
mean 1.175. Four-wavelength PPG 1.190. **PPG loses to the null model; sex beats PPG by
30%.** Adding PPG to demographics does not improve demographics (0.824 vs 0.831 — noise).
**Why this matters more than any PPG number.** A "PPG + demographics" model scores MAE
0.824, inside the pre-declared VIABLE band. Reported without the baseline it would look
like a working PPG haemoglobin estimator. **It is a sex classifier with a PPG-shaped
decoration attached.** Men carry higher haemoglobin — it is why the WHO thresholds
themselves differ by sex (13 vs 12 g/dL). Task 3 exists to catch exactly this, and did.
**Consequences.** This failure mode is a standing risk for every later claim in this
project and for the literature it was meant to improve on.

### 2026-09-11 — The dataset's published SNR could not be reproduced
**Decision.** Reported as a difference of definition, NOT tuned into agreement.
**Evidence.** The dataset reports 850 nm cleanest (19.04 dB) and 940 nm worst
(16.44 dB, 17.5% below 10 dB). Independent computation — cardiac-band power including
harmonics, against out-of-band power — gives **8.1-8.3 dB for all four channels**, no
meaningful ordering, 71-73% below 10 dB. The README does not define its SNR.
**An extraction bug WAS found and fixed along the way:** an earlier version counted PPG
harmonics as noise, giving ~4.5 dB. A real pulse has a sharp systolic upstroke and a
dicrotic notch, so 2f and 3f carry genuine signal. Fixing that moved SNR to 8.2 dB but
still did not reproduce the published ordering.
**Why no further tuning.** Matching a published number by adjusting an undocumented
definition is fitting to the answer. Extraction was validated instead against physiology
it can be checked on: heart rate median 82.5 bpm, IQR 75-90, 90.5% within 40-120 bpm,
and all four channels agreeing to **0.0 bpm SD** — the same heart, correctly found.

### 2026-09-11 — The Task 2 SQI does NOT repeat the Phase 2 defect, but cannot be validated here
**Evidence.** The Phase 2 image quality score had AUROC 0.816 yet rejected **0 of 17**
deliberately-bad frames — it ranked but never refused. This PPG SQI rejects **17.5%** at
its 0.3 operating threshold, and rejected subjects do show higher error (0.930 vs 0.810).
**But it cannot be meaningfully validated on this data.** r(SQI, |error|) = **-0.033**
and MAE by SQI quartile is flat (0.892, 0.796, 0.868, 0.769). More fundamentally, the
only model with any skill is the demographics model, which uses **no PPG at all** — so
"signal quality predicting its error" has no mechanism and the small difference is most
likely chance. A quality index cannot be validated against a model that ignores the
signal it measures.

## PHASE 4.5 DECISIONS (2026-09-11)

### 2026-09-11 — The deep-learning hole is CLOSED with evidence
**Decision.** Deep models over raw waveforms were tested and do not change the Phase 4
verdict. The PPG arm remains NOT VIABLE. No further representation will be tried.
**Evidence.** Three architectures (1D dilated CNN, bidirectional GRU, spectrogram CNN)
x two conditions (four-wavelength, 660 nm), subject-disjoint 10-fold CV, target
standardised per fold. Best: **speccnn on 660 nm, MAE 1.113-1.121 g/dL, R^2 +0.061**.
**None beats sex alone (0.831).** Three of six have negative R^2.
**Consequences.** A negative-results write-up can now answer "did you try deep
learning?" with evidence rather than omission.

### 2026-09-11 — CORRECTION: the raw waveform DOES contain a real signal
**Decision.** The claim "deep learning found nothing" is **wrong and must not be
written**. A more precise two-part finding replaces it.
**Evidence.** The best deep model was permutation-tested on its own terms (same
architecture, same folds, Hb shuffled across subjects, n=30): real MAE **1.1210**, null
**1.1969 +/- 0.0161**, **z = -4.72**, distinguishable from chance at p<0.05.
Meanwhile the hand-engineered feature model permutation-tested at **p = 0.978** — worse
than 97.8% of shuffled-label models.
**The two-part finding.**
1. The hand-engineered AC/DC features contain **no** signal (0 of 51 features above the
   null mutual information, 0 surviving FDR, permutation p=0.978).
2. The raw waveform contains a **real but useless** signal: significant at z=-4.72, yet
   MAE 1.12 g/dL against 0.83 for sex alone and 1.18 for a constant.
**Interpretation.** The AC/DC features were discarding something real. That is exactly
what this phase was run to find out, and it is a more defensible finding than a blanket
negative. It is still nowhere near clinical utility: MAE 1.12 g/dL separates no WHO
severity band.
**Caveat on attribution.** The permutation breaks subject-level association, so
significance means the waveform encodes something tracking Hb at the subject level —
Hb itself or a physiological correlate. The sex probe rules out sex specifically
(43.6-52.3% against a 57.0% base rate) but not every confound.

### 2026-09-11 — Memorisation was measured, not assumed
**Decision.** Subject-disjoint folds are asserted in code; train-test gaps are reported.
**Evidence.** Every fold raises if a subject id appears in both splits. Gaps: cnn1d
four-wavelength **+0.557** (train 0.623 / test 1.180), cnn1d 660 nm +0.421, gru
four-wavelength +0.308, speccnn 660 nm +0.096. The larger models fit training subjects
well and carry none of it across — the signature of memorising subject identity.
**The sex probe came back clean**, so unlike Phase 4's feature models these did not
secretly become sex classifiers.

### 2026-09-11 — A fair test required standardising the target
**Decision.** The regression target is standardised using TRAIN-fold statistics only.
**Rationale.** Without it the output head starts at 0 against a mean Hb of 13.9 g/dL and
spends the whole budget travelling to the intercept: the first run gave MAE 9.1, which
looks like catastrophic failure but is only an unfair initialisation. The phase was
trying to FIND signal, so the models got the best honest chance.
**Consequences.** Any future negative result from a regression head should be checked
for this before being believed.

## PHASE 5 DECISIONS (2026-09-11)

### 2026-09-11 — The positive claim SURVIVES hardening. Not retracted.
**Decision.** The claim that a spectrogram CNN on raw 660 nm PPG is distinguishable
from chance survives all four hardening tests and is retained — with its uselessness
attached as a mandatory clause.
**Evidence.**
- **Selection-aware permutation (the decisive test):** the full best-of-six selection
  re-run inside each permutation. **Extended to n = 240 on 2026-09-12**: real MAE
  **1.1124**, null **1.1959 +/- 0.0168**, null min 1.1279, **empirical p <= 0.0041**,
  z = -4.96, **zero of 240 permutations reached the real value**. (At n = 60 this read
  p = 0.0164; the figure is superseded, not withdrawn.)
- **Selected model alone, n=200:** empirical p = **0.00498**, z = -5.34, null
  1.2009 +/- 0.0166.
- **Seed stability, 10 seeds:** SD **0.0069**, range 1.1069-1.1279. The real-vs-null gap
  (0.0815) is **11.9x** the seed SD.
- **Subject robustness:** dropping the best-performing decile moves MAE 1.1124 ->
  **1.2258** — the model degrades rather than the effect vanishing, consistent with a
  weak signal spread across the cohort rather than a few lucky subjects.
**Why the selection-aware construction was chosen over a correction.** It reflects the
procedure that actually produced the claim and needs no assumption about how the six
configurations correlate. A Bonferroni-style correction would have required that
assumption and is strictly more conservative than warranted.
**The correction mattered and did not explain the effect.** Taking the best of six does
buy 0.0071 g/dL by chance (selection-aware null 1.1938 vs single-model null 1.2009) —
real, and an order of magnitude below the 0.0815 gap.
**Honest statement of the p-value.** p is **still a floor, now 1/(240+1) = 0.0041**,
not a measured value; the true p is bounded above by it. Extending the run from 60 to
240 permutations tightened the bound fourfold and did NOT turn it into a measurement,
because no null draw ever reached the real value. The parametric z is
reported beside it and assumes a normal null, which the 200-permutation distribution
supports but does not prove.
**Mandatory clause.** Any statement of this claim must carry: *the effect improves on
predicting a constant by ~0.05 g/dL, sex alone beats it by six times that margin, and
an estimator at MAE 1.12 g/dL separates no WHO severity band.*

### 2026-09-11 — Consolidation and reproducibility package complete
**Decision.** The project's results are consolidated into a publication-ready set. No
further modelling will be run.
**Artefacts.** `reports/final_results.md` (master table of all six representations,
nine mechanisms as measured quantities, limitations from every phase, and a **12-item
corrections table**); `reports/dataset_manifest.md` (generated from disk: 38.1 GB,
40,831 files, **8 of 10 licences UNVERIFIED**); `reports/literature_gap.md` (counts
only, with caveats enforced by a test); `scripts/reproduce_all.py` (33 stages, ~12 h
full / ~22 min `--fast`, per-stage runtimes, `--list` and `--from`).
**Reproducibility limits recorded rather than hidden.** Two stages are non-deterministic
from cuDNN autotune: segmentation training reproduces sclera IoU to ~0.005, and the deep
sweep reproduces MAE to ~0.01 — which is the measured seed SD and an order of magnitude
below every effect reported.
**Git hygiene enforced by test.** 0 data files, 0 figures, 0 binary artefacts tracked.
`tests/test_phase5.py::test_no_dataset_files_are_tracked_by_git` fails the suite if that
ever regresses.

### 2026-09-11 — The literature table is deliberately under-claimed
**Decision.** `reports/literature_gap.md` reports counts over 10 already-cited sources
and explicitly refuses to generalise.
**Rationale.** The sample is 10 sources chosen because this project used them, not
sampled from the field, and most attributes are UNKNOWN because the full papers were not
read. The report states that UNKNOWN is not evidence of absence, that the sample cannot
support claims of the form "most papers omit X", and that a systematic review would be
required for any general statement.
**The one attribute recorded as NO** is `duplicate_or_leakage_check`, and only where
this project **measured** duplicates a check would have caught: 52.7% and 50.8%
redundancy in the two Ghana sets, and 419 MD5 hashes shared between two datasets
distributed separately. That is a measurement of the data, not an inference about the
papers.
**A test enforces the caveats.** `test_literature_table_does_not_overclaim` fails if the
"too small to support" and "UNKNOWN is not evidence of absence" language is removed.

### 2026-09-12 — The selection-aware permutation null is being extended to n >= 240
**Decision.** The selection-aware test (Phase 5 Task 1, test B) is being re-run to at
least 240 permutations. **Until that run completes and is consolidated deliberately, the
reported figure remains p = 0.0164 at n = 60 and must not be altered anywhere.** The
runner reads the real MAE from `harden.json` and writes only its own files, so it cannot
move the number it is testing against; `test_extended_run_does_not_alter_the_reported_p`
enforces that.
**Rationale.** p = 0.0164 is the **floor** 1/(60+1), not a measurement: zero of the 60
draws reached the real MAE, so the test reported the smallest number its sample size
allowed. At n = 240 the floor is 0.0041. Either the real value still sits below every
draw — a bound four times tighter — or a draw finally lands at or below it and the p
becomes measured. Both are better statements than the one on record, and neither
requires a new modelling direction, so this does not reopen any closed arm.
**A first attempt was killed by an out-of-memory condition at n = 41 and could not be
resumed.** Its 41 draws are **discarded, not reused**, because its shuffles came from one
sequentially consumed generator: permutation *i* depended on every permutation before it,
so a partial run could not be continued or reproduced. The replacement draws permutation
*i*'s labels from `default_rng(PERM_SEED + i)` and from nothing else, which is what makes
the checkpoint sound rather than merely convenient.
**What was fixed before relaunching.**
- **Checkpointing.** Each completed permutation is appended to
  `data/interim/phase5/perm_selection_aware.jsonl` and fsynced immediately. A restart
  reads the file, skips the indices present and continues. A torn final line from a
  killed process is dropped, not fatal (`test_checkpoint_reader_survives_a_torn_final_line`).
- **Memory.** One permutation builds 6 architectures x 10 folds = 60 models and nothing
  was released between them. Each fold now drops its model, optimiser, schedule and
  resident tensors explicitly and returns the CUDA cache to the driver; evaluation is
  chunked rather than forwarding a whole fold at once, which is numerically exact here
  (no cross-sample operation, BatchNorm in eval mode) and removes the largest single
  allocation. **Measured before relaunching: 401 MB peak allocated, 824 MB reserved
  against the 8,585 MB ceiling, identical on consecutive permutations** — flat, not
  accumulating. Host RSS is recorded per permutation as well, because the cause of the
  kill was never confirmed to be GPU memory.
- **Detachment.** The run is launched by `scripts/launch_perm_extended.ps1` as an
  independent OS process, not a Claude Code background job, so it survives this session
  being compacted, cleared or closed. Verified: the launching shell exited while the run
  continued. It does not survive a reboot; re-running the launcher resumes from the
  checkpoint.
**OUTCOME (added 2026-09-12, on completion).** The run finished: **240/240 permutations
in 10.65 h, zero draws at or below the real MAE, empirical p = 0.004149 = 1/241.** Of the
two possible outcomes set out above, this is the first: the bound is four times tighter
and the p is **still a floor, not a measurement.** Consolidated into `harden.json` by
`scripts/phase5_consolidate_extended.py` as a separate deliberate step; the n=60 block is
retained with a `superseded_by` pointer. Peak GPU 401 MB of 8,585 throughout, flat.

**Consequences.** The shared CV driver was extracted to `src/hemosight/ppg/cv.py` so the
original hardening script and the extended runner cannot drift apart; the extraction
preserves seeding, folds and batch size exactly, so `phase5_harden.py` reproduces the
numbers already logged. Progress is readable at any time with
`scripts/phase5_perm_status.py`. **Nothing else about the claim changes**: whatever p the
extended run returns, the mandatory clause stands — the effect improves on predicting a
constant by ~0.05 g/dL, sex alone beats it by six times that margin, and an estimator at
MAE 1.12 g/dL separates no WHO severity band.

### 2026-09-12 - Phase 6 is an AUDIT HARNESS, not conformal prediction
**Decision.** Phase 6 was redirected on instruction to build the project's software
deliverable: **HemoSight Audit**, a tool that takes a claimed screening model's
predictions and runs the checks Phases 1-5 ran. The original Phase 6 (N4, conformal
prediction and abstention) is **retained verbatim and marked NOT APPLICABLE**, not
deleted.
**Rationale.** N4 wraps a haemoglobin estimator in calibrated intervals and a
three-state decision rule. There is no estimator to wrap. Building split-conformal
intervals around a model that loses to sex alone would produce a correctly calibrated
interval around a number nobody should use, which is a worse outcome than not building
it. The same reasoning applies downstream: **Phase 7 (fairness audit of an estimator),
Phase 8 (multimodal fusion into one physical estimate), Phase 9's inference API and
Phase 10's mobile capture flow all presuppose a working estimator** and are affected.
They are left as written and unticked; no claim is made here about what should replace
them.
**What was built instead, and why it is the honest product.** The project's own
literature survey found 0 of 5 applicable sources reporting a demographic baseline and
0 reporting a duplicate check. Its own duplicate check found 419 MD5 hashes shared
between two datasets distributed as independent sources and 52.7% / 50.8% internal
redundancy in two others; its own split construction found 1,708 nominal subject ids
collapsing to 1,067 leak-proof groups; its own demographic baseline found sex alone at
MAE 0.831 g/dL beating every model it built. Each of those is a check, each is already
implemented, and none of them is visible from a reported score.
**Wrapped, not rewritten.** `hemosight.io.hashing` and `hemosight.io.splits` are
imported unchanged; the baseline estimator is Phase 4 Gate B's exact construction; and
`benjamini_hochberg()` was re-homed into `hemosight.audit.stats` with
`scripts/phase4_5_ceiling.py` importing it from there - the same move as
`phase5_harden.py` importing its CV driver from `hemosight.ppg.cv`, for the same reason:
two copies of a statistical routine drift, and the drift is invisible. A test asserts
the script no longer defines its own.
**Consequences.** `scripts/reproduce_all.py` gains two Phase 6 stages (35 total). The
extended Phase 5 permutation run is deliberately NOT a stage: it is a ~10 h GPU job
whose figure has not been consolidated. Phase 6 is CPU and disk work throughout and did
not touch the GPU; **p = 0.0164 stands unaltered everywhere.**

### 2026-09-12 - Three checks were generalised deliberately, and the deviations are recorded
**Decision.** Three Phase 1-5 checks could not be lifted unchanged into a tool that
receives predictions rather than re-running training. Each deviation is logged here
rather than made quietly.
**1. Subgroup robustness now compares ADVANTAGE, not raw MAE.** Phase 5 reported MAE
1.1124 -> 1.2258 after dropping the best-performing decile. Read as a raw before/after
that comparison is uninterpretable: removing the subjects a model does best on also
removes the easiest subjects, so *any* model looks worse afterwards, a perfect one
included. The check recomputes the baseline on the same reduced set and reports the
retained advantage fraction. The Phase 5 result reproduces as a PASS under it, which it
should - Phase 5 read its own number that way in prose.
**2. The demographic proxy probe counts as evidence only on a SUPPLIED representation.**
Phase 4.5 ran its sex probe on each learned representation. Probing the prediction
vector instead is still reported but cannot be a finding on its own: a model
legitimately given sex as an input will of course encode sex in its output. Before this
distinction was drawn the check failed 2 of 5 clean replicates.
**3. The permutation test permutes labels against FIXED predictions.** Phases 4.5 and 5
refit the model inside every permutation; that is unavailable to a tool that receives
predictions. The nulls are genuinely different and the numbers differ - on the Phase 4
feature model the harness reports p = 0.271 where the refitting construction reported
0.978. The VERDICT is identical (not distinguishable from chance) and the check states
its scope in its own output, but **the 0.271 must never be presented as a reproduction
of the 0.978.**
**Consequences.** All three are stated in `reports/phase6_audit_harness.md` section 8.

### 2026-09-12 - The frontend-design skill could not be read; Task 3 item left unticked
**Decision.** The Phase 6 brief required reading
`/mnt/skills/public/frontend-design/SKILL.md` before writing any component. That path
does not exist on this machine. The checkbox is left **unticked** and the omission is
recorded rather than the task being reported as complete.
**What was done instead.** The design was driven by the brief's stated intent - an
instrument rather than a consumer app, data-forward, animation supporting comprehension
rather than decorating. Concretely: colour is used for nothing except verdicts; numbers
are set in a monospace so columns of them can be read against each other; result cards
keep their identity under Framer Motion layout animation while the reader re-sorts or
filters, so a card that moves can be tracked; detail panes animate their height so it is
visible what opened.
**Also not verified.** The front end type-checks and builds (`tsc -b && vite build`, 400
modules) and serves with the API proxy reachable, but no browser automation was
available on this machine, so **no screenshot-level check of the rendered pages was
made**. Recorded in the report's limitations rather than left for a reader to assume.

### 2026-09-12 - CORRECTION: the Phase 6 fault-injection seeds were not reproducible
**What was wrong.** `scripts/phase6_validate_harness.py` seeded each injected fault with
`abs(hash(kind)) % 2**31`. Python salts string hashing per process, so that seed changes
between runs: the injected faults were a different dataset every time the validation was
executed. The recorded sensitivity of 12/12 was therefore a measurement of one
unrepeatable draw, and the claim in `scripts/reproduce_all.py` that every stage is
deterministic given the frozen seed would have been false for that stage.
**How it surfaced.** Writing the validation inputs out as CSV files for the sample-data
directory. Two consecutive generations produced different files from the same code,
which is the symptom.
**Fix.** `case_seed(name) = (SEED + zlib.crc32(name)) % 2**31`, which is stable across
processes and versions. Verified by generating the sample CSVs twice and comparing
SHA-256 hashes: 9 of 9 identical.
**Effect on the recorded result: none.** Re-running the validation under the corrected
seeds returns the same figures - 15/15 known-truth verdicts reproduced, 12/12 faults
caught, 6 of 160 clean check-runs false-positive (3.75%), with the same per-check
breakdown. The RESULTS LOG entry dated 2026-09-12 stands unamended. The clean replicates
were never affected: they were already seeded `4000 + i`.
**Lesson, matching the one logged on 2026-09-11 about inferred causes.** A seed that is
not reproducible does not announce itself - every individual run looks fine. The only
thing that exposes it is running the same code twice and comparing the bytes.

### 2026-09-12 - Sample submissions are split by whether they contain real measurements
**Decision.** `app/backend/sample_data/` holds the nine SYNTHETIC submissions and is
tracked in git. The three submissions derived from real data are written to
`data/interim/phase6/known_truth/`, which is not tracked, and the sample images and
their zip to `data/interim/phase6/`.
**Rationale.** The known-truth inputs carry 41 PPG features and venous-blood haemoglobin
for 252 real subjects from `Hb_PPG_Dataset`, plus file paths into the Ghana pool.
Committing them would redistribute dataset-derived measurements from collections whose
terms are unverified - 8 of 10 ship no licence file - which is the exposure that got
`reports/figures/` untracked in Phase 1.5. The images are binary, and
`test_no_dataset_files_are_tracked_by_git` fails the suite if a `.png` is ever tracked.
**Consequences.** A fresh clone has the nine synthetic samples immediately and
regenerates the other three with `scripts/phase6_make_sample_data.py`, which is now a
stage in `reproduce_all.py` (36 stages). `app/backend/sample_data/README.md` records, per
file, which checks do not pass - measured by running the harness over each file, not
predicted.

### 2026-09-12 - CORRECTION: NumPy scalars reached a JSON column and 500ed the upload endpoint
**Symptom.** `POST /api/submissions` returned 500 for every submission with a `split`
column. The traceback ended in SQLAlchemy's `json_serializer`, with the final line
`TypeError: Object of type bool is not JSON serializable` - which reads as nonsense
until you notice the type is `numpy.bool_`, which prints as `bool` and is **not** a
subclass of it.
**Cause.** `AuditInput.has()` was written as
`col in self.df.columns and self.df[col].notna().any()`. `and` returns its second
operand, and `notna().any()` is a `numpy.bool_`. That value reached `summary()` as
`has_split` and `has_image_path`, and from there a JSON column.
**Fix, placed at the boundary rather than on the field.** Three layers, because a
per-field repair only relocates the defect to whichever field is added next:
1. `hemosight.audit.jsonsafe.to_jsonable()` - NumPy scalars to natives, `ndarray` to
   lists, NaN and +/-Inf to `null`, recursively.
2. `SafeJSON`, a SQLAlchemy `TypeDecorator` in `app/backend/db.py`, used by **every**
   JSON column in `models.py`. It is a column type, not a helper someone has to
   remember to call, so a column added later is covered without anyone thinking about
   it. A test fails the suite if a plain `JSON` column ever reappears.
3. `AuditReport.to_dict()` coerces at the point the report leaves the analysis, so the
   Markdown renderer, the report fingerprint and the database all see the same values
   and a fingerprint computed in memory matches one computed after a round trip.
`AuditInput.has()` now returns a real `bool` as well - correct regardless of storage.
**NaN and Infinity were the quieter half.** `json.dumps` emits them as the bare tokens
`NaN` and `Infinity` **without raising**; SQLite stores the text and Python reads it
back, so the defect stays invisible until a PostgreSQL `json` column or a non-Python
client rejects it. This service is declared PostgreSQL-ready, so they are coerced to
null now rather than after a migration.
**Second affected column, found by audit rather than by report.** `Run.report` takes the
same analysis output and would have failed the same way; it is covered by the same
column type, and an end-to-end run through the API now persists, re-reads and exports.
`Run.options`, `Run.checks` and `PreRegistrationRow.thresholds` arrive already decoded
from request JSON and were never at risk. `/api/submissions/{id}/preview` routes through
pandas' own JSON writer and `/api/case-study` reads files from disk; neither was
affected.
**Verified to bite.** The fix was reverted and the new tests re-run: 4 of the 6 fail
without it. The other two pass because `main.py` coerces on assignment as an independent
second layer - which is the point of having more than one.
**Effect on the recorded Phase 6 result: none.** The validation re-run returns 15/15
known-truth verdicts, 12/12 faults caught, 6 of 160 clean check-runs false-positive
(3.75%). The RESULTS LOG entry dated 2026-09-12 stands unamended. Tests: **129 passing**
(was 121).

### 2026-09-12 - OBSERVATION: the Overview page became unresponsive to browser automation
**Observation, recorded before any explanation.** Automated browser inspection of
`http://localhost:5173` loaded and rendered the Overview page, then became
unresponsive. Every subsequent script injection timed out with "the page is busy".
Screenshot, scroll and text extraction all failed, consistently, across waits of 5 and
10 seconds and repeated retries. A page-text extraction reported that the document never
reached `document_idle` after 45 seconds.
**What that establishes.** The page did not settle into an idle state as far as that
tooling could tell, and script execution was not scheduled.
**What it does not establish.** Anything about the cause. The observation was made
through a browser extension, which sits between the question and the answer; the
document state, the main thread and the extension's own injection mechanism are three
different things and this observation cannot separate them.
**Recorded separately from its explanation deliberately**, following the lesson logged on
2026-09-11 about the CPU-only PyTorch entry: an inferred cause must not be written down
as a finding. The investigation is the next entry.

### 2026-09-12 - INVESTIGATION: the Overview page is idle; two real polling defects were found elsewhere
**Method.** The question was asked directly through the DevTools protocol instead of
through the extension, driving a headless instance of the installed Chrome
(`app/frontend/tools/measure_idle.mjs`, `measure_polling.mjs`,
`measure_poll_failure.mjs`). Instrumentation is installed before any page script runs,
counting `requestAnimationFrame`, `setInterval`, `setTimeout` and WebSocket
constructions, alongside CDP performance counters and request logs.
**Result 1 - the Overview page is idle, in both builds.** Over a 10-second window after
load, identical in the Vite dev server and the production `vite preview` build: main
thread 0.0024 s (**0.02% of wall clock**), script time 0 s, layout count 0, style
recalc count 0, **0 network requests, 0 rAF callbacks, 0 timers**, `readyState`
"complete", network idle reached, and a trivial `evaluate()` returning in **1 ms (dev)
and 3 ms (prod)**. Whatever "the page is busy" described, it is not main-thread
occupancy, a render loop, a polling loop or an animation.
**Result 2 - the code agrees.** `Landing.tsx`, the Overview page, contains no
`useState`, no `useEffect` and no network call. It is static. A React render or polling
loop cannot live there.
**Result 3 - the only difference between dev and production is the HMR WebSocket**: 1
socket open in dev, 0 in production, with identical idle profiles otherwise.
**Conclusion, stated with its limits.** Every cause internal to the application is ruled
out by measurement. The remaining candidates - the dev server's persistent HMR socket
holding off whatever readiness signal the extension waits for, or the extension's
injection mechanism itself - **could not be distinguished from this side**, because the
browser extension is not connected to this environment and cannot be driven. **No cause
is recorded as established.** What is established is that the application is not
responsible, and that a production build behaves identically.
**Two real defects WERE found, in the pages that genuinely poll.** Neither can explain
the Overview observation - `Run.tsx` is not mounted at `/` - but both are the exact
failure class the investigation was asked to look for, and both were measured, not
inferred:
- **A poll loop with no terminating condition.** With the backend made to stop
  answering, `await api.run(id)` rejected inside a `setInterval` callback with nothing
  catching it. The interval kept firing every **706 ms indefinitely**, producing an
  uncaught `TypeError: Failed to fetch` per tick - **34 uncaught errors in 12 seconds** -
  while the interface went on animating a progress bar. Measured: **17 polls in 12 s,
  no end.**
- **Overlapping requests.** `setInterval` does not wait for the request it has already
  issued. Against a 3-second response, **5 concurrent polls** were in flight, growing
  with latency.
**Fix.** Polling moved out of the effect into `src/polling.ts`, a plain async function
that schedules the next request only after the previous one settles, backs off linearly
on failure, gives up after a bounded number of consecutive failures, and cancels
synchronously on unmount. **Measured after: 17 polls -> 5 then stop; 34 uncaught errors
-> 0 uncaught `TypeError`s; 5 concurrent requests -> 1.** The give-up is surfaced in the
interface, which also takes down the live progress view - and with it the app's only
`repeat: Infinity` animation - rather than leaving a spinner implying progress that has
stopped.
**Two further defects found while in there.** Navigating away from a running job and
back stranded the user: the component remounted with no run, never polled again, and
never moved on while the job completed on the server unnoticed. It now resumes from the
session. And `Upload.tsx` carried an `eslint-disable-line react-hooks/exhaustive-deps`
whose only purpose was a `!sub` guard that could never fire on mount; the guard was
removed and the suppression with it.
**Prevention.** ESLint is now configured with `react-hooks/exhaustive-deps` set to
**error** and `npm run lint` is clean with **zero suppressions anywhere in `src/`** - the
original defect had been sitting behind exactly such a comment, which costs nothing when
there is no lint run to suppress it from. `src/polling.ts` has 8 vitest cases covering
stop-on-done, stop-on-error, give-up, recovery from a transient failure, no overlapping
requests, cancel-during-flight and idempotent cancel. Four structural tests in
`tests/test_phase6.py` keep the shape of the fix from regressing without needing node.
**Honest note on the measurement tooling.** Two of the early readings were artefacts of
the probe, not of the application, and are recorded rather than quietly corrected: the
probe re-seeded `localStorage` on every navigation, destroying the `runId` the resume
path reads and making the app look as though it had failed to resume; and "never reached
the results page" was the two-worker job queue saturated by the investigation's own
400,000-permutation sabotage runs. Both were found by checking the probe before blaming
the code.

---


### 2026-09-12 — Phase plan restructured for readability after a completeness audit
**Decision.** Every unticked box in section 6 now carries an inline class — SUPERSEDED,
BLOCKED or OUTSTANDING — with the gate or blocker cited on the same line, and a
state-at-a-glance table heads the section. Eight boxes whose work was already on disk were
ticked with their evidence appended. Three ticked boxes with a reduced or missing artefact
were annotated ⚠️ and left ticked. **No text was deleted and no box was un-ticked.**
**Rationale.** 68 unticked boxes across eleven phases read as 68 pieces of outstanding
work. The audit (`reports/claude_md_audit.md`) found 57 superseded by a failed gate, 1
blocked, 8 already done, and **2 genuinely outstanding** — the deferred Phase 6 deep-model
validation (now unblocked: the permutation run finished and the GPU is free) and the
Phase 3 empirical-signal figure, whose computation is not on disk.
**Findings that are not plan items, recorded so they are not lost.** (1) Nothing from
Phase 4 onward is committed — 32 paths. (2) The 0.70 dE2000/g/dL empirical signal on 216
Eyes-Defy subjects is hard-coded in `scripts/phase3_report.py` with no producing script;
it is the numerator of the project's central noise/signal ratio. (3) Section 3's hard
constraint — a CNN baseline for every claim — is unmet for the imaging arm; no image CNN
was trained. (4) The last three RESULTS LOG entries sit after section 9, not in section 8.
(5) Network is now reachable (`pip download reportlab` succeeded), so the licence, constants
and reportlab items are closeable. (6) Three smoke-test pre-registration rows (`t`, `t`,
`e2e`) sit in the untracked development `audit.db`.
**Consequences.** The plan can be read at a glance. Nothing about any result, verdict or
claim changes. The two outstanding items and the hygiene list are prioritised in the
audit report's section 5; the answer to "what remains" is the write-up and those.
## PHASE 6.5 DECISIONS (2026-09-12)

### 2026-09-12 — CORRECTION: the empirical signal was a constant; it is withdrawn and replaced by a measurement
**What was wrong.** The Phase 3 report's "~0.70 dE2000 per g/dL, measured on 216 Eyes-Defy subjects, binned
by haemoglobin" was a string in `scripts/phase3_report.py` with no script and no output behind it (audit
2026-09-12). It was the numerator of the 5.6x noise/signal ratio that closed the imaging arm.
**What the measurement found.** The binned method returns **2.29** on the real labels and
**2.13 +/- 0.46 with haemoglobin shuffled** (p = 0.33):
it cannot resolve the signal, so the figure is **withdrawn as a measurement, not corrected**. A regression
estimator (Lab ~ Hb + site + sex + age, CIEDE2000 per +1 g/dL, bootstrap CI, permutation null) gives
**0.84 dE2000/g/dL (CI 0.57-1.17; null 0.13, p = 0.002)**. That it brackets 0.70 is coincidence.
**Downstream, recomputed rather than adjusted.** noise/signal **4.7x** (was 5.6x); equivalent error at the
measured residual **4.7 g/dL** (CI 3.4-6.9; 2.9 with the unadjusted signal);
sim-to-real gap 1.9x (was "within 1.5x"). **No verdict changes**: the gate figure (3.893) was computed on the
simulated inversion, and the empirical cross-check remains above 2.0 g/dL at every bound. Phases 2, 2.5 and 3.5
never used the constant. The margin is smaller than was written and is now stated correctly everywhere.
**Two findings the constant hid.** Sex confounds colour-vs-Hb in Eyes-Defy (r = 0.55; site-only slope
1.37 -> adjusted 0.84), the same confound Phase 4 found in PPG. And between-subject colour at fixed
Hb, sex, age and site is 4.55 dE2000 (5.4 g/dL equivalent) under a fixed white LED with ambient
light excluded - a noise floor intrinsic to tissue and capture, several times the signal, before calibration.
**Prevention.** Stage in `reproduce_all.py`; the three reports read the JSON and refuse to run without it;
`tests/test_phase3.py` fails if a copy reappears, if the binned method is presented as a measurement, or if
the equivalent error falls below 2.0 (a verdict change, to be reported not absorbed).
**Lesson.** A number typed into a report generator is indistinguishable from a measured one until someone
tries to regenerate it. The project's own audit harness exists to catch this class of defect in other
work; it was caught here by the same discipline applied to itself.

### 2026-09-12 — The image CNN baseline is built; the §3 constraint is met for the imaging arm
**Decision.** `src/hemosight/baseline/image_cnn.py` and `scripts/phase6_5_image_cnn.py` provide the
conventional comparison arm on Eyes-Defy: ResNet-18, subject-disjoint folds, target standardised, the Phase 4
baselines and bands, three seeds, train-test gap, sex probe, permutation, cross-site both ways.
**Result.** MAE **1.301** (MARGINAL) against sex alone 1.631, demographics without site
1.607, **site + sex + age 1.273**, population mean 2.003; cross-site
italy_to_india 1.958 (MARGINAL, bias +1.59), india_to_italy 1.995 (MARGINAL, bias -1.52).
Beats the site-inclusive demographic baseline: **False**. Image increment over it: +0.078 g/dL.
**Consequences.** The imaging verdict stands. The comparison arm agrees with the ambient-light refutation and adds a caveat the write-up must carry: under a controlled illuminant conjunctival colour carries real haemoglobin information (within-site r 0.5-0.65; three Lab numbers nearly match the CNN) worth ~0.1 g/dL over demographics - real and clinically useless.
The Phase 5 (original) CNN items are ticked with this evidence. Limitation carried verbatim: 217 subjects, one
Galaxy S6 in two variants, two sites, no severe cases - a pilot arm, not a validation.

### 2026-09-12 — CORRECTION: the CNN baseline script omitted SITE from the demographic baseline
**What was wrong.** The first run of `phase6_5_image_cnn.py` (19:28) used age and sex as "demographics",
as Phase 4 had (the PPG data has one site). Eyes-Defy has two sites that are also two device variants, with a
2.4 g/dL gap in mean Hb (Italy 13.83, India 11.47). The CNN (1.309) appeared to beat demographics
(1.607) and sex alone (1.631); with site in the baseline, demographics alone reach 1.273 and the CNN
does not beat them. It had learned the site. The ±1.5 g/dL cross-site bias is the same fact seen from the other
direction: without the site label the model transfers the wrong intercept.
**Fix.** Site added wherever demographics are a baseline (site alone; site + sex + age; colour + site + sex + age;
CNN + site + sex + age); `beats_demographics` now means the site-inclusive baseline; the whole analysis was
re-run end to end, not patched. The first run's JSON was overwritten by the re-run.
**Checked elsewhere.** The PPG dataset has no site, cohort or session column. Its unused covariates were tested on
the Phase 4 folds: r(Hb, signal length) = -0.01, SBP +0.18, DBP +0.21, glucose +0.04; demographics 0.831 ->
0.825 with BP -> 0.822 with BP + signal length + glucose; signal length alone 1.180 (= population mean). Nothing
to recompute. The Phase 6 audit harness's demographic-baseline check takes `site` as an optional column and
uses it when present; the Eyes-Defy submission in the case study must supply it.
**Lesson.** "Demographics" means every non-signal variable the data carries that the model could learn. Site
is one whenever sites differ in the outcome, and the sites here differ by more than sex does.

### 2026-09-12 — The deferred deep-model validation is closed
**Decision.** Per-subject predictions for the Phase 4.5/5 deep model (10 seeds + 6 candidates) are regenerated
by `scripts/phase6_5_deep_predictions.py` with the Phase 5 driver and driven through the harness
(`phase6_validate_harness.py` A8). All four verdicts match the record (19/19 known-truth cases).
**Caveat retained.** The harness's permutation null (labels against fixed predictions) is not Phase 5's
refitting null; its p is not a reproduction of 0.0041 and is never presented as one.

### 2026-09-12 — Two over-claiming ticks resolved by producing the artefact
**Phase 2 Task 4.** The illuminant estimator is now applied to every Eyes-Defy image and the estimates
stored (`scripts/phase6_5_eyes_defy_illuminant.py`). Within-subject stability is recorded as not measurable
(one image per subject) rather than approximated.
**Phase 6 Task 2.** `reportlab` installed (network available) and declared in `pyproject.toml`; PDF export
verified through the API. The "no network" comment in `main.py` is corrected.

### 2026-09-12 — Licences verified, constants banner narrowed, database cleaned
**Licences.** All 8 previously UNVERIFIED sources checked from their landing pages or access forms: 4 are
CC BY 4.0 (Ghana conjunctiva, Ghana fingernails, CP-AnemiC with the authors' "academic purpose only"
statement, Hb-PPG via the figshare API); SBVPI and MOBIUS are custom non-commercial research agreements
forbidding redistribution (MOBIUS alone permits scaled-down or watermarked figures); NUS-8 and Eyes-Defy
state no licence at all. `test_dataset_manifest_states_every_licence` now asserts each state is written.
Nothing permits committing images or derived measurements; the rule stands.
**Constants.** Efron 2009 and Zhivov 2006 fetched: neither abstract carries a thickness and both full texts
are paywalled, so stromal and tarsal thicknesses and all BVFs stay flagged. The 32 um epithelium is
corroborated independently (Li et al. 2015 OCT, 34.0 +/- 5.8 um, n=62) and its flag is lifted. Zhivov 2006
is in *The Ocular Surface*, not *Cornea*; corrected. Phase 3 Task 4's tolerances mean no correction moves a verdict.
**Database.** Three smoke-test pre-registrations (`t`, `t`, `e2e`) and two near-duplicate real ones deleted;
the two smoke-test runs that cited deleted rows carry `prereg_id = NULL`, not a substituted record.
`PreRegIn.title` requires >= 8 characters after stripping; test added.
**Logs.** The three RESULTS LOG entries stranded after section 9 moved into section 8.

## PHASE 7 DECISIONS (2026-09-12)

### 2026-09-12 — The controlled-capture hypothesis was tested; outcome B
**Decision.** Thresholds and three outcomes were declared in the Phase 7 plan before running.
The Phase 3 gate was re-run at MEASURED residuals - the within-subject sclera colour spread
under each capture condition, best of {none, grey-world full, grey-world 25% crop} - not at
an assumed one. At the studio residual the gate returns 1.04 g/dL - +0.04 from the VIABLE line: studio-grade control brings the CALIBRATION term to the edge of viable, and what keeps the empirical Eyes-Defy result in MARGINAL is the between-subject tissue term the gate never modelled. In the controlled regime the limiting factor shifts from calibration to tissue. The refutation is restated in TWO PARTS: (1) from uncontrolled photographs the colour-to-Hb inversion is NOT RECOVERABLE (unchanged); (2) from controlled capture it reaches the MARGINAL band only - screening bands at best - does not beat site + sex + age, and moves no clinical threshold. The distinction a reviewer would raise is real, is now measured, and does not rescue the claim.
**Evidence.** Residuals (dE2000): MOBIUS across phones x lighting 3.456 (grey_world_full); MOBIUS same phone + lighting 1.981 (grey_world_full); SBVPI studio 1.062 (grey_world_full).
Gate: MOBIUS across phones x lighting -> 3.47 g/dL NOT RECOVERABLE; MOBIUS same phone + lighting -> 2.03 g/dL NOT RECOVERABLE; SBVPI studio -> 1.04 g/dL MARGINAL;
reference 3.935 -> 3.98. VIABLE needs a residual < 0.99 dE2000 on this model;
the studio residual is 1.1x that. Eyes-Defy (fixed LED, one image per subject, so no
within-subject residual is measurable): mean-Lab colour model 1.343 g/dL, CNN 1.301,
cross-site italy_to_india 1.96, india_to_italy 1.99, site + sex + age alone 1.273 -
MARGINAL; between-subject colour at fixed Hb/sex/age/site 4.55 dE2000, a second
noise term the gate never modelled.
**Consequences.** Section 2's imaging verdict is not reversed; its scope is now stated precisely.
"Nothing further should be built" stands: the controlled-capture regime is the one Eyes-Defy
already occupies, and it was measured in Phase 6.5 at MARGINAL.

### 2026-09-12 — The statistically-real / clinically-useless pattern is formalised
**Decision.** `reports/statistical_vs_clinical.md` states the pattern and quantifies both instances on
the same axes: detectability (z, empirical p and its floor) and utility (gain over a constant; gain
over the cheapest baseline on identical folds; increment when added to it; fraction of the baseline's
advantage; WHO-band AUROC and sensitivity/specificity vs the baseline). PPG: +0.066 over a constant,
-0.009 added to sex, 0.00 sensitivity at the WHO threshold (no anaemic subject flagged).
Conjunctiva: +0.702 over a constant, +0.078 added to site + sex + age, AUROC
0.875 vs 0.816.
**Reporting standard proposed** (four items): cheap-baseline comparison on identical folds with every
non-signal variable the model could learn; permutation p beside z with the floor stated and the
selection re-run inside; an explicit decision-threshold statement (sens/spec of model AND baseline);
cross-site numbers with bias. **Retrospective:** nine project results placed in the 2x2; the headline
cell has exactly two members; detectability and utility separated in seven of nine. Recorded rather
than overclaimed.

### 2026-09-12 — External audit path built; NOT run
**Decision.** `hemosight.audit.ingest` converts released tables (per-image rows with present,
derivable or absent subject ids; missing splits; missing demographics; g/L; word-coded sex) into the
contract and records every assumption; `run_audit(unsupported=...)` forces checks that rest on an
ASSUMED column to INSUFFICIENT DATA - a test shows that a table with one "subject" per image would
otherwise PASS split integrity; `to_external_markdown` gives "could not be checked" equal prominence;
`scripts/external_audit.py` and an empty register complete the path. No external work has been
audited and no outcome is simulated. Candidates arrive separately; `auditable: none` will be recorded
with the same weight as an audit that ran.

### 2026-09-13 — External audit run: the availability finding is the result; the harness returned no verdict
**Decision.** Three external candidates were examined and entered in the register with their availability
statements verbatim; **0 of 3 released artefacts sufficient for an independent audit**, so the harness ran on
none. "Available upon request" is recorded as its own category - neither released nor unavailable - and was
not tested: nothing is claimed about the specific authors.
**The one released codebase** (mbedmutha/anemia-detection: a three-person student repository, 18 commits, zero
stars, "initial experiments" - NOT a paper, NOT evidence about the literature, used only to exercise the
harness's external path) was executed in an isolated environment with data paths repointed and Colab mount
cells skipped as the only allowances: **0 of 7 notebooks ran.** Five stopped at their first
unreleased intermediate (`y_forniceal_*.npy`, `y_base_italy.npy`, an augmented-image folder), one at parsing
the dataset's own `Italy.xlsx` (the authors used an unreleased cleaned copy), two at Keras-2 imports under
unpinned dependencies. `requirements.txt` does not install as written (`glob`, `pathlib`). No weights, no
saved outputs, no predictions. Code-text observations (splits without a seed; a loader that ignores its own
split slice; an XGBoost cell evaluated on training rows) are recorded as observations, **not** harness verdicts.
**BPANet** (Lin et al. 2025): data "available from the corresponding authors upon reasonable request"; no code
statement. From the full text: 5-fold CV on Eyes-Defy with the fold unit not stated; an ablation removing
age/gender (1.460 vs 1.212) but no demographics-only baseline; India+Italy pooled; NTUH evaluated separately
after retraining; no duplicate check mentioned. Entered in `literature_gap.md` as **NOT REPORTED** - a value
added for full-text-read papers, distinct from UNKNOWN (not read) and NO (measured by this project).
**"Hemo-ConViT"**: no primary source found (Europe PMC, Crossref, arXiv: 0 hits); not cited, not audited.
**Standing rule.** "Not auditable" and "audited and failed" are different findings. No external model is
recorded as failing any check, because no check ran. Three candidates support no statement about the
field; the register is how one would be earned.

## PHASE 8A DECISIONS (2026-09-13)

### 2026-09-13 — Plain language is the default view; the claim is never simplified with the sentence
**Decision.** Every check's user-facing wording lives in `hemosight.audit.content` and nowhere
else: the plain headline is a template over the check's measured values, so the same numbers
that produce the technical statement produce the plain one, and the two cannot drift. The
plain layer is attached server-side to every result (`plain` on each CheckResult dict) and is
read by the results page, the Markdown export, the PDF and the case study. The technical
statement is preserved verbatim beneath it, one click away, never removed.
**What survived the rewrite, by construction and by test.** INSUFFICIENT DATA reads "We could
not check this - your file did not include X" and its what-to-do says it must not be read as a
pass; no pass-like word appears in any insufficient wording and the one place verdict colour
is assigned maps it to its own class. A p at the permutation floor reads "N is the smallest
p-value n permutations can produce; the true value may be smaller. It is a bound, not a
measurement", and whether the null re-ran the model selection is stated either way. A narrow
demographic margin and a near-threshold retained fraction are carried into the plain sentence.
Precision is a claim too: a first draft printed a +0.0047 margin as "+0.00" and a seed SD of
0.00049 as "0.000"; both templates now keep significant figures.
**What to do, with the framing that keeps it honest.** Each check's remedy is one of FIXABLE,
REPORT IT or STOP, and the category is shown beside the text. FAIL is FIXABLE only for the two
split-construction checks (duplicates across the split, subjects across the split), because a
correction to how the evidence is produced exists there. Losing to a demographic baseline, or
being a demographic in disguise, is REPORT IT. Indistinguishable from shuffled labels, an
effect no bigger than seed noise, or an empty input, is STOP. No text is phrased as a way to
make a failing check pass; a test forbids the phrasing. The project's own history is the
worked example throughout: six representations refuted, and the correct action each time was
to report the negative result rather than search for a seventh.
**Glossary.** Twenty-four terms, served from the same module, linked from the results page
and the landing page. Plain text avoids them where a plain substitute exists.
**Not changed.** Visual design, layout, colours and typography (Phase 8B). The checks' own
technical headlines and explanations are untouched.
**Known limit.** Plain headlines are templates; a check that gains a new measured key or caveat
must extend its template and the test table together, or the plain layer will silently omit it.

## PHASE 8B DECISIONS (2026-09-13)

### 2026-09-13 — The visual system: dark instrument, generated imagery, motion behind one switch
**Colour.** Sixteen tokens in `app/frontend/src/tokens.css`, written by `scripts/phase8b_contrast.py`,
which also measures every text/ground pair the interface uses: all required pairs meet WCAG AA
(all_aa = True), most AAA; the one recorded sub-3:1 pair is a decorative hairline with no
requirement, and interactive borders got their own token at 3.7:1. The baseline cream palette had
lost accessibility points to 18 colour-contrast failures. Verdicts never rely on colour alone: FAIL
is a cross in a square, PASS a tick in a circle, INSUFFICIENT DATA a dashed diamond with a dash,
each with its label, and INSUFFICIENT is never rendered at reduced opacity.
**Imagery.** The hard constraint - no stock photography, nothing derived from a dataset image, for
the same licence exposure that untracked `reports/figures/` in Phase 1.5 - is met by generating
everything: the OMLC haemoglobin extinction curves are the hero (the physical quantity the project
is about), a CIE-derived spectral band divides sections, and three result figures are drawn from
the project's own aggregates (240 permutation minima vs the real MAE; residual per capture
condition vs the measured signal; the gate's breakeven curve). A test forbids raster images and
external fetches in the front end.
**Motion.** GSAP + ScrollTrigger loaded lazily and only when motion is on; Framer Motion keeps
component transitions. `enabled = !prefers-reduced-motion && userToggle` governs every decorative
effect through `html[data-motion]`; off, the particle field and cursor do not render, GSAP is never
downloaded, `.reveal` hides nothing, and layouts are static with the same content. The custom cursor
runs only for fine pointers, hides on any keydown so it cannot cover a focus ring, and the native
cursor is hidden only while the reticle is live.
**Measured, not asserted.** Lighthouse 13.4 on the preview build with the backend running: landing
97 / 100 / 100 (mobile) and 100 / 100 / 100 (desktop); upload and results 99-100 / 100 / 100; the
bar was 90 / 97. `tools/verify_8b.mjs` drove every page x 3 widths x 2 motion modes = 48 states:
48 clean. Bundle: main 118.4 kB gzipped (was 107.5) plus 46 kB of GSAP fetched only with
motion on.
**Corrected during verification, recorded rather than hidden.** Lazy-loading the landing page cost
CLS 0.12 (reverted; only GSAP is split). Story steps dimmed to 35% failed AA (now >= 75%, body only).
The results page's empty-state-then-cards swap cost CLS 0.73 on desktop (loading state + viewport-tall
column; now 0). Two `bg-white` fragments survived the palette change (found by Lighthouse; a test now
forbids hex colours outside tokens.css). The hero spectra overlapped the heading on phones (moved).
The first verification probe scrolled too abruptly for ScrollTrigger and reported reveals as hidden -
a probe artefact, confirmed by a direct check, and fixed in the probe.
**Nothing was cut for performance:** every planned effect ships because the scores held above the bar.

## 8. RESULTS LOG

Dated entries recording **every** metric produced, including failures and negative
results. A run that produced a bad number is a result. A run that crashed after
consuming a day is a result. Append only; never delete an entry.

Format: `### YYYY-MM-DD — Experiment name`, then **Config** (script, config file,
commit), **Data** (split, sites, n), **Metric(s)**, **Interpretation**, **Status**
(provisional / confirmed / superseded).

### 2026-09-11 — Phase 1 dataset inventory
**Config.** `scripts/phase1_manifests.py`, `scripts/phase1_audit.py`.
**Data.** All of `data/raw/`, read-only. **Metrics.** 28,275 manifest rows over 2,333
subjects; integrity check PASS (no duplicate `image_id` or `file_path`, all Hb inside
1–25 g/dL, 0 unparsed filenames of 8,522 Ghana files).

| dataset | images | subjects | imgs/subj | with Hb | Hb range | severe <7 | devices |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cp_anemic | 710 | 710* | 1.0 | 710 | 3.1–15.0 | 48 | 0 (EXIF stripped) |
| ghana_conj | 4,262 | 523 | 8.1 | 0 | — | — | 0 (EXIF stripped) |
| ghana_nail | 4,260 | 475 | 9.0 | 0 | — | — | 0 (EXIF stripped) |
| eyes_defy | 218 | 218 | 1.0 | 217 | 7.0–17.4 | 0 | 2 |
| hb_ppg | 252 | 252 | 1.0 | 252 | 8.5–17.3 | 0 | 1 |
| sbvpi | 1,856 | 55 | 33.8 | 0 | — | — | 1 |
| mobius | 16,717 | 100 | 167.2 | 0 | — | — | 3 |

\* CP-AnemiC subject ids are a **fallback** (= image id); its sheet has no participant
column. Every other dataset has a true subject id — 27,565 of 28,275 rows (97.5%).
**Interpretation.** Only 3 of 7 datasets carry Hb, totalling 1,179 labelled
measurements — of which 710 are the unreliable CP-AnemiC set. **Status: confirmed.**

### 2026-09-11 — Phase 1 overlap check (N/A — this is a data result, not a model metric)
**Config.** `scripts/phase1_overlap.py`; pHash/dHash threshold 10, embedding cosine
0.92, ResNet18 ImageNet features on GPU.
**Data.** cp_anemic (710), ghana_conj (4,262), ghana_nail (4,260).
**Metrics.**
- cp_anemic vs ghana_conj: 419 shared MD5; pHash ≤10 **697/710 (98.17%)**, 646 at
  distance 0; dHash ≤10 708/710; embedding ≥0.92 **701/710**; max cosine 1.0000.
- cp_anemic vs ghana_nail: 0 shared MD5; pHash min 10; embedding max 0.9344.
- ghana_conj vs ghana_nail: 0 shared MD5; pHash min 10; embedding max 0.9394.
- Cross-body-site subject numbering: non-anemic **Jaccard 1.000 (204/204)**, anemic
  0.919 (250 shared of 271).
- Intra-dataset duplication: cp_anemic 498 unique of 710 (29.9% redundant), ghana_conj
  2,015 of 4,262 (52.7%), ghana_nail 2,097 of 4,260 (50.8%).
- CP-AnemiC label conflicts: 90 of 91 exact-duplicate groups carry >1 distinct Hb.
**Interpretation.** CP-AnemiC is contained inside ghana_conj → one site. Conjunctiva and
nail share a participant roster → N6 opportunity. Headline file counts overstate the
Ghana data by ~2x. **Status: confirmed.** Metadata-correspondence signal **not
computable** (Ghana sets ship no Hb/age/sex) — recorded as unavailable, not negative.

### 2026-09-11 — Phase 1 image-content check (NEGATIVE RESULT for N1)
**Config.** `scripts/phase1_audit.py`, 60 images/dataset, seed 0, near-black =
max channel < 12.
**Metrics.** Mean near-black fraction: cp_anemic **0.705**, ghana_conj **0.723**,
ghana_nail 0.205, eyes_defy **0.000**, sbvpi 0.000, mobius 0.019. Images over 30% black:
cp_anemic **100%**, ghana_conj **100%**.
**Interpretation.** **Negative result, recorded prominently.** The two largest
conjunctiva datasets are pre-segmented cutouts with the sclera removed, so N1's white
reference does not exist in them. N1's end-to-end validation set is Eyes-Defy alone:
**218 subjects, 2 sites, 2 variants of one phone, no severe cases.** **Status:
confirmed.**

### 2026-09-11 — Phase 1 splits
**Config.** `scripts/phase1_splits.py`, `configs/phase1_splits.yaml`, seed `20260911`.
**Metrics.** Ghana pool 9,232 images; **1,708 nominal subject ids → 1,067 leak-proof
groups**; train 5,508 img/640 grp, calibration 1,950/213, test 1,774/214. Eyes-Defy
cross-site: italy_to_india 123 train / 95 test, reverse 95/123. Hb_PPG 151/51/50
subjects. nus8 1,265 images, 6 cameras, per-camera 3-fold plus leave-one-camera-out.
**Leak check: PASS** — no subject and no byte-identical image spans a boundary.
**Interpretation.** The 1,708→1,067 collapse is the leakage a plain subject-level split
would have permitted; it is the single most important guard in Phase 1.
**Status: confirmed.**

### 2026-09-11 — Phase 1 nus8 parse
**Config.** `src/hemosight/io/nus8.py`.
**Metrics.** 6 cameras, 1,265 images, **0 missing PNGs, 0 missing colorchecker masks**,
all ground-truth illuminants unit-normalised (‖v‖ = 1.000). Black/saturation levels
differ per camera (0–2048 / 4,043–15,892), confirming both 12-bit and 14-bit sensors.
**Interpretation.** N1's illuminant-accuracy arm is fully supported over six sensors.
Two of the benchmark's eight cameras are not extracted — report six.
**Status: confirmed.**

### 2026-09-11 — Phase 1.5 uncropped-original search (NEGATIVE RESULT, conclusive)
**Config.** `scripts/phase1_5_search_originals.py`. Full scan, not sampled.
**Data.** All 710 CP-AnemiC, 4,262 Ghana conjunctiva, 4,260 Ghana nail, 218 Eyes-Defy
images; all 13 archives under `data/raw/`.
**Metrics.**

| dataset | n | black mean | **black MIN** | n < 5% black | max MP | n > 1 MP |
| --- | --- | --- | --- | --- | --- | --- |
| cp_anemic | 710 | 0.713 | **0.497** | 0 | 0.14 | 0 |
| ghana_conj | 4,262 | 0.713 | **0.496** | 0 | 0.14 | 0 |
| ghana_nail | 4,260 | 0.238 | 0.043 | 6 | 0.05 | 0 |
| eyes_defy | 218 | 0.000 | 0.000 | 218 | 11.90 | 218 |

`Fingernails.rar`: 4,261 entries, 4,260 `.png`, names identical to the extracted folder.
**Interpretation.** **Negative result, conclusive.** Not one uncropped image exists in
either conjunctiva dataset — the least-cropped is still 49.7% black and the largest is
0.14 MP against Eyes-Defy's 11.9 MP. N1c's data base cannot be widened. Question closed.
**Status: confirmed.**

### 2026-09-11 — Phase 1.5 haemoglobin label arbitration
**Config.** `scripts/phase1_5_label_arbitration.py`.
**Data.** cp_anemic (710), ghana_conj (4,262), 419 shared unique images.
**Metrics.**
- Q1 CP-AnemiC Hb self-consistent: **False** — 90/91 duplicate groups conflict; worst
  spread **7.10 g/dL** within one byte-identical image.
- Q2 Ghana binary self-consistent: **True** — 0/1,397 duplicate groups conflict.
  Ghana Hb values present: **0**.
- Q3 cross-collection binary agreement: **412/419 (98.33%)**, 7 disagreements.
- Q4 CP-AnemiC Hb vs its own binary label at WHO 11.0 g/dL: **0/710 mismatches** — the
  label is exactly `hb < 11.0`, and severity bins are the exact WHO bands.
- Resulting flags: trusted Hb rows **469 of 28,275** (eyes_defy 217, hb_ppg 252);
  untrusted 27,806.
**Interpretation.** Verdict **BINARY_LABEL_ONLY**. The Ghana pool leaves Hb regression
entirely. Two numbers to carry forward: the project's trustworthy Hb base is **469 rows
with zero severe cases**, and the retained binary label carries a **1.67% noise floor**
measured where checkable — an accuracy ceiling of ~98.3% on that pool.
**Status: confirmed.**

### 2026-09-11 — Phase 1.5 repository hygiene
**Config.** `git rm -r --cached reports/figures`, `.gitignore` updated.
**Metrics.** `git ls-files reports/figures/` → 0 entries. `git check-ignore` matches at
`.gitignore:26`. Tracked files: 22, of which 1 under `reports/`. 5 figures remain on
disk and regenerate from `data/raw/` via 3 documented commands.
`data/raw/scin-main/` deleted: 5 files, 212 KB, 0 data files.
**Interpretation.** No dataset pixels can now enter version control.
**Status: confirmed.**

### 2026-09-11 — N1a: illuminant estimation on nus8 (SUPPORTED)
**Config.** `scripts/phase2_nus8_n1a.py`, `src/hemosight/calibration/`. Per-camera
3-fold CV and leave-one-camera-out from `configs/phase1_splits.yaml` (seed 20260911).
**Data.** 1,265 images, 6 cameras, ground-truth illuminants. ColorChecker masked out of
every classical baseline's input.
**Metrics** (angular error in degrees, pooled over cameras):

| method | mean | median | trimean | best25 | worst25 |
| --- | --- | --- | --- | --- | --- |
| reference-patch, fixed population prior | **0.666** | 0.376 | 0.414 | 0.131 | 1.734 |
| reference-patch, assumed neutral | 1.266 | 1.125 | 1.134 | 0.610 | 2.192 |
| max-RGB p99 | 3.076 | 2.276 | 2.500 | 0.694 | 6.762 |
| shades-of-grey p6 | 3.401 | 2.548 | 2.699 | 0.861 | 7.425 |
| grey-world | 4.020 | 3.100 | 3.279 | 0.878 | 8.749 |
| grey-edge 2 / 1 | 6.325 / 6.486 | | | | |
| max-RGB | 11.140 | 11.917 | | | |

Leave-one-camera-out pooled: 0.735 deg (vs 0.666 in-camera), so the prior transfers
across sensors. Classical baselines land in the published NUS range, an independent
check that the harness is not flattering itself.
**Prior ablation.** neutral 1.266 -> fixed 0.666 deg: **knowing the reference
reflectance halves the error (47%)**. The oracle reaches exactly 0.000 by construction
and is reported only to show the measurement model inverts exactly, i.e. all residual
error is prior error, not model error.
**Interpretation.** SUPPORTED against a criterion declared before the run. **Status:
confirmed.**

### 2026-09-11 — Sclera segmentation (SBVPI + MOBIUS)
**Config.** `scripts/phase2_train_segmentation.py`, U-Net + ImageNet ResNet-18, 384px,
batch 12, AMP, 8 epochs. Subject-level split: train 4,294 / val 1,088.
**Metrics.** Held-out IoU: sclera **0.8749** (Dice 0.9333), iris 0.7949, pupil 0.6865,
periocular 0.9750, background 0.9640. Peak GPU **1.5 GB** of 8 GB.
Per dataset: MOBIUS sclera 0.8541, SBVPI sclera 0.9045.
**By device:** iPhone 6s 0.8475, Sony Xperia Z5 0.8431, Xiaomi Pocophone F1 0.8784 —
spread **0.0352**.
**By lighting:** indoor 0.8944, natural 0.8702, **poor 0.7971** — spread **0.0973**.
**Interpretation.** Device does NOT meaningfully confound segmentation; **lighting
does**. The pipeline degrades ~10 IoU points exactly in the poor-light condition that
field deployment would face. Any later result stratified by lighting inherits this.
SBVPI iris/pupil IoU is 0.000 — those classes are annotated on only ~128 of 1,840 SBVPI
images, so iris segmentation does not transfer to that domain. N1b is unaffected (it
runs on MOBIUS, iris IoU 0.8148). **Status: confirmed.**

### 2026-09-11 — N1b: sclera self-consistency (PARTIALLY SUPPORTED — negative on the headline)
**Config.** `scripts/phase2_n1b_selfconsistency.py`. MOBIUS, 3 phones x 3 lighting,
1,796 frames, 100 subjects; prior fitted on 60 subjects, evaluated on 40 held out.
Primary region **iris** (non-circular); secondary sclera spatial holdout.
**Metrics — within-subject dE2000 spread on the iris (lower is better):**

| method | mean | median |
| --- | --- | --- |
| **grey-world** | **6.08** | 5.57 |
| sclera, neutral prior | 7.31 | 6.82 |
| sclera, fixed population prior | 7.43 | 7.16 |
| sclera, per-subject prior | 7.43 | 7.16 |
| shades-of-grey p6 | 7.55 | 6.99 |
| max-RGB p99 | 8.26 | 7.14 |
| no correction | 9.53 | 10.12 |

**Paired Wilcoxon over the same 40 subjects** (sclera fixed prior vs):
no correction -2.104, p=2.4e-08, better in 35/40; **grey-world +1.351, p=3.1e-08,
better in only 6/40**; shades-of-grey -0.123, p=0.44 (tie); max-RGB -0.830, p=5.4e-06;
neutral prior +0.115, p=0.25 (no significant difference).
**Variance decomposition (iris, fraction of total):** phone 0.203 / lighting 0.246 for
the sclera method, versus 0.220 / 0.262 uncorrected and 0.184 / 0.179 for grey-world.
**The phone effect survives correction.**
**Secondary (partially circular) sclera-holdout region:** sclera 2.47 vs shades-of-grey
3.33 vs none 6.23 — the sclera methods *appear* to win there, which is exactly why the
circular measure is not the headline.
**Interpretation. NEGATIVE RESULT, recorded without softening.** Sclera-referencing
removes real capture-condition variation (significantly better than no correction and
than max-RGB) but is **significantly worse than plain grey-world** on a held-out region,
and the device effect it is supposed to remove survives. Under the criterion declared
before the run — beat no-correction AND every classical baseline — this is PARTIALLY
SUPPORTED. The claim that the sclera is a *sufficient* endogenous white reference is
**not supported**. **Status: confirmed. Not to be retried until it passes.**

### 2026-09-11 — Sensitivity of the sclera estimate (diagnoses the N1b result)
**Config.** `scripts/phase2_sensitivity.py`, 120 MOBIUS frames, angular shift in degrees.

| perturbation | mean | median | p90 |
| --- | --- | --- | --- |
| scleral yellowing +20% | 8.445 | 8.487 | 9.419 |
| scleral yellowing +10% | **4.399** | 4.443 | 4.842 |
| scleral yellowing +5% | 2.243 | 2.272 | 2.451 |
| vasculature left in | 1.569 | 1.421 | 2.134 |
| specular: naive mean vs robust trim | 0.485 | 0.383 | 1.052 |
| mask dilate 31 px | 0.404 | 0.355 | 0.695 |
| mask erode 31 px | 0.315 | 0.275 | 0.536 |
| mask erode/dilate 5 px | 0.055-0.060 | | |

**Interpretation — this explains N1b.** Segmentation boundary error is negligible
(0.06 deg at 5 px, 0.40 deg at 31 px) and the estimation mathematics is excellent
(N1a, 0.67 deg). But a 10% scleral yellowing shift — well inside normal inter-subject
and age variation — moves the estimate by **4.40 deg**, larger than grey-world's entire
error. **The bottleneck is knowledge of the sclera's own reflectance, which varies
between people by more than the illuminant signal being estimated and cannot be
recovered per subject without ground truth a deployment will never have.** This is a
mechanistic explanation of the negative result and it was predicted by the phase's
stated premise. **Status: confirmed.**

### 2026-09-11 — Segmentation quality score is too weak for N4 (negative)
**Config.** `scripts/phase2_eval_segmentation.py`, validated against MOBIUS's 17
deliberately-unusable `_bad` frames vs 120 normal frames.
**Metrics.** AUROC 0.816; good mean 0.918 vs bad mean 0.889 (difference 0.029);
**0 of 17 bad frames fall below the 0.3 threshold**.
**Interpretation.** It ranks bad frames slightly lower but **rejects nothing**. As an
abstention signal for N4 it is currently useless, and N4 must rely on the spectral
reconstruction residual it already specifies rather than on this score. **Status:
confirmed (negative).**

### 2026-09-11 — Vasculature exclusion is crude (negative)
**Metrics.** Removing 25.0% of sclera area recovers only **40.4%** of true vessel
pixels at **10.9%** precision, against vessels occupying 6.9% of the sclera (SBVPI
ground truth, n=60).
**Interpretation.** The redness percentile is a blunt instrument: it discards a quarter
of the reference to catch two fifths of a 6.9% target. It is still worth doing — leaving
vessels in costs 1.57 deg — but SBVPI's 128 vessel masks would support a proper vessel
segmenter if Phase 4 needs one. **Status: confirmed.**

### 2026-09-11 — Task 4: the pipeline runs on Eyes-Defy-Anemia
**Metrics.** n=218; mean quality 0.814, median 0.817; mean predicted sclera area
fraction 0.2623; **failure rate (quality < 0.3) 0.0%**. India 0.811, Italy 0.816.
**Interpretation.** Phase 4 has a working front end and the two sites behave alike.
This is a confidence measure, not accuracy: Eyes-Defy ships no masks, so segmentation
correctness there remains unverified. **Status: confirmed.**

### 2026-09-11 — Phase 2.5 Task 1: corneal-highlight feasibility census (GATE PASSED)
**Config.** `scripts/phase2_5_census.py`; detection requires >=3x region median luminance
AND >99th percentile; saturation threshold 250/255.
**Data.** 900 MOBIUS + 200 SBVPI frames.
**Metrics.** MOBIUS detected 74.7%, **usable (unsaturated) 71.7%**, pupil highlight
37.3%, median area 41 px. SBVPI 0.0% (segmentation yields zero iris/pupil pixels).
Saturation among detected highlights: p50 = 0.000, p75 = 0.031, p90 = 0.315; only 4.0%
of frames fully clipped; median 1,326 unsaturated pixels in the best highlight.
**By device:** Xiaomi Pocophone F1 91.5%, iPhone 6s 69.8%, Sony Xperia Z5 **52.1%** —
spread **39.3 percentage points**.
**By lighting:** indoor 78.8% (most clipping, 0.204), poor 72.6% (least clipping,
0.018), natural 65.1% — spread 13.7 pp.
**Interpretation.** Gate of 30% declared in advance: **PASSED at 71.7%**. Saturation is
not the blocker it was expected to be. Device dependence is larger than any device
effect found in Phase 2, and runs opposite to lighting: poor light is *not* the worst
case here, unlike segmentation. **Status: confirmed.**

### 2026-09-11 — Phase 2.5 Task 2: dichromatic specular estimation
**Config.** `scripts/phase2_5_evaluate.py`, `src/hemosight/calibration/specular.py`.
**Metrics.** Specular estimate obtainable on **1,393/1,796 frames (77.6%)**.
Decomposition routes: pupil_highlight_direct 862, iris_highlight_direct 273,
dichromatic_plane_intersection 173, degenerate_dark_surface 85, none 403.
Distinct chromatic clusters per frame: 1 in 817 frames, 2 in 356, 3 in 111, >=4 in 109 —
**41.3% of frames carry more than one light source**.
**Interpretation.** A genuine dichromatic decomposition, verified against synthetic
surfaces with a known illuminant. Direct routes dominate (81% of successful estimates)
because a clean pupil highlight usually exists and is the most direct reading. High
cluster counts (up to 17) most likely reflect detection fragmentation rather than 17
physical sources, but multi-source frames are common either way and are counted rather
than averaged. **Status: confirmed.**

### 2026-09-11 — Phase 2.5 Task 3: specular PARTIALLY SUPPORTED; the rescue failed
**Config.** Identical MOBIUS protocol to Phase 2; held-out iris; 720 frames, 40 subjects.
**Metrics** (within-subject dE2000 spread, lower is better):

| method | mean | median |
| --- | --- | --- |
| grey-world | **6.076** | 5.572 |
| specular + sclera | 7.047 | 6.722 |
| sclera, neutral prior | 7.312 | 6.821 |
| sclera, fitted prior | 7.427 | 7.157 |
| shades-of-grey p6 | 7.550 | 6.990 |
| **specular** | **7.821** | 7.255 |
| max-RGB p99 | 8.257 | 7.143 |
| no correction | 9.530 | 10.115 |

**Paired Wilcoxon, 40 subjects:** specular vs no correction -1.709, p=2.3e-04, wins
29/40. Specular vs grey-world **+1.745, p=4.5e-06, wins 5/40**. Specular vs sclera
**+0.394, p=0.29, NOT SIGNIFICANT**. specular+sclera vs grey-world +0.971, p=4.5e-04,
wins 10/40.
**Variance decomposition (iris):** specular+sclera has the lowest phone fraction (0.178,
below grey-world's 0.184) and the highest between-subject fraction (0.380). Noted but
not over-read: a higher between-subject fraction can also mean the method spreads
subjects apart, and its absolute within-subject spread is still worse than grey-world's.
**Interpretation.** Against thresholds declared in advance: **PARTIALLY SUPPORTED** —
beats no correction, does not beat grey-world. **The rescue did not rescue anything:
specular is statistically indistinguishable from the sclera method it was designed to
replace (p = 0.29).** Removing the per-subject reflectance term did not help.
**Status: confirmed. NEGATIVE RESULT, not to be retried until it passes.**

### 2026-09-11 — Phase 2.5 Task 4: grey-world IMPROVES under tight crops (hypothesis refuted)
**Config.** Centre crops around the segmented eye, grey-world recomputed per crop.
**Metrics.** Field of view 100% -> 6.076 dE2000; 60% -> 5.790; 40% -> 5.416;
**25% -> 3.935**; 15% -> 4.889. Crop-invariant references for comparison: sclera 7.427,
specular 7.821, none 9.530.
**Interpretation.** The Task 4 hypothesis — that grey-world would degrade as scene
context vanished, favouring local references — is **refuted**. Grey-world's best result
anywhere in Phase 2 or 2.5 is on a tight periocular crop, beating every endogenous
method by 3.1-3.9 dE2000. A wide frame is skin-dominated and strongly red, violating the
grey-world assumption; a periocular crop is far more balanced, so the assumption is
better satisfied on exactly the input a screening app would capture. **Grey-world's
advantage widens in the deployment-realistic regime rather than evaporating.**
Caveat: crops are eye-centred using the segmentation and therefore idealised; hand-framing
noise was not simulated. **Status: confirmed.**

### 2026-09-11 — N1 OVERALL: REFUTED (headline negative result)
**Summary.** Sclera (Phase 2) and corneal specular highlight (Phase 2.5) both tested on
the same held-out-iris protocol. Neither beats grey-world; the two are statistically
indistinguishable from each other; and grey-world's margin grows under the tight crops
that deployment implies.
**The surviving contribution is the diagnosis**, with each component measured:
inter-individual reflectance variance dominates (10% scleral yellowing = 4.40 deg),
segmentation is exonerated (31 px mask perturbation = 0.40 deg), estimation mathematics
is exonerated (0.666 deg given a known reference reflectance, six sensors,
leave-one-camera-out stable).
**What survives:** N1a intact; the segmentation pipeline intact (sclera IoU 0.875, 0%
failure on Eyes-Defy); and grey-world on a tight periocular crop as the practical
downstream recommendation. **Status: confirmed.**

### 2026-09-11 — Phase 3 TASK 0 GATE: colour-to-Hb inversion NOT RECOVERABLE (major negative result)
**Config.** `scripts/phase3_task0_gate.py`, `src/hemosight/simulation/`. Layered
diffusion forward model, D65, CIE 1931 observer as camera proxy, 240 random illuminant
perturbations per Hb level, Hb grid 4-18 g/dL.
**Metrics.**

| residual dE2000 | MAE g/dL | median | p90 | worst | band |
| --- | --- | --- | --- | --- | --- |
| 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | VIABLE |
| 1.000 | 0.864 | 0.653 | 1.958 | 3.992 | VIABLE |
| 2.000 | 1.801 | 1.341 | 4.069 | 8.000 | MARGINAL |
| **3.935 (measured, grey-world @25% FOV)** | **3.417** | 2.699 | 7.541 | 13.000 | **NOT RECOVERABLE** |
| 6.076 (measured, grey-world full frame) | 5.096 | 4.349 | 10.799 | 17.000 | NOT RECOVERABLE |

Inversion self-consistency with no perturbation: max error 0.0001 g/dL, so the error is
caused by colour error alone.
**WHO boundaries at the measured residual:** severe/moderate (7.0) MAE 1.975 p90 3.581 —
NOT distinguishable; moderate/mild (10.0) MAE 3.311 p90 8.156 — NOT distinguishable;
mild/normal (11.0) MAE 4.160 p90 10.935 — NOT distinguishable. **No WHO severity
boundary survives.**
**Interpretation.** Against thresholds declared before running, **NOT RECOVERABLE** at
1.7x the failing threshold. Work stopped; Tasks 1-3 not built.
**Status: confirmed. MAJOR NEGATIVE RESULT.**

### 2026-09-11 — Phase 3: signal-to-noise is the mechanism, checked against real tissue
> ⚠️ **SUPERSEDED 2026-09-12** by "Phase 6.5 Task 1: the empirical signal, measured" below. The ~0.70 figure and the 5.6x ratio are withdrawn; the binned method cannot measure the signal.
**Metrics.** Simulated signal **0.452 dE2000 per g/dL** (mean over Hb 4-18). Empirical
signal from **216 real Eyes-Defy subjects** using the dataset's own palpebral masks,
binned by Hb: **~0.70 dE2000 per g/dL** (excluding the n=3 lowest bin, which gave 5.26
and is sampling noise). Model/empirical agree within ~1.5x.
Noise: 3.935 (best measured) and 6.076 (full frame).
**noise/signal = 5.6x empirical, 8.7x simulated.**
Assumption robustness: BVF 0.02/0.06/0.15 and StO2 0.60/0.75/1.00 give equivalent errors
of 7.46 / 8.71 / 12.24 / 9.73 / 7.51 g/dL respectively — no variant rescues it.
**Interpretation.** The calibration residual alone is equivalent to 5.6-8.7 g/dL of Hb
error against a 14 g/dL clinical range. The empirical figure is an *upper* bound on the
true Hb signal (bin differences also contain inter-subject and capture variation), and
using it rather than the model's own makes the gate easier to pass — it still fails.
**Status: confirmed.**

### 2026-09-11 — Phase 3: sensitivity is HIGHER at low Hb (the one favourable finding)
**Metrics.** At the measured 3.935 residual: mean MAE at Hb <= 8 g/dL = **1.900 g/dL**;
at Hb >= 14 = **4.645 g/dL**; ratio **0.41x**. Per-g/dL colour change: 1.013 dE2000 at
Hb 4 versus 0.203 at Hb 16 — a 5x difference.
**Interpretation.** The reflectance-vs-Hb curve saturates, so the measurement is most
sensitive exactly where screening decisions are made. Not enough to rescue the method —
even at its most sensitive it needs calibration ~4x better than the best measured — but
it is a real and favourable asymmetry and the correct answer to "is low Hb worse?" is
**no, it is better**. **Status: confirmed.**

### 2026-09-11 — Phase 3 TASK 4: prior sensitivity (closes the Phase 2 question)
**Config.** Illuminant held perfect; each tissue prior perturbed alone; Hb truth 12.0.
**Metrics.**

| prior | tolerable range for <1.0 g/dL error | verdict |
| --- | --- | --- |
| blood volume fraction (nom 0.06) | 0.045-0.10 (about +/-30%) | tolerable |
| oxygenation StO2 (nom 0.75) | 0.60-1.00 (entire physiological range) | **benign** |
| layer thickness scale (nom 1.0) | 0.8-2.0 | tolerable |
| **melanin fraction (nom 0.0)** | **0.0 only** | **catastrophic** |

Melanin detail: 0.005 -> **+9.60 g/dL**; 0.010 and above -> +12.00 (estimate rails to the
top of the search range, i.e. total failure).
**Interpretation.** Phase 2 could not answer the prior question because within-subject
self-consistency is mathematically blind to a per-subject constant. Simulation answers
it: oxygenation is a non-issue, BVF and thickness are tolerable, and **melanin is
catastrophic**. This is a quantified mechanism for skin-tone bias and is flagged forward
to N5. Qualifications: the epithelial melanin layer is thin so sensitivity may be
overstated, and above 0.01 only the fact of failure is meaningful, not its magnitude.
**Status: confirmed.**

### 2026-09-11 — Phase 3: optical constants self-check FAILED then passed after correction
**Metrics.** First run: 500 nm isosbestic found at 515 nm (15 nm error, FAIL); the
529/545 pair collapsed. After correcting two transcription errors: all six isosbestic
points within **0.5 nm** (500.0 -> 499.5, 529 -> 529.0, 545 -> 545.0, 570 -> 570.0,
584 -> 584.0, 797 -> 797.5); HbO2 visible peak 576 nm; deoxy/oxy ratio 650-700 nm 8.36x.
**Interpretation.** The self-check caught real errors in data that would otherwise have
silently propagated into every downstream number. Internal consistency is **not**
verification: the tables are transcribed, not read from primary sources, and must be
re-verified before publication. **Status: confirmed (provisional data).**

### 2026-09-11 — Phase 3.5 TASK 1: ratio reformulation REFUTED (major negative result)
**Config.** `scripts/phase3_5_task1_cancellation.py`. Identical MOBIUS protocol to
Phases 2/2.5: 1,796 frames, 100 subjects, 3 phones x 3 lighting.
**Metrics** (within-subject spread across capture conditions):

| feature | dE2000 | equivalent g/dL |
| --- | --- | --- |
| grey-world on sclera | 3.330 | 5.23 |
| uncorrected sclera | 5.682 | 8.92 |
| **iris / sclera (best ratio)** | **6.399** | **10.04** |
| pupil / iris | 7.541 | 11.83 |
| pupil / sclera | 9.091 | 14.27 |

Ratio sensitivity 0.637 dE2000 per g/dL (absolute colour was 0.452).
**Implementation verification:** synthetic diagonal illuminant change gives ratio spread
**0.000000 dE2000** (plain mean) and 0.046 (trimmed summariser) — the observed 6.399 is
**139x** the implementation residual, so the negative result is real.
**Variance decomposition:** phone fraction 0.177 for the ratio vs 0.202 uncorrected —
essentially unchanged, the signature of von Kries diagonality failing.
**Interpretation.** Pre-declared threshold >2.0 g/dL = fails. At 10.04 g/dL this is 5x
over. Every ratio feature is worse than no correction at all. **Status: confirmed.
NEGATIVE RESULT. Task 2 not run.**

### 2026-09-11 — Phase 3.5 TASK 3: sclera reference stability (diagnoses Task 1)
**Metrics.**

| dataset | within-subject dE2000 | between-subject dE2000 | within/between |
| --- | --- | --- | --- |
| MOBIUS (100 subj, 898 captures) | **5.860** | 4.050 | **1.447** |
| SBVPI studio (54 subj, 699 captures) | 1.685 | 1.825 | 0.924 |

**Interpretation.** On phone captures the sclera varies MORE within a subject than
between subjects — the opposite of the regime the ratio method requires. Studio
conditions cut within-subject variation 3.5x, so the instability is capture-driven
(geometry, gaze, specular, focus), not tissue-driven; but even there the ratio is 0.92,
short of << 1. A perfect per-subject offset removes the between term (4.050) and leaves
the within term (5.860) — the wrong term — and is not obtainable in deployment anyway.
**Status: confirmed.**

### 2026-09-11 — Phase 3.5 TASK 0: sourced constants vs transcription
**Metrics.** 112 points compared: median relative error 1.30%, **18.8% of points >10%
off**, max **252%** (deoxy-Hb at 470 nm: 16,156 sourced vs 56,880 transcribed).
Melanin power-law fit: A=6.6e11, k=3.330, max log-residual **0.000000** (exactly a power
law, not measured data). 28 cameras parsed from camspec; only 2 of 6 nus8 cameras
matched.
**Effect on the Phase 3 gate:** MAE at the measured 3.935 residual moves from 3.417
(transcribed) to **3.893** (sourced); 2.0 dE2000 moves MARGINAL -> NOT RECOVERABLE.
**Verdict unchanged and marginally stronger.**
**Interpretation.** The Phase 3 isosbestic self-check PASSED on the bad data — it
verified crossing points, which were right, not the values between them. Internal
consistency is not verification. **Status: confirmed.**

### 2026-09-11 — Phase 4 GATE A: AC/DC normalisation FAILS to cancel (negative)
**Config.** `scripts/phase4_gate_a.py`, `src/hemosight/ppg/features.py`. 252 subjects,
200 Hz, 4th-order Butterworth zero-phase: DC low-pass 0.4 Hz, AC band-pass 0.5-8 Hz,
per-beat median trough-to-peak amplitude.
**Metrics.** Median nuisance CV: raw DC 0.5633 | raw AC ~1.03 | **AC/DC 1.5299
(-171.6%)** | **ratio-of-ratios 1.1152 (-98.0%)**. Median R^2 with Hb <= 0.021 in every
group. Best single-feature equivalent Hb noise **9.75 g/dL** vs population SD **1.470**.
**Interpretation.** Pre-declared threshold was >=50% nuisance reduction. Normalisation
*increases* nuisance variance. Device-invariance is untestable here (single device);
tissue-invariance is decisively refuted. **Status: confirmed. GATE A FAIL.**

### 2026-09-11 — Phase 4 GATE B: no recoverable Hb signal in PPG (major negative)
**Config.** `scripts/phase4_gate_b.py`. Grouped 10-fold CV, Ridge + gradient boosting.
**Metrics.**

| condition | n feat | MAE g/dL | Pearson r | R^2 | band |
| --- | --- | --- | --- | --- | --- |
| four wavelengths | 41 | 1.190 | +0.059 | **-0.025** | NOT VIABLE |
| 660 nm only | 9 | 1.209 | +0.013 | **-0.037** | NOT VIABLE |
| simulated phone-RGB | 13 | 1.175 | +0.090 | +0.007 | NOT VIABLE |
| gradient boosting (4 wl) | 41 | 1.193 | +0.121 | — | NOT VIABLE |

Phone sensor coverage (camspec, 28 cameras): 660 nm R=0.179/G=0.016/B=0.007;
**730, 850, 940 nm = 0.000 in all channels** (beyond 720 nm and behind the IR-cut
filter).
**Interpretation.** Two of three conditions have NEGATIVE R^2 — worse than a constant.
Three of the four wavelengths are invisible to the target hardware regardless.
**Status: confirmed. GATE B FAIL in all conditions.**

### 2026-09-11 — Phase 4 TASK 3: sex alone beats PPG by 30% (the decisive baseline)
**Metrics.** Identical folds: population mean MAE **1.175**; **sex alone MAE 0.831,
R^2 0.415**; full demographics MAE **0.831** (age/height/weight add nothing);
four-wavelength PPG **1.190**; PPG+demographics 0.824 (vs demographics 0.831 — noise).
**Interpretation.** PPG loses to the null model. A "PPG + demographics" model lands
inside the pre-declared VIABLE band at 0.824 and would look like a working PPG
estimator if reported without the baseline — **it is a sex classifier**. Men carry
higher haemoglobin, which is why WHO thresholds differ by sex (13 vs 12 g/dL).
**Status: confirmed. This is the finding that decides the phase.**

### 2026-09-11 — Phase 4 TASK 2: SQI rejects, but cannot be validated here
**Metrics.** Rejection rate 4.4% / 10.7% / **17.5%** / 32.1% at SQI < 0.1/0.2/0.3/0.5.
MAE rejected 0.930 vs retained 0.810. r(SQI, |error|) = **-0.033**; MAE by quartile
0.892, 0.796, 0.868, 0.769 (no trend).
Independent SNR: **8.1-8.3 dB all four channels**, no ordering, 71-73% below 10 dB —
does NOT reproduce the dataset's published 850 nm cleanest (19.04) / 940 nm worst
(16.44, 17.5% below 10 dB). README does not define its SNR; not tuned to match.
Extraction validated instead on physiology: HR median 82.5 bpm, 90.5% in 40-120 bpm,
four channels agreeing to 0.0 bpm SD.
**Interpretation.** Unlike the Phase 2 image SQI (AUROC 0.816, rejected 0 of 17), this
one does refuse. But the error relationship is ~zero and the only skilled model uses no
PPG, so there is no mechanism for SQI to predict its error. **Status: confirmed.**

### 2026-09-11 — Phase 4.5: deep models on raw PPG (verdict unchanged, finding refined)
**Config.** `scripts/phase4_5_deep.py`, `src/hemosight/ppg/deep.py`. 200 Hz -> 50 Hz,
0.5-8 Hz band-pass, 10 s windows (2,584 from 252 subjects), per-channel z-score within
window. Subject-disjoint 10-fold CV, target standardised per fold.
**Metrics.**

| model | condition | MAE g/dL | r | R^2 | train gap | sex probe |
| --- | --- | --- | --- | --- | --- | --- |
| speccnn | 660 nm | **1.113** | +0.248 | +0.061 | +0.096 | 50.0% |
| gru | 660 nm | 1.119 | +0.247 | +0.003 | +0.213 | 52.3% |
| speccnn | 4-wl | 1.121 | +0.244 | +0.051 | +0.137 | 50.2% |
| cnn1d | 660 nm | 1.161 | +0.203 | -0.077 | +0.421 | 46.1% |
| cnn1d | 4-wl | 1.180 | +0.201 | -0.112 | +0.557 | 43.6% |
| gru | 4-wl | 1.196 | +0.118 | -0.116 | +0.308 | 50.3% |

Baselines: sex alone **0.831**, demographics 0.831, population mean 1.175, Phase 4
features 1.190. Sex-probe base rate 57.0% — **no representation encodes sex above it**.
**Interpretation.** No deep model beats a single binary demographic variable. Three of
six have negative R^2. Large train-test gaps show the bigger models memorise subject
identity. **Status: confirmed. PPG arm remains NOT VIABLE.**

### 2026-09-11 — Phase 4.5 ceiling analysis: features carry NO signal (stronger claim warranted)
**Config.** `scripts/phase4_5_ceiling.py`, 51 PPG features, 500 permutations.
**Metrics.** Mutual information: max 0.0608 vs null p95 0.0676 — **0 of 51 features
above the null**. Correlations: 4 at raw p<0.05 against **2.6 expected by chance**;
**0 survive Benjamini-Hochberg FDR** (best ac_dc_660 r=+0.149, p_FDR=0.359).
Permutation: real MAE **1.2075**, null **1.1869 +/- 0.0102**, **p = 0.978**, z = +2.03
(wrong direction).
**Interpretation.** The feature model is **not distinguishable from models trained on
shuffled labels** — it is worse than 97.8% of them. This licenses the stronger claim for
the feature representation: the signal is not present, not merely that one model failed.
**Status: confirmed.**

### 2026-09-11 — Phase 4.5: the raw waveform DOES carry a real signal (positive, but useless)
**Config.** Permutation test on the best deep model specifically (speccnn, 660 nm), same
architecture and folds, Hb shuffled across subjects, n=30 permutations.
**Metrics.** Real MAE **1.1210**; null **1.1969 +/- 0.0161**; **z = -4.72**;
distinguishable from chance at p<0.05.
**Interpretation.** **This corrects the blanket negative.** The raw waveform contains
haemoglobin-correlated information that the AC/DC ratio features discard — the features
were throwing something away. But the effect improves on predicting a constant by only
0.054 g/dL, and sex alone beats it by six times that margin. **Real, statistically
significant, and clinically useless: MAE 1.12 g/dL separates no WHO severity band.**
Attribution caveat: significance means the waveform tracks something at the subject
level — Hb or a correlate; the sex probe excludes sex but not every confound.
**Status: confirmed. The one positive finding in Phases 4 and 4.5.**

### 2026-09-11 — Phase 5 TASK 1: the positive claim survives hardening
**Config.** `scripts/phase5_harden.py`. 10-fold subject-disjoint CV, 40 epochs, target
standardised per fold. 270 full CV runs in total.
**Metrics.**

| test | n | real MAE | null mean +/- SD | empirical p | parametric z |
| --- | --- | --- | --- | --- | --- |
| selected model alone | 200 | 1.1124 | 1.2009 +/- 0.0166 | **0.00498** | -5.34 |
| **selection-aware (best-of-six inside each perm)** | 60 | 1.1124 | 1.1938 +/- 0.0162 | **0.01639** | -5.02 |
| **selection-aware, EXTENDED (supersedes the row above)** | **240** | 1.1124 | 1.1959 +/- 0.0168 | **0.00415** | -4.96 |

Seed stability (10 seeds): mean 1.1153, **SD 0.0069**, range 1.1069-1.1279.
Subject robustness: MAE 1.1124 -> **1.2258** after dropping the best-performing decile.
**Interpretation.** All four tests pass. The real-vs-null gap (0.0815) is **11.9x** the
seed SD. The selection step buys 0.0071 g/dL by chance — real, and an order of magnitude
below the gap. The p is the **empirical floor**, not a measured value - 0.0164 at n=60,
and 0.0041 after the 2026-09-12 extension to n=240.
**The claim is retained and remains clinically useless**: ~0.05 g/dL better than a
constant, six times worse than sex alone, separating no WHO severity band.
**Status: confirmed. NOT retracted.**

### 2026-09-11 — Phase 5 TASKS 2-4: consolidation, reproducibility, literature
**Artefacts.** `reports/final_results.md`, `reports/dataset_manifest.md`,
`reports/literature_gap.md`, `scripts/reproduce_all.py`.
**Metrics.** Reproduction: 33 stages, ~12 h full / ~22 min `--fast`; 12 CPU-only stages
verified to regenerate. Manifest: 38.1 GB, 40,831 files, **8 of 10 licences
UNVERIFIED**. Git: **0 data files, 0 figures, 0 binary artefacts tracked**, enforced by
test. Literature counts over 5 applicable sources: demographic baseline 0 yes / 5
unknown; subject-level splits 1/0/4; cross-device 1/1/3; duplicate check 0 yes / **3 no**
/ 2 unknown. Tests: **98 passing**.
**Reproduction VERIFIED, not just claimed.** A clean `--fast` run completed 22/22
stages in **10.3 minutes** and regenerated the reported numbers exactly: Phase 3 gate
3.893, Phase 4 four-wavelength 1.190, sex-alone 0.831, Phase 4.5 permutation p=0.978,
Phase 2 yellowing 4.40 deg. The single non-exact stage is the deep sweep (1.111 vs 1.113
reported), which differs by less than the measured seed SD of 0.0069 — the expected
cuDNN non-determinism, documented in the entry point.
**Interpretation.** The package reproduces from raw data with a frozen seed, and the two
non-deterministic stages have measured tolerances an order of magnitude below the
reported effects. The literature table is deliberately under-claimed and its caveats are
test-enforced. **Status: confirmed.**

---

### 2026-09-12 - Phase 6: the audit harness, validated against known ground truth
**Config.** `scripts/phase6_validate_harness.py` (58 s, CPU only),
`src/hemosight/audit/`, 8 checks. Verdicts compared against CLAUDE.md's own DECISION and
RESULTS LOG entries dated 2026-09-11.
**Data.** (A) this project's own artefacts: 9,232 Ghana-pool images, the 252-subject PPG
feature table, `harden.json`; (B) 7 synthetic submissions carrying one injected fault
each plus a genuine-signal positive control; (C) 20 clean replicates, n=240, no fault.
**Metrics.**

| | result |
| --- | --- |
| known-truth verdicts reproduced | **15 / 15 (100%)** |
| sensitivity to injected faults | **12 / 12 (100%)** |
| false positives on clean inputs | **6 of 160 check-runs (3.75%)** |

Reproduced exactly from this project's own data: **419** byte-identical image groups
spanning the split boundary (Phase 1 recorded 419 shared MD5); **1,708 nominal subject
ids -> 1,067 leak-proof groups** (Phase 1 recorded the same); PPG four-wavelength MAE
**1.190** and PPG+demographics **0.824** g/dL, regenerated with Phase 4's own estimator;
0 of 41 features above the MI null; empirical p **0.01639** at n=60 with `at_floor` true;
effect **11.9x** the seed SD.
**The false positives are reported, not tuned away.** All 6 fall in the two checks that
compare point estimates with no uncertainty interval (`demographic_baseline` 2/20,
`subgroup_robustness` 4/20), on a clean generator whose model advantage over the
population mean is genuinely modest - borderline inputs rather than clean ones. Both
checks now flag a narrow margin in their own output; the thresholds were **not** moved,
because matching a number by adjusting a definition is fitting to the answer.
**Interpretation.** The harness returns the verdict the phase returned on every case
already on the record, catches every fault it was built to catch, and cries wolf on
3.75% of clean check-runs with a named and measured cause. Tests: **121 passing** (was
102). **Status: confirmed.**

### 2026-09-12 - Phase 5 extended permutation run: IN PROGRESS, not consolidated
**Config.** `scripts/phase5_perm_extended.py`, detached OS process, target 240.
**Metrics at the time of writing (111 of 240 complete).** Real MAE 1.1124 (read from
`harden.json`, never recomputed); null mean 1.1951, SD 0.0154, min 1.1425; **0 draws at
or below the real value**; empirical p **0.00893, which is the floor 1/(n+1)**;
parametric z -5.37. Peak GPU 401 MB of 8,585, flat across every permutation.
**Interpretation.** Provisional and **not** a reportable figure. Until the run reaches
240 and is consolidated as a deliberate step, **the reported result remains p = 0.0164
at n = 60** and must not be altered anywhere. **Status: SUPERSEDED by the entry below,
dated the same day, once the run completed.**


### 2026-09-12 - Phase 5 extended permutation: COMPLETE at n=240. The bound tightens fourfold; it is still a bound
**Config.** `scripts/phase5_perm_extended.py`, detached OS process, 240 permutations,
each re-running the full best-of-six selection (60 complete 10-fold subject-disjoint CV
runs per permutation). **14,400 CV runs in 10.65 h.** Consolidated into `harden.json` by
`scripts/phase5_consolidate_extended.py`, a separate deliberate step; the runner itself
never writes that file and a test enforces it.
**Data.** 252 subjects, 2,584 windows, Hb shuffled across subjects with permutation i's
labels drawn from `default_rng(770000 + i)` and nothing else.
**Metrics.**

| | n = 60 (superseded) | **n = 240** |
| --- | --- | --- |
| real MAE (seed-averaged, unchanged) | 1.1124 | **1.1124** |
| null mean | 1.1938 | **1.1959** |
| null SD | 0.0162 | **0.0168** |
| null minimum | - | **1.1279** |
| draws at or below the real MAE | 0 of 60 | **0 of 240** |
| empirical p | 0.01639 | **0.004149** |
| floor 1/(n+1) | 0.01639 | **0.004149** |
| at the floor? | yes | **yes** |
| parametric z | -5.02 | **-4.96** |

**Interpretation - and the honest reading of what was asked.** The run was launched to
find out whether the empirical p would become a *measured value* rather than the n=60
floor. **It did not.** Two outcomes were declared in advance: either a draw finally lands
at or below the real value and the p becomes a measurement, or none does and the bound
gets four times tighter. This is the second. Zero of 240 permutations reached the real
MAE, so p = 0.004149 is again exactly 1/(n+1) - **a bound, not a measurement**, and any
statement of it that omits that word repeats the error this whole exercise existed to
correct.
The closest any null draw came was **1.1279 against the real 1.1124**, still 0.0155
above it - more than twice the seed SD of 0.0069. The null mean moved by 0.0021 between
n=60 and n=240, and the SD by 0.0006, so the n=60 estimate of the null was already
sound; what n=60 could not do was resolve the tail.
**The parametric z moved the WRONG way and that is worth stating**: -5.02 to -4.96,
because the larger sample gave a slightly wider null SD. The two statistics are
answering different questions - the z assumes a normal null and got marginally less
extreme, while the empirical bound got four times tighter - and reporting only the more
flattering one would be the exact selection this project keeps refusing to make.
**Nothing else about the claim changes.** The mandatory clause stands verbatim: the
effect improves on predicting a constant by ~0.05 g/dL, sex alone beats it by six times
that margin, and an estimator at MAE 1.12 g/dL separates no WHO severity band. Real,
statistically distinguishable from chance, and clinically useless.
**Consolidated into:** `data/interim/phase5/harden.json` (n=60 retained with a
`superseded_by` pointer), the FINAL STATUS banner in section 2, the Phase 5 DECISION LOG
evidence block, the Phase 5 RESULTS LOG table, `reports/final_results.md`, the audit
package's own provenance docstrings, and the case-study endpoint - which reads the figure
from `harden.json` rather than holding a copy. **Status: confirmed.**


### 2026-09-12 — Phase 6.5 Task 1: the empirical signal, MEASURED (supersedes the 0.70 figure)
**Config.** `scripts/phase3_empirical_signal.py` -> `data/interim/phase3/empirical_signal.json`;
`reproduce_all.py` stage "Phase 3 empirical signal"; seed 20260911; 500 permutations, 2,000 bootstrap.
**Data.** Eyes-Defy-Anemia, 215 subjects with a palpebral mask (2 lack one),
the dataset's own masks in all three encodings found on disk (alpha cutout 184,
white-background 31, 3-channel 0),
cutout-vs-JPEG alignment max 11938.9/255.
**Metrics** (dE2000 per g/dL; null = Hb shuffled across subjects):

| estimator | value | null | p |
| --- | --- | --- | --- |
| binned by Hb, the method on record | 2.29 | **2.13 +/- 0.46** | 0.33 |
| regression Hb + site (upper bound) | 1.37 (CI 1.06-1.71) | 0.17 | 0.002 |
| **regression Hb + site + sex + age** | **0.84 (CI 0.57-1.17)** | 0.13 | 0.002 |

Per site (adjusted): India 0.68, Italy 0.92.
Grey-world tight crop: 0.78. r(Hb, male) = 0.55. Between-subject colour at fixed
Hb/sex/age/site: **4.55 dE2000 = 5.4 g/dL equivalent**.
**Downstream.** noise/signal at 3.935: **4.7x** (CI 3.4-6.9), was 5.6x;
at 6.076: 7.3x. Equivalent Hb error at the measured residual **4.7 g/dL**
(2.9 even with the unadjusted signal) - above 2.0 at every bound.
Model/empirical: the model underestimates by 1.9x (was "within 1.5x").
**Interpretation.** The binned method returns ~2.1 with NO Hb signal - CIEDE2000 between noisy bin means
measures the noise in the means - so the figure on record was never a measurement and is WITHDRAWN, not
corrected. The regression figure brackets 0.70 by coincidence. **No verdict changes**: the Phase 3 gate
(3.893 g/dL) was computed on the simulated inversion; the empirical cross-check still puts the equivalent
error above the 2.0 g/dL line at the central estimate and both CI bounds. **Status: confirmed.**

### 2026-09-12 — Phase 6.5 Task 2: image CNN baseline on Eyes-Defy (MARGINAL; the §3 comparison arm)
**Config.** `scripts/phase6_5_image_cnn.py`, `src/hemosight/baseline/image_cnn.py`. ResNet-18 ImageNet init,
palpebral bbox crop 224 px, 30 epochs, 10-fold subject-disjoint CV, target standardised on train
folds, geometric augmentation only, 3 seeds. Bands <1.0 viable, 1.0-2.0 marginal, >2.0 not viable.
**Data.** 216 Eyes-Defy subjects (India 95, Italy 121), one image each,
one Galaxy S6 in two variants, Hb 7.0-17.4, no severe cases. **Pilot comparison arm, not a validation.**
**Metrics** (identical folds):

| model | MAE g/dL | r | R² | band |
| --- | --- | --- | --- | --- |
| population mean | 2.003 | — | — | NOT VIABLE |
| sex alone | 1.631 | +0.544 | +0.295 | MARGINAL |
| demographics without site (age, sex) | 1.607 | +0.548 | +0.301 | MARGINAL |
| site alone | 1.641 | +0.490 | +0.240 | MARGINAL |
| **demographics WITH site (site, sex, age)** | **1.273** | +0.697 | +0.485 | MARGINAL |
| colour features (mean Lab + ridge) | 1.343 | +0.703 | +0.494 | MARGINAL |
| colour features + demographics | 1.243 | +0.746 | +0.557 | MARGINAL |
| **CNN, seed-averaged** | **1.301** | +0.709 | +0.499 | **MARGINAL** |
| CNN + age + sex (stacked) | 1.225 | +0.738 | +0.544 | MARGINAL |
| CNN + site + sex + age (stacked) | 1.195 | +0.744 | +0.553 | MARGINAL |
| colour features + site + sex + age | 1.161 | +0.758 | +0.574 | MARGINAL |

Site Hb: India 11.47 +/- 2.06; Italy 13.83 +/- 2.04 - a 2.4 g/dL gap between two device
variants. Image increment over site+sex+age: **+0.078 g/dL**. WHO-band AUROC: CNN
0.875, colour 0.874, site+sex+age 0.816.
Per site (pooled CNN vs site+sex+age): India 1.386 vs 1.290; Italy 1.234 vs 1.260.

Seeds: 1.344, 1.436, 1.328 (SD 0.0476); train MAE 0.476,
**train-test gap +0.893**. Sex probe on features 0.713 vs base 0.602;
r(CNN pred, male) +0.502 vs r(Hb, male) +0.558. Permutation (n=30): real 1.3435, null 2.2018 +/- 0.0814, empirical p 0.0323 (floor 0.0323), z -10.54.

**Cross-site (the only cross-site axis):**

| direction | train/test | train-site mean | sex | demographics | colour | **CNN** | r | bias | band |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| italy to india | 121/95 | 2.625 | 2.246 | 2.739 | 2.035 | **1.958** | +0.60 | +1.59 | MARGINAL |
| india to italy | 95/121 | 2.819 | 2.405 | 2.486 | 1.995 | **1.995** | +0.53 | -1.52 | MARGINAL |

**Interpretation.** Beats population mean: True; beats sex alone: True;
beats demographics without site: True; **beats demographics WITH site: False**.
The CNN beat sex alone by reading the site; against the site-inclusive baseline it does not win. Under Eyes-Defy's controlled illuminant the image carries real haemoglobin information (within-site r 0.5-0.65, permutation far from chance, three Lab numbers nearly match the CNN) worth ~0.1 g/dL over demographics - real and clinically useless, the PPG-waveform shape again. The imaging verdict stands; the write-up carries the controlled-illuminant caveat.
**Status: confirmed.**

### 2026-09-12 — Phase 6.5 Task 3: the three Phase 5 checks driven END TO END on the deep model
**Config.** `scripts/phase6_5_deep_predictions.py` (Phase 5 driver, same seeds and folds; 10 seeds + 6
candidates in 9.7 min) -> `data/interim/phase6/known_truth/phase5_deep_model.csv` (untracked);
`scripts/phase6_validate_harness.py` section A8.
**Metrics.** Regenerated seed-averaged MAE 1.1126 vs recorded 1.1124;
max |per-seed - recorded| 0.0041. Harness verdicts: demographic_baseline FAIL (expected FAIL); permutation PASS (expected PASS); seed_stability PASS (expected PASS); subgroup_robustness PASS (expected PASS).
Known-truth cases **19/19**, faults 13/13, false positives
6/160 (3.75%).
**Interpretation.** The deferred Phase 6 item is closed. The harness's permutation p is a different null
(labels permuted against fixed predictions) and is NOT a reproduction of 0.0041; the verdict agrees. **Status: confirmed.**

### 2026-09-12 — Phase 6.5 Task 4a: the Phase 2 estimator applied to Eyes-Defy and STORED
**Config.** `scripts/phase6_5_eyes_defy_illuminant.py` -> `data/interim/phase6_5/eyes_defy_illuminant.{csv,json}`.
**Metrics** (angular spread about the site mean, degrees; n=218, sclera estimate on 218):
sclera_neutral: all 3.48, India 2.69, Italy 2.65, between-site 4.82; grey_world_full: all 4.09, India 1.87, Italy 2.56, between-site 7.37; grey_world_25pct: all 4.40, India 4.24, Italy 4.04, between-site 2.93.
Sclera vs grey-world(25%) per image 3.56 deg.
**Interpretation.** Eyes-Defy is captured under a fixed white LED with ambient light excluded, so the true
illuminant is nearly constant and the spread is mostly estimator error - consistent with Phase 2's MOBIUS
finding that the sclera reference varies per subject. Within-subject stability is NOT measurable (one image
per subject). The Phase 2 tick is now backed by the artefact its wording implies. **Status: confirmed.**

### 2026-09-12 — Phase 7 Task 1: residuals by capture condition and the gate re-run (outcome B)
**Config.** `scripts/phase7_controlled_capture.py`; Phase 2 U-Net; sclera colour, vessel-excluded,
robust RGB; within-subject mean pairwise CIEDE2000; gate machinery imported from `phase3_task0_gate.py`
(240 trials per Hb level, seed 20260911).
**Data.** MOBIUS: 898 across-condition captures (100 subjects, 1 per phone x lighting cell) and
3588 within-cell captures (898 cells, left eye, four gazes); SBVPI: 700 studio captures, 54 subjects.
**Metrics** (within-subject dE2000; none / grey-world full / grey-world 25% crop):

| condition | none | gw full | gw crop | best | gate MAE g/dL | band |
| --- | --- | --- | --- | --- | --- | --- |
| MOBIUS across phones x lighting | 5.860 | 3.456 | 5.070 | **3.456** | **3.471** | **NOT RECOVERABLE** |
| MOBIUS same phone + lighting | 3.045 | 1.981 | 3.357 | **1.981** | **2.027** | **NOT RECOVERABLE** |
| SBVPI studio | 1.685 | 1.062 | 2.591 | **1.062** | **1.040** | **MARGINAL** |

Breakeven on the gate model: VIABLE needs residual < 0.99 dE2000, MARGINAL < 2.07.
Reference 3.935 -> 3.977 (Phase 3 recorded 3.893; same model, different RNG stream).
Eyes-Defy: within-subject residual NOT MEASURABLE; colour model 1.343, CNN 1.301, MARGINAL.
**Interpretation.** At the studio residual the gate returns 1.04 g/dL - +0.04 from the VIABLE line: studio-grade control brings the CALIBRATION term to the edge of viable, and what keeps the empirical Eyes-Defy result in MARGINAL is the between-subject tissue term the gate never modelled. In the controlled regime the limiting factor shifts from calibration to tissue. The refutation is restated in TWO PARTS: (1) from uncontrolled photographs the colour-to-Hb inversion is NOT RECOVERABLE (unchanged); (2) from controlled capture it reaches the MARGINAL band only - screening bands at best - does not beat site + sex + age, and moves no clinical threshold. The distinction a reviewer would raise is real, is now measured, and does not rescue the claim. **Status: confirmed.**

### 2026-09-12 — Phase 7 Task 2: both modalities on comparable axes
**Config.** `scripts/phase7_statistical_vs_clinical.py`; identical 10-fold subject-disjoint folds; WHO
thresholds 12 (F) / 13 (M) g/dL.
**Metrics.** PPG waveform: z -4.96, p <= 0.0041 (floor); gain over constant +0.066;
vs sex alone -0.282; added to sex -0.009; 19% of the baseline's advantage;
WHO AUROC 0.566 vs 0.432; sensitivity 0.00 (prevalence 7%).
Conjunctival colour: CNN z -10.5; gain over constant +0.702; vs site+sex+age
-0.028; added +0.078; 96%; AUROC 0.875 vs 0.816;
sens/spec 0.76/0.80 vs 0.86/0.74.
**Interpretation.** Real in both; useless in PPG on every axis; marginal-and-within-site-only in the
conjunctiva. Retrospective 2x2 over nine results: two in the headline cell, three in "apparent utility",
two in "real but worse than the cheap baseline". **Status: confirmed.**

### 2026-09-12 — Phase 7 Task 3: external audit path (no external result)
**Metrics.** `tests/test_phase7.py`: 6 tests, including the demonstration that a per-image table with
no subject id PASSES split integrity without the ingestion record and returns INSUFFICIENT DATA with
it. Synthetic smoke test of the CLI: 150 per-image rows -> 75 subjects, 4 of 8 checks INSUFFICIENT.
Register: 0 entries. **Status: built; no external audit run.**

### 2026-09-13 — Phase 7 Task 3B: external audit (availability is the result)
**Config.** `scripts/phase7_external_run.py` (isolated env `anemia-detection-env`, CPU torch, TF 2.21 /
Keras 3, nbclient, 900 s cell timeout); `scripts/external_audit.py register`; `scripts/phase7_external_report.py`.
**Metrics.** Candidates examined **3**; auditable **0**. anemia-detection: notebooks 7, ran to completion
**0**, predictions produced **0**; `requirements.txt` installable as written: False. BPANet: predictions
upon_request, code not_stated. Hemo-ConViT: unlocated (0/0/0 hits). Literature table: 11 sources, with one
full-text-read paper recorded as NOT REPORTED on all four attributes.
**Interpretation.** The harness's external path was exercised to the point of ingestion and never reached it,
because nothing ingestible was released. That is the finding. **Status: confirmed; sample of three, no
field-level claim.**

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