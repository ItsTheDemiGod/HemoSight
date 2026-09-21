# CLAUDE.md — HemoSight

**This document governs all work in this repository.** It is the source of truth for
scope, claims, constraints, and sequencing. Read it fully before starting any task.
If a request conflicts with this document, say so before acting.

**The evidentiary record — every DECISION LOG entry, every RESULTS LOG entry, every
superseded claim and every correction — lives in `docs/archive/`.** See THE ARCHIVE
below. Nothing was summarised away in moving it.

---

## CURRENT STATE

*Updated 2026-09-20. This section is the one-screen answer to "where is the
project?". The evidence behind every statement here is in `docs/archive/`.*

**Active phase: none. Every phase in section 6 is closed. What remains is the
write-up.**

| | |
| --- | --- |
| Phases complete | 0, 1, 1.5, 2, 2.5, 3 (closed at gate), 3.5 (closed at gate), 4, 4.5, 5, 6, 6.5, 7, 8A, 8B, 9A, 9B, 9C, 9D |
| Open plan items | **0** — every unticked box is classified 🔴 SUPERSEDED or ⛔ BLOCKED, with its gate or blocker cited inline |
| Imaging arm | 🔴 **CLOSED, FINAL** — four representations refuted, each with a measured mechanism. **Phase 9A: as a screening task it beats site+sex+age within site (+0.192 specificity at matched sensitivity, CI excludes zero) but collapses cross-site (sensitivity 0.397). Not deployable, for the cross-site reason** |
| PPG arm | 🔴 **NOT VIABLE** — negative R²; sex alone beats it by 30%. **Phase 9A confirms as a screening task**: AUROC diff vs demographics −0.000 (CI [−0.195,+0.189]); NNS 15.8 vs 14.0 for referring everybody |
| Conventional CNN baseline (§3 hard constraint) | ✅ built, Phase 6.5 — MAE 1.301, MARGINAL; site + sex + age alone 1.273 |
| Shipped software | **HemoSight Audit** — the methodological audit harness, `src/hemosight/audit/` + `app/` |
| The benchmark nothing beat | **sex alone, MAE 0.831 g/dL** (PPG). On the imaging screening task the benchmark to beat is **site + sex + age**, AUROC 0.816 |
| The one positive claim | raw-PPG spectrogram CNN, z = −4.96, empirical p ≤ 0.0041 (a **floor**, not a measurement) — and clinically useless: ~0.05 g/dL better than a constant |
| Gate result, with uncertainty (Phase 9C) | **median 4.67 g/dL, 95% [2.37, 8.02]** at the 3.935 dE2000 residual over a declared prior on the 14 fixed tissue parameters — point estimate 3.893 retained. 99.5% of the prior is > 2.0, and the whole interval is, so the imaging refutation is **ROBUST to parameter uncertainty**. The **studio** number (1.040) is **FRAGILE**: 95% [0.60, 4.90], spanning all three bands (`reports/phase9c_uncertainty.md`) |

| Statistical power (Phase 9D) | MDE at 80% power on each arm's **deciding** comparison. **ADEQUATELY POWERED:** imaging regression (0.18 g/dL vs a 1.0 g/dL clinical yardstick) and PPG regression (0.14 g/dL) — both negative results are informative. **UNDERPOWERED:** imaging screening within site (0.116 vs the 0.10 margin, 67% power), **imaging cross-site (italy→india 0.314 — 3.1× the margin, 14% power, specificity on 27 non-anaemic subjects)** and PPG screening AUROC (0.27 on 18 anaemic subjects). Retrospective power deliberately NOT computed (`reports/phase9d_power.md`) |

| Literature audit (Phase 9B) | **7 full texts read, 12 identified**; a convenience sample, not a review. Demographic baseline reported by **0 of 7**; per-site results by **0 of the 3 multi-site papers**; deduplication mentioned by 0 of 7. **No paper is recorded as failing a check.** The claim "a literature that frequently omits it" was **narrowed** to a statement about these seven (`reports/literature_gap.md` §9B) |

**What is outstanding.** The write-up, and nothing else. Section 6 records no open
work. The project's contribution is the body of negative results and their
mechanisms; **nothing further should be built.**

**One thing the write-up must not repeat.** Phase 9A retired the phrase "moves no
clinical threshold" (`docs/archive/corrections.md` §8). Within site the image does
move a referral threshold; what fails is transfer to another site. If any future
imaging work is ever started, it should begin from **three mean palpebral CIELAB
numbers**, which match the CNN on AUROC and beat it on specificity — not from a CNN.

**Before adding anything to this file, read the WORKING PROTOCOL (section 9).** New
decisions, results and corrections go to `docs/archive/`, not here.

---

## THE ARCHIVE

**The project's evidentiary record lives in `docs/archive/`.** It was moved there on
2026-09-17, when this file reached 233,820 characters and was being truncated on
load — which meant sessions were silently reading a partial record. The split moved
text; it changed none. The pre-split file is recoverable from the git tag
`pre-claude-md-split` (commit `715096a`).

| file | what is in it |
| --- | --- |
| `docs/archive/decision_log.md` | **Section 7, DECISION LOG** — the 81 entries that stood in this file, 2026-09-10 to 2026-09-13, in date order, verbatim, plus everything appended since. Every design decision, deviation and changed assumption. |
| `docs/archive/results_log.md` | **Section 8, RESULTS LOG** — the 48 entries that stood in this file, in date order, verbatim, plus everything appended since. Every metric produced, including failures and negative results. |
| `docs/archive/superseded_claims.md` | Every original claim wording retained under a refuted or superseded banner (N1 headline, N1 pre-restructure, N2 justification, N5 method), plus a register of the 10 other superseded banners and where each is retained. |
| `docs/archive/corrections.md` | All 7 standalone correction entries verbatim, each with the entry it corrects, plus a register of 9 in-place correction banners. |
| `docs/archive/README.md` | The index, the split's verification numbers, and the append rules. |

`superseded_claims.md` and `corrections.md` are **cross-cutting collections**: every
block in them also stands in its original place, in this file's section 2 or in the
decision log. Neither file is the only copy of anything.

Section 7 and section 8 below are stubs that point into the archive. The section
numbering is unchanged, so existing references elsewhere in the repository —
`reports/*.md` cite "section 8 RESULTS LOG" and "DECISION LOG 2026-09-11" — still
resolve.

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
back to a physical quantity, it needs justification in the DECISION LOG (`docs/archive/decision_log.md`).

---

## 2. THE NOVELTY CLAIMS

These drive every design decision.

> **Revised 2026-09-11 (Phase 1.5).** N1 was split into three sub-claims, N2's
> justification was corrected, N5 was rebuilt without SCIN, and N6 was scoped to what
> the data actually supports. The **original wording of every changed claim is preserved
> verbatim in the DECISION LOG (`docs/archive/decision_log.md`)** — nothing was deleted. Each revision cites the Phase 1
> finding that forced it.

### CLAIM HIERARCHY (restructured 2026-09-11 after Phase 2.5 refuted N1)

| rank | claim | status |
| --- | --- | --- |
| ~~**CO-PRIMARY (imaging arm)**~~ | N3 + N4 from photographs | 🔴 **CLOSED, FINAL (Phase 3.5)** — four approaches refuted, each with a mechanism. **Phase 9A (screening reframe) WEAKENED this within site and CONFIRMED it cross-site**: the image does move a referral threshold within site; it collapses across sites |
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
> | 3 | Imaging | Absolute colorimetric Hb inversion | 3 | **NOT RECOVERABLE** | signal 0.45 (sim) / **0.84** (measured, CI 0.57-1.17) vs 3.9 dE2000 noise = 4.7x *(corrected 2026-09-12; was "0.45-0.70")*; gate MAE **3.893 g/dL, 95% [2.37, 8.02]** over the parameter prior — **ROBUST** (Phase 9C) |
> | 4 | Imaging | Illuminant-free within-image ratio | 3.5 | **REFUTED** | reference within/between = 1.447 |
> | 5 | PPG | AC/DC + ratio-of-ratios features | 4 | **NOT VIABLE** | R² **-0.025**; permutation **p=0.978** |
> | 6 | PPG | Raw waveform, 3 deep architectures | 4.5 | **NOT VIABLE** | best MAE 1.113; **sex alone 0.831** |
> | 7 | Imaging | **Conventional CNN baseline** (ResNet-18, Eyes-Defy, the §3 comparison arm) | 6.5 | **MARGINAL** | MAE 1.301; site+sex+age alone 1.273; image adds +0.08; cross-site italy_to_india 1.96, india_to_italy 1.99 |
> | 8 | Imaging | **Controlled capture** (studio residual 1.06 dE2000 vs 3.94 uncontrolled) | 7 | **MARGINAL**, and **FRAGILE** under parameter uncertainty (Phase 9C) | gate MAE 1.04 g/dL at the measured studio residual, **95% [0.60, 4.90] over the parameter prior — spanning VIABLE, MARGINAL and NOT RECOVERABLE**; VIABLE needs < 0.99; Eyes-Defy (fixed LED) colour model 1.34 - refutation restated in two parts |
> | 9 | Both | **The SCREENING reframe** — the same models re-scored as a referral decision, not a g/dL estimate | 9A | **imaging WEAKENED within site, CONFIRMED cross-site; PPG CONFIRMED** | within site the image beats site+sex+age by **+0.192 specificity at matched sensitivity, CI [+0.114,+0.276]** (mean-CIELAB) — margin cleared; cross-site **sensitivity 0.397**, flagging 27 of 68 anaemic. PPG: AUROC diff **−0.000, CI [−0.195,+0.189]**, NNS **15.8 vs 14.0 for referring everybody** |
>
> ### 🔴 One recorded claim did NOT survive the reframe (Phase 9A, 2026-09-17)
>
> Phase 7 wrote that controlled capture "does not beat site + sex + age, and **moves
> no clinical threshold**". The first clause stands on MAE. **The second is
> contradicted and is corrected**: evaluated as the referral decision the product
> actually makes, at an operating point pre-declared before the run, the image cuts
> the referral rate from 0.634 to 0.519 at the same ~0.90 detection rate. The phrase
> is retired. **The arm is still not deployable — but the binding reason is now the
> cross-site collapse, not the absence of a within-site effect.** "CLOSED, FINAL" for
> the imaging arm remains a decision not to build further; it is **not** a claim that
> the image carries no decision-relevant information, because it demonstrably does
> within site. See `docs/archive/corrections.md` §8.
>
> ### 🟢 Phase 9C (2026-09-20): the gate result now carries an interval, and it survives
>
> The number that closed the imaging arm was a point estimate from a forward model whose oxygenation, blood volume fractions, melanin and layer thicknesses were **fixed and known**, 13 of 14 of them unsourced. Propagated over a deliberately generous declared prior: at the 3.935 dE2000 residual **median 4.67 g/dL, 95% [2.37, 8.02]**, with the point estimate 3.893 at percentile 32 and **99.5% of the prior above the 2.0 threshold**. The entire interval is above 2.0, so by the rule declared before running, **the refutation is ROBUST to parameter uncertainty** — and the most favourable single draw in 2,048 still lands at 1.75 g/dL, MARGINAL, never VIABLE.
>
> **One recorded number is weakened: the studio condition.** Phase 7's 1.040 g/dL MARGINAL becomes **median 1.52, 95% [0.60, 4.90]** — 27.1% of the prior VIABLE, 35.9% MARGINAL, 37.0% NOT RECOVERABLE. **Its band is a property of the nominal parameter choice as much as of the capture condition, and it must never again be quoted as 1.04 alone.**
>
> **The sensitivity ranking did not confirm the expected story.** Phase 3 called melanin the model's most consequential assumption; in the self-consistent setting it ranks **3rd** at the gate residual (behind the **deep-layer contribution weight**, an uncited modelling constant, and the epithelial blood volume fraction) and **1st** at the studio residual. Melanin's +9.6 g/dL result stands but belongs to the *mismatch* setting, reported separately. A measured melanin curve is the most valuable future *spectroscopic* measurement; at the uncontrolled residual two unsourced structural quantities matter as much, and one of them is not a tissue property at all.
>
> ### 🟡 Phase 9D (2026-09-20): what these negative results could have detected
>
> *"We found no effect"* is weaker than *"we found no effect and could have detected one of size Y"*. The minimum detectable effect at 80% power, on the comparison that actually decided each arm: **imaging regression 0.18 g/dL** of MAE and **PPG regression 0.14 g/dL**, both against a 1.0 g/dL clinical yardstick (the narrowest WHO band) — **ADEQUATELY POWERED**, so those negative results are informative evidence of absence, and the effects too small to detect are also far too small to matter. **Imaging screening within site is marginally UNDERPOWERED** (0.116 against the 0.10 pre-declared margin, 67% power at the margin), though the effect it did find (+0.192 specificity) was comfortably detectable.
>
> **The uncomfortable finding, reported because it is true: the project's most load-bearing result is its least powered comparison.** The cross-site collapse is what turns a within-site success into a non-deployable verdict, and per direction the MDE is **0.314 specificity for italy→india (3.1× the margin, 14% power — specificity is estimated on 27 non-anaemic subjects) and 0.165 for india→italy (40% power)**. The cross-site *direction* was directly observed (sensitivity 0.397, 27 of 68 anaemic flagged) and a power analysis does not weaken an observed collapse — but **the magnitude of the cross-site penalty is poorly pinned down and must not be quoted as precise.** Likewise the PPG AUROC comparison (MDE 0.27 on 18 anaemic subjects) is uninformative alone; that arm's verdict rests on its MAE and NNS numbers, which are well powered.
>
> **Retrospective / observed power was deliberately not computed** — it is a deterministic function of the observed p-value and would hand every negative result here a built-in excuse. `hemosight.evaluation.power` contains no such function and a test enforces that. **No recorded verdict changes.** See `reports/phase9d_power.md`.
>
> **The strongest within-site screening model is not the CNN**: three mean palpebral
> CIELAB numbers plus a ridge match it on AUROC (0.874 vs 0.875) and beat it on
> specificity at matched sensitivity (0.752 vs 0.656).
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
> alone is a contribution to ~~a literature that frequently omits it~~ *(wording
> **narrowed 2026-09-20**, Phase 9B: none of the **seven** anaemia-estimation papers whose
> full text this project read reports a demographics-only baseline — a statement about
> those seven, from a convenience sample, not about the field; original wording kept in
> `docs/archive/superseded_claims.md` §6)*.
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
> `reports/phase2_5_specular.md` and the DECISION LOG (`docs/archive/decision_log.md`).
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
  which is BINARY-LABEL-ONLY (see N2's justification and the DECISION LOG (`docs/archive/decision_log.md`)). No fused,
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
- Negative results are recorded in the RESULTS LOG (`docs/archive/results_log.md`) with the same weight as positive ones.

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
DECISION LOG (`docs/archive/decision_log.md`), 2026-09-11).

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
  overlap verdict above and the DECISION LOG (`docs/archive/decision_log.md`).
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
> | 3 Simulator (N2) | 🔴 CLOSED AT GATE | Task 0: 3.893 g/dL vs >2.0, 95% [2.37, 8.02] (Phase 9C) | 0 (empirical signal now measured, Phase 6.5) |
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
> | 9A Screening reframe | ✅ COMPLETE — imaging **WEAKENED** within site, **CONFIRMED** cross-site; PPG **CONFIRMED** | — | 0 (one recorded claim corrected) |
> | 9B Literature audit widened | ✅ COMPLETE — 7 full texts, 6 criteria; one claim **NARROWED** | — | 0 |
> | 9C Parameter uncertainty | ✅ COMPLETE — imaging refutation **ROBUST**; the studio number **FRAGILE**; one banner kept and strengthened | — | 0 |
> | 9D Power analysis | ✅ COMPLETE — 2 arms **ADEQUATELY POWERED**, 3 comparisons **UNDERPOWERED**; the most load-bearing finding is the least powered | — | 0 |
> | 6 (orig) Conformal (N4) | 🔴 SUPERSEDED | no estimator | 0 |
> | 7 Fairness (N5) | 🔴 SUPERSEDED | no estimator; mechanism measured in Phase 3 Task 4 | 0 |
> | 8 Fusion (N6) | 🔴 SUPERSEDED | no g/dL estimate from any modality | 0 (2 items found done, ticked) |
> | 9 Web app | 🔴 SUPERSEDED | replaced by Phase 6 audit app | 0 (2 scaffold items ticked, with caveat) |
> | 10 Flutter | 🔴 SUPERSEDED | no estimator | 0 |
>
> **Open work in the whole plan: none (Phase 9D, 2026-09-20).** What remains is the write-up.
>
> ⚠️ **The write-up must carry the Phase 9A correction**: the imaging arm's refutation is
> about **cross-site transfer**, not about the absence of a within-site screening effect.
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
- [x] Define and freeze patient-level, site-aware train/calibration/test splits; write them to `data/interim/splits/` *(path amended from `data/processed/splits/`; see DECISION LOG (`docs/archive/decision_log.md`) 2026-09-11)*
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
- [x] Apply the estimator to the conjunctiva datasets and inspect stability within and across sites *(scope amended: the Ghana conjunctiva pool has no sclera (Phase 1.5), so this ran on Eyes-Defy-Anemia only — see DECISION LOG (`docs/archive/decision_log.md`) 2026-09-11)* *(⚠️ reduced artefact RESOLVED 2026-09-12: per-image illuminant estimates now stored by `scripts/phase6_5_eyes_defy_illuminant.py`; within-subject stability recorded as not measurable, one image per subject)*
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
- [ ] 🔴 SUPERSEDED — Task 1: layered conjunctival optical model with EVERY constant cited in one documented module *(PARTIAL: constants module built and cited; full layered MC NOT built — gate failed, see DECISION LOG (`docs/archive/decision_log.md`) 2026-09-11)* *(gate: Phase 3 Task 0, 3.893 g/dL at the measured 3.935 dE2000 residual vs >2.0 NOT RECOVERABLE)*
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
- [x] Collect or fit camera spectral sensitivity curves and illuminant SPDs; project spectra to synthetic RGB *(ticked 2026-09-12 audit: REDUCED — camspec (28 cameras, 400-720 nm) on disk and parsed; projection in `forward.py` is via D65 + CIE 1931 observer as camera proxy; only 2 of 6 nus8 cameras have measured SSFs (DECISION LOG (`docs/archive/decision_log.md`) 2026-09-11))*
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
> (DECISION LOG (`docs/archive/decision_log.md`) 2026-09-11): Phase 3 Task 0 gate 3.893 g/dL and Phase 3.5 Task 1 ratio
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
purposes only; the original is retained verbatim below.** See the DECISION LOG (`docs/archive/decision_log.md`),
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
- [ ] ⛔ BLOCKED — Task 3: read `/mnt/skills/public/frontend-design/SKILL.md` before writing components *(NOT DONE - the file does not exist on this machine; see the DECISION LOG (`docs/archive/decision_log.md`), 2026-09-12)* *(blocker: the path is a Linux mount from another environment and has no source here; the components have since been written, built and linted, so the step can no longer precede them. CLOSED AS NOT APPLICABLE — not ticked because it was not done)*
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
- [x] Task 1: restate the imaging refutation as the outcome dictates; log it *(ticked 2026-09-12: outcome B - partial - controlled capture reaches MARGINAL only; see the DECISION LOG (`docs/archive/decision_log.md`))*
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


### Phase 9A: The screening reframe — re-evaluating both arms as a TRIAGE task (2026-09-17)

**Why this phase exists.** Every gate in this project was built around mean absolute
error in g/dL. But the product a screening tool delivers is a **binary referral
decision** — should this person get a blood test — not a haemoglobin estimate. Those
are different tasks with different metrics, and the project made the regression task
its primary outcome. Its own Phase 6.5 result records **WHO-band AUROC 0.875 within
site** for the image CNN, which is not a negligible number for triage. A reviewer can
reasonably say the imaging arm was refuted on a metric the deployed product would not
use. **This phase tests the refutation on the product's own terms. It is not an attempt
to rescue it.** If the screening framing changes a verdict, that is reported as a
changed verdict and logged as a correction — not softened and not buried.

**A methodological note fixed in advance.** Phase 7 reported PPG screening
`sensitivity 0.00` using a **plug-in** rule: refer if the *predicted* Hb falls below
the diagnostic threshold. That is not the operating point a screening tool would
choose — a regression model shrinks its predictions toward the mean, so the plug-in
rule is systematically insensitive. Both operating points are reported here: the
plug-in point (what is on record, and what a naive deployment would do) and the
screening point defined below.

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

- [x] Task 1: screening metrics (sens, spec, PPV, NPV, AUROC, AUPRC, ROC, NNS, false-referral and referral rate) for every model AND every baseline on identical folds, bootstrap CIs *(ticked 2026-09-17: `scripts/phase9a_screening.py` -> `screening.json`; 9 imaging and 9 PPG models/baselines, 2,000-resample subject-level CIs)*
- [x] Task 1: regenerate any per-subject baseline predictions not already on disk, with the recorded seeds and folds, and report that they were regenerated *(ticked 2026-09-17: ALL baseline predictions regenerated — Phase 4 Gate B and Phase 6.5 Task 2 stored only summary metrics — plus the cross-site CNN predictions (`scripts/phase9a_cross_site_preds.py`); folds verified identical, reused PPG predictions reproduce the recorded MAEs to 0.0000)*
- [x] Task 1: within-site and cross-site reported separately for the imaging arm *(ticked 2026-09-17: never pooled into a headline; the recorded AUROC 0.875 is shown to be a POOLED figure — within site India **0.688**, Italy **0.909**)*
- [x] Task 2: model vs best demographic baseline at identical operating points, paired bootstrap CI on the difference, against the pre-declared ≥ 0.10 margin *(ticked 2026-09-17: both directions; margin cleared by the mean-CIELAB model pooled (+0.192, CI [+0.114,+0.276]) and by the CNN within Italy; no model earns USEFUL)*
- [x] Task 2: how many anaemic subjects each model actually flags at its chosen operating point, in the headline comparison *(ticked 2026-09-17: in the section-2 table of the report; PPG plug-in flags **0 of 18**, reproducing Phase 7 exactly, now labelled a plug-in artefact)*
- [x] Task 3: a table placing every model's recorded regression verdict beside its new screening verdict *(ticked 2026-09-17: `reports/phase9a_screening_metrics.md` section 4, 9 rows)*
- [x] Task 3: state per arm whether the screening framing CONFIRMS, WEAKENS or OVERTURNS the recorded verdict; if any verdict moves, stop and report before anything else *(ticked 2026-09-17: imaging **WEAKENED** within site / **CONFIRMED** cross-site; PPG **CONFIRMED**, strengthened. Nothing OVERTURNED. Logged as a correction with the original text preserved)*
- [x] Task 4: `reports/phase9a_screening_metrics.md`, leading with model-vs-baseline, not AUROC alone *(ticked 2026-09-17)*
- [x] Task 4: CLAUDE.md updated; results logged including any that weaken the project's own conclusions *(ticked 2026-09-17: 3 RESULTS LOG entries, 3 DECISION LOG entries, 2 corrections — including the one that weakens the project's own recorded claim)*

### Phase 9B: The literature methodology audit, widened to every full text obtained (2026-09-20)

**Why this phase exists.** The project's loudest rhetorical claim — that this field
publishes accuracy figures without the checks that would make them meaningful — rested
on 5 sources with most fields UNKNOWN and a single measured NO. Too thin for the claim
being made. This phase reads every full text available (seven PDFs in
`data/raw/literature/`) against six criteria so the claim either becomes defensible or
is narrowed to what the counts support. **Rules fixed before scoring:** five answer
categories (YES / NOT REPORTED / UNKNOWN / NOT APPLICABLE / FULL TEXT UNAVAILABLE), never
collapsed; **no paper is ever recorded as failing a check** — the audit measures what is
reported; the single measured NO (Phase 1, Ghana duplicates) stays on the dataset rows.
Scoring is data in `hemosight.audit.literature`; the report is `reports/literature_gap.md`
§9B; the counts are in `data/interim/phase9b/literature_audit.json`.

- [x] Task 1: score each of the 7 PDFs on six criteria — demographic baseline; split level *and* augmentation-before/after-split; cross-site or cross-device; duplicate *and* leakage statement; pooled versus per-site; dataset used *(ticked 2026-09-20: 7 papers x 8 recorded fields, every value cites its section)*
- [x] Task 2: five answer categories kept strictly distinct; single-site status recorded as NOT APPLICABLE, never as a failure *(ticked 2026-09-20; test-enforced: no paper value may begin NO or FAIL)*
- [x] Task 3: the dataset-overlap consequence — how many audited papers use the Ghana collections; any paper treating overlapping collections as independent recorded factually, no conclusion drawn *(ticked 2026-09-20: **1 of 7** uses them (Asare 2023, as three modalities of the same 710 children); **1** cannot be determined (Sehar 2025); **0 of 7** treat two overlapping collections as independent or validate across them)*
- [x] Task 4: `reports/literature_gap.md` extended with the full table, counts per criterion, the obtainability count, and what the sample can and cannot support *(ticked 2026-09-20: **12 identified, 7 obtained**; demographic baseline **0 of 7**; per-site results **0 of 3** multi-site papers; dedup **0 of 7**; leakage statement 3 of 7; a convenience sample, not a review)*
- [x] Task 5: the claim follows the counts — narrowed *(ticked 2026-09-20: "a literature that frequently omits it" is **not supported at the rate it implies** and is narrowed to a statement about the seven papers read; the pooled-reporting point is licensed only as a worked example. Original wording kept in `docs/archive/superseded_claims.md` §6; DECISION LOG entry of this date)*
- [x] CLAUDE.md updated; decisions and results logged to `docs/archive/`; `tests/test_phase9b.py`; reproduce stage added

### Phase 9C: Parameter uncertainty propagated into the gate result (2026-09-20)

**Why this phase exists.** The number that closed the imaging arm — Hb MAE **3.893 g/dL**
at the 3.935 dE2000 residual (Phase 3 Task 0 on sourced constants; 3.471 at the
uncontrolled 3.456 and 1.040 at the studio 1.062 residual, Phase 7) — is a point
estimate from a forward model whose oxygenation, blood volume fractions, melanin and
layer thicknesses were held **fixed and known**. Several are unsourced (VERIFICATION
REQUIRED banner on thicknesses and BVFs; melanin a fitted power law). The gate result
inherits uncertainty the project documented but never propagated. **This phase
propagates it; it does not rebuild the forward model.**

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

- [x] Task 1: parameter prior declared with SOURCED / UNSOURCED status and justification per parameter; nominal reproduces the three point estimates exactly; gate MAE reported as a distribution (median, 95% interval, histogram) at 3.935, 3.456 and 1.062 dE2000 *(ticked 2026-09-20: 14 parameters, **13 UNSOURCED**; nominal reproduces 3.892987 / 3.470951 / 1.039592 to 1e-12; medians 4.67 / 4.28 / 1.52, 95% [2.37,8.02] / [2.09,7.90] / [0.60,4.90]; `hemosight.simulation.uncertainty`, `scripts/phase9c_uncertainty.py`)*
- [x] Task 2: fraction of the prior above 2.0 g/dL per residual; the interpretation rule applied; any combination below 2.0 identified with its plausibility; the studio condition against 1.0 g/dL *(ticked 2026-09-20: 99.5% / 98.4% / 37.0% above 2.0; **ROBUST, ROBUST, FRAGILE**; 10 of 2,048 draws below 2.0 at the gate residual, needing 5 of 14 parameters simultaneously in the outer quarter of their ranges, best draw 1.75 g/dL — MARGINAL, never VIABLE; studio 27.1% VIABLE / 35.9% MARGINAL / 37.0% NOT RECOVERABLE)*
- [x] Task 3: Sobol first-order and total indices, ranked; one-at-a-time swing per parameter; the melanin recommendation stated if supported *(ticked 2026-09-20: at 3.935 the ranking is deep-layer weight 0.303, epithelial BVF 0.284, **melanin 0.258**, stromal BVF 0.187 — melanin is 3rd here and 1st at the studio residual; the expected "melanin dominates" is only partly supported and is reported as such; mechanism measured: rank correlation between gate MAE and colour-per-g/dL span **-0.96**)*
- [x] Task 4: Efron 2009 and Zhivov 2006 sought; outcome recorded; banner lifted or kept *(ticked 2026-09-20: **Efron 2009 OBTAINED** via the open-access QUT thesis that carries the same study — and it contains **no palpebral thickness in µm at all**, only "two or three cell-layers deep"; its 32.9 µm is **BULBAR**, a different tissue. **Zhivov 2006 NOT OBTAINED** (closed access, no repository copy). **Banner KEPT and strengthened** from "could not be verified" to "the source was read and does not contain them"; correction logged)*
- [x] Task 5: `reports/phase9c_uncertainty.md`; the interval placed beside the point estimate in CLAUDE.md, `final_results.md`, the audit package provenance and the case study, the point estimate retained with a pointer; CLAUDE.md, logs, tests, reproduce stage *(ticked 2026-09-20: report written; interval added to CLAUDE.md (CURRENT STATE, section 2 rows 3 and 8, the Phase 3 row), `final_results.md` master table, `phase3_simulation.md` headline box, `phase7.md` gate table and outcome-B verdict, and the front end's case study and pre-registration pages; **no point estimate deleted anywhere**; `tests/test_phase9c.py`; reproduce stage added)*

### Phase 9D: Power analysis — what this study could have detected (2026-09-20)

**Why this phase exists.** The project reports a body of negative results. *"We found no
effect"* is a substantially weaker statement than *"we found no effect and had X% power to
detect an effect of size Y"*, and the project currently cannot answer the second. This phase
answers it. **It is not an attempt to reinterpret any result**, and no verdict recorded
anywhere else changes on the strength of it.

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

- [x] Task 1: n and MDE at 80% and 90% power for the deciding comparison of each arm, paired methods stated per comparison; cross-site reported per direction and prominently *(ticked 2026-09-20: imaging regression n=216 MDE 0.181/0.209 g/dL; imaging screening n=216 spec 0.116/0.135 and sens 0.114/0.132; cross-site **italy→india n=95 (68 anaemic) 0.314/0.363** and **india→italy n=121 (23 anaemic) 0.165/0.191**; PPG n=252 MAE 0.137/0.159 g/dL, AUROC 0.270/0.313, spec 0.073/0.084. Paired throughout — exact paired SE for MAE (error r=0.62, pairing saves 38% of the SE), 2,000-resample paired bootstrap for the screening metrics; Phase 9A's recorded differences reproduced before reporting)*
- [x] Task 2: every MDE restated in clinical units — g/dL against the WHO boundaries and the gate bands; percentage points against additional anaemic subjects detected and unnecessary referrals avoided at the reported operating point *(ticked 2026-09-20: 0.18 and 0.14 g/dL move **no** WHO boundary and no gate band — the narrowest band is 1.0 g/dL wide; within site 0.116 specificity = 15 of 125 needless referrals avoided and 0.114 sensitivity = 10 of 91 anaemic subjects, ~1 extra case per 21 screened; italy→india 0.314 = 8 of 27 non-anaemic subjects)*
- [x] Task 3: retrospective power explicitly NOT computed, and the distinction stated in the report *(ticked 2026-09-20: stated in report section 1 with the reason — observed power is a deterministic function of the observed p-value and is low by construction after a null result; `hemosight.evaluation.power` has no such function and `test_retrospective_power_is_absent_from_the_module` enforces it. `power_at()` exists but takes a **pre-declared** yardstick, never an observed effect)*
- [x] Task 4: `reports/phase9d_power.md` with the single summary table; ADEQUATELY POWERED / UNDERPOWERED per arm; the statements added to `final_results.md` limitations and to CLAUDE.md; logs, tests, reproduce stage *(ticked 2026-09-20: 8-row summary table with a power-at-the-yardstick column; **ADEQUATELY POWERED** imaging regression, PPG regression, PPG specificity; **UNDERPOWERED** imaging screening within site, both cross-site directions, PPG AUROC; new limitations subsection in `final_results.md`; `tests/test_phase9d.py` (14 tests); two reproduce stages)*

### Phase 9E: The project's boundaries, stated precisely (2026-09-21)

**Why this phase exists.** Three boundaries are implicit in the record and none is
named. (A) Phase 7 measured three capture regimes and a deployed screening app operates
in none of them — its guided capture sits between the two most controlled, which is
exactly where the gate crosses bands and where Phase 9C found the verdict fragile.
(B) Phase 9D called three comparisons UNDERPOWERED without saying what sample would fix
them. (C) Several statements on the record are more precise, or more absolute, than the
evidence behind them. **This phase names all three. It builds no new model, collects no
data, and is not permitted to change any verdict.**

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

- [ ] Task 1 (Part A): the guided-capture gap named as a boundary in CLAUDE.md, `final_results.md` and `reports/phase7.md`; the evidence that would settle it specified (protocol, measurement, sample, result in either direction); the interpolation run and labelled; recorded as the primary future-work item
- [ ] Task 2 (Part B): required n at 80% and 90% power for all three underpowered comparisons, with the SE scaling measured by subsampling; reported as a minimum count in the group that carries the metric, then as totals; minimum non-anaemic count stated per cross-site direction
- [ ] Task 3 (Part C): the three overstatements corrected everywhere they appear; generating scripts edited and reports regenerated, never hand-patched; supported conclusions verified unweakened
- [ ] Task 4 (Part D): `reports/phase9e_boundaries.md` with all three parts and a consolidated "what a confirmatory study would need" section; CLAUDE.md updated; `tests/test_phase9e.py`; reproduce stages; decisions and results logged to `docs/archive/`

### Phase 6 (original plan): Conformal prediction and abstention (N4)

> WARNING: **NOT APPLICABLE as written, and not started.** N4 wraps a haemoglobin
> estimator in conformal intervals and a three-state decision rule. There is no
> estimator to wrap: the imaging arm is closed and the PPG arm is not viable. The tasks
> are retained verbatim rather than deleted, per the WORKING PROTOCOL. See the DECISION
> LOG (`docs/archive/decision_log.md`), 2026-09-12.

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
- [ ] 🔴 SUPERSEDED — Attach skin tone labels using SCIN (self-reported Fitzpatrick, dermatologist Fitzpatrick, Monk Skin Tone); document how labels transfer to the anemia datasets and where they cannot *(also superseded by DECISION LOG (`docs/archive/decision_log.md`) 2026-09-11: SCIN deleted, N5 rebuilt on ITA)*
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
- [x] Document which subjects have which modalities and the resulting evaluation limits *(ticked 2026-09-12 audit: Phase 1 overlap — conjunctiva/nail roster Jaccard 1.000 (204/204), ~454 paired subjects, binary labels only; Hb_PPG shares no subject with any image set (`data/interim/overlap/overlap_results.json`; DECISION LOG (`docs/archive/decision_log.md`) 2026-09-11, N6 scoped))*

### Phase 9: Web application

> 🔴 **SUPERSEDED except the two scaffold items (audit 2026-09-12).** This phase is the
> inference application around an estimator that does not exist. The software deliverable
> became the audit harness (Phase 6, DECISION LOG (`docs/archive/decision_log.md`) 2026-09-12). The two scaffold items are
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

➡️ **Moved to `docs/archive/decision_log.md`.** All 81 entries that stood here, in date
order, verbatim, plus everything appended since. Nothing was summarised or deleted.

Dated entries recording any design decision, deviation from this plan, or changed
assumption. Append only. Never delete an entry; supersede it with a newer one that
says what changed and why.

Format: `### YYYY-MM-DD — Title`, then **Decision**, **Rationale**, **Alternatives
considered**, **Consequences**.

**New entries append to the END of `docs/archive/decision_log.md`.**
Corrections are additionally collected in `docs/archive/corrections.md`.

---

## 8. RESULTS LOG

➡️ **Moved to `docs/archive/results_log.md`.** All 48 entries that stood here, in date
order, verbatim, plus everything appended since. Nothing was summarised or deleted.

Dated entries recording **every** metric produced, including failures and negative
results. A run that produced a bad number is a result. A run that crashed after
consuming a day is a result. Append only; never delete an entry.

Format: `### YYYY-MM-DD — Experiment name`, then **Config** (script, config file,
commit), **Data** (split, sites, n), **Metric(s)**, **Interpretation**, **Status**
(provisional / confirmed / superseded).

**New entries append to the END of `docs/archive/results_log.md`.**

---

## 9. WORKING PROTOCOL

After completing any task:

1. **Tick its checkbox in CLAUDE.md.** A task is complete when its output exists on
   disk, not when the code is written.
2. **Record any deviation in the DECISION LOG**, dated, with the rationale —
   appended to the END of `docs/archive/decision_log.md`.
3. **Record any metric in the RESULTS LOG**, dated, including failures and negative
   results — appended to the END of `docs/archive/results_log.md`.
4. **Never delete a log entry.** Supersede it with a newer entry instead. **This
   rule applies to the archive files exactly as it applied to CLAUDE.md**: they are
   append-only, and a superseded entry stays where it is under a banner saying what
   superseded it.
5. **Never silently change a phase plan item.** Editing or removing a task requires a
   DECISION LOG entry saying what changed and why.

### Where each kind of writing goes (amended 2026-09-17; see the split entry in the DECISION LOG)

| what you are writing | where it goes |
| --- | --- |
| A new DECISION LOG entry | append to `docs/archive/decision_log.md` |
| A new RESULTS LOG entry | append to `docs/archive/results_log.md` |
| A correction to anything already on the record | append the entry to `docs/archive/decision_log.md`, **and** add it to `docs/archive/corrections.md` |
| Claim text being refuted or superseded | the original wording moves to `docs/archive/superseded_claims.md`; the claim keeps its place in section 2 under a verdict banner |
| A phase plan change, a tick, a classification | **CLAUDE.md section 6** |
| A change to what is done / outstanding / active | **CLAUDE.md, CURRENT STATE** |
| A change to the claim set or a verdict | **CLAUDE.md section 2** |

**CLAUDE.md itself records only the claim set, the constraints, the inventory, the
tech stack, the phase plan, the current state and this protocol.** It must stay
small enough to load in full: a test fails the suite if it exceeds **120,000
characters** (`tests/test_docs.py::test_claude_md_fits_in_context`). If it grows
past that, split again — move content to `docs/archive/`, never delete it.

Additional standing rules:

- Never write to `data/raw/`.
- Never split at image level; splits are patient-level and site-aware.
- Never report a single-site number as a headline result.
- Never describe any output as diagnostic, validated, or clinically approved.
- Keep the CNN baseline current: if the physical model changes, the comparison arm is
  re-run before the new number is reported.
- When a result is worse than the baseline, log it and say so plainly. That is the
  point of having a baseline.