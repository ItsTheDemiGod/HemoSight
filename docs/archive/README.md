# docs/archive — the HemoSight evidentiary record

This directory holds the project's append-only logs. It was created on **2026-09-17**,
when `CLAUDE.md` reached **233,820 characters** against a 150,000-character load limit
and was being **silently truncated** — meaning sessions were reading a partial record
without being told which part was missing.

**The split moved text. It changed none.** Nothing was summarised, condensed or
deleted. The pre-split file is recoverable in full from the git tag
`pre-claude-md-split` (commit `715096a`), whose `CLAUDE.md` has
SHA-256 `86f6ff5d4cca64b47179afaeee2fc22d826832d699d43533d9c4839b49a17775`.

## What is in each file

| file | contents |
| --- | --- |
| `decision_log.md` | **Section 7, DECISION LOG** — all 81 entries, 2026-09-10 onward, in date order, verbatim, under their 12 original phase-group headers. Every design decision, deviation from the plan, and changed assumption. |
| `results_log.md` | **Section 8, RESULTS LOG** — all 48 entries, in date order, verbatim. Every metric produced, including failures and negative results. |
| `superseded_claims.md` | The 4 original claim wordings retained under a refuted or superseded banner (N1 headline; N1 before the N1a/N1b/N1c restructure; N2's original justification; N5's original method), plus a register of the 10 other superseded banners and where each is retained. |
| `corrections.md` | All 7 standalone correction entries verbatim — each with the entry it corrects — plus a register of 9 in-place correction banners that are not standalone entries. |
| `predeclarations.md` | **Every pre-declaration the project made, verbatim** — all **10** threshold, gate, operating-point and interpretation-rule blocks, in phase order (2.5, 3, 3.5, 4, 4.5, 7, 9A, 9C, 9D, 9E), moved out of CLAUDE.md section 6 on **2026-09-21**. CLAUDE.md keeps each heading, a one-line summary and a pointer. **Moving a pre-declaration cannot weaken it:** what makes it a *pre*-declaration is that it was committed before the run, which git records permanently. |

`predeclarations.md` was created on **2026-09-21** for the same
reason the directory exists: CLAUDE.md had reached **120,380 characters** against its
**120,000-character** test-enforced limit (`tests/test_docs.py`) once the Phase 9E
results were recorded in it. **The split moved text; it changed none** — verified block by block, all **20,304
characters byte-identical**. Every block is also recoverable from git at the commit that
first carried it, which is what establishes that each predates its own results. Two of
them (9D and 9E) briefly had their own files, `phase9d_predeclaration.md` and
`phase9e_predeclaration.md`, before being consolidated here the same day; those files
remain in git history and nothing in them is lost. See the DECISION LOG entry of
2026-09-21.

`superseded_claims.md` and `corrections.md` are **cross-cutting collections**. Every
block in them also stands in its original place: in `CLAUDE.md` section 2 (the claim
set) or in `decision_log.md` (the entry that made the change). Neither file is the only
copy of anything, and nothing was removed from its original position to build them.
`decision_log.md` remains the canonical chronological record.

## The rules, unchanged from CLAUDE.md

- **Append only.** New entries go at the END of `decision_log.md` / `results_log.md`.
- **Never delete an entry.** Supersede it with a newer one that says what changed and
  why. A superseded entry stays where it is, under a banner naming what superseded it.
- **A negative result is recorded with the same weight as a positive one.**
- Section headings (`## 7. DECISION LOG`, `## 8. RESULTS LOG`) are retained inside these
  files so that existing references elsewhere in the repository — `reports/*.md` cite
  "section 8 RESULTS LOG" and "DECISION LOG 2026-09-11" — still resolve.

See `CLAUDE.md` section 9, WORKING PROTOCOL, for which kind of writing goes where.

## Verification of the split

Measured, not asserted. Counted in the pre-split file and again across the post-split
files:

| quantity | pre-split | post-split | |
| --- | --- | --- | --- |
| DECISION LOG entries | 81 | 81 | titles identical and in the same order |
| RESULTS LOG entries | 48 | 48 | titles identical and in the same order |
| DECISION phase-group headers | 12 | 12 | identical |
| `**Original wording, preserved.**` blocks | 3 | 3 | all collected |
| standalone correction entries | 7 | 7 | all collected |
| non-blank lines of sections 7–8 absent from the archive | — | **0** | |

Byte-identity: the moved blocks were copied by line range and contain **no heading-level
changes**, so each is byte-identical to its source — section 7 (lines 828–2275,
108,230 chars) and section 8 (lines 2277–3130, 56,556 chars), plus each claim and
correction block individually.

Retained head (`CLAUDE.md` lines 1–826): **0 lines removed**, 19 lines replaced, and
every one of those 19 differs from its original by **exactly** an inserted
`` (`docs/archive/…`) `` pointer — verified by stripping the pointer and comparing for
equality.

Sizes: `CLAUDE.md` went from 233,820 to **76,128 characters** — 51% of the 150k load
limit, with 43,872 characters spare under the 120k ceiling now enforced by
`tests/test_docs.py::test_claude_md_fits_in_context`.
