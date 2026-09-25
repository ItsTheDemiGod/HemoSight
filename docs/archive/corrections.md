*Renamed files and folders since these entries were written are mapped in [docs/CODE_MAP.md](../CODE_MAP.md); nothing below is rewritten to match new names.*

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
| `reports/final_results.md` §6 read "5 applicable sources" while `literature_counts.json` had 6 since 2026-09-13 — a stale generated report, regenerated 2026-09-20 with no other line changed | `docs/archive/results_log.md`, entry 2026-09-20 "one item on the record is corrected in passing" |
| The Phase 3 gate point estimate appearing without its Phase 9C interval — corrected in place in CLAUDE.md, `final_results.md`, `phase3_simulation.md`, `phase7.md` and the front end; the point estimate is retained in every case | `reports/phase9c_uncertainty.md` §7; `docs/archive/decision_log.md`, 2026-09-20 |

A twelve-item corrections table covering the same ground from the results side is in
`reports/final_results.md`.

## 8. "Moves no clinical threshold" (Phase 7, 2026-09-12) — corrected 2026-09-17 by Phase 9A

*Corrects: the Phase 7 DECISION LOG entry "The controlled-capture hypothesis was tested; outcome B" (2026-09-12), retained verbatim in `docs/archive/decision_log.md`. The full correction entry is in that file under PHASE 9A DECISIONS and is reproduced below.*

**Original text, preserved verbatim.** *"(2) from controlled capture it reaches the MARGINAL band only - screening bands at best - does not beat site + sex + age, and moves no clinical threshold."*

**What was wrong.** Only the final clause. The project evaluated its imaging arm on mean absolute error in g/dL and concluded no clinical threshold moved. Evaluated as the referral decision the product actually makes — at an operating point pre-declared and committed before the run, and chosen on training folds only — a threshold does move: at matched sensitivity (~0.90) the image reduces the referral rate from 0.634 to 0.519 against site+sex+age, a specificity gain of **+0.192, CI [+0.114,+0.276]** for the mean-CIELAB model and **+0.096, CI [+0.017,+0.179]** for the CNN. AUROC over the same baseline: **+0.057** and **+0.059**, both with CIs excluding zero.

**What did not change, and why.** The arm is still not deployable, but the binding reason is now the cross-site collapse — `italy_to_india` **sensitivity 0.397**, flagging 27 of 68 anaemic subjects; `india_to_italy` **specificity 0.418** — and no longer the absence of a within-site effect. Two boundary misses are reported as unresolved rather than decisive: the 0.90 sensitivity floor by **0.010** and the CNN's margin by **0.004**, both inside the bootstrap noise at 91 anaemic subjects.

**Prevention.** The phrase "moves no clinical threshold" is retired. `reports/phase9a_screening_metrics.md` leads with the model-versus-baseline screening comparison, and `tests/test_phase9a.py` fails if the report states an AUROC without a baseline beside it or if the retired phrase reappears in the claim set.

**Lesson.** The project criticised the literature for reporting a score without a cheap baseline. Its own mirror-image error was reporting a *baseline comparison* on a metric the product does not use. Both are failures to evaluate the deployed decision; this one took a reframe rather than a new model to expose.

---

## 9. Phase 7's PPG "sensitivity 0.00" — qualified 2026-09-17, not withdrawn

*The figure is correct as computed and is retained. See the entry of 2026-09-17 in `docs/archive/decision_log.md`.*

The 0.000 comes from a **plug-in** rule — refer if the *predicted* haemoglobin is below the diagnostic threshold. A regression model shrinks toward the mean, so that rule is systematically insensitive and 0.000 measures the rule as much as the model: at an operating point chosen for screening the same PPG models reach **sensitivity 0.889**. The qualification travels with the number from here on. It does not rescue the arm — at that point specificity is **0.098**, the referral rate **90.1%**, and NNS **15.8 against 14.0 for referring everybody**.

---

## 10. Efron 2009's thicknesses (Phase 3, banner since 2026-09-11) — source obtained 2026-09-20 and does NOT contain them

*Full entry: `docs/archive/decision_log.md`, 2026-09-20 "CORRECTION: Efron 2009 was obtained and
does NOT contain the thicknesses attributed to it". The banner it corrects stands in
`src/hemosight/simulation/constants.py`.*

**What was recorded (2026-09-12, Phase 6.5).** "Re-checked 2026-09-12 (network available): the
abstracts of [5] and [6] contain NO numeric thicknesses and both full texts are subscription-only,
so the values attributed to them **could not be verified against the source**."

**What is now known.** The Efron 2009 study **was** obtained — not the paywalled paper but the
same study as a chapter of the open-access QUT thesis it came from (Al Dossari M., QUT ePrints
18316; same 11 participants, same instrument, matching abstract), read in full. It reports **no
palpebral thickness in micrometres for any layer**: the epithelium "appears to be only two or
three cell-layers deep", the stroma is "thin", the tarsal plate "dark and amorphous". Its one
thickness figure, **32.9 +/- 1.1 um, is BULBAR epithelium** — a different tissue. It states that
"it is therefore not possible to determine the overall thickness of the conjunctiva using this (or
any other) technique with any degree of certainty". **No blood volume fraction appears in it.**

**The correction.** "Could not be verified" understated it. For [5] the source **was** read and
**does not contain** the stromal thickness (200 um), the tarsal-plate thickness (800 um) or any
blood volume fraction. Zhivov 2006 [6] remains unobtainable (OpenAlex `oa_status: closed`).
The banner is **kept and strengthened**, not lifted; the citation is **not removed**, because [5]
is still the source of the qualitative layer structure. The 32 um epithelial thickness keeps its
lifted status on Li et al. 2015 alone (OCT, 34.0 +/- 5.8 um, palpebral).

**No verdict changes.** Phase 9C ranks stroma thickness 7th and tarsal-plate thickness 14th of 14
by Sobol total index, so sourcing them would have moved the gate interval very little. What
dominates is unsourced in a different way: a modelling constant (the 0.6 deep-layer weight) and
the epithelial blood volume fraction.

## 11. "Moves no clinical threshold" again — the §8 correction had never reached `reports/phase7.md` (found and fixed 2026-09-21, Phase 9E)

**This entry corrects the application of correction §8, not its content.** §8 (2026-09-17)
records that Phase 9A retired the clause **"and moves no clinical threshold"** from the
Phase 7 DECISION LOG entry of 2026-09-12. That retirement was written into
`docs/archive/corrections.md`, into `docs/archive/decision_log.md`, into CLAUDE.md and
into `reports/phase9a_screening_metrics.md`.

**It was never applied to `scripts/phase7_report.py`.** For four days `reports/phase7.md`
continued to assert the retired clause as a live conclusion, in the Task 1 verdict
paragraph that restates the imaging refutation in two parts:

> **The refutation is restated in two parts:** from uncontrolled photographs the inversion
> is NOT RECOVERABLE; from controlled capture it reaches screening bands at best, does not
> beat site + sex + age, ~~and moves no clinical threshold~~.

A second instance stood in `reports/statistical_vs_clinical.md`: *"it loses to or barely
matches the cheapest available baseline on the same folds, and it moves no screening
threshold."*

**How it was caught.** The Phase 9E Part C language pass (2026-09-21), which audited every
reader-facing statement of a result rather than only the statements a phase had flagged.

**What it now says.** The clause is removed from the generator and both reports were
regenerated. In its place the Phase 7 verdict states what stood there, that Phase 9A
retired it, and what replaces it: within site the image cuts the referral rate from 0.634
to 0.519 at the same ~0.90 detection rate — a margin the mean-CIELAB model clears with a
CI excluding zero — and what controlled capture does **not** rescue is transfer between
sites. `statistical_vs_clinical.md` now says the threshold such a model moves, if it moves
one at all, does not survive a change of site.

**Enforced from here on.**
`tests/test_phase9e.py::test_the_retired_phase9a_phrase_is_not_asserted_in_the_phase7_report`
fails the suite if the phrase reappears in that report outside a sentence that retires it.

**The generalisable lesson, recorded because this will happen again.** A correction is not
applied when it is logged; it is applied when **every generated artefact that carried the
claim has been regenerated**. This project generates its reports from scripts precisely so
that *numbers* cannot drift from the evidence — but **prose inside a generator drifts
exactly as easily as prose inside a document**, and nothing was checking it. Each of the
ten corrections above should be read with the same question attached: which generated
files carried that claim, and were they regenerated?

**No verdict changes.** The Phase 7 outcome is still B; the imaging arm is still CLOSED,
FINAL; §8 itself is unchanged and stands.

## 12. The italy→india required-n figure was reported as one number where there are two (reporting corrected 2026-09-21, Phase 9F)

**Nothing here is numerically wrong, and the headline figure does not change.** This is a
correction to how a figure was *presented*, recorded in this file because the presentation
made a result look better supported than it is — which is the failure mode this file
exists to catch.

**What was on the record.** Phase 9E (2026-09-21) reported the cross-site `italy_to_india`
requirement as **266 non-anaemic subjects** at 80% power, with the measured-slope
alternative of **778** given once, in a bullet list beneath the table. CLAUDE.md,
`reports/final_results.md` and `reports/phase9d_power.md` carried **266 alone**.

**Why that is not good enough.** Three facts hold at once:

1. The two candidate answers differ by **2.9×** — 266 against 778 non-anaemic subjects,
   or test sites of roughly 936 against 2,736 at that direction's prevalence.
2. The rule that chose between them — an **R² floor of 0.50** on the subsample scaling
   fit, below which the 1/√n reference replaces the measured slope — was **added
   mid-run**, after the subsampling had been done. Phase 9E's pre-declaration
   (`predeclarations.md` §10) anticipated a slope *departing* from 0.5, not the fit
   *failing*.
3. The rule **happened to select the more optimistic figure**, here and on the only other
   comparison it touched (PPG AUROC: 131 chosen over 202, R² 0.23).

Each is defensible alone. Together they mean a reader who sees only **266** has been shown
the most favourable of two numbers, chosen by a rule invented after the fact, without
being told. The rule itself is sound — it keys on R² and never on the size of the answer,
a test asserts the headline tracks R² and that both bases stay on the record, and the
deviation was logged — but soundness of the rule is not the same as adequacy of the
reporting.

**What changed.** Both figures now appear **in the same cell or the same sentence**
wherever the requirement appears — `reports/phase9e_boundaries.md` (required-n table,
composition table, headline box, consolidated study specification, and a new boxed
side-by-side section giving the rule, the R² that triggered it, and when it was fixed),
`reports/final_results.md`, `reports/phase9d_power.md` and CLAUDE.md. The same treatment
was applied to the PPG AUROC comparison. A recommendation was added and kept separate
from the rule-derived number: **size against the larger figure unless the scaling can be
measured on your own pilot.**

**What did NOT change.** The headline is still **266**, by the stated rule. Making 778 the
headline because it is more conservative would be selection by size — exactly what the R²
rule exists to prevent — and would be the same error in the opposite direction. No MDE, no
power figure, no verdict and no other recorded number moved.

**The generalisable lesson.** A decision rule fixed after the data is seen is not
neutralised by logging it. It has to be **visible at the point of use**, with its trigger
value and its timing, next to the number it produced — because the reader who needs it
most is the one reading the number, not the one reading the log.
