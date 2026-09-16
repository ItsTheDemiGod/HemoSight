# RESULTS LOG — HemoSight

> **Provenance.** Moved verbatim out of `CLAUDE.md` on 2026-09-17, when that file
> reached 233,820 characters and was being truncated on load. The text below is
> byte-identical to the corresponding section of `CLAUDE.md` at commit `715096a`,
> recoverable in full from the git tag `pre-claude-md-split`. **Nothing was
> summarised, condensed or deleted.** See `docs/archive/README.md`.

> **Append new entries to the END of this file**, per the WORKING PROTOCOL in
> `CLAUDE.md`. Every metric produced is recorded here, including failures and
> negative results. Never delete an entry; supersede it with a newer one. The
> section heading below is retained so existing references to
> "CLAUDE.md section 8 / the RESULTS LOG" still resolve.

---

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