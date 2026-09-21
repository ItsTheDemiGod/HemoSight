# Phase 9E — the pre-declaration, verbatim

Moved out of CLAUDE.md on 2026-09-21, the day it was written, under the file's own
splitting rule (section 9: *"It must stay small enough to load in full... If it grows
past that, split again — move content to `docs/archive/`, never delete it."*). CLAUDE.md
stood at 117,314 characters against a 120,000 limit before the Phase 9E results were
recorded in it.

**Nothing was summarised.** The text below is exactly what was committed in CLAUDE.md as
commit `f4a3fc0`, *"Phase 9E: pre-declare the boundary statements, the required-n method
and the language-pass rules BEFORE running"*, before any Phase 9E script was run. The
commit is the evidence that it predates the results; this file is the readable copy. See
the DECISION LOG entry of 2026-09-21.

---

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
