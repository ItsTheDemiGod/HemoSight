# External audit procedure (Phase 7 Task 3 — path built, not yet run)

This documents how a third party's released predictions are brought into the HemoSight
Audit contract, what the tool does when a release lacks what a check needs, how the
result is reported, and how every attempt — including the ones where nothing auditable
was released — is recorded. **No external audit has been run.** The register is empty
by design; it is filled one attempt at a time from real releases.

## 1. What the harness needs, and what a release usually has

| contract column | needed by | typical release |
| --- | --- | --- |
| `subject_id` (required) | everything subject-level | **usually absent**; per-image rows only |
| `y_true`, `y_pred` (required) | everything | sometimes released as per-image CSV; often only summary metrics; often a classifier's label/probability rather than Hb |
| `split` | split integrity, leak test | rarely released |
| `age`, `sex`, `device`, `site` | demographic baseline, proxy probe, subgroups | rarely per row; sometimes in a supplementary table |
| `image_path` + images | duplicate detection | dataset-dependent; often re-obtainable from the public dataset |
| `y_pred__<name>` | selection-aware permutation | essentially never |
| `y_pred_seed__<k>` | seed stability | essentially never |

## 2. Conversion: `hemosight.audit.ingest`

`IngestSpec` is the auditor's statement of how to read the source. Every field is copied
verbatim into the `IngestRecord` and printed in the report before any verdict.

```
python scripts/external_audit.py ingest --source their.csv --spec spec.json --out data/interim/phase7/external/<slug>
python scripts/external_audit.py run    --dir data/interim/phase7/external/<slug> [--images DIR]
```

Common cases and what they cost:

| case | handling | consequence |
| --- | --- | --- |
| per-image rows, subject id present | aggregate to one row per subject (median), keep image paths | none |
| per-image rows, id encoded in the filename | `subject_from_image` regex; recorded as DERIVED | independence is only as good as the pattern; stated |
| per-image rows, no subject id at all | `subject_id := image`; recorded as ASSUMED | **`split_integrity` and `subgroup_robustness` are forced to INSUFFICIENT DATA** — a split that shows no "subject" in two folds proves nothing when each image is its own subject. Duplicate detection still runs if images are supplied. |
| no `split` | nothing to convert | split integrity INSUFFICIENT |
| no demographics | nothing to convert | demographic baseline and proxy probe INSUFFICIENT |
| Hb in g/L | must be declared `hb_units: "g/L"`; a median > 30 with no declaration is refused | never converted by guesswork |
| classification-only outputs (label / probability) | `NotAuditable` raised, recorded in `not_auditable.json` | no regression check can run; enter the register as `auditable: none` or `partial` |
| sex as words / 0-1 | normalised to M / F; unknown spellings reported | — |

The forcing of INSUFFICIENT DATA on assumed columns is implemented in
`run_audit(..., unsupported=...)` and is covered by
`tests/test_phase7.py::test_assumed_subject_id_forces_split_integrity_to_insufficient_not_pass`,
which demonstrates that without the record the same table would PASS.

## 3. Reporting: `to_external_markdown`

The external report (`external_audit.md`) has two halves with equal prominence:

- **Part 1 — what was checked:** every check that returned PASS or FAIL, with the measured quantity.
- **Part 2 — what could NOT be checked, and why:** every INSUFFICIENT DATA verdict with the
  exact column or artefact that was missing, plus any check not selected.

The ingestion record — source description, rows in/out, columns supplied vs DERIVED,
every assumption — is printed above both. The scope note states that INSUFFICIENT DATA
is a statement about the release, not the model: a model whose artefacts do not allow a
check is *unaudited* on that axis, not cleared.

## 4. The register: `configs/external_audit_register.json` → `reports/external_audit_register.md`

```
python scripts/external_audit.py register --slug <slug> --paper "..." --links "..." \
    --predictions {released,partial,none} --subject-ids {yes,no,derivable} --splits {yes,no} \
    --demographics {yes,partial,no} --images {yes,no} --auditable {full,partial,none} \
    --checks-possible "duplicates,permutation" --notes "..."
```

One row per candidate. `auditable: none` is recorded with the same weight as an audit
that ran. If most candidates release nothing auditable, the register's summary line
(“N of M candidates released nothing auditable”) is a measured finding about
reproducibility in this field and is reported as one.

## 5. What is NOT done here

- No external submission has been ingested; the only run is a synthetic smoke test of
  the path (`data/interim/phase7/external/_smoke_synthetic`, untracked, labelled as such).
- No expected outcome of any external audit is stated anywhere.
- Candidate papers and artefact links are supplied separately; each attempt goes into
  the register whether or not it yields an audit.
