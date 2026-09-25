# reports/

Markdown reports here **are** version-controlled. `reports/figures/` is **not**.

## Why figures are excluded from git

Every figure in `reports/figures/` renders pixels taken from the source datasets -
conjunctiva photographs, fingernail photographs, duplicate-pair comparisons. As
recorded in [`phase1_dataset_licences.md`](phase1_dataset_licences.md), **9 of the 10
datasets ship no licence file**, so their redistribution terms are unverified.
Committing rendered dataset imagery would redistribute that data through the
repository, which is exactly what the project's "public datasets only, nothing
committed" rule exists to prevent.

`reports/figures/` is therefore in `.gitignore` alongside `data/`. The figures stay on
disk for local reading; they simply never enter version control.

## Regenerating every figure from scratch

All figures are reproducible from `data/raw/` with no manual steps. From the repository
root, with the venv active:

```powershell
.\.venv\Scripts\python.exe scripts\dataset_manifests_phase1.py          # manifests
.\.venv\Scripts\python.exe scripts\participant_overlap_check_phase1.py            # hashes + embeddings
.\.venv\Scripts\python.exe scripts\data_audit_figures_phase1.py            # -> reports/figures/
```

| Figure | Produced by | Depends on |
| --- | --- | --- |
| `phase1_overlap_cp_anemic__ghana_conj.png` | `scripts/data_audit_figures_phase1.py` | `data/interim/overlap/hashes_*.csv` |
| `phase1_cp_anemic_label_conflict.png` | `scripts/data_audit_figures_phase1.py` | hashes + `manifests/cp_anemic.csv` |
| `phase1_hb_distributions.png` | `scripts/data_audit_figures_phase1.py` | `manifests/master.csv` |
| `phase1_overlap_*__ghana_nail.png` | `scripts/participant_overlap_check_phase1.py` | hashes + embeddings |

`scripts/participant_overlap_check_phase1.py` caches hashes and embeddings under
`data/interim/overlap/`. Delete that directory to force a full recomputation; the
GPU embedding pass over ~9,200 images takes well under a minute on the RTX 4060.

## Markdown reports

| File | Contents |
| --- | --- |
| `phase1_data_audit.md` | Task 1 + 2: full dataset characterisation and the overlap check |
| `phase1_summary.md` | Task 5: sanity tables, split sizes, and the "what this data CANNOT support" list |
| `phase1_dataset_licences.md` | Licence and redistribution status per dataset |
| `phase1_5_remediation.md` | Phase 1.5: decisions taken in response to the Phase 1 findings |

These contain numbers and prose only - no dataset pixels - so they are safe to commit.
Note that `phase1_data_audit.md` does quote CP-AnemiC haemoglobin values and hospital
names in aggregate; that is derived statistics, not redistribution of the dataset.
