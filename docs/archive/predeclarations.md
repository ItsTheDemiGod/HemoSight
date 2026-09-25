*Renamed files and folders since these declarations were written are mapped in [docs/CODE_MAP.md](../CODE_MAP.md); nothing below is rewritten to match new names.*

# Pre-declarations, verbatim

**Every threshold, gate, operating-point criterion and interpretation rule this project
fixed BEFORE the experiment it governs, in one place, exactly as it was written.**

## Why these live here and not in CLAUDE.md

A pre-declaration is load-bearing while its phase is open - it is what stops a threshold
being chosen after the result is known - and it is *evidence* once the phase closes.
Evidence belongs in this directory. Keeping ten of them inline was also what pushed
CLAUDE.md from 76,000 characters back to 120,380 within a few phases of the 2026-09-17
split, against a test-enforced 120,000-character limit.

**Moving a pre-declaration does not weaken it, and cannot.** What makes a declaration a
*pre*-declaration is not which file it sits in but that it was **committed before the
run**, and git records that permanently. Phase 9E's block, for instance, is in commit
`f4a3fc0`, whose message says it pre-declares the phase, and the results landed in
`cc4767f`. The commit is the evidence; this file is the readable copy.

**The split moved text. It changed none.** Nothing here was summarised, condensed,
reworded or deleted. CLAUDE.md keeps each phase's heading, a one-line summary and a
pointer to the section below.

Governed by CLAUDE.md section 9, WORKING PROTOCOL. See the DECISION LOG entry of
2026-09-21.

## Index

| section | phase | declared | moved here |
| --- | --- | --- | --- |
| 1 | Phase 2.5 - specular (corneal highlight) rescue attempt for N1 | 2026-09-11 | 2026-09-21 |
| 2 | Phase 3 - Monte Carlo tissue simulator (N2), Task 0 gate | 2026-09-11 | 2026-09-21 |
| 3 | Phase 3.5 - ratio reformulation | 2026-09-11 | 2026-09-21 |
| 4 | Phase 4 - PPG arm, Gate A and Gate B | 2026-09-11 | 2026-09-21 |
| 5 | Phase 4.5 - deep models on raw PPG | 2026-09-11 | 2026-09-21 |
| 6 | Phase 7 - the controlled-capture hypothesis | 2026-09-12 | 2026-09-21 |
| 7 | Phase 9A - the screening reframe | 2026-09-17 | 2026-09-21 |
| 8 | Phase 9C - parameter uncertainty propagated into the gate result | 2026-09-20 | 2026-09-21 |
| 9 | Phase 9D - power analysis: what this study could have detected | 2026-09-20 | 2026-09-21 (first split to its own file, consolidated here the same day) |
| 10 | Phase 9E - the project's boundaries, stated precisely | 2026-09-21 | 2026-09-21 (first split to its own file, consolidated here the same day) |

---

## 1. Phase 2.5 - specular (corneal highlight) rescue attempt for N1

*Declared 2026-09-11, before the phase ran. Verbatim.*

**Thresholds declared BEFORE running (2026-09-11):**
- **Feasibility gate:** if fewer than **30%** of images yield a detectable AND
  unsaturated corneal highlight, STOP at Task 1 and report non-viability.
- **SUPPORTED:** specular beats grey-world on held-out-iris within-subject dE2000
  spread, paired Wilcoxon p < 0.05.
- **PARTIALLY SUPPORTED:** specular beats no-correction (p < 0.05) but not grey-world.
- **REFUTED:** specular fails to beat no-correction.

## 2. Phase 3 - Monte Carlo tissue simulator (N2), Task 0 gate

*Declared 2026-09-11, before the phase ran. Verbatim.*

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

## 3. Phase 3.5 - ratio reformulation

*Declared 2026-09-11, before the phase ran. Verbatim.*

**Thresholds declared BEFORE running (2026-09-11), in the equivalent-Hb units of the
Phase 3 gate so the comparison is direct:**
- **Equivalent residual < 1.0 g/dL** -> the illuminant cancels; proceed to Task 2.
- **1.0 to 2.0 g/dL** -> partial cancellation; MARGINAL.
- **> 2.0 g/dL** -> von Kries diagonality or region stability is failing; the
  reformulation does NOT rescue the claim. STOP, do not proceed to Task 2.

## 4. Phase 4 - PPG arm, Gate A and Gate B

*Declared 2026-09-11, before the phase ran. Verbatim.*

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

## 5. Phase 4.5 - deep models on raw PPG

*Declared 2026-09-11, before the phase ran. Verbatim.*

**Same pre-declared thresholds as Phase 4 Gate B:** <1.0 g/dL viable, 1.0-2.0 marginal,
>2.0 not viable. Same baselines: population mean, sex alone, full demographics. Same
grouped leave-subject-out splits.

⚠️ **With 252 subjects a deep model can trivially memorise.** Subject-disjoint folds are
verified explicitly, the train-test gap is reported, and **if any model beats the
demographic baseline a sex probe is run on its learned representation FIRST** — Phase 4
Task 3 showed how easily an apparent Hb model is really a sex classifier.

## 6. Phase 7 - the controlled-capture hypothesis

*Declared 2026-09-12, before the phase ran. Verbatim.*

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

## 7. Phase 9A - the screening reframe

*Declared 2026-09-17, before the phase ran. Verbatim.*

#### PRE-DECLARED, 2026-09-17, before any Phase 9A script was run

**1. WHO thresholds, and which subjects they apply to.** Every subject in both
datasets is an adult — Eyes-Defy ages 19-88, Hb-PPG ages 21-90, **no subject under
19** — so only the adult thresholds apply and no child threshold (6-59 mo 11.0;
5-11 y 11.5; 12-14 y 12.0) is used on anyone. Applied: **men ≥15 y, Hb < 13.0 g/dL;
non-pregnant women ≥15 y, Hb < 12.0 g/dL.** Resulting prevalence: Eyes-Defy
**91 of 216 (42.1%)**, Hb-PPG **18 of 252 (7.1%)**.
*Limitation, stated before running:* **pregnancy status is not recorded in either
dataset.** The non-pregnant threshold is applied to all women. A pregnant woman's
threshold is 11.0 g/dL, so any pregnant subject is over-called anaemic here. This
cannot be corrected from the available data and is carried into every result.

**2. The operating point, declared before it is computed.** For a referral triage the
costly error is a missed anaemic case, so: **the threshold with the highest
specificity subject to sensitivity ≥ 0.90.** It is chosen **on the training folds
only**, inside each CV fold, and applied to the held-out fold — nested selection, so
no operating point is ever picked after seeing the test data it is scored on. If no
training-fold threshold reaches sensitivity 0.90, the most sensitive available
threshold is used and the failure to reach the criterion is reported.

**3. What counts as clinically meaningful, declared before it is measured.** At
**matched specificity**, the model must improve sensitivity over the best demographic
baseline by **≥ 0.10 (10 percentage points)**, AND the lower bound of the 95%
subject-level bootstrap CI on the paired difference must be **> 0**.
*Justification.* At Eyes-Defy's prevalence, +0.10 sensitivity is ~9 more anaemic
subjects referred per 216 screened — about **1 per 24 people screened**. At Hb-PPG's
prevalence it is 1.8 more cases per 252, about **1 per 140 screened**. Ten points is
the smallest sensitivity gain that could plausibly change a referral policy, given
that the added cost is one photograph or one PPG capture per person screened. A point
estimate whose CI includes zero is not evidence of improvement, whatever its size.
The symmetric test is also reported: at **matched sensitivity**, a specificity gain
≥ 0.10 with CI lower bound > 0 counts equally.

**4. Screening verdict bands, declared before any number is seen.**
- **USEFUL** — sensitivity ≥ 0.90 **and** specificity ≥ 0.50 at the chosen point,
  **and** the margin in item 3 is cleared. The specificity floor is there because a
  tool that refers almost everyone has perfect sensitivity and no value.
- **MARGINAL** — meets the sensitivity and specificity floors but does not clear the
  margin over the demographic baseline, or clears it with a CI that includes zero.
- **NOT USEFUL** — fails either floor, or does not reduce the referral rate against
  referring everybody.

**5. Uncertainty.** 2,000 subject-level bootstrap resamples, seed 20260911, percentile
95% CIs. Differences between models are **paired**: both are recomputed on the same
resample. Number needed to screen = 1 / (prevalence x sensitivity); false-referral
rate = 1 − PPV; referral rate = (TP+FP)/n, reported always so "refers everyone" is
visible.

**6. Within-site and cross-site are reported separately for the imaging arm and never
pooled into one headline number.**

## 8. Phase 9C - parameter uncertainty propagated into the gate result

*Declared 2026-09-20, before the phase ran. Verbatim.*

#### PRE-DECLARED, 2026-09-20, before any Phase 9C script was run

**1. Interpretation rule.** The verdict at a residual is **ROBUST** to parameter
uncertainty if the **entire 95% interval** of the gate MAE over the parameter prior
falls on one side of the pre-declared **2.0 g/dL** threshold, and **FRAGILE** if the
interval spans it. For the studio condition the same rule is applied at the **1.0 g/dL**
VIABLE boundary as well. The rule is applied whichever way it falls; **ranges are not
adjusted after seeing results.**

**2. The propagation.** Self-consistent: for every draw of the parameter vector θ the
forward model, the inversion LUT and the truth all use θ, and the residual colour error
is applied exactly as in Phase 3 Task 0 (same perturbation generator, same Hb grid 4-18,
same 240 trials per Hb, same LUT 2-24 step 0.05). The perturbation banks are regenerated
in the original RNG order so that θ = nominal must reproduce **3.893 / 3.471 / 1.040
exactly**; that reproduction is reported first, and if it fails the run is invalid. A
second, separately labelled variant — LUT at nominal, truth at θ (the Phase 3 Task 4
mismatch question) — is reported after the main result and never pooled with it.

**3. Parameter prior, fixed before running.** Each parameter is labelled SOURCED (backed
by a downloaded file or an independent measurement) or UNSOURCED (transcribed, assumed
or fitted). Where no source exists the range is deliberately generous. The Phase 3 Task 4
tolerances (BVF ±30%, thickness scale 0.8-2.0, oxygenation benign across 0.60-1.00) are
the starting envelope and each range below is at least as wide.

| parameter | nominal (gate) | prior | status |
| --- | --- | --- | --- |
| oxygenation StO2 | 0.75 | U[0.60, 1.00] | UNSOURCED — physiological assumption (`OXYGENATION_RANGE`) |
| stromal blood volume fraction | 0.060 | U[0.01, 0.15] | UNSOURCED — Jacques 2013 soft-tissue range, transcribed (`BVF_RANGE`) |
| epithelial melanin volume fraction | 0.0 | log-U[1e-4, 5e-2] | UNSOURCED — top of `MELANIN_RANGE`; conjunctiva is a sparsely pigmented mucosa, so results are also reported conditional on ≤ 0.005 |
| melanin power-law exponent k | 3.33 (spectralLIB fit) | U[3.0, 4.0] | UNSOURCED — a fit, not a measurement; Jacques 1998 gives 3.48 |
| melanin amplitude scale at 500 nm | 1.0 | log-U[0.5, 2.0] | UNSOURCED — inter-individual amplitude variation |
| epithelium thickness | 32 µm | U[22, 46] µm | **SOURCED** — Li 2015 OCT 34 ± 5.8 µm, ±2 SD |
| stroma thickness | 200 µm | U[100, 400] µm | UNSOURCED — VERIFICATION REQUIRED banner; 0.5-2× |
| tarsal plate thickness | 800 µm | U[400, 1600] µm | UNSOURCED — VERIFICATION REQUIRED banner; 0.5-2× |
| epithelium BVF | 0.002 | U[0, 0.01] | UNSOURCED |
| tarsal plate BVF | 0.010 | U[0.002, 0.03] | UNSOURCED |
| water fraction shift (all layers) | 0 | U[−0.10, +0.10] | UNSOURCED — assumed 0.70/0.75/0.60 |
| reduced-scattering scale | 1.0 | log-U[0.5, 2.0] | SOURCED-GENERIC — spectralLIB soft tissue, not conjunctiva-specific |
| deep-layer contribution weight | 0.6 | U[0.3, 1.0] | UNSOURCED — modelling constant in `forward.layered_reflectance` |
| tissue refractive index n_rel | 1.40 | U[1.33, 1.45] | UNSOURCED — typical soft tissue |

Held fixed and out of scope, stated: the D65 illuminant and the CIE 1931 observer as
camera proxy (a capture-side limitation already logged, addressed by the measured
residuals, not a tissue constant); the haemoglobin extinction and water spectra (sourced
from downloaded files, Phase 3.5 Task 0).

**4. Sampling and sensitivity.** Sobol quasi-random Saltelli design, base N = 1024, so
the plain Monte Carlo sample is the 2,048 rows of the A and B matrices and the
first-order and total Sobol indices come from the (d + 2) × 1024 evaluations; Jansen
estimators; seed 20260911. Percentile 95% intervals. Reported for the three measured
residuals 3.935, 3.456 and 1.062 dE2000. Sensitivity is ranked by total index; if
melanin dominates, the report says so and names a measured melanin absorption curve as
the single most valuable future measurement.

**5. Task 4.** Efron 2009 and Zhivov 2006 are sought with network access. If obtained,
the thickness and BVF values are replaced with sourced ones, the priors narrowed, and
Tasks 1-3 re-run and reported side by side with the assumed-range results. If not, the
attempt is recorded and the banner stays.

## 9. Phase 9D - power analysis: what this study could have detected

*Declared 2026-09-20, before the phase ran. Verbatim.*

#### PRE-DECLARED, 2026-09-20, before any Phase 9D number was computed

**1. The quantity computed is the MINIMUM DETECTABLE EFFECT (MDE), not observed power.**
For a two-sided test at alpha = 0.05 and power 1 − beta,

    MDE = (z_0.975 + z_{1−beta}) x SE(difference)      multiplier 2.802 at 80%, 3.242 at 90%

**Retrospective / observed / post-hoc power — recomputing power at the effect size that was
actually observed — is a known statistical error and is NOT computed here.** Observed power is
a deterministic function of the observed p-value and so adds no information; it is also
guaranteed to look low whenever a result was null, which would manufacture a false excuse for
every negative finding in this project. The question asked is what effect size **the design**
could detect given its sample size and the variance structure of its own measurements. The
distinction is stated in the report so a reader can see which analysis was run.
*Stated limitation of the MDE approach itself:* SE is estimated from this sample, so it carries
its own sampling uncertainty, and for the screening metrics SE depends mildly on the true effect
size. Neither is corrected for; both are reported.

**2. One comparison per arm, and only the comparison that ACTUALLY DECIDED that arm.** No power
is computed for a comparison the project never made.

| arm | n | deciding comparison | SE method |
| --- | --- | --- | --- |
| Imaging regression | 216 Hb-labelled Eyes-Defy subjects | image-CNN MAE vs **site + sex + age** (1.273 g/dL) | paired, per-subject absolute-error differences (exact SE = sd(d)/sqrt(n)); bootstrap reported beside it |
| Imaging screening | 216, 91 anaemic | specificity gain at matched sensitivity, and AUROC difference, vs site + sex + age | **paired subject-level bootstrap**, the identical 2,000-resample scheme Phase 9A used (`screening.paired_difference_ci` / `bootstrap_ci`, seed 20260911) |
| PPG | 252, venous HemoCue | deep-model MAE vs **sex alone** (0.831 g/dL); AUROC vs best demographic baseline | paired per-subject absolute-error differences; paired bootstrap for AUROC |
| Imaging cross-site | **per direction, reported separately** — italy→india and india→italy | same as the within-site screening comparison, per direction | paired subject-level bootstrap within each direction |

Predictions are correlated across models on the same subjects, so every difference is **paired**;
an unpaired SE would be wider than the evidence warrants and would inflate every MDE. Where a
statistic is a non-smooth function of the data (sensitivity and specificity at a nested operating
point) the bootstrap SD is used rather than a closed form, because no closed form applies.

**3. The clinical yardstick each MDE is judged against is one the project ALREADY declared. No
new threshold is invented here.**
- **Screening:** the **0.10 (10 percentage point)** clinically meaningful margin pre-declared in
  Phase 9A, with its justification (at Eyes-Defy prevalence, ~9 more anaemic subjects referred
  per 216 screened, about 1 per 24 people).
- **MAE:** the Phase 3 / Phase 7 band structure — **VIABLE < 1.0, MARGINAL 1.0-2.0, NOT
  RECOVERABLE > 2.0 g/dL** — plus whether the detectable improvement could move a **WHO severity
  boundary** (severe < 7.0, moderate 7.0-9.9, mild 10.0-10.9 men / 10.0-11.9 women). A band is
  1-3 g/dL wide, which is the scale an MAE improvement must reach to change a clinical decision.

**4. The verdict per arm, declared before the numbers.** Exactly one of:
- **ADEQUATELY POWERED** — the MDE at 80% power is **at or below** the arm's clinical yardstick,
  so the design could have detected any effect large enough to matter clinically, and the
  negative result is informative evidence of absence.
- **UNDERPOWERED** — the MDE at 80% power is **above** the yardstick, so only effects larger
  than those that would matter clinically were detectable, and the negative result is weak
  evidence of absence and must be reported as such.

Applied per arm, whichever way it falls, **including if the project's most load-bearing finding
(the cross-site collapse) turns out to rest on its least powered comparison.** The cross-site
directions are reported separately and prominently, never pooled, because each uses a fraction of
the cohort.

## 10. Phase 9E - the project's boundaries, stated precisely

*Declared 2026-09-21, before the phase ran. Verbatim.*

#### PRE-DECLARED, 2026-09-21, before any Phase 9E script was run

**1. The guided-capture gap is a named boundary, not a gap to be closed.** It cannot be
closed without collecting data, which section 3 forbids permanently. What is produced is
a statement of the gap, a specification of the evidence that would settle it, and an
**interpolation** between the two measured residuals that bracket it (1.981 dE2000,
MOBIUS one phone + one lighting cell, gaze varying; 1.062, SBVPI studio). The
interpolation is labelled as such everywhere it appears and **is never called a
measurement**. Its headline point is the geometric mean of the two bracketing residuals,
**1.450 dE2000**, chosen before the gate was run at it; the whole bracketing interval is
reported beside it, and the Phase 9C prior is propagated at the headline point so the
interpolated number carries an interval from the start. Fresh perturbation banks are
drawn for the interpolation grid (no original RNG order exists at a residual nobody
measured); the two bracketing anchors are re-run on those same fresh banks and reported
beside their recorded values, so the bank draw is visibly not doing the work.

**2. Required n is computed from the SE scaling, and the scaling is MEASURED, not
assumed.** For a target MDE of the pre-declared **0.10** margin at 80% and 90% power,
required group size = observed group size × (observed MDE / 0.10)². That step assumes
SE ∝ 1/√n at fixed per-subject variance. **The assumption is checked by subsampling this
project's own data** at several fractions, re-running the whole nested-operating-point
and paired-bootstrap pipeline at each, and fitting log SE against log n: the fitted slope
is reported, and if it departs materially from −0.5 the required-n figures are reported
as approximate with the measured slope stated. Phase 9D's MDEs are asserted to reproduce
before any new number is computed, exactly as Phase 9D asserted Phase 9A's.

**3. Required n is reported by the group that carries the metric, not as a total alone.**
Specificity is a proportion over **non-anaemic** subjects and sensitivity over **anaemic**
subjects, so each required n is stated first as a **minimum count in that group**, then
converted to a total at the observed prevalence and at a balanced 50%. Phase 9D
established that italy→india's 14% power is a composition problem — 68 of 95 test
subjects anaemic, leaving specificity on 27 people — so the composition figure is the
one a study designer acts on and is reported first.

**4. The language pass is calibration in both directions, and may not weaken a supported
conclusion.** Three specific overstatements are corrected wherever they appear in
CLAUDE.md, the reports, `hemosight.audit.content` and the case-study endpoint:
*(i)* a cross-site **rate** quoted without its interval — observed **counts** are
preferred where both exist, and a CI is attached wherever a rate is quoted; *(ii)* an
**underpowered null stated as absence** — restated as bounded ("no gain of 0.10 or larger
was detected; the study could have detected 0.116"); *(iii)* the **studio result quoted
without its Phase 9C interval**. **The two regression arms are ADEQUATELY POWERED and
their negative results keep their full strength**; hedging them would be the same error in
the opposite direction and is forbidden here. **No verdict changes in this phase** — the
cross-site collapse was directly observed and a power analysis constrains null
conclusions, not observed ones; only the precision claimed for its magnitude changes.
