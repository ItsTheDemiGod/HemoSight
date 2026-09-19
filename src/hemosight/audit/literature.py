"""Phase 9B - the literature methodology audit, widened to every full text obtained.

This module holds the scoring of each paper read in full, the answer categories, the
counts, and the Markdown that `reports/literature_gap.md` embeds. It is data plus
rendering; nothing here is inferred from anything the papers do not say.

Rules fixed before scoring (2026-09-20):

* Five answer categories, never collapsed: YES (reported; section cited),
  NOT REPORTED (full text read, absent), UNKNOWN (text ambiguous or not read),
  NOT APPLICABLE (the criterion cannot apply), FULL TEXT UNAVAILABLE (identified,
  not obtained). A value may carry a qualifier after " - " (e.g. "YES - subject-level
  stated"); the category is the part before it.
* No paper is ever recorded as FAILING a check. This audit measures what is REPORTED.
  "Not reported" and "audited and failed" are different findings. The single measured
  NO in the project (Phase 1, duplicates in the Ghana collections) stays on the dataset
  rows of the Phase 5 table and is not transferred to any paper row.
* Two criteria are split into the two things they actually ask: split level and
  augmentation order; deduplication and a leakage statement.
"""

from __future__ import annotations

from typing import Any

CATEGORIES = ("YES", "NOT REPORTED", "UNKNOWN", "NOT APPLICABLE", "FULL TEXT UNAVAILABLE")

# criterion key -> (column label, what YES means)
CRITERIA: dict[str, tuple[str, str]] = {
    "demographic_baseline": (
        "demographic baseline",
        "a population-mean, sex, age or other demographics-only predictor is scored on the same folds"),
    "split_level": (
        "split level",
        "the paper states the unit of its train/test split (subject or image/random)"),
    "augmentation_order": (
        "augmentation vs split",
        "the paper states whether augmentation preceded or followed the split"),
    "cross_site_or_device": (
        "cross-site / device",
        "a result is reported on a site, cohort or camera absent from training"),
    "dedup_check": (
        "deduplication",
        "a deduplication step is mentioned"),
    "leakage_statement": (
        "leakage statement",
        "a train/test leakage-avoidance measure is stated explicitly"),
    "per_site_reporting": (
        "per-site reporting",
        "results are broken down per site or source where the study spans more than one"),
    "dataset": (
        "dataset used",
        "the dataset is identifiable from the text"),
}


def base_category(value: str) -> str:
    """The category part of a value such as 'YES - subject-level stated'."""
    head = value.split(" - ", 1)[0].strip()
    if head not in CATEGORIES:
        raise ValueError(f"not an allowed category: {value!r}")
    return head


# --------------------------------------------------------------------------- #
# The seven full texts. Files are in data/raw/literature/ (not tracked).
# Every 'detail' quotes or cites the section it comes from.
# --------------------------------------------------------------------------- #
PAPERS: list[dict[str, Any]] = [
    {
        "key": "lin-2025-bpanet",
        "citation": "Lin ET, Lu SC, Liu AS, Ko CH, Huang CH, Tsai CL, Fu LC. Deep learning-based "
                    "model for noninvasive hemoglobin estimation via body parts images: a "
                    "retrospective analysis and a prospective emergency department study. "
                    "J Imaging Inform Med 2025;38:775-792. DOI 10.1007/s10278-024-01209-4",
        "short": "Lin 2025 (BPANet)",
        "file": "10278_2024_Article_1209.pdf",
        "obtained": True,
        "task": "Hb regression + WHO-threshold classification",
        "single_site": False,
        "uses_ghana_collections": "no",
        "headline": "MAE 1.212 g/dL, accuracy 0.849, F1 0.828 (Eyes-Defy, 5-fold CV); MAE 2.024 (NTUH)",
        "availability": "data 'available from the corresponding authors upon reasonable request'; "
                        "no code statement",
        "scores": {
            "dataset": {
                "value": "YES - Eyes-Defy-Anemia + own collection",
                "detail": "Retrospective: EYES-DEFY-ANEMIA, '218 patients in Italy and India' "
                          "(Data Sets). Prospective: NTUH emergency department, Taiwan, 101 "
                          "patients, 268 images after screening (conjunctiva 100 / palm 85 / "
                          "fingernail 83), iPhone 13 (Data Sets)."},
            "demographic_baseline": {
                "value": "NOT REPORTED",
                "detail": "Tables 8 and 10 ablate age and gender OUT of the image model "
                          "(Eyes-Defy MAE 1.460 with neither vs 1.212 with both); no age/sex-only "
                          "or population-mean predictor is scored."},
            "split_level": {
                "value": "NOT REPORTED",
                "detail": "'5-fold cross validation' on Eyes-Defy and 'fourfold cross-validation, "
                          "with each body part evenly distributed across different folds' on NTUH "
                          "(Implementation Details; Results on NTUH Dataset). The fold unit "
                          "(patient vs image) is not stated. On Eyes-Defy one image per subject "
                          "makes the two coincide; on NTUH (268 images from 101 patients) it is "
                          "not stated."},
            "augmentation_order": {
                "value": "NOT APPLICABLE - headline result uses no augmentation",
                "detail": "'we did not apply data augmentation to the training set' (Discussion). "
                          "A random-rotation ablation is reported (Tables 12-13, no significant "
                          "change); its order relative to the folds is not stated."},
            "cross_site_or_device": {
                "value": "NOT REPORTED",
                "detail": "Eyes-Defy's Italy and India sites are pooled inside the CV. NTUH is a "
                          "separate cohort, but the model is 'retrained' on it with 4-fold CV "
                          "(Implementation Details) - no result on a site absent from training."},
            "dedup_check": {"value": "NOT REPORTED", "detail": "Not mentioned."},
            "leakage_statement": {"value": "NOT REPORTED", "detail": "Not mentioned."},
            "per_site_reporting": {
                "value": "NOT REPORTED - pooled only",
                "detail": "Every Eyes-Defy table pools Italy and India; no per-country result. "
                          "NTUH results are broken down per body part (Table 5), not per site."},
        },
    },
    {
        "key": "camporeale-2025-vit",
        "citation": "Camporeale M, Clemente F, Dimauro G, Lomonte N, Maglietta R, Pasciolla C, "
                    "Sacco D, Zaccaria GM. Highly reliable personalized noninvasive hemoglobin "
                    "estimation by using Vision Transformers and dual fine-tuning. Comput Biol "
                    "Med 2025;197:111026. DOI 10.1016/j.compbiomed.2025.111026",
        "short": "Camporeale 2025",
        "file": "1-s2.0-S0010482525013782-main.pdf",
        "obtained": True,
        "task": "Hb regression, patient-personalised",
        "single_site": True,
        "uses_ghana_collections": "no",
        "headline": "Hb-personalized model: MAE 0.25 g/dL, R2 0.94, sensitivity 1.0, specificity "
                    "0.72 (25 patients with >= 4 images). The non-personalised Hb-specialized "
                    "model 'did not achieve satisfactory results' (Table 1); no MAE is given for it",
        "availability": "'All the data acquired are protected by privacy laws'; no data or code "
                        "availability statement",
        "scores": {
            "dataset": {
                "value": "YES - own collection",
                "detail": "109 patients, 436 photos, haematology ward, Istituto Tumori 'Giovanni "
                          "Paolo II', Bari (3.2); one smartphone in a custom 3D-printed case with "
                          "macro lens and white LEDs (3.1); 125 photos retained for training after "
                          "downsampling over-represented Hb values (4.1)."},
            "demographic_baseline": {
                "value": "NOT REPORTED",
                "detail": "No demographic or per-patient-mean comparator; the comparison table "
                          "(Table 3) is against other papers' headline numbers."},
            "split_level": {
                "value": "YES - subject-level stated",
                "detail": "Hb-specialized model: 'fine-tuned on all the images in the dataset "
                          "except those of a single patient' (leave-one-patient-out, 4.2). The "
                          "personalised stage is leave-one-image-out within that patient by "
                          "design."},
            "augmentation_order": {
                "value": "NOT APPLICABLE - no augmentation reported",
                "detail": "The dataset was reduced, not augmented (4.1)."},
            "cross_site_or_device": {
                "value": "NOT APPLICABLE - single site, single device",
                "detail": "One hospital, one smartphone with a fixed LED (3.1-3.2). Limitations: "
                          "'the limited size and diversity of the dataset may constrain the "
                          "model's ability to generalize to broader populations'."},
            "dedup_check": {"value": "NOT REPORTED", "detail": "Not mentioned."},
            "leakage_statement": {
                "value": "YES",
                "detail": "'ensuring that the model is never trained or evaluated on the same "
                          "image, and by enforcing generalization across subjects' (4.2)."},
            "per_site_reporting": {
                "value": "NOT APPLICABLE - single site",
                "detail": "One site."},
        },
    },
    {
        "key": "nakahara-2026-slitlamp",
        "citation": "Nakahara Y, Shimizu E, Mizukami T, Nishimura H, Nakayama S, Ishikawa T, "
                    "Hirayama M, Hokama R, Sakurada K, Negishi K. Development of a deep learning "
                    "model to estimate anemia from palpebral conjunctiva taken with a portable "
                    "slit-lamp microscope. Bioengineering 2026;13:824. "
                    "DOI 10.3390/bioengineering13070824",
        "short": "Nakahara 2026",
        "file": "bioengineering-13-00824.pdf",
        "obtained": True,
        "task": "Hb regression + sex-specific threshold screening",
        "single_site": True,
        "uses_ghana_collections": "no",
        "headline": "video-level r = 0.42, MAE 1.375 g/dL (44 test videos); frame-level AUC 0.75, "
                    "video-level AUC 0.69",
        "availability": "data 'not publicly available due to privacy and ethical restrictions'; "
                        "upon reasonable request; no code statement",
        "scores": {
            "dataset": {
                "value": "YES - own collection",
                "detail": "225 Japanese participants, one centre (Keio University), Smart Eye "
                          "Camera slit-lamp on an iPhone 7 or iPhone SE 2nd gen (2.3); 9,903 "
                          "frames, train 8,082 / test 1,821 (Figure 1)."},
            "demographic_baseline": {
                "value": "NOT REPORTED",
                "detail": "No demographics-only comparator; subgroup analyses by age and sex are "
                          "listed as not performed (4.3)."},
            "split_level": {
                "value": "YES - subject-level stated",
                "detail": "'the dataset was partitioned at the participant level before model "
                          "development ... all frames derived from the same participant were "
                          "assigned exclusively to either the training or test set' (2.5)."},
            "augmentation_order": {
                "value": "YES - after split",
                "detail": "Partition 'before model development'; 'During training, data "
                          "augmentation, including random rotation, brightness and contrast "
                          "adjustment, and image blurring, was applied' (2.5)."},
            "cross_site_or_device": {
                "value": "NOT APPLICABLE - single centre",
                "detail": "'a single-center Japanese population using a single portable slit-lamp "
                          "device' (4.3). Two iPhone models were used for capture (2.3) but no "
                          "per-device or held-out-device result is reported."},
            "dedup_check": {"value": "NOT REPORTED", "detail": "Not mentioned."},
            "leakage_statement": {
                "value": "YES",
                "detail": "'To avoid data leakage arising from highly correlated images, the "
                          "dataset was partitioned at the participant level' (2.5); "
                          "'participant-level separation successfully prevented data leakage' "
                          "(4.3)."},
            "per_site_reporting": {
                "value": "NOT APPLICABLE - single site",
                "detail": "One site. Frame-level (n = 1,821) and video-level (n = 44) results "
                          "are reported separately (3.2-3.3)."},
        },
    },
    {
        "key": "asare-2023-ghana",
        "citation": "Asare JW, Appiahene P, Donkoh ET, Dimauro G. Iron deficiency anemia "
                    "detection using machine learning models: a comparative study of "
                    "fingernails, palm and conjunctiva of the eye images. Engineering Reports "
                    "2023;5(11):e12667. DOI 10.1002/eng2.12667",
        "short": "Asare 2023",
        "file": "Engineering Reports - 2023 - Asare - ....pdf",
        "obtained": True,
        "task": "binary anaemia classification (Hb < 11 g/dL)",
        "single_site": False,
        "uses_ghana_collections": "yes",
        "headline": "CNN accuracy 98.45% (conjunctiva), 98.33% (fingernails), 99.12% (palm)",
        "availability": "datasets released on Mendeley Data (conjunctiva nt7r8hv2pz, palm "
                        "ccr8cm22vz, fingernails 2xx4j3kjg2 - Data Availability Statement); "
                        "no code statement (Orange Data Mining v3.32 GUI)",
        "scores": {
            "dataset": {
                "value": "YES - the Ghana collections (own collection)",
                "detail": "710 children aged 6-59 months from 10 hospitals in Ghana (Table A1), "
                          "conjunctiva + palm + fingernails from the same participants ('All "
                          "three images were from the same patient/person', 3.2); Samsung Galaxy "
                          "Tab 7A via Kobo Collect (3.1). The Data Availability Statement names "
                          "the three Mendeley collections, two of which are the ones this "
                          "project audited in Phase 1."},
            "demographic_baseline": {
                "value": "NOT REPORTED",
                "detail": "Age and sex are collected as biodata (Table 2) but no demographics-only "
                          "predictor is scored."},
            "split_level": {
                "value": "YES - random split of the augmented image set stated",
                "detail": "'a random selection technique was used to divide the dataset for "
                          "training which consists of 70% ... 10% for validation and 20% for "
                          "testing' (3.2); also '10-fold cross-validation' (3.5). The unit is the "
                          "augmented image; no subject grouping is stated."},
            "augmentation_order": {
                "value": "YES - before split",
                "detail": "'After the augmentation of the images was completed, the final datasets "
                          "in Table 5 were used. Afterwards, a random selection technique was "
                          "used to divide the dataset' (3.2). 710 -> 2,635 images per modality by "
                          "rotation, flip and translation (Table 5)."},
            "cross_site_or_device": {
                "value": "NOT REPORTED",
                "detail": "Ten hospitals with per-hospital counts from 8 to 134 (Table A1); every "
                          "result pools all ten. No held-out-hospital result. One device model."},
            "dedup_check": {
                "value": "NOT REPORTED",
                "detail": "Not mentioned. (This project measured 52.7% / 50.8% byte-identical "
                          "redundancy in the conjunctiva and fingernail collections this paper "
                          "names - see the Phase 5 dataset rows and section 9B.3. That is a "
                          "property of the released data, recorded there, not a verdict on this "
                          "paper.)"},
            "leakage_statement": {"value": "NOT REPORTED", "detail": "Not mentioned."},
            "per_site_reporting": {
                "value": "NOT REPORTED - pooled only",
                "detail": "Results are broken down per body part (Tables 6-8), never per hospital, "
                          "although Table A1 lists ten."},
        },
    },
    {
        "key": "sabir-2024-fingertip",
        "citation": "Sabir H, Khan KU, Ishaq O, Alazeb A, Aljuaid H, Algarni A, Park J. "
                    "Fingertip video dataset for non-invasive diagnosis of anemia using "
                    "ResNet-18 classifier. IEEE Access 2024 (author version). "
                    "DOI 10.1109/ACCESS.2024.3398353",
        "short": "Sabir 2024",
        "file": "Fingertip_Video_Dataset_..._ResNet-18_Classifier.pdf",
        "obtained": True,
        "task": "Hb regression from fingertip video (smartphone PPG)",
        "single_site": True,
        "uses_ghana_collections": "no",
        "headline": "RMSE 0.81 (90/10 split) to 1.39 g/dL (80/20 split); re-implemented HemaApp "
                    "RMSE 1.70 on the same data",
        "availability": "dataset released 'for research purposes' via a request form; code on "
                        "GitHub (IntelliHb)",
        "scores": {
            "dataset": {
                "value": "YES - own collection",
                "detail": "150 thalassaemia patients, one day-care centre (Pakistan Thalassemia "
                          "Welfare Society, Rawalpindi), 1-minute fingertip video on a Redmi Note "
                          "10 (III.A, III.D); ages 6 months to 32 years; Hb 4.3-12.4 g/dL."},
            "demographic_baseline": {
                "value": "NOT REPORTED",
                "detail": "The comparator is a re-implementation of HemaApp. Figure 8 notes that "
                          "male and female Hb distributions differ; no sex or age predictor is "
                          "scored. Experiment 2 restricts to the 73 female records."},
            "split_level": {
                "value": "NOT REPORTED",
                "detail": "'80% of the data was used for training and remaining 20% was used for "
                          "testing' (IV.A-C) and a 90/10 variant. Experiment 1 builds 450 records "
                          "from three 15-s sub-clips per subject; whether sub-clips of one subject "
                          "were kept on one side is not stated. Experiment 3 has one record per "
                          "subject. The Conclusion states: 'We have tested our trained model on "
                          "secondary records taken from same patients whose values are used in "
                          "training.'"},
            "augmentation_order": {
                "value": "YES - before split",
                "detail": "Experiment 1: three sub-clips per video are made, then the 80/20 split "
                          "is applied to the 450 records (IV.A); grouping by subject not stated. "
                          "Experiment 3 (the headline) uses one record per subject, no augmentation."},
            "cross_site_or_device": {
                "value": "NOT APPLICABLE - single centre, single phone",
                "detail": "One collection site over three weeks; one phone model (III.A, III.D)."},
            "dedup_check": {"value": "NOT REPORTED", "detail": "Not mentioned."},
            "leakage_statement": {
                "value": "NOT REPORTED",
                "detail": "No leakage-avoidance measure is stated; the Conclusion's statement about "
                          "testing on the same patients is recorded above verbatim."},
            "per_site_reporting": {
                "value": "NOT APPLICABLE - single site",
                "detail": "One site."},
        },
    },
    {
        "key": "sehar-2025-hir",
        "citation": "Sehar N, Krishnamoorthi N, Kumar CV. Deep learning model-based detection "
                    "of anemia from conjunctiva images. Healthc Inform Res 2025;31(1):57-65. "
                    "DOI 10.4258/hir.2025.31.1.57",
        "short": "Sehar 2025",
        "file": "hir-2025-31-1-57.pdf",
        "obtained": True,
        "task": "binary anaemia classification",
        "single_site": False,
        "uses_ghana_collections": "cannot be determined",
        "headline": "stacking ensemble (VGG16 + ResNet-50 + InceptionV3) AUC 0.97, accuracy "
                    "89.48% on DCGAN-augmented images; KNN 78.2% on non-augmented",
        "availability": "not stated",
        "scores": {
            "dataset": {
                "value": "UNKNOWN - 54 own images + 710 from an online database whose identity "
                         "the text does not settle",
                "detail": "54 images captured on an iPhone XR (II.1) plus '710 images were "
                          "downloaded from an online database', cited as reference 15 = Dimauro "
                          "et al. 2023, Artif Intell Med (the Eyes-Defy-Anemia paper). But "
                          "Eyes-Defy has 218 subjects, while 710 - and Table 1's split of the "
                          "online set into 426 anaemic / 284 non-anaemic - matches the "
                          "CP-AnemiC / Ghana conjunctiva collection (710 files; 424 / 286 in "
                          "Asare et al. Table 3). The stated age range, 16-59 years, matches "
                          "neither (Eyes-Defy 19-88 years; Ghana 6-59 months). Which collection "
                          "was used cannot be determined from the text."},
            "demographic_baseline": {"value": "NOT REPORTED", "detail": "Not mentioned."},
            "split_level": {
                "value": "NOT REPORTED",
                "detail": "'divided into three subsets: 70% for training, 10% for validation using "
                          "10-fold cross-validation, and 20% for testing' (III). The unit is not "
                          "stated."},
            "augmentation_order": {
                "value": "NOT REPORTED",
                "detail": "DCGAN augmentation 764 -> 4,315 images, 'then used in the deep learning "
                          "models for classification' (III); whether the generator was trained "
                          "and sampled before or after the split is not stated."},
            "cross_site_or_device": {
                "value": "NOT REPORTED",
                "detail": "Two sources (own iPhone XR captures and the downloaded set) are pooled; "
                          "no held-out-source result."},
            "dedup_check": {"value": "NOT REPORTED", "detail": "Not mentioned."},
            "leakage_statement": {"value": "NOT REPORTED", "detail": "Not mentioned."},
            "per_site_reporting": {
                "value": "NOT REPORTED - pooled only",
                "detail": "Two sources, one set of results."},
        },
    },
    {
        "key": "zhao-2024-emoglobin",
        "citation": "Zhao L, Vidwans A, Bearnot CJ, Rayner J, Lin T, Baird J, Suner S, Jay GD. "
                    "Prediction of anemia in real-time using a smartphone camera processing "
                    "conjunctival images. PLoS ONE 2024;19(5):e0302883. "
                    "DOI 10.1371/journal.pone.0302883",
        "short": "Zhao 2024",
        "file": "journal.pone.0302883.pdf",
        "obtained": True,
        "task": "Hb estimate from a fixed RAW high-hue-ratio algorithm; anaemia-threshold "
                "classification (prospective validation)",
        "single_site": True,
        "uses_ghana_collections": "no",
        "headline": "accuracy 75.4%; AUC 0.76 at the sex-specific anaemia threshold, 0.92 at "
                    "7 g/dL; Bland-Altman bias 0.10, LOA (-4.73, 4.93) g/dL",
        "availability": "data released (Zenodo 8277462); app code not stated; patent held",
        "scores": {
            "dataset": {
                "value": "YES - own collection",
                "detail": "426 adult emergency-department patients, Rhode Island Hospital, "
                          "June 2022 - February 2023, iPhone X, RAW capture under ambient light "
                          "(Study design; Image capture)."},
            "demographic_baseline": {
                "value": "NOT REPORTED",
                "detail": "AUC is stratified by sex (women 0.74, men 0.79) - a stratification, not "
                          "a demographics-only comparator."},
            "split_level": {
                "value": "NOT APPLICABLE - no model was fitted",
                "detail": "The algorithm was derived on a prior dataset (their ref. 4); this study "
                          "is a validation cohort in which each of 426 subjects contributes one "
                          "estimate (the mean of four images)."},
            "augmentation_order": {"value": "NOT APPLICABLE - no training", "detail": "No training."},
            "cross_site_or_device": {
                "value": "YES - new cohort",
                "detail": "'we used a data set that was collected separately from a previously "
                          "reported training and validation set [4]' (Discussion). Same "
                          "institution's ED; whether the derivation device matched is not stated "
                          "in this paper."},
            "dedup_check": {
                "value": "NOT REPORTED",
                "detail": "'435 unique participating patients' (Results); no image-level "
                          "deduplication mentioned."},
            "leakage_statement": {
                "value": "YES",
                "detail": "'A separate validation study is an important requirement ... to avoid "
                          "data overfitting where noise in the derivation data set negatively "
                          "affects the accuracy of the device' (Discussion)."},
            "per_site_reporting": {
                "value": "NOT APPLICABLE - single site",
                "detail": "One site. Results are stratified by sex, by anaemia threshold and by "
                          "operator (ICC), not by site."},
        },
    },
]

# Papers identified by this project whose full text was NOT obtained. These count in
# the obtainability denominator and nowhere else.
IDENTIFIED_NOT_OBTAINED: list[dict[str, str]] = [
    {"short": "Appiahene 2023 (CP-AnemiC dataset paper)",
     "citation": "Appiahene P, Chaturvedi K, Asare JW, Donkoh ET, Prasad M. CP-AnemiC: a "
                 "conjunctival pallor dataset and benchmark for anemia detection in children. "
                 "Med Nov Technol Devices 2023;18:100244",
     "status": "FULL TEXT UNAVAILABLE - not sought in this phase; the dataset and its "
               "documentation were consulted in Phase 1 and Phase 5"},
    {"short": "Appiahene 2023 (Ghana conjunctiva / BioData Mining)",
     "citation": "Appiahene P, Asare JW, Donkoh ET, Dimauro G, Maglietta R. Detection of iron "
                 "deficiency anemia by medical images: a comparative study of machine learning "
                 "algorithms. BioData Min 2023;16:2",
     "status": "FULL TEXT UNAVAILABLE - not sought in this phase"},
    {"short": "Dimauro 2023 (Eyes-Defy-Anemia dataset paper)",
     "citation": "Dimauro G, Griseta ME, Camporeale MG, Clemente F, Guarini A, Maglietta R. An "
                 "intelligent non-invasive system for automated diagnosis of anemia exploiting "
                 "a novel dataset. Artif Intell Med 2023;136:102477",
     "status": "FULL TEXT UNAVAILABLE - not sought in this phase; per-site results for it are "
               "quoted second-hand by Asare et al. 2023 (Italy 88% / India 75% accuracy) and "
               "are not scored here"},
    {"short": "Hb-PPG dataset paper (four-wavelength PPG, 252 subjects)",
     "citation": "the figshare record's associated paper (doi 10.6084/m9.figshare.22256143)",
     "status": "FULL TEXT UNAVAILABLE - not sought in this phase; README consulted in Phase 4"},
    {"short": "'Hemo-ConViT'",
     "citation": "no primary source located",
     "status": "FULL TEXT UNAVAILABLE - searched 2026-09-13 (Europe PMC, Crossref, arXiv: 0 "
               "hits); recorded in reports/external_audit_availability.md"},
]

# Phase 1 measurements about the Ghana collections, quoted for section 9B.3.
GHANA_OVERLAP_FACTS = {
    "md5_shared_cp_anemic_vs_ghana_conjunctiva": 419,
    "cp_anemic_files_byte_identical_to_ghana": "620 / 710 (87.3%)",
    "ghana_conjunctiva_redundancy_pct": 52.7,
    "ghana_fingernail_redundancy_pct": 50.8,
    "source": "reports/phase1_data_audit.md",
}


# --------------------------------------------------------------------------- #
# counts
# --------------------------------------------------------------------------- #
def obtained() -> list[dict[str, Any]]:
    return [p for p in PAPERS if p["obtained"]]


def counts() -> dict[str, dict[str, int]]:
    """Per criterion, how many obtained papers fall in each base category."""
    out: dict[str, dict[str, int]] = {}
    for crit in CRITERIA:
        c = {cat: 0 for cat in CATEGORIES}
        for p in obtained():
            c[base_category(p["scores"][crit]["value"])] += 1
        out[crit] = c
    return out


def multi_site_papers() -> list[dict[str, Any]]:
    return [p for p in obtained() if not p["single_site"]]


def obtainability() -> dict[str, int]:
    n_obt = len(obtained())
    n_not = len(IDENTIFIED_NOT_OBTAINED)
    return {"identified": n_obt + n_not, "full_text_obtained": n_obt,
            "not_obtained": n_not,
            "not_obtained_unlocated": sum(1 for x in IDENTIFIED_NOT_OBTAINED
                                          if "no primary source" in x["citation"]),
            "not_obtained_not_sought": sum(1 for x in IDENTIFIED_NOT_OBTAINED
                                           if "not sought" in x["status"])}


def ghana_usage() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"yes": [], "no": [], "cannot be determined": []}
    for p in obtained():
        out[p["uses_ghana_collections"]].append(p["short"])
    return out


def to_json() -> dict[str, Any]:
    return {"generated_for": "Phase 9B, 2026-09-20",
            "categories": list(CATEGORIES),
            "criteria": {k: v[0] for k, v in CRITERIA.items()},
            "n_full_text": len(obtained()),
            "n_multi_site": len(multi_site_papers()),
            "counts": counts(),
            "obtainability": obtainability(),
            "ghana_usage": ghana_usage(),
            "ghana_overlap_facts": GHANA_OVERLAP_FACTS,
            "papers": PAPERS,
            "identified_not_obtained": IDENTIFIED_NOT_OBTAINED}


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
def _row(cells: list[Any]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |\n"


def render_markdown() -> str:
    """The Phase 9B section embedded in reports/literature_gap.md."""
    ps = obtained()
    n = len(ps)
    c = counts()
    ob = obtainability()
    ms = multi_site_papers()
    gu = ghana_usage()
    M: list[str] = []
    A = M.append

    A("\n---\n\n## Phase 9B (2026-09-20) - the audit widened to every full text obtained\n\n")
    A(f"> **Sample: {n} papers, full text read.** This is a **convenience sample of "
      "accessible papers, not a systematic review**: no search strategy, no inclusion "
      "criteria, no screening log. Every count below is a count over these "
      f"{n} papers and supports a statement about them, not about the field. The "
      "Phase 5 caveats stand: **UNKNOWN is not evidence of absence**, NOT REPORTED is "
      "not 'audited and failed', and a sample this size is far too small to support "
      "any general claim about the anemia-estimation literature.\n>\n")
    A("> **Answer categories, kept distinct.** YES (reported; section cited) / "
      "NOT REPORTED (full text read, absent) / UNKNOWN (text ambiguous) / "
      "NOT APPLICABLE (the criterion cannot apply, e.g. cross-site for a single-site "
      "study) / FULL TEXT UNAVAILABLE (identified, not obtained). **No paper is "
      "recorded as failing a check.** The single measured NO in this project (Phase 1 "
      "duplicates in the Ghana collections) stays on the dataset rows above and is not "
      "transferred to any paper.\n\n")

    # ---- obtainability
    A("### 9B.0 Obtainability\n\n")
    A(f"**{ob['identified']} papers identified, {ob['full_text_obtained']} full texts "
      f"obtained** ({ob['full_text_obtained']}/{ob['identified']}). Of the "
      f"{ob['not_obtained']} not obtained, {ob['not_obtained_unlocated']} could not be "
      f"located as a primary source and {ob['not_obtained_not_sought']} were not sought "
      "in this phase (they are dataset papers whose data and documentation this project "
      "consulted directly). This is the same measurement Phase 7 made about released "
      "artefacts (0 of 3 candidates auditable), one level up: the text itself.\n\n")
    A(_row(["identified, not obtained", "status"]))
    A(_row(["---", "---"]))
    for x in IDENTIFIED_NOT_OBTAINED:
        A(_row([f"{x['short']} - {x['citation']}", x["status"]]))
    A("\n")

    # ---- counts
    A(f"### 9B.1 Counts per criterion, over the {n} full texts\n\n")
    A(_row(["criterion", "YES", "NOT REPORTED", "UNKNOWN", "NOT APPLICABLE", "what YES means"]))
    A(_row(["---"] * 6))
    for k, (label, meaning) in CRITERIA.items():
        cc = c[k]
        A(_row([label, cc["YES"], cc["NOT REPORTED"], cc["UNKNOWN"], cc["NOT APPLICABLE"],
                meaning]))
    A("\nFULL TEXT UNAVAILABLE is 0 in every row by construction: only obtained papers "
      "are scored, and the unobtained ones are listed in 9B.0.\n\n")

    # ---- the table
    A(f"### 9B.2 The full table ({n} papers x 8 recorded fields)\n\n")
    A("Split level and augmentation order are recorded separately, as are "
      "deduplication and a leakage statement, because each pair asks two different "
      "things. The qualifier after each dash is what the paper states.\n\n")
    A(_row(["paper", "dataset", "demographic baseline", "split level", "augmentation vs split",
            "cross-site / device", "dedup", "leakage statement", "per-site reporting"]))
    A(_row(["---"] * 9))
    for p in ps:
        s = p["scores"]
        A(_row([p["short"], s["dataset"]["value"], s["demographic_baseline"]["value"],
                s["split_level"]["value"], s["augmentation_order"]["value"],
                s["cross_site_or_device"]["value"], s["dedup_check"]["value"],
                s["leakage_statement"]["value"], s["per_site_reporting"]["value"]]))
    A("\n#### Evidence, per paper\n\n")
    for p in ps:
        A(f"**{p['short']}** - {p['citation']}. *Task:* {p['task']}. *Headline:* "
          f"{p['headline']}. *Availability:* {p['availability']}.\n\n")
        for k, (label, _) in CRITERIA.items():
            A(f"* *{label}* - **{p['scores'][k]['value']}**. {p['scores'][k]['detail']}\n")
        A("\n")

    # ---- Task 3
    A("### 9B.3 The dataset-overlap consequence\n\n")
    f = GHANA_OVERLAP_FACTS
    A("**What this project measured (Phase 1, `reports/phase1_data_audit.md`).** "
      f"{f['md5_shared_cp_anemic_vs_ghana_conjunctiva']} distinct MD5 hashes are shared "
      "between CP-AnemiC and the Ghana conjunctiva collection (Mendeley nt7r8hv2pz), "
      f"which are distributed as separate datasets; {f['cp_anemic_files_byte_identical_to_ghana']} "
      "of CP-AnemiC's files are byte-identical to a Ghana file; and within the Ghana "
      f"conjunctiva and fingernail collections {f['ghana_conjunctiva_redundancy_pct']}% and "
      f"{f['ghana_fingernail_redundancy_pct']}% of files are byte-identical duplicates of "
      "another file in the same collection. These are properties of the released data.\n\n")
    A(f"**How many of the {n} audited papers use those collections.** "
      f"**{len(gu['yes'])}** ({', '.join(gu['yes']) or 'none'}) states that it does; "
      f"**{len(gu['cannot be determined'])}** ({', '.join(gu['cannot be determined']) or 'none'}) "
      "may - its 710 downloaded images are cited as Eyes-Defy-Anemia but match the "
      "CP-AnemiC / Ghana collection in count and class split, and the text does not "
      f"settle it; **{len(gu['no'])}** do not.\n\n")
    A("**Papers treating two overlapping collections as independent sources, or "
      "validating on one after training on the other: 0 of "
      f"{n}.** Asare et al. 2023 uses the conjunctiva, palm and fingernail collections as "
      "three modalities of the same 710 participants and says so ('All three images were "
      "from the same patient/person', 3.2); it does not use CP-AnemiC. No audited paper "
      "trains on one Ghana collection and reports a result on the other.\n\n")
    A("**What is and is not concluded.** For Asare et al. 2023 the fact recorded is: the "
      "paper states a random split of the augmented image set, and this project measured "
      "that the released collections it names contain byte-identical duplicates. Whether "
      "any duplicate pair straddled that paper's train/test boundary was **not tested here** "
      "- the paper's split is not released - and no conclusion about its reported "
      "accuracy is drawn. The overlap is a property of the data; its effect on any specific "
      "paper's result is unmeasured.\n\n")

    # ---- Task 4: what the counts support
    A("### 9B.4 What these counts do and do not support\n\n")
    db = c["demographic_baseline"]
    ps_ms = ", ".join(p["short"] for p in ms)
    A(f"**Supported, about these {n} papers only.**\n\n")
    A(f"* **Demographic baseline: {db['YES']} of {n} report one.** This count is complete - "
      "no UNKNOWN - because every full text was read. It supports the sentence "
      f"*'none of the {n} anaemia-estimation papers whose full text this project read "
      "scores a demographics-only predictor'*. It does not support *'the field omits "
      "it'*: the sample is small and was not drawn to represent the field. This project's "
      "own reason for caring is measured, not rhetorical: sex alone gives MAE 0.831 g/dL "
      "on the PPG cohort and site + sex + age AUROC 0.816 on Eyes-Defy, and neither "
      "number has a counterpart in any of these papers' comparisons.\n")
    A(f"* **Per-site reporting: of the {len(ms)} multi-site or multi-source papers "
      f"({ps_ms}), {c['per_site_reporting']['YES']} report a per-site result.** This is "
      f"the criterion Phase 9A made important - a pooled AUROC of 0.875 decomposed into "
      "0.688 (India) and 0.909 (Italy) on this project's own model - and it is the one "
      f"where the sample is thinnest: n = {len(ms)}. It supports a worked example, not a "
      "rate. One of the three (Lin 2025) pools the very two sites this project "
      "decomposed.\n")
    A(f"* **Deduplication: {c['dedup_check']['YES']} of {n} mention one. Leakage "
      f"statement: {c['leakage_statement']['YES']} of {n} state a leakage-avoidance "
      "measure** (leave-one-patient-out, participant-level partition, or a separately "
      "collected validation cohort). The two are different things and are counted "
      "separately for that reason.\n")
    sl = c["split_level"]
    A(f"* **Split level: {sl['YES']} of {n} state the unit of their split** (2 subject-level, "
      f"1 random over augmented images); {sl['NOT REPORTED']} do not state it; "
      f"{sl['NOT APPLICABLE']} fitted no model. **Augmentation order: "
      f"{c['augmentation_order']['YES']} of {n} state it** (2 before the split, 1 after); "
      f"{c['augmentation_order']['NOT REPORTED']} augments without stating the order; "
      f"{c['augmentation_order']['NOT APPLICABLE']} do not augment.\n")
    A(f"* **Cross-site / device: {c['cross_site_or_device']['YES']} of {n} reports a result "
      "on data absent from training** (a new prospective cohort; same institution). Of the "
      f"{len(ms)} multi-site papers, {sum(1 for p in ms if base_category(p['scores']['cross_site_or_device']['value']) == 'YES')} "
      "hold a site out. Single-site studies are recorded as NOT APPLICABLE, not as a "
      "failure; three of them say in their own limitations that external validation is "
      "needed.\n")
    A("* **An observation in the sample, not a finding.** Of the three papers that "
      "augment (Asare 2023, Sabir 2024, Sehar 2025), none states a subject-level split; "
      "two state augmentation before the split and one does not state the order. Their "
      "headline figures are 98-99% accuracy, RMSE 0.81-1.39 g/dL and AUC 0.97 "
      "respectively. The two papers that state a subject-level split report 69% "
      "accuracy (Nakahara 2026, video level) and, patient-personalised on 25 patients, "
      "98% (Camporeale 2025). Seven papers cannot establish whether any co-occurrence "
      "here is systematic, and no causal reading is offered.\n\n")
    A("**NOT supported.**\n\n")
    A("* Any statement of the form *'most papers in this field do not report X'*, *'the "
      "field publishes accuracy figures without the checks that would make them "
      "meaningful'*, or any rate with the field as its denominator. The denominator here "
      f"is {n} accessible papers; nothing about how they were obtained makes them "
      "representative.\n")
    A("* Any statement that a paper scored NOT REPORTED did not perform the check. "
      "The audit measures reporting.\n")
    A("* Any statement about the effect of the Ghana duplicates on any specific paper's "
      "result (9B.3).\n\n")
    A("**Recommendation on the project's framing (Task 5).** The sentence this project "
      "has carried since Phase 4.5 - that a demographic baseline is *'a contribution to a "
      "literature that frequently omits it'* - is **not supported at the rate it implies** "
      "and is narrowed to what the count supports: *none of the seven anaemia-estimation "
      "papers whose full text this project read reports a demographics-only baseline; "
      "this is a statement about those seven, from a convenience sample, not about the "
      "field*. The more specific claim the audit does license is about **pooled "
      "reporting**, and only as a worked example: all three multi-site papers read pool "
      "their sites, and this project has shown on its own model what a pooled number can "
      "conceal. To make any field-level claim, a systematic review with defined inclusion "
      "criteria and full-text screening would be required. This audit is not that.\n")
    return "".join(M)
