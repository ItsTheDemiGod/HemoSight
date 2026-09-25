"""Phase 5, TASK 3 (manifest) and TASK 4 (literature positioning).

The dataset manifest is generated from what is actually on disk, so it cannot drift
from reality. The literature table is restricted to papers already cited in this
project's own reports - no new reading - and records only four factual attributes per
paper. Counts are reported; no characterisation beyond what the counts support.

    .\\.venv\\Scripts\\python.exe scripts\\dataset_manifest_and_literature_phase5.py
"""

from __future__ import annotations

import json

from hemosight.audit import literature as lit9b
from hemosight.io import paths

# --------------------------------------------------------------------------- #
# TASK 3: dataset manifest
# --------------------------------------------------------------------------- #
DATASETS = [
    {"dir": "nus8", "name": "NUS 8-camera colour constancy benchmark",
     "source": "https://yorkucvil.github.io/projects/public_html/illuminant/illuminant.html (the cvil.eecs.yorku.ca URL redirects here)",
     "licence": "NONE STATED - verified 2026-09-12: the landing page carries download links, a funding acknowledgement and no licence, citation or redistribution terms at all. Research use is customary, not licensed",
     "used_for": "N1a illuminant accuracy (6 of 8 cameras extracted)",
     "obtain": "Download per-camera PNG + CHECKER archives and groundtruth .mat"},
    {"dir": "SBVPI", "name": "Sclera Blood Vessels, Periocular and Iris",
     "source": "https://sclera.fri.uni-lj.si/database.html",
     "licence": "CUSTOM AGREEMENT - verified 2026-09-12 from the provider's access form (University of Ljubljana): non-commercial research only, for the purpose stated in the request; NO redistribution of the dataset or its parts; a Data Access and Processing Agreement is signed beforehand; a fixed acknowledgement and three references are mandatory in every publication; copies of publications go to the provider. Unlike MOBIUS, the SBVPI form makes no allowance for publishing figures",
     "used_for": "sclera segmentation; vessel ground truth (128 masks); stability",
     "obtain": "Request access from the authors"},
    {"dir": "MOBIUS", "name": "Mobile Ocular Biometrics In Unconstrained Settings",
     "source": "https://sclera.fri.uni-lj.si/database.html",
     "licence": "CUSTOM AGREEMENT - verified 2026-09-12 from the provider's access form (University of Ljubljana): non-commercial research only, for the purpose stated; NO redistribution of the dataset or its parts, EXCEPT limited publication for demonstrative purposes (figures) using sufficiently scaled-down or watermarked images; Data Access and Processing Agreement signed beforehand; fixed acknowledgement and three references mandatory; copies of publications to the provider",
     "used_for": "N1b self-consistency; 3 phones x 3 lighting x 100 subjects",
     "obtain": "Request access from the authors"},
    {"dir": "CP-AnemiC dataset", "name": "CP-AnemiC conjunctival pallor (Ghana)",
     "source": "https://data.mendeley.com/datasets/m53vz6b7fx/1 (DOI 10.17632/m53vz6b7fx.1)",
     "licence": "CC BY 4.0 - verified 2026-09-12 on Mendeley Data, with the authors' added statement: \"This dataset can be reused by other author(s) for academic purpose only and should be cited as such\"",
     "used_for": "REJECTED for Hb regression (Phase 1.5 arbitration); binary label only",
     "obtain": "See the dataset's publication"},
    {"dir": paths.GHANA_CONJ.name,   # real folder name, double space and all
     "name": "Ghana conjunctiva (Mendeley nt7r8hv2pz)",
     "source": "https://data.mendeley.com/datasets/nt7r8hv2pz",
     "licence": "CC BY 4.0 - verified 2026-09-12 on Mendeley Data (DOI 10.17632/nt7r8hv2pz.1, version 1)",
     "used_for": "BINARY LABEL ONLY; superset containing CP-AnemiC",
     "obtain": "Mendeley Data DOI"},
    {"dir": "Detection of Anemia using Colour of the Fingernails Image Datasets from Ghana",  # noqa: E501
     "name": "Ghana fingernails (Mendeley 2xx4j3kjg2)",
     "source": "https://data.mendeley.com/datasets/2xx4j3kjg2",
     "licence": "CC BY 4.0 - verified 2026-09-12 on Mendeley Data (DOI 10.17632/2xx4j3kjg2.1, version 1)",
     "used_for": "N6 paired-body-site evidence; binary label only",
     "obtain": "Mendeley Data DOI"},
    {"dir": "dataset anemia", "name": "Eyes-Defy-Anemia (India + Italy)",
     "source": "https://ieee-dataport.org/documents/eyes-defy-anemia (IEEE DataPort, subscription required; Dimauro et al., University of Bari)",
     "licence": "NONE STATED - verified 2026-09-12: the IEEE DataPort record has no licence field; the bundled \"Dataset anemia.docx\" says the data is provided free of charge and asks that three papers be cited (Maglietta et al., under submission; Dimauro et al. Appl. Sci. 2020, DOI 10.3390/app10144804; Dimauro & Simone, Electronics 2020, DOI 10.3390/electronics9060997). A third-party Kaggle mirror exists and is not the authoritative source",
     "used_for": "the ONLY full photographs paired with Hb; 217 trusted rows",
     "obtain": "See the dataset's publication"},
    {"dir": "Hb_PPG_Dataset", "name": "Four-wavelength Hb-PPG (252 subjects)",
     "source": "https://doi.org/10.6084/m9.figshare.22256143 (figshare; README cites v5, the record is at v7)",
     "licence": "CC BY 4.0 - verified 2026-09-12 via the figshare API (article 22256143, licence \"CC BY 4.0\", https://creativecommons.org/licenses/by/4.0/)",
     "used_for": "Phases 4 and 4.5; 252 subjects, venous HemoCue reference",
     "obtain": "See the dataset's publication"},
    {"dir": "optical_constants", "name": "Optical constants (Prahl, mcxyz spectralLIB)",
     "source": "https://omlc.org/spectra/hemoglobin/summary.html ; "
               "https://omlc.org/software/mc/mcxyz/",
     "licence": "Public research resources (OMLC)",
     "used_for": "Phase 3/3.5 forward model; replaced hand-transcribed tables",
     "obtain": "Download from omlc.org"},
    {"dir": "camera_sensitivities", "name": "Jiang et al. camspec + average mobile SSF",
     "source": "https://www.gujinwei.org/research/camspec/camspec_database.txt ; "
               "https://ohlab.kic.ac.jp/index/mobilespec_database",
     "licence": "Public research resources",
     "used_for": "Gate B phone-response analysis; 28 cameras, 400-720 nm",
     "obtain": "Download from the URLs above"},
]

# --------------------------------------------------------------------------- #
# TASK 4: literature positioning - ONLY papers already cited in this project's
# own reports and constants module. Four factual attributes each.
#
# "reported" means: stated in the material this project actually consulted (the
# dataset READMEs, the dataset papers as described by their own documentation, and
# the optical-constants sources). Where the project did not read the full paper, the
# attribute is recorded as UNKNOWN rather than guessed. That distinction is the whole
# point of this exercise.
# --------------------------------------------------------------------------- #
PAPERS = [
    {"key": "CP-AnemiC dataset paper",
     "cited_in": "phase1_data_audit.md", "type": "anemia imaging dataset",
     "demographic_baseline": "UNKNOWN", "subject_level_splits": "UNKNOWN",
     "cross_device_or_site": "UNKNOWN", "duplicate_or_leakage_check": "NO",
     "evidence": "This project found 710 files contain only 498 unique images and 90 of "
                 "91 duplicate groups carry conflicting Hb values. A duplicate check "
                 "was therefore demonstrably not performed."},
    {"key": "Ghana conjunctiva (Mendeley nt7r8hv2pz)",
     "cited_in": "phase1_data_audit.md", "type": "anemia imaging dataset",
     "demographic_baseline": "UNKNOWN", "subject_level_splits": "UNKNOWN",
     "cross_device_or_site": "UNKNOWN", "duplicate_or_leakage_check": "NO",
     "evidence": "2,015 unique images among 4,262 files (52.7% redundant); 419 MD5 "
                 "hashes shared with CP-AnemiC, which is distributed as a separate "
                 "dataset. Phase 9B read Asare et al. 2023, which names this collection "
                 "in its Data Availability Statement; that paper is scored in the Phase "
                 "9B table, and this dataset row is unchanged."},
    {"key": "Ghana fingernails (Mendeley 2xx4j3kjg2)",
     "cited_in": "phase1_data_audit.md", "type": "anemia imaging dataset",
     "demographic_baseline": "UNKNOWN", "subject_level_splits": "UNKNOWN",
     "cross_device_or_site": "UNKNOWN", "duplicate_or_leakage_check": "NO",
     "evidence": "2,097 unique among 4,260 files (50.8% redundant); shares a "
                 "participant numbering roster with the conjunctiva set "
                 "(non-anemic Jaccard 1.000). Phase 9B read Asare et al. 2023, which "
                 "names this collection in its Data Availability Statement; that paper is "
                 "scored in the Phase 9B table, and this dataset row is unchanged."},
    {"key": "Eyes-Defy-Anemia",
     "cited_in": "phase1_data_audit.md", "type": "anemia imaging dataset",
     "demographic_baseline": "UNKNOWN", "subject_level_splits": "YES",
     "cross_device_or_site": "YES", "duplicate_or_leakage_check": "UNKNOWN",
     "evidence": "Ships one folder per participant across two sites (India, Italy), so "
                 "subject-level structure and a site split are available by "
                 "construction. Devices are two variants of one phone."},
    {"key": "Hb-PPG dataset paper",
     "cited_in": "phase4_ppg_gate.md", "type": "PPG dataset",
     "demographic_baseline": "UNKNOWN", "subject_level_splits": "UNKNOWN",
     "cross_device_or_site": "NO", "duplicate_or_leakage_check": "UNKNOWN",
     "evidence": "One device for all 252 subjects, stated in the README. The README "
                 "reports per-channel SNR (850 nm 19.04 dB, 940 nm 16.44 dB) without "
                 "defining the SNR; this project could not reproduce the ordering."},
    {"key": "MOBIUS",
     "cited_in": "phase2_calibration.md", "type": "ocular imaging dataset",
     "demographic_baseline": "N/A", "subject_level_splits": "YES",
     "cross_device_or_site": "YES", "duplicate_or_leakage_check": "UNKNOWN",
     "evidence": "3 phones x 3 lighting x 100 subjects, documented in the README; "
                 "subject id is in every filename. Not an Hb dataset, so a demographic "
                 "baseline does not apply."},
    {"key": "SBVPI",
     "cited_in": "phase2_calibration.md", "type": "ocular imaging dataset",
     "demographic_baseline": "N/A", "subject_level_splits": "YES",
     "cross_device_or_site": "NO", "duplicate_or_leakage_check": "UNKNOWN",
     "evidence": "One folder per subject; single studio camera (Canon EOS 60D in EXIF)."},
    # ---- Phase 7 Task 3B: an external candidate whose FULL TEXT was read (2026-09-13).
    # "NOT REPORTED" is used only for papers whose full text this project read; it is
    # distinct from UNKNOWN (paper not read) and from NO (this project measured a
    # problem the check would have caught). NOT REPORTED is never "audited and failed".
    {"key": "BPANet - Lin et al. 2025, J Imaging Inform Med (PMC11950610)",
     "cited_in": "external_audit_availability.md", "type": "external anemia model (full text read)",
     "demographic_baseline": "NOT REPORTED", "subject_level_splits": "NOT REPORTED",
     "cross_device_or_site": "NOT REPORTED", "duplicate_or_leakage_check": "NOT REPORTED",
     "evidence": "Full text read via PMC. Demographic baseline: an ablation REMOVING age and "
                 "gender from the image model is reported (MAE 1.460 without vs 1.212 with), "
                 "but no demographics-only or population-mean model. Splits: '5-fold cross "
                 "validation with 140 epochs' on EYES-DEFY-ANEMIA and 4-fold on the NTUH set; "
                 "the unit of the fold (patient vs image) and any seed are not stated (on "
                 "Eyes-Defy one image per subject makes the two coincide; on NTUH, 3 body "
                 "parts per patient, it is not stated). Cross-site: 'This dataset collects "
                 "images from 218 patients in Italy and India' - pooled, no per-country result; "
                 "the prospective NTUH set is evaluated separately with the model 'retrained', "
                 "not as a transfer test. Duplicate/leakage check: not mentioned. Data: "
                 "'available from the corresponding authors upon reasonable request'. Code: "
                 "no statement. Reported MAE 1.212 g/dL (Eyes-Defy, 5-fold CV), 2.024 (NTUH)."},
    {"key": "Prahl haemoglobin compilation (Gratzer, Kollias)",
     "cited_in": "simulation/constants.py", "type": "optical reference data",
     "demographic_baseline": "N/A", "subject_level_splits": "N/A",
     "cross_device_or_site": "N/A", "duplicate_or_leakage_check": "N/A",
     "evidence": "Reference spectra, not a predictive study."},
    {"key": "Jacques 2013 tissue optics review",
     "cited_in": "simulation/constants.py", "type": "optical reference data",
     "demographic_baseline": "N/A", "subject_level_splits": "N/A",
     "cross_device_or_site": "N/A", "duplicate_or_leakage_check": "N/A",
     "evidence": "Reference parameters, not a predictive study."},
    {"key": "Jiang et al. camspec database",
     "cited_in": "phase4_ppg_gate.md", "type": "camera characterisation",
     "demographic_baseline": "N/A", "subject_level_splits": "N/A",
     "cross_device_or_site": "YES", "duplicate_or_leakage_check": "N/A",
     "evidence": "28 cameras measured 400-720 nm."},
]


def main() -> int:
    paths.ensure_dirs()

    # ---------------------------------------------------- manifest ----------
    L = ["# Dataset manifest\n\n",
         "Generated by `scripts/dataset_manifest_and_literature_phase5.py`. Presence and size are read "
         "from disk; source and licence are recorded from the download provenance.\n\n",
         "> **Licence status, verified 2026-09-12 (Phase 6.5) from each source's landing page "
         "or access form - none ships a licence file.** 4 are CC BY 4.0 (both Ghana Mendeley "
         "sets, CP-AnemiC, Hb-PPG); 2 are custom non-commercial research agreements that "
         "forbid redistribution (SBVPI, MOBIUS - MOBIUS alone permits scaled-down or "
         "watermarked figures); 2 state NO licence at all (NUS-8, Eyes-Defy-Anemia) and are "
         "used under the customary research-use expectation their pages imply, with the "
         "citations their authors request. Nothing here permits committing images or "
         "dataset-derived measurements to this repository, which remains the rule.\n\n"]
    L.append("| dataset | on disk | files | size | used for | licence |\n")
    L.append("| --- | --- | --- | --- | --- | --- |\n")
    total = 0
    for d in DATASETS:
        p = paths.RAW / d["dir"]
        present = p.exists()
        n, sz = 0, 0
        if present:
            for f in p.rglob("*"):
                if f.is_file():
                    n += 1
                    try:
                        sz += f.stat().st_size
                    except OSError:
                        pass
        total += sz
        d["present"], d["n_files"], d["bytes"] = present, n, sz
        L.append(f"| {d['name']} | {'yes' if present else '**NO**'} | {n:,} | "
                 f"{sz/1e9:.2f} GB | {d['used_for']} | {d['licence'].split(' - ')[0]} |\n")
    L.append(f"\nTotal on disk: **{total/1e9:.1f} GB** across "
             f"{sum(d['n_files'] for d in DATASETS):,} files.\n")

    L.append("\n## Sources and how to obtain\n\n")
    for d in DATASETS:
        L.append(f"### {d['name']}\n\n")
        L.append(f"* **Directory:** `data/raw/{d['dir']}/`\n")
        L.append(f"* **Source:** {d['source']}\n")
        L.append(f"* **Licence:** {d['licence']}\n")
        L.append(f"* **Obtain:** {d['obtain']}\n")
        L.append(f"* **Used for:** {d['used_for']}\n\n")

    L.append("## Deleted\n\n`scin-main` was removed in Phase 1.5. It contained no data "
             "(5 documentation files) and SCIN is dermatology imagery with no "
             "conjunctiva, no haemoglobin and no participant overlap, so its skin-tone "
             "labels could not be attached to any subject here. Recoverable from "
             "`github.com/google-research-datasets/scin`.\n")
    (paths.REPORTS / "dataset_manifest.md").write_text("".join(L), encoding="utf-8")
    print(f"wrote {paths.REPORTS / 'dataset_manifest.md'}")

    # ---------------------------------------------------- literature --------
    fields = ["demographic_baseline", "subject_level_splits", "cross_device_or_site",
              "duplicate_or_leakage_check"]
    predictive = [p for p in PAPERS if p["demographic_baseline"] != "N/A"]
    counts = {f: {v: sum(1 for p in predictive if p[f] == v)
                  for v in ("YES", "NO", "NOT REPORTED", "UNKNOWN")} for f in fields}

    M = ["# Literature positioning - evidence gathering only\n\n",
         "Generated by `scripts/dataset_manifest_and_literature_phase5.py`.\n\n",
         "> ## ⚠️ READ THIS BEFORE USING ANY NUMBER BELOW\n>\n",
         f"> This table covers **only the {len(PAPERS)} sources already cited in this "
         "project's own reports**, of which only "
         f"**{len(predictive)} are predictive studies or datasets** where these "
         "attributes apply. No new literature was read for it (Phase 5). **Phase 9B "
         f"(2026-09-20) read {len(lit9b.obtained())} full texts against six criteria; "
         "that audit is the section at the end of this file**, and its counts, not "
         "these, are the ones to cite.\n>\n",
         "> **The sample is far too small to support any general claim about the "
         "anemia-estimation literature.** It cannot support statements of the form "
         "'most papers do not report X'. What it can support is a statement about "
         "these specific sources, and a statement about what this project could "
         "*verify* rather than what the papers claim.\n>\n",
         "> Attributes are marked **UNKNOWN** where this project consulted the dataset "
         "and its documentation but not the full paper. UNKNOWN is not evidence of "
         "absence. The one exception is `duplicate_or_leakage_check = NO`, which is "
         "recorded only where this project **measured** duplicates that a check would "
         "have caught.\n\n"]

    M.append("## Counts across the "
             f"{len(predictive)} applicable sources\n\n")
    M.append("| attribute | YES | NO (measured by this project) | NOT REPORTED (full text read) | UNKNOWN (not read) |\n| --- | --- | --- | --- | --- |\n")
    for f in fields:
        c = counts[f]
        M.append(f"| {f.replace('_', ' ')} | {c['YES']} | {c['NO']} | {c['NOT REPORTED']} | {c['UNKNOWN']} |\n")

    M.append("\n## Per source\n\n")
    M.append("| source | type | demographic baseline | subject-level splits | "
             "cross-device/site | duplicate check |\n")
    M.append("| --- | --- | --- | --- | --- | --- |\n")
    for p in PAPERS:
        M.append(f"| {p['key']} | {p['type']} | {p['demographic_baseline']} | "
                 f"{p['subject_level_splits']} | {p['cross_device_or_site']} | "
                 f"{p['duplicate_or_leakage_check']} |\n")

    M.append("\n## Evidence for each entry\n\n")
    for p in PAPERS:
        if p["evidence"]:
            M.append(f"* **{p['key']}** (cited in `{p['cited_in']}`): {p['evidence']}\n")

    M.append("\n## What these counts do and do not support\n\n")
    nod = counts["duplicate_or_leakage_check"]["NO"]
    M.append(f"**Supported:** in {nod} of the "
             f"{len(predictive)} applicable sources, this project directly measured "
             "duplicate or overlap problems that a duplicate check would have caught - "
             "52.7% and 50.8% redundancy in the two Ghana sets, and 419 MD5 hashes "
             "shared between two datasets distributed separately. That is a measurement "
             "of the data, not an inference about the papers.\n\n")
    M.append(f"**Supported:** {counts['demographic_baseline']['YES']} of the applicable "
             "sources are known to report a demographic baseline. Phase 4 found that "
             "sex alone predicts haemoglobin at MAE 0.831 g/dL in the Hb-PPG cohort, "
             "beating every PPG model tested - so the presence or absence of that "
             "baseline materially changes how a reported result should be read.\n\n")
    M.append("**NOT supported:** any claim that the wider literature omits these "
             f"practices. The sample is {len(PAPERS)} sources, chosen because this project used "
             "them, not sampled from the field. Most attributes are UNKNOWN because the "
             "full papers were not read - that was outside this task's scope, and "
             "guessing would defeat its purpose.\n\n")
    M.append("**To make a general claim**, a systematic review with defined inclusion "
             "criteria and full-text screening would be required. This table is not "
             "that, and should not be cited as though it were.\n")
    M.append("\n## Phase 7 Task 3B extension - external candidates that could not be run\n\n")
    M.append("The external audit (`reports/external_audit_availability.md`) examined three "
             "candidates. One (BPANet) is a published paper whose full text was read and is "
             "added to the table above with the value **NOT REPORTED** where the paper does not "
             "state an item. **NOT REPORTED from a full-text read is not 'audited and failed'**: "
             "the harness never ran on that paper because nothing runnable was released, and "
             "a check that was never run has no verdict. The second candidate "
             "(mbedmutha/anemia-detection) is a student code repository, not a paper, and is "
             "excluded from this table by construction. The third (\"Hemo-ConViT\") could not "
             "be located as a primary source (0 hits in Europe PMC, Crossref and arXiv on "
             "2026-09-13) and is neither cited nor characterised here.\n\n")
    M.append("The caveats above stand unchanged: UNKNOWN is not evidence of absence, NOT REPORTED "
             "is not evidence of malpractice, and a sample this small supports no claim about "
             "the field.\n")
    # ---- Phase 9B (2026-09-20): the widened audit, rendered from hemosight.audit.literature
    M.append(lit9b.render_markdown())

    (paths.REPORTS / "literature_gap.md").write_text("".join(M), encoding="utf-8")
    print(f"wrote {paths.REPORTS / 'literature_gap.md'}")
    (paths.INTERIM / "phase5").mkdir(parents=True, exist_ok=True)
    (paths.INTERIM / "phase5" / "literature_counts.json").write_text(
        json.dumps({"counts": counts, "n_sources": len(PAPERS),
                    "n_applicable": len(predictive)}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
