# Phase 1 - Dataset licences and redistribution terms

Compiled during the Phase 1 audit. **This is a record of what is stated on disk plus
the known provenance of each dataset, not legal advice.** Anything marked *unverified*
must be confirmed against the source landing page before any redistribution, and
before the paper's data-availability statement is written.

## Redistribution status

`.gitignore` excludes `data/` in full and this was verified: `git status --porcelain`
shows zero files under `data/` staged or tracked. **No dataset image, label file or
derived crop is committed to this repository.** Derived artefacts under
`data/interim/` (manifests, hashes, embeddings, splits) are likewise untracked.

Two consequences to keep:

* Manifests contain absolute file paths and, for CP-AnemiC, haemoglobin values, ages
  and hospital names. They are derived data about human participants and must stay out
  of version control and off any public artefact.
* The overlap figures in `reports/figures/` **contain dataset images**. `reports/` is
  tracked. Before any public release of this repository, those figures must be removed
  or replaced with non-image summaries.

## Per-dataset

| Dataset | Licence file on disk | Stated terms | Status |
| --- | --- | --- | --- |
| `scin-main` | `LICENSE` - "SCIN Data Use License" | Custom Google data-use licence; permissive for research, with conditions | On disk, readable |
| `MOBIUS` | none | `README.md` documents structure only; no licence text | **Unverified** - check the MOBIUS landing page |
| `Hb_PPG_Dataset` | none | `README.md` describes the dataset; no licence text | **Unverified** |
| `SBVPI` | none | Distributed on request for research use | **Unverified** - typically requires a signed research agreement |
| `CP-AnemiC dataset` | none | Published dataset accompanying a paper | **Unverified** |
| Ghana conjunctiva (`nt7r8hv2pz`) | none | Mendeley Data, usually CC BY 4.0 | **Unverified** - confirm the CC variant on Mendeley |
| Ghana fingernails (`2xx4j3kjg2`) | none | Mendeley Data, usually CC BY 4.0 | **Unverified** |
| Eyes-Defy-Anemia (`dataset anemia`) | none | Research dataset, Italy/India collection | **Unverified** |
| `nus8` | none | NUS colour-constancy benchmark, free for research use | **Unverified** |

## Attribution owed

Every dataset above requires citation in any publication. The two Mendeley sets carry
DOIs (`nt7r8hv2pz`, `2xx4j3kjg2`) that must appear in the references. SCIN's licence
additionally imposes conditions on downstream use that must be read in full before
SCIN data is downloaded - which, per the audit, has not happened: `scin-main/` on disk
contains no data.

## Human-subjects position

All datasets are pre-existing public releases collected by other groups under their own
ethical approvals. This project collects no new data and enrols no participants, so it
requires no separate ethics approval - but it inherits each source's consent scope.
Nothing here supports a clinical claim, and none of these consents covers clinical
deployment.
