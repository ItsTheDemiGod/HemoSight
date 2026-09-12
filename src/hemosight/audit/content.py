"""The content model: every user-facing sentence about a check, in one place.

Two audiences, equally: a researcher who needs every number, caveat and bound intact,
and a first-time visitor who needs to know what happened and what it means. The plain
layer is the DEFAULT; the technical layer is one click away and never removed.

The rule that governs every string here: **simplify the sentence, never the claim.**
  - INSUFFICIENT DATA stays a first-class outcome. Plain wording is "we could not check
    this - your file did not include X", never anything that reads as a pass.
  - A p-value at the permutation floor is still a bound, in plain words: "this is the
    smallest p-value this many permutations can produce; the true value may be smaller."
  - A verdict close to its threshold still says so.
  - No plain sentence claims more certainty than the technical statement supports.

Each check carries:
  headline_plain(result)      one sentence: what happened, no jargon, from the measured values
  what_it_means_plain         why it matters to a real decision
  mechanism_plain             why this failure happens, in human terms
  mechanism_technical         the same mechanism computationally: estimate, null, folds, assumptions
  statement_technical         the check's own precise headline + explanation (preserved verbatim,
                              taken from the CheckResult at render time)
  what_to_do(result)          exactly one of FIXABLE / REPORT IT / STOP, visible to the user;
                              never phrased as a way to make a failing check pass
  provenance                  which phase of this project the check came from and what it caught

The worked examples are this project's own results. They are real and measured.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .verdict import FAIL, INSUFFICIENT, PASS

FIXABLE = "FIXABLE"
REPORT_IT = "REPORT IT"
STOP = "STOP"
CATEGORIES = (FIXABLE, REPORT_IT, STOP)

CATEGORY_PLAIN = {
    FIXABLE: ("A concrete methodological correction exists. It changes how the evidence is "
              "produced, not the model, and it can make the number worse - that is the point."),
    REPORT_IT: ("Nothing in the code fixes this. The honest response is to state the limitation "
                "next to the result, every time the result appears."),
    STOP: ("The result says the approach does not reach the accuracy the claim needs. The correct "
           "action is to report the negative result, not to search for a variant that passes."),
}

# Plain translations of the exact `missing` strings the checks emit. Anything not listed
# is shown as-is, so a new reason is never silently reworded.
MISSING_PLAIN = {
    "content hashes (image_path column or image directory)":
        "the images themselves (an image folder, or an image_path column pointing at them)",
    "a split column": "a split column saying which rows were used for training and which for testing",
    "split column": "a split column saying which rows were used for training and which for testing",
    "at least one of age, sex, device, site": "any of age, sex, device or site",
    "a completed run": "a completed run (the check raised an error, which is recorded, not hidden)",
}


@dataclass
class WhatToDo:
    category: str
    text: str

    def to_dict(self) -> dict:
        return {"category": self.category, "category_plain": CATEGORY_PLAIN[self.category],
                "text": self.text}


@dataclass
class CheckContent:
    check_id: str
    title_plain: str
    question_plain: str
    what_it_means_plain: str
    mechanism_plain: str
    mechanism_technical: str
    provenance: str
    headline_plain: Callable[[dict], str]
    what_to_do: Callable[[dict], WhatToDo]
    glossary_terms: list[str] = field(default_factory=list)

    def render(self, result: dict) -> dict:
        """The `plain` block attached to a CheckResult dict."""
        return {
            "title": self.title_plain,
            "question": self.question_plain,
            "headline": self.headline_plain(result),
            "what_it_means": self.what_it_means_plain,
            "mechanism": self.mechanism_plain,
            "mechanism_technical": self.mechanism_technical,
            "what_to_do": self.what_to_do(result).to_dict(),
            "provenance": self.provenance,
            "glossary_terms": list(self.glossary_terms),
        }


def _missing_plain(result: dict) -> str:
    items = result.get("missing") or []
    plain = [MISSING_PLAIN.get(m, m) for m in items]
    if not plain:
        return "We could not check this - the file did not include what the check needs."
    return "We could not check this - your file did not include " + "; ".join(plain) + "."


def _insufficient_todo(result: dict, what: str) -> WhatToDo:
    return WhatToDo(FIXABLE, f"Supply {what}, and run again. Until then this check has no verdict, "
                             "and the report says so; it must not be read as a pass.")


def _m(result: dict, key: str, default=None):
    return (result.get("measured") or {}).get(key, default)


# =============================================================================== checks
def _dup_headline(r: dict) -> str:
    if r["verdict"] == INSUFFICIENT:
        return _missing_plain(r)
    m = r["measured"]
    n = m.get("n_images", 0)
    cross = (m.get("n_exact_duplicate_groups_crossing_a_split", 0)
             + m.get("n_near_duplicate_groups_crossing_a_split", 0))
    rate = m.get("exact_duplicate_rate", 0.0)
    if r["verdict"] == FAIL and cross:
        return (f"{cross} group{'s' if cross != 1 else ''} of identical or near-identical images "
                f"sit on both sides of the train/test split, so the model was tested on "
                f"pictures it had already seen.")
    if r["verdict"] == FAIL:
        return (f"About {rate:.0%} of the {n} images are duplicates of another image in the "
                "file, and no split column was supplied, so whether they cross the split "
                "cannot be told.")
    if rate > 0:
        return (f"About {rate:.0%} of the {n} images are duplicates, but none of them sit on "
                "both sides of the split.")
    return f"No duplicate images were found among the {n} supplied."


def _dup_todo(r: dict) -> WhatToDo:
    if r["verdict"] == INSUFFICIENT:
        return _insufficient_todo(r, "the images (a folder or an image_path column)")
    if r["verdict"] == FAIL:
        return WhatToDo(FIXABLE, "Remove duplicates by content hash BEFORE splitting, and rebuild the "
                                 "split so that every copy of an image lands on the same side. "
                                 "Then re-run the model. The score will usually drop; the new score "
                                 "is the real one.")
    return WhatToDo(REPORT_IT, "Nothing to change. State in the write-up that duplicates were checked "
                               "by content hash and none cross the split; readers cannot tell that "
                               "from a score.")


def _split_headline(r: dict) -> str:
    if r["verdict"] == INSUFFICIENT:
        return _missing_plain(r)
    m = r["measured"]
    cross = m.get("n_subjects_in_more_than_one_split", 0)
    nominal, groups = m.get("nominal_subject_ids"), m.get("leakproof_groups")
    if r["verdict"] == FAIL:
        parts = []
        if cross:
            parts.append(f"{cross} subject{'s' if cross != 1 else ''} have data in more than one "
                         "part of the split, so the model was trained and tested on the same people")
        if nominal and groups and groups < nominal:
            parts.append(f"{nominal} subject ids collapse to {groups} genuinely separate people or "
                         "images once identical content is linked, so the split leaks even where "
                         "the ids look clean")
        if m.get("declared_groups_cutting_a_leakproof_component"):
            parts.append("the grouping the submitter declared cuts through linked records")
        return ("; ".join(parts) or "the split does not keep people apart") + "."
    return (f"Every one of the {m.get('n_subjects', '?')} subjects is on one side of the split "
            "only, and no identical content links records across sides.")


def _split_todo(r: dict) -> WhatToDo:
    if r["verdict"] == INSUFFICIENT:
        return _insufficient_todo(r, "a split column (train / calibration / test per row) and, "
                                     "if the check asked for them, the images")
    if r["verdict"] == FAIL:
        return WhatToDo(FIXABLE, "Split by connected components of (subject id, content hash) - every "
                                 "record that shares a person OR a pixel-identical image goes to the "
                                 "same side - not by subject id alone. Freeze the split with a seed "
                                 "and record it. This project's own splits collapsed 1,708 nominal "
                                 "ids into 1,067 leak-proof groups; the gap was the leak.")
    return WhatToDo(REPORT_IT, "Nothing to change. Record how the split was grouped and the seed, so "
                               "a reader can see that the model never met its test subjects.")


def _base_headline(r: dict) -> str:
    if r["verdict"] == INSUFFICIENT:
        return _missing_plain(r)
    m = r["measured"]
    name = (m.get("best_single_demographic") or "a demographic variable").replace("_", " ")
    mm, bm = m.get("model_mae"), m.get("best_single_demographic_mae")
    margin = m.get("model_advantage_over_best_single")
    narrow = m.get("margin_is_narrow")
    unit = " g/dL" if mm is not None and mm < 50 else ""
    if r["verdict"] == FAIL:
        s = (f"Knowing only the subject's {name} predicts the outcome as well as or better than "
             f"the model (error {bm:.2f}{unit} versus the model's {mm:.2f}{unit}).")
    else:
        s = (f"The model beats the best single demographic guess ({name}, {bm:.2f}{unit}) with an "
             f"error of {mm:.2f}{unit}.")
    if narrow and margin is not None:
        s += (f" The margin is small ({margin:+.3f}{unit}) compared with how much the outcome "
              "varies, so this verdict could flip with a different sample.")
    return s


def _base_todo(r: dict) -> WhatToDo:
    if r["verdict"] == INSUFFICIENT:
        return _insufficient_todo(r, "at least one of age, sex, device or site per row - and every "
                                     "such variable the data has, because a model can learn any of them")
    if r["verdict"] == FAIL:
        return WhatToDo(REPORT_IT, "No code change makes a model that loses to a demographic variable "
                                   "measure what it claims. Report the model beside the baseline on "
                                   "identical folds, and say which one wins. This project reported "
                                   "sex alone at 0.831 g/dL beating every model it built, and closed "
                                   "the arm.")
    return WhatToDo(REPORT_IT, "Keep the baseline in the results table, on identical folds, every time "
                               "the score is quoted. If the margin was flagged as small, say so.")


def _proxy_headline(r: dict) -> str:
    if r["verdict"] == INSUFFICIENT:
        return _missing_plain(r)
    m = r["measured"]
    worst = (m.get("worst_demographic") or "a demographic variable").replace("_", " ")
    frac = m.get("skill_explained_by_worst_demographic")
    probes = m.get("n_probes_above_base_rate", 0)
    where = m.get("probe_ran_on", "")
    if r["verdict"] == FAIL:
        s = (f"Most of what the model adds over a plain average - about {frac:.0%} - disappears "
             f"once {worst} is already known, so the model is largely detecting {worst}.")
        if probes:
            s += (f" The model's own output also reveals {worst} better than chance"
                  + (" (measured on the prediction vector, which is reported but is not a "
                     "finding on its own)." if "prediction vector" in where else "."))
        return s
    return (f"At most {frac:.0%} of the model's advantage is explained by any demographic "
            f"variable supplied ({worst} is the closest), so the model is not simply reading "
            "a demographic.")


def _proxy_todo(r: dict) -> WhatToDo:
    if r["verdict"] == INSUFFICIENT:
        return _insufficient_todo(r, "at least one demographic column - and, for a finding rather "
                                     "than a report, the model's internal representation as extra columns")
    if r["verdict"] == FAIL:
        return WhatToDo(REPORT_IT, "Report the model's error WITH the demographic already in the "
                                   "baseline, and state that the image or signal adds little beyond "
                                   "it. Removing the demographic from the inputs does not help: the "
                                   "model reads it from the data. This project's 'PPG + demographics' "
                                   "model scored inside the viable band at 0.824 g/dL and was a sex "
                                   "classifier; its image CNN 'beat demographics' until site was added "
                                   "to them.")
    return WhatToDo(REPORT_IT, "Report the increment the model adds over the demographic baseline, not "
                               "only its standalone score.")


def _perm_headline(r: dict) -> str:
    if r["verdict"] == INSUFFICIENT:
        m = r.get("measured") or {}
        if "p_floor" in m and "n_permutations" in m:
            return (f"We could not check this - {m['n_permutations']} permutations cannot produce a "
                    f"p-value below {m['p_floor']:.3f}, which is above the significance level asked "
                    "for. More permutations are needed, not a different model.")
        return _missing_plain(r)
    m = r["measured"]
    p, n, floor = m.get("p_empirical"), m.get("n_permutations"), m.get("p_floor")
    at_floor = m.get("p_is_at_the_floor")
    aware = m.get("construction") == "selection-aware"
    draws = m.get("draws_at_or_below_real")
    if draws is None:
        draws = max(0, round(p * (n + 1)) - 1)
    if r["verdict"] == PASS:
        s = ((f"None of the {n} shuffles scored as well as the real model" if draws == 0 else
              f"Only {draws} of the {n} shuffles scored as well as the real model")
             + f" (p = {p:.3g}), so the model has learned something real.")
    else:
        s = (f"{draws} of the {n} shuffles scored as well as or better than the real model "
             f"(p = {p:.2g}), so the model cannot be told apart from chance.")
    if at_floor:
        s += (f" {p:.3g} is the smallest p-value {n} permutations can produce; the true value "
              "may be smaller. It is a bound, not a measurement.")
    if aware:
        s += (" The shuffles re-ran the choice among the candidate models, so picking the best "
              "of several is priced in.")
    elif r["verdict"] == PASS and (m.get("n_candidates") or 1) <= 1:
        s += (" Only the submitted model was tested against the shuffles; if it was chosen as "
              "the best of several, that choice is not priced in.")
    return s


def _perm_todo(r: dict) -> WhatToDo:
    if r["verdict"] == INSUFFICIENT:
        return WhatToDo(FIXABLE, "Run more permutations so the floor 1/(n+1) sits below the "
                                 "significance level, or supply what the check asked for.")
    if r["verdict"] == FAIL:
        return WhatToDo(STOP, "A model indistinguishable from shuffled labels has found nothing. Do "
                              "not tune until it passes - a tuned pass against this null is the "
                              "selection effect the check exists to catch. Report it. This project's "
                              "hand-engineered PPG features permutation-tested at p = 0.978 and the "
                              "representation was closed.")
    return WhatToDo(REPORT_IT, "Report the empirical p beside any z-score, state the floor when the p "
                               "sits on it, and say whether the null re-ran the model selection. "
                               "Significance is not usefulness: this project's one surviving positive "
                               "(p <= 0.0041 at n = 240) improves on a constant by 0.05 g/dL.")


def _seed_headline(r: dict) -> str:
    if r["verdict"] == INSUFFICIENT:
        m = r.get("measured") or {}
        return ("We could not check this - fewer than three re-runs of the model under different "
                "random seeds were supplied, so the spread between runs cannot be measured.")
    m = r["measured"]
    ratio, sd, k = m.get("effect_to_seed_sd_ratio"), m.get("mae_sd"), m.get("n_seeds")
    eff = m.get("claimed_effect")
    if r["verdict"] == FAIL:
        return (f"Re-running the same model with a different random seed moves its error by about "
                f"as much as the effect being claimed ({k} runs; spread {sd:.2g} against an effect of "
                f"{eff:.3g}), so the claimed improvement could be luck of the seed.")
    return (f"The claimed effect ({eff:.3g}) is {ratio:.0f} times larger than the spread across "
            f"{k} re-runs with different seeds ({sd:.2g}), so it is not an artefact of one lucky run.")


def _seed_todo(r: dict) -> WhatToDo:
    if r["verdict"] == INSUFFICIENT:
        return _insufficient_todo(r, "the same model retrained under at least three seeds, as "
                                     "y_pred_seed__<k> columns")
    if r["verdict"] == FAIL:
        return WhatToDo(STOP, "An effect no bigger than seed noise is not an effect. Report the seed "
                              "spread beside the score and do not present the single best run. This "
                              "project's rule, declared before running, was to retract if the seed "
                              "spread was comparable to the real-vs-null gap.")
    return WhatToDo(REPORT_IT, "Report the number of seeds and the spread beside every score; quote "
                               "the seed-averaged prediction, never the best seed.")


def _sub_headline(r: dict) -> str:
    if r["verdict"] == INSUFFICIENT:
        return _missing_plain(r)
    m = r["measured"]
    ret, drop = m.get("retained_advantage_fraction"), m.get("n_subjects_dropped")
    losing = m.get("n_subgroups_where_model_loses_to_baseline", 0)
    near = m.get("retained_fraction_is_near_the_threshold")
    if r["verdict"] == FAIL and ret is None:
        return "The model does not beat a plain average, so there is no advantage to test for robustness."
    if r["verdict"] == FAIL:
        s = (f"Take away the {drop} subjects the model does best on and only {ret:.0%} of its "
             "advantage over a plain average remains, so the result rests on a small group of "
             "subjects.")
    else:
        s = (f"Take away the {drop} subjects the model does best on and {ret:.0%} of its advantage "
             "over a plain average remains, so the result is spread across the cohort.")
    if losing:
        s += f" In {losing} submitted subgroup{'s' if losing != 1 else ''} the model loses to the baseline."
    if near:
        s += " The retained fraction is close to the threshold, so this verdict is not stable."
    return s


def _sub_todo(r: dict) -> WhatToDo:
    if r["verdict"] == INSUFFICIENT:
        return _insufficient_todo(r, "held-out predictions for every subject (this check needs no "
                                     "extra column; it declined because there was no advantage to test)")
    if r["verdict"] == FAIL:
        return WhatToDo(REPORT_IT, "Report per-subgroup error, and the error after dropping the best "
                                   "decile, beside the headline score. Do not remove the 'difficult' "
                                   "subjects to improve it - that is the failure in reverse.")
    return WhatToDo(REPORT_IT, "Report the retained-advantage fraction and per-subgroup errors with "
                               "the score, so the reader sees the effect is not carried by a few.")


def _ceil_headline(r: dict) -> str:
    if r["verdict"] == INSUFFICIENT:
        return _missing_plain(r)
    m = r["measured"]
    n, above = m.get("n_features"), m.get("n_features_above_mi_null_p95", 0)
    fdr = (m.get("n_surviving_fdr_pearson", 0) or 0) + (m.get("n_surviving_fdr_spearman", 0) or 0)
    if r["verdict"] == FAIL:
        return (f"None of the {n} input features carries more information about the outcome than "
                "a shuffled outcome would, so the input has no signal for any model to find.")
    return (f"{above} of the {n} input features {'carries' if above == 1 else 'carry'} more "
            "information about the outcome than shuffling would produce"
            + (f", and {fdr} correlation{'s' if fdr != 1 else ''} survive{'s' if fdr == 1 else ''} "
               "correction for multiple testing" if fdr else "")
            + ", so the input could contain the target.")


def _ceil_todo(r: dict) -> WhatToDo:
    if r["verdict"] == INSUFFICIENT:
        return _insufficient_todo(r, "the model's input features as extra numeric columns")
    if r["verdict"] == FAIL:
        return WhatToDo(STOP, "When the inputs carry no information about the target, no model built "
                              "on them can; a better model is not the remedy. Report that the "
                              "representation is empty. This project found 0 of 51 PPG features above "
                              "the null and stopped building feature models - and then found, "
                              "separately, that the raw waveform did carry a small real signal.")
    return WhatToDo(REPORT_IT, "A non-empty input is a necessary condition, not a result. Report the "
                               "number of features above the null and the multiple-testing correction.")


CONTENT: dict[str, CheckContent] = {
    "duplicates": CheckContent(
        check_id="duplicates",
        title_plain="Duplicate images across the split",
        question_plain="Are the same pictures in both the training set and the test set?",
        what_it_means_plain=(
            "A model tested on pictures it was trained on gets credit for remembering, not for "
            "measuring. Duplicates are common in medical image collections - the same photograph "
            "filed under two names, or two datasets distributed separately that share files - "
            "and they are invisible in a results table."),
        mechanism_plain=(
            "When a copy of a training image sits in the test set, the model has already seen "
            "the answer. The score rises for reasons that have nothing to do with the body. "
            "This project found 419 identical images shared between two datasets that were "
            "published as independent sources; one was 87% contained inside the other."),
        mechanism_technical=(
            "MD5 over file bytes for exact duplicates; pHash and dHash with a Hamming threshold "
            "for near-duplicates; connected components over the near-duplicate graph; an "
            "ImageNet-embedding nearest-neighbour pass for semantic near-copies. The decisive "
            "statistic is the number of duplicate components whose members carry more than one "
            "split label. Duplicate rate alone is reported but does not fail the check unless a "
            "split is supplied and crossed."),
        provenance=("Phase 1 overlap check: CP-AnemiC and the Ghana conjunctiva set shared 419 MD5 "
                    "hashes and 98.2% of one fell within pHash 10 of the other; they were merged "
                    "into one site. Two other collections were 52.7% and 50.8% internally redundant."),
        headline_plain=_dup_headline, what_to_do=_dup_todo,
        glossary_terms=["content hash", "split", "near-duplicate"]),
    "split_integrity": CheckContent(
        check_id="split_integrity",
        title_plain="People kept apart across the split",
        question_plain="Was the model tested on people it never saw during training?",
        what_it_means_plain=(
            "If one person's images are split between training and test, the model can "
            "recognise the person rather than the condition. Splitting by row or by image "
            "instead of by person is the single most common way a medical model's score is "
            "inflated, and it cannot be seen in the score."),
        mechanism_plain=(
            "Subjects contribute several images, and identical images sometimes appear under "
            "different subject ids. A split that keeps subject ids apart can still put the same "
            "picture on both sides. This project's 1,708 nominal subject ids collapsed to 1,067 "
            "genuinely separate groups once identical content was linked; the difference is "
            "exactly what a plain subject split would have leaked."),
        mechanism_technical=(
            "Rows are grouped by connected components of a graph joining subject ids and "
            "content hashes (MD5 of the image). The check counts subject ids present in more "
            "than one split label, counts nominal ids against leak-proof components, and - if the "
            "submitter declared a grouping column - counts declared groups that cut through a "
            "component. Without images the content axis cannot be checked and the check declines "
            "on that axis rather than passing on the subject axis alone."),
        provenance=("Phase 1 splits: grouping by (subject_id, content hash) components collapsed "
                    "1,708 ids to 1,067 groups in the Ghana pool. An automated leak check fails "
                    "the split script on any violation."),
        headline_plain=_split_headline, what_to_do=_split_todo,
        glossary_terms=["split", "content hash", "connected components", "leakage"]),
    "demographic_baseline": CheckContent(
        check_id="demographic_baseline",
        title_plain="Beating the obvious guess",
        question_plain="Does the model do better than simply knowing the subject's sex, age, device or site?",
        what_it_means_plain=(
            "A screening model is only useful if it knows something a form would not have told "
            "you. Sex, age and where the data came from often predict the outcome surprisingly "
            "well on their own, and a model can learn to read them from the data. A score "
            "reported without this comparison cannot be interpreted."),
        mechanism_plain=(
            "Men naturally carry more haemoglobin than women - the WHO anaemia thresholds "
            "themselves differ by sex - so a model that has effectively learned to detect sex "
            "will look like it detects blood. This project measured exactly that in Phase 4: "
            "sex alone predicted haemoglobin with an error of 0.831 g/dL, better than every "
            "model built across two modalities. In Phase 6.5 the same thing happened with the "
            "collection site: two sites differed by 2.4 g/dL in mean haemoglobin, and an image "
            "model 'beat demographics' until site was added to them."),
        mechanism_technical=(
            "On identical whole-subject folds: the population mean, each submitted demographic "
            "alone (ridge), and all together, against the submitted predictions. The verdict "
            "compares the model's MAE with the best single-variable baseline; a margin below 5% "
            "of the target's SD is flagged as narrow. Every non-signal variable the model could "
            "have learned belongs in the baseline - site and device as much as sex and age."),
        provenance=("Phase 4 Task 3: sex alone 0.831 g/dL vs four-wavelength PPG 1.190; 'PPG + "
                    "demographics' 0.824 was a sex classifier. Phase 6.5: site + sex + age 1.273 "
                    "vs image CNN 1.301 on Eyes-Defy, after a first run that omitted site."),
        headline_plain=_base_headline, what_to_do=_base_todo,
        glossary_terms=["baseline", "MAE", "identical folds"]),
    "proxy_probe": CheckContent(
        check_id="proxy_probe",
        title_plain="The demographic in disguise",
        question_plain="Is the model's skill really a demographic variable wearing a model's clothes?",
        what_it_means_plain=(
            "A model can beat the plain average and still be adding nothing: if what it learned "
            "IS the subject's sex or site, then a baseline that already knows the sex or site "
            "gains nothing from it. This check asks how much of the model's advantage survives "
            "once the demographic is already on the table."),
        mechanism_plain=(
            "Take the model's advantage over a plain average. Now give the baseline the "
            "demographic variable too and ask how much of that advantage is left. If most of "
            "it vanishes, the model was a proxy for the demographic. A second probe asks the "
            "model's own output to guess the demographic; if it can, the demographic is in "
            "there. This project's 'PPG + demographics' model, at 0.824 g/dL, sat inside the "
            "viable band and added 0.007 to demographics alone."),
        mechanism_technical=(
            "For each submitted demographic: advantage over the population mean, versus the "
            "advantage remaining when the demographic is already in the model (stacked ridge on "
            "identical folds); the fraction explained is reported per variable and the worst is "
            "judged. A logistic probe recovers the demographic from a supplied representation; "
            "on the prediction vector alone it is reported but does not count as a finding, "
            "because a model legitimately given sex as an input encodes sex in its output."),
        provenance=("Phase 4 Task 3 and Phase 4.5's sex probe on learned representations "
                    "(43.6-52.3% against a 57.0% base rate: the deep PPG models did not become sex "
                    "classifiers; the feature model with demographics did)."),
        headline_plain=_proxy_headline, what_to_do=_proxy_todo,
        glossary_terms=["proxy", "baseline", "representation"]),
    "permutation": CheckContent(
        check_id="permutation",
        title_plain="Better than shuffled labels",
        question_plain="Is the model's score better than what pure chance would produce on this data?",
        what_it_means_plain=(
            "Shuffle the true answers among the subjects and score the model again, many times. "
            "If the real score is not clearly better than the shuffled ones, the model has found "
            "nothing. If it is, the model has found something real - which is a low bar: real is "
            "not the same as useful."),
        mechanism_plain=(
            "Every shuffle gives a score a model could get by luck. The p-value is the fraction "
            "of shuffles that did as well as the real model. Two traps: with n shuffles the "
            "smallest p-value you can ever see is 1/(n+1), so a p-value sitting exactly there is "
            "a bound, not a measurement; and if the model was picked as the best of several, the "
            "shuffles must re-run that choice, or the p-value flatters it. This project's one "
            "surviving positive result is p <= 0.0041 at 240 permutations - still the floor - and "
            "improves on predicting a constant by 0.05 g/dL."),
        mechanism_technical=(
            "Labels are permuted across subjects against the FIXED submitted predictions; the "
            "empirical p is (draws at or below the real MAE + 1)/(n + 1), reported with the floor "
            "1/(n+1) and a flag when it sits there; a parametric z is reported beside it and "
            "assumes a normal null. If y_pred__<name> candidate columns are supplied, the null "
            "re-selects the best candidate on each draw (selection-aware). This construction does "
            "not refit the model, so it is a different null from Phase 5's; verdicts, not p-values, "
            "are comparable across the two."),
        provenance=("Phase 4.5 ceiling: feature model p = 0.978 (worse than shuffled). Phase 5: "
                    "selection-aware p = 0.0164 at n = 60 -> 0.0041 at n = 240, at the floor both "
                    "times; z -5.02 -> -4.96, the two statistics moving in opposite directions."),
        headline_plain=_perm_headline, what_to_do=_perm_todo,
        glossary_terms=["permutation test", "p-value", "floor", "selection-aware", "null"]),
    "seed_stability": CheckContent(
        check_id="seed_stability",
        title_plain="Same model, different luck",
        question_plain="If you trained the same model again with a different random start, would the result hold?",
        what_it_means_plain=(
            "Training has randomness in it. Two runs of the same code give two scores. If the "
            "improvement being claimed is no bigger than the wobble between runs, the claim is "
            "about a lucky run, not about the method."),
        mechanism_plain=(
            "Compare the effect (how much better the model is than the null or the baseline) "
            "with the spread of scores across re-runs under different seeds. This project ran "
            "ten seeds and found a spread of 0.007 g/dL against an effect of 0.08 - eleven times "
            "larger - which is why the claim was kept. Its rule, declared before running, was to "
            "retract if the two were comparable."),
        mechanism_technical=(
            "MAE per submitted y_pred_seed__<k> column; SD across seeds (ddof = 1) against the "
            "claimed effect - by default the model's advantage over the population mean on "
            "identical folds, or the real-vs-null gap when supplied. Fewer than three seeds "
            "gives a range, not a spread, and the check declines."),
        provenance=("Phase 5 Task 1: 10 seeds, SD 0.0069, range 1.1069-1.1279, effect 0.0815, "
                    "ratio 11.9."),
        headline_plain=_seed_headline, what_to_do=_seed_todo,
        glossary_terms=["seed", "effect size"]),
    "subgroup_robustness": CheckContent(
        check_id="subgroup_robustness",
        title_plain="Carried by a few subjects?",
        question_plain="Does the result rest on a handful of people the model happens to do well on?",
        what_it_means_plain=(
            "A model can look good on average because it is very good on a few subjects and "
            "ordinary on the rest. Screening has to work on the next person, so an advantage "
            "carried by a small group is not an advantage."),
        mechanism_plain=(
            "Remove the tenth of subjects the model does best on and see how much of its "
            "advantage over a plain average survives. The trap is comparing the model before "
            "and after: removing easy subjects makes every model look worse, so the baseline "
            "has to be recomputed on the same reduced set. This project's surviving PPG result "
            "degraded from 1.11 to 1.23 g/dL after the drop but kept its advantage - a weak "
            "signal spread across the cohort, not a few lucky subjects."),
        mechanism_technical=(
            "Per-subject absolute error; drop the best decile; recompute both the model's MAE "
            "and the population-mean baseline's MAE on the retained subjects; report the "
            "fraction of the original advantage retained. Per submitted subgroup (sex, site, "
            "device, age band), count subgroups where the model loses to the baseline. A "
            "retained fraction within 10 points of the threshold is flagged as near it."),
        provenance=("Phase 5 Task 1: 1.1124 -> 1.2258 after dropping the best decile; the "
                    "harness re-reads that as retained advantage with the baseline recomputed."),
        headline_plain=_sub_headline, what_to_do=_sub_todo,
        glossary_terms=["decile", "baseline"]),
    "ceiling": CheckContent(
        check_id="ceiling",
        title_plain="Is the signal there at all?",
        question_plain="Do the inputs contain any information about the outcome, before any model is built?",
        what_it_means_plain=(
            "If the measurements fed to a model carry no information about the target, no model "
            "can succeed and a failed model is not a modelling failure. This check looks at the "
            "inputs directly, without a model, and asks whether any of them relate to the "
            "outcome more than chance."),
        mechanism_plain=(
            "For each input feature, measure how much it tells you about the outcome, then "
            "measure the same thing with the outcome shuffled. A feature that does no better "
            "than the shuffle is empty. This project's 51 hand-engineered PPG features were all "
            "below the shuffled null; the representation was closed - and then the raw waveform, "
            "tested separately, turned out to carry a small real signal the features had "
            "thrown away."),
        mechanism_technical=(
            "Mutual information per feature against the target, compared with the 95th "
            "percentile of MI under a shuffled target; Pearson and Spearman correlations with "
            "Benjamini-Hochberg FDR at q. The verdict is the count of features above the MI null "
            "and the count surviving FDR. It is a necessary-condition test on the representation, "
            "not on any model."),
        provenance=("Phase 4.5 ceiling analysis: 0 of 51 features above the MI null (max 0.061 vs "
                    "null p95 0.068); 4 raw p < 0.05 against 2.6 expected; 0 survive FDR."),
        headline_plain=_ceil_headline, what_to_do=_ceil_todo,
        glossary_terms=["mutual information", "FDR", "null"]),
}

# ============================================================================== glossary
GLOSSARY: dict[str, str] = {
    "MAE": "Mean absolute error: on average, how far the model's prediction is from the true "
           "value, in the target's own units (here grams of haemoglobin per decilitre of blood). "
           "Smaller is better.",
    "baseline": "The simplest competitor: predicting the average, or predicting from one obvious "
                "variable such as sex. A model that cannot beat it on the same folds is not "
                "measuring what it claims.",
    "identical folds": "The data was divided into the same groups for the model and for every "
                       "baseline, so the comparison is fair.",
    "split": "How the data was divided into the part used to train the model and the part used "
             "to test it. The test part must contain people the model never saw.",
    "leakage": "Information from the test set reaching the model during training - a shared "
               "person, a duplicated image, a decision tuned against the test score. It inflates "
               "the score without improving the model.",
    "content hash": "A fingerprint computed from an image's pixels. Two files with the same hash "
                    "are the same picture, whatever they are called.",
    "near-duplicate": "Two images that are not byte-identical but are the same picture - "
                      "re-saved, resized or slightly cropped. Perceptual hashes catch these.",
    "connected components": "Groups formed by following links: if record A shares a person with "
                            "B and B shares a picture with C, all three belong together and must "
                            "land on the same side of the split.",
    "permutation test": "Shuffle the true answers among the subjects many times and score the "
                        "model each time. The result shows what scores luck alone produces.",
    "p-value": "The fraction of shuffles that scored as well as the real model. Small means the "
               "real score is hard to get by luck.",
    "floor": "With n shuffles the smallest p-value that can appear is 1/(n+1). A p-value sitting "
             "exactly there is a bound - the true value may be smaller - not a measurement.",
    "null": "What the statistic looks like when there is nothing to find: the distribution of "
            "scores under shuffled labels.",
    "selection-aware": "When a model was chosen as the best of several, the shuffled runs re-do "
                       "that choice, so the p-value accounts for having picked the winner.",
    "seed": "The random starting point of a training run. Different seeds give different "
            "results from the same code; the spread between them is noise, not signal.",
    "effect size": "How much better the model is than the null or the baseline, in the target's "
                   "units. It has to be compared with the noise around it to mean anything.",
    "proxy": "Something the model has learned in place of the thing it claims to measure - "
             "sex instead of haemoglobin, for instance.",
    "representation": "The internal numbers a model computes from its input before producing "
                      "a prediction. Probing them shows what the model has actually encoded.",
    "decile": "A tenth of the subjects. Dropping the best decile removes the 10% the model "
              "does best on.",
    "mutual information": "How much knowing one quantity reduces uncertainty about another. "
                          "Zero means no relationship of any kind, linear or not.",
    "FDR": "False discovery rate: when many correlations are tested at once, some look "
           "significant by chance. The correction keeps the expected fraction of false "
           "discoveries below a set level.",
    "INSUFFICIENT DATA": "The check could not run because the file lacked what it needs. It is "
                         "not a pass and not a fail; nothing was inferred from what could not be "
                         "measured.",
    "pre-registration": "Writing down the thresholds a result will be judged against before "
                        "seeing the result. It is what makes a verdict a verdict rather than an "
                        "interpretation.",
    "WHO band": "The World Health Organization's haemoglobin thresholds: anaemia below 12 g/dL "
                "in women and 13 in men; severity bands at 7, 10 and 11 g/dL.",
    "g/dL": "Grams per decilitre, the unit haemoglobin is measured in. Normal adult values are "
            "roughly 12-17.",
}


def enrich(result: dict) -> dict:
    """Attach the plain layer to a CheckResult dict. Unknown checks get nothing."""
    c = CONTENT.get(result.get("check_id"))
    if c is None:
        return result
    out = dict(result)
    out["plain"] = c.render(result)
    return out


def catalogue() -> list[dict]:
    """Static content per check, for the API and the pages."""
    return [{"check_id": c.check_id, "title_plain": c.title_plain, "question_plain": c.question_plain,
             "what_it_means_plain": c.what_it_means_plain, "mechanism_plain": c.mechanism_plain,
             "mechanism_technical": c.mechanism_technical, "provenance": c.provenance,
             "glossary_terms": c.glossary_terms} for c in CONTENT.values()]
