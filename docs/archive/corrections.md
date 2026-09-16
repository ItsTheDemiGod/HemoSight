# CORRECTIONS — HemoSight

> **Provenance.** Moved verbatim out of `CLAUDE.md` on 2026-09-17, when that file
> reached 233,820 characters and was being truncated on load. The text below is
> byte-identical to the corresponding section of `CLAUDE.md` at commit `715096a`,
> recoverable in full from the git tag `pre-claude-md-split`. **Nothing was
> summarised, condensed or deleted.** See `docs/archive/README.md`.

> **What this file is.** Every correction the project has made to its own record,
> reproduced verbatim. This is a *cross-cutting collection*: each entry below is a
> DECISION LOG entry and also stands in date order in
> `docs/archive/decision_log.md`, which remains the canonical chronological record.
> Nothing here is the only copy of anything.

> **Why the project keeps this list.** Two lessons were logged and are repeated
> across these entries: *do not record an inferred cause as a finding* (2026-09-11),
> and *a number typed into a report generator is indistinguishable from a measured
> one until someone tries to regenerate it* (2026-09-12).

---

## 1. 2026-09-11 — CORRECTION to the 2026-09-10 CPU-only entry: the machine has CUDA hardware

*Corrects: DECISION LOG 2026-09-10 "PyTorch installed CPU-only; no GPU
available", which is retained verbatim under its SUPERSEDED banner in
`docs/archive/decision_log.md`. That superseded entry is reproduced below the
correction so the pair can be read together.*

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

---

## 2. 2026-09-11 — N2's justification corrected

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

---

## 3. 2026-09-11 — CORRECTION: the raw waveform DOES contain a real signal

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

---

## 4. 2026-09-12 - CORRECTION: the Phase 6 fault-injection seeds were not reproducible

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

---

## 5. 2026-09-12 - CORRECTION: NumPy scalars reached a JSON column and 500ed the upload endpoint

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

---

## 6. 2026-09-12 — CORRECTION: the empirical signal was a constant; it is withdrawn and replaced by a measurement

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

---

## 7. 2026-09-12 — CORRECTION: the CNN baseline script omitted SITE from the demographic baseline

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

---

## Register of in-place corrections that are not standalone entries

These corrections are banners or clauses attached to the text they correct, rather
than separate log entries. They are listed so the set is enumerable; each is
retained verbatim where it stands.

| correction | where it stands verbatim |
| --- | --- |
| `*(corrected 2026-09-12; was "0.45-0.70")*` on row 3 of the FINAL STATUS table | `CLAUDE.md` section 2 |
| `**Justification (corrected 2026-09-11).**` on N2 | `CLAUDE.md` section 2 |
| `⚠️ **CORRECTED 2026-09-12 (Phase 6.5 Task 1).**` — the withdrawn 0.70 dE2000/g/dL constant | `docs/archive/decision_log.md`, entry 2026-09-11 "The failure is a signal-to-noise limit" |
| `⚠️ **SUPERSEDED 2026-09-12**` — the same constant in the results record | `docs/archive/results_log.md`, entry 2026-09-11 "Phase 3: signal-to-noise is the mechanism" |
| "The honest rate is 71.7% on MOBIUS, not 97.3%" — the percentile-only detector artefact | `docs/archive/decision_log.md`, entry 2026-09-11 "Highlight detection must be physics-based" |
| "An extraction bug WAS found and fixed along the way" — PPG harmonics counted as noise | `docs/archive/decision_log.md`, entry 2026-09-11 "The dataset's published SNR could not be reproduced" |
| `**Corrected during verification, recorded rather than hidden.**` — five Phase 8B defects | `docs/archive/decision_log.md`, entry 2026-09-13 "The visual system" |
| Zhivov 2006 journal attribution corrected to *The Ocular Surface* | `docs/archive/decision_log.md`, entry 2026-09-12 "Licences verified, constants banner narrowed" |
| The probe artefacts disclosed rather than quietly fixed (localStorage re-seeding; queue saturation) | `docs/archive/decision_log.md`, entry 2026-09-12 "INVESTIGATION: the Overview page is idle" |

A twelve-item corrections table covering the same ground from the results side is in
`reports/final_results.md`.