# DECISION LOG — HemoSight

> **Provenance.** Moved verbatim out of `CLAUDE.md` on 2026-09-17, when that file
> reached 233,820 characters and was being truncated on load. The text below is
> byte-identical to the corresponding section of `CLAUDE.md` at commit `715096a`,
> recoverable in full from the git tag `pre-claude-md-split`. **Nothing was
> summarised, condensed or deleted.** See `docs/archive/README.md`.

> **Append new entries to the END of this file**, per the WORKING PROTOCOL in
> `CLAUDE.md`. Never delete an entry; supersede it with a newer one that says what
> changed and why. The section heading below is retained so existing references to
> "CLAUDE.md section 7 / the DECISION LOG" still resolve.

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

## DOCUMENTATION DECISIONS (2026-09-17)

### 2026-09-17 — CLAUDE.md split: the evidentiary record moved to `docs/archive/`
**Decision.** `CLAUDE.md` had reached **233,820 characters** against a 150,000-character
load limit and was being **silently truncated** on every session load. The DECISION LOG
(this file), the RESULTS LOG, the superseded claim texts and the corrections were moved
verbatim into `docs/archive/`. `CLAUDE.md` keeps the claim set, the hard constraints, the
dataset inventory, the tech stack, the phase plan, a new CURRENT STATE section, an archive
index and the WORKING PROTOCOL. **No content was summarised, condensed or deleted.**
**Rationale.** Truncation is the worst possible failure mode for this file: it removes
content without saying which content, so a session reads a partial record and cannot tell.
The logs are the largest part and the part a session does not need loaded on every turn,
while the claims, constraints and phase plan are exactly what it does need. Splitting on
that line is what makes the remainder loadable in full.
**Alternatives considered.** (1) Summarising the logs — rejected outright: the logs are the
project's evidence, and its whole contribution is a body of negative results whose value is
in the detail of how each was measured. (2) Deleting superseded entries — rejected; it is
forbidden by the WORKING PROTOCOL and would destroy the corrections record, which is itself
a finding. (3) Renumbering sections 7–9 — rejected: `reports/*.md` cite "section 8 RESULTS
LOG" and "DECISION LOG 2026-09-11", so the numbering was kept, sections 7 and 8 became
pointer stubs, and the `## 7.` / `## 8.` headings were retained inside the archive files so
every existing reference still resolves.
**Verification — measured, not asserted.** Counted before and after:

| quantity | pre-split | post-split |
| --- | --- | --- |
| DECISION LOG entries | 81 | **81** (titles identical, same order) |
| RESULTS LOG entries | 48 | **48** (titles identical, same order) |
| DECISION phase-group headers | 12 | **12** |
| `**Original wording, preserved.**` blocks | 3 | **3** |
| standalone correction entries | 7 | **7** |
| non-blank lines of sections 7–8 absent from the archive | — | **0** |

Byte-identity: every moved block was copied by line range with **no heading-level changes**,
so each is byte-identical to its source — section 7 (lines 828–2275, 108,230 chars), section 8
(lines 2277–3130, 56,556 chars), and each claim and correction block individually. In the
retained head (lines 1–826): **0 lines removed**, 19 replaced, each differing from its original
by **exactly** an inserted `` (`docs/archive/…`) `` pointer, verified by stripping the pointer
and comparing for equality. `CLAUDE.md`: 233,820 → **76,128 characters**.
**Two defects were found and fixed during verification, not after it.** A first pass used a
regex that spanned line breaks: it collapsed the wrapped reference at line 647–648 into one
line (losing a line, though not a word), and it silently **missed** the reference wrapped as
`See the DECISION` / `> LOG, 2026-09-12.` because the `> ` continuation marker broke the
whitespace match. Both were caught by diffing the head line-by-line rather than trusting the
substitution count. The repointing was redone per line, which preserves the line structure
exactly and keeps the phrase "DECISION LOG" verbatim with the path annexed after it — so the
verification could be tightened from "differs plausibly" to "differs by exactly this string".
**Consequences.**
- New DECISION LOG entries append to the END of this file; RESULTS LOG entries to
  `docs/archive/results_log.md`; corrections additionally to `docs/archive/corrections.md`;
  superseded claim wording to `docs/archive/superseded_claims.md`. The phase plan, the claim
  set and CURRENT STATE stay in `CLAUDE.md`. Section 9 of `CLAUDE.md` carries the routing table.
- **The never-delete rule applies to these archive files exactly as it applied to CLAUDE.md.**
- `tests/test_docs.py` fails the suite if `CLAUDE.md` exceeds **120,000 characters**, if an
  archive file goes missing or unreferenced, if either log's entry count drops below its
  split-time value, or if a dated log entry is appended to `CLAUDE.md` by mistake.
- The pre-split file is recoverable from the git tag `pre-claude-md-split` (commit `715096a`),
  SHA-256 `86f6ff5d4cca64b47179afaeee2fc22d826832d699d43533d9c4839b49a17775`.
- **No result, verdict, claim or number changed.** This is a reorganisation only.
**Recorded here rather than in the RESULTS LOG** because it produced no experimental metric;
the counts above are measurements of the move itself. `docs/archive/README.md` repeats them.