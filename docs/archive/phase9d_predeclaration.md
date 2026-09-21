# Phase 9D — the pre-declaration, verbatim

Moved out of CLAUDE.md on 2026-09-21, together with Phase 9E's, under the file's own
splitting rule (section 9). CLAUDE.md had reached 120,380 characters against its 120,000
limit once the Phase 9E results were recorded in it.

**Nothing was summarised.** The text below is exactly what stood in CLAUDE.md section 6,
committed as part of the Phase 9D work before any Phase 9D number was computed. See the
DECISION LOG entry of 2026-09-21.

---

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
