*Renamed files and folders since this text was written are mapped in [docs/CODE_MAP.md](../CODE_MAP.md); nothing below is rewritten to match new names.*

# SUPERSEDED AND REFUTED CLAIM TEXT — HemoSight

> **Provenance.** Moved verbatim out of `CLAUDE.md` on 2026-09-17, when that file
> reached 233,820 characters and was being truncated on load. The text below is
> byte-identical to the corresponding section of `CLAUDE.md` at commit `715096a`,
> recoverable in full from the git tag `pre-claude-md-split`. **Nothing was
> summarised, condensed or deleted.** See `docs/archive/README.md`.

> **What this file is.** Every original claim wording that the project has since
> revised, refuted or superseded, reproduced verbatim. This is a *cross-cutting
> collection*: each block below also stands in its original place — in `CLAUDE.md`
> section 2 (the claim set) or in `docs/archive/decision_log.md` (the entry that
> changed it). Nothing here is the only copy of anything, and nothing was removed
> from its original position to build this file.

---

## 1. N1 — the original headline claim, REFUTED

*Source: `CLAUDE.md` section 2, retained there in full. Refuted 2026-09-11
(Phase 2.5); see `docs/archive/decision_log.md`, entry 2026-09-11 "N1 is REFUTED in
its entirety; the contribution becomes the diagnosis".*

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

---

## 2. N1 — original wording as it stood before the N1a / N1b / N1c restructure

*Source: `docs/archive/decision_log.md`, entry 2026-09-11 "N1 restructured into
N1a / N1b / N1c".*

**Original wording, preserved.** *"N1. Calibration-free spectral super-resolution. Use
the sclera as an endogenous white reference to estimate the scene illuminant, removing
the per-camera spectral profiling and per-use radiometric calibration that currently
blocks hyperspectral-reconstruction methods from field deployment. THIS IS THE HEADLINE
CLAIM."*

---

## 3. N2 — original justification, corrected 2026-09-11

*Source: `docs/archive/decision_log.md`, entry 2026-09-11 "N2's justification
corrected". The correction entry is also in `docs/archive/corrections.md`.*

**Original wording, preserved.** *"This supplies severe-anemia cases that no public
dataset contains."*

---

## 4. N5 — original wording, before SCIN was removed and the method rebuilt on ITA

*Source: `docs/archive/decision_log.md`, entry 2026-09-11 "N5 rebuilt without SCIN;
`data/raw/scin-main` deleted". The claim stands; only its method changed.*

**Original wording, preserved.** *"N5. Mechanistic fairness audit. Report performance
stratified by skin tone and source device, and DECOMPOSE any gap into melanin absorption
versus illuminant estimation error."* (The claim stands; only its method changed.)

---

## 5. Register of every other superseded or refuted banner

These are banners over text that is retained verbatim **in place**. They are listed
here so the set is enumerable; the text itself is not duplicated, because moving or
copying it would separate it from the tasks or entries it annotates.

| what is superseded | where it is retained verbatim | superseded by |
| --- | --- | --- |
| DECISION LOG 2026-09-10 "PyTorch installed CPU-only; no GPU available" — marked SUPERSEDED and FACTUALLY WRONG | `docs/archive/decision_log.md` | the 2026-09-11 CUDA correction (`corrections.md` §1) |
| RESULTS LOG 2026-09-11 "Phase 3: signal-to-noise is the mechanism" — the ~0.70 dE2000/g/dL figure, WITHDRAWN | `docs/archive/results_log.md` | Phase 6.5 Task 1 measurement (`corrections.md` §6) |
| RESULTS LOG 2026-09-12 "Phase 5 extended permutation run: IN PROGRESS" | `docs/archive/results_log.md` | the completed n=240 entry of the same date |
| Phase 4 (N3) spectral-reconstruction task list — SUPERSEDED IN FULL | `CLAUDE.md` section 6 | Phase 3 Task 0 and Phase 3.5 Task 1 gates |
| Phase 6 (original) conformal-prediction task list — NOT APPLICABLE as written | `CLAUDE.md` section 6 | no estimator exists to wrap (DECISION LOG 2026-09-12) |
| Phase 7 (N5) fairness-audit task list — SUPERSEDED | `CLAUDE.md` section 6 | no estimator; mechanism measured in Phase 3 Task 4 |
| Phase 8 (N6) fusion task list — SUPERSEDED except two items | `CLAUDE.md` section 6 | no g/dL estimate from any modality |
| Phase 9 web-application task list — SUPERSEDED except two scaffold items | `CLAUDE.md` section 6 | replaced by the Phase 6 audit app |
| Phase 10 Flutter task list — SUPERSEDED IN FULL | `CLAUDE.md` section 6 | no estimator |
| N1 as the headline claim in the CLAIM HIERARCHY | `CLAUDE.md` section 2 | Phase 2.5 refutation; hierarchy restructured 2026-09-11 |

---

## 6. "A literature that frequently omits it" (Phase 4.5 wording, CLAUDE.md section 2) — NARROWED 2026-09-20 by Phase 9B

*Source: `CLAUDE.md` section 2, the FINAL STATUS block, retained there in full under a
banner. Narrowed 2026-09-20; see `docs/archive/decision_log.md`, entry 2026-09-20 "the
claim 'a literature that frequently omits it' is NARROWED to what the counts support".*

**Original wording, preserved verbatim.** *"The project's contribution is the body of
negative results and their mechanisms — six refutations, thresholds declared before every
experiment, cross-device and cross-subject validation throughout, and a demographic
baseline that exposes how easily an apparently working estimator is really a sex
classifier. That last point alone is a contribution to a literature that frequently omits
it."*

**What replaced the last clause.** *None of the seven anaemia-estimation papers whose full
text this project read reports a demographics-only baseline — a statement about those
seven, from a convenience sample of accessible papers, not about the field.*

**Why.** "Frequently" is a rate with the field as its denominator. Phase 9B's denominator
is seven papers obtained without a search strategy or inclusion criteria. The count
(0 of 7, complete, no UNKNOWN) is consistent with the original sentence and cannot
establish it. The claim follows the counts. The same standard was applied in Phase 5
(`reports/literature_gap.md`: "a sample this small supports no claim about the field")
when the sample was five; the wording in section 2 had not been brought into line with it
until now.
