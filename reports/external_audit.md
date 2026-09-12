# External audit - Phase 7 Task 3B

**Lead result: 0 of 3 external candidates could be independently audited.** The harness therefore produced no verdict on any external model. The availability record is the primary output of this task and is in `reports/external_audit_availability.md`; the register is `reports/external_audit_register.md`.

## How many, and why not

| candidate | could it be audited? | why |
| --- | --- | --- |
| anemia-detection (student repository) | no | code released, but every notebook depends on preprocessed arrays, an augmented-image folder or a cleaned spreadsheet that were not released; 0 of 7 notebooks ran; no weights, no predictions |
| BPANet (Lin et al. 2025) | no | data "available from the corresponding authors upon reasonable request"; no code availability statement; no released predictions or weights; not requested |
| "Hemo-ConViT" | no | no primary source located (Europe PMC, Crossref, arXiv: 0 hits) |

## Harness output

None. The external path (`hemosight.audit.ingest`, `scripts/external_audit.py`) was exercised end to end on the one released codebase up to the point where a predictions table would be ingested; that point was never reached. For the record, the path's behaviour on a release-shaped table is demonstrated only on a SYNTHETIC smoke test (`data/interim/phase7/external/_smoke_synthetic`, labelled as such), and the INSUFFICIENT DATA behaviour on assumed subject ids is covered by `tests/test_phase7.py`.

## Methodology from paper text, for the paper that could not be run

BPANet's full text was read. none without released predictions; from the text alone: 5-fold CV on Eyes-Defy (unit not stated), 4-fold on NTUH; ablation removing age/gender reported (1.460 vs 1.212), no demographics-only baseline; India+Italy pooled, no per-country result; NTUH evaluated separately after retraining; no duplicate/leakage check mentioned. These are entered in `reports/literature_gap.md` as **NOT REPORTED** where the paper does not state an item - a value distinct from UNKNOWN (paper not read) and from NO (this project measured a problem). **NOT REPORTED is not a failed check**; no check ran.

## The student repository

> **Scope, stated first.** `mbedmutha/anemia-detection` is a three-person student project with 18 commits, zero stars, self-described as "initial experiments". It is **not** a published paper and is **not** evidence about the published literature. Its role here is solely to demonstrate that the harness can ingest and audit external code. Nothing about it generalises.

Run record: `data/interim/phase7/external/anemia-detection/run_results.json`; executed copies with their first error under `runs/`. The cloned repository was not modified.

## What would change the result

- A release of per-subject predictions with subject ids and the split used - for any model - would let all eight checks run; a release of predictions alone would let the demographic baseline, permutation and (with images) duplicate checks run.
- Every further candidate goes into the register whether or not it can be audited. If most cannot, that is a measured finding about reproducibility in this field and will be reported as one - after enough entries to support it, which three is not.
