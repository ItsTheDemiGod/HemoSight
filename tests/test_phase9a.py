"""Tests for Phase 9A, the screening reframe.

Two jobs: keep the screening arithmetic honest, and keep the correction this phase
forced from being quietly rolled back.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from hemosight.evaluation import screening as scr
from hemosight.io import paths

RESULT = paths.INTERIM / "phase9a" / "screening.json"
REPORT = paths.REPORTS / "phase9a_screening_metrics.md"


# ------------------------------------------------------------------ thresholds
def test_who_threshold_refuses_children():
    """An adult threshold must never be applied silently to a child."""
    with pytest.raises(ValueError, match="under 15"):
        scr.who_threshold(np.array([True, False]), np.array([30.0, 9.0]))


def test_who_threshold_refuses_missing_age():
    with pytest.raises(ValueError, match="age missing"):
        scr.who_threshold(np.array([True]), np.array([np.nan]))


def test_who_threshold_is_sex_specific():
    got = scr.who_threshold(np.array([True, False]), np.array([40.0, 40.0]))
    assert list(got) == [13.0, 12.0]


# --------------------------------------------------------------------- metrics
def test_refer_everybody_has_perfect_sensitivity_and_no_value():
    """The point the report must always make visible."""
    truth = np.array([1, 0, 0, 1, 0], dtype=bool)
    m = scr.screening_metrics(truth, np.ones(5, dtype=bool))
    assert m["sensitivity"] == 1.0
    assert m["specificity"] == 0.0
    assert m["referral_rate"] == 1.0
    assert m["false_referral_rate"] == pytest.approx(0.6)


def test_flagging_nobody_gives_infinite_number_needed_to_screen():
    truth = np.array([1, 0, 1, 0], dtype=bool)
    m = scr.screening_metrics(truth, np.zeros(4, dtype=bool))
    assert m["sensitivity"] == 0.0
    assert m["n_anaemic_flagged"] == 0
    assert m["number_needed_to_screen"] == float("inf")


def test_number_needed_to_screen_is_one_over_detected_per_screened():
    truth = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0], dtype=bool)
    call = np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=bool)
    # one true case detected in ten screened
    assert scr.screening_metrics(truth, call)["number_needed_to_screen"] == pytest.approx(10.0)


def test_operating_point_never_sees_the_test_labels():
    """nested_calls must pick its cut on the train fold only.

    Constructed so that the test fold's own optimal cut is far from the train fold's:
    if the implementation peeked, the held-out calls would be perfect.
    """
    rng = np.random.default_rng(0)
    n = 200
    truth = rng.random(n) < 0.4
    scores = np.where(truth, 11.0, 14.0)
    scores[:20] = 20.0            # 20 subjects with a deliberately misleading score
    truth[:20] = True
    folds = [(np.arange(20, n), np.arange(0, 20))]
    out = scr.nested_calls(scores, truth, folds)
    # the held-out 20 all score 20.0, above any train-derived cut, so none are flagged
    assert out["call"][:20].sum() == 0, "the cut must come from the train fold alone"


def test_plugin_rule_is_insensitive_for_a_shrunken_predictor():
    """Why Phase 7's sensitivity 0.00 is a property of the rule, not only the model."""
    truth = np.array([True] * 10 + [False] * 10)
    thr = np.full(20, 12.0)
    shrunk = np.full(20, 13.5)      # every prediction pulled to the cohort mean
    assert scr.screening_metrics(truth, scr.plugin_calls(shrunk, thr))["sensitivity"] == 0.0


def test_margin_needs_both_size_and_a_ci_above_zero():
    assert scr.margin_cleared(0.20, 0.05)
    assert not scr.margin_cleared(0.20, -0.01), "a CI touching zero is not evidence"
    assert not scr.margin_cleared(0.05, 0.01), "below the declared margin"


def test_verdict_accepts_either_margin_direction():
    """The pre-declaration says the symmetric test counts equally."""
    assert scr.verdict(0.95, 0.60, 0.20, 0.05, float("nan"), float("nan")) == "USEFUL"
    assert scr.verdict(0.95, 0.60, 0.01, -0.05, 0.20, 0.05) == "USEFUL"
    assert scr.verdict(0.95, 0.60, 0.01, -0.05, 0.01, -0.05) == "MARGINAL"
    assert scr.verdict(0.80, 0.60, 0.20, 0.05, 0.20, 0.05) == "NOT USEFUL"
    assert scr.verdict(0.95, 0.10, 0.20, 0.05, 0.20, 0.05) == "NOT USEFUL"


# ------------------------------------------------------- the recorded findings
def _result():
    if not RESULT.exists():
        pytest.skip("run scripts/screening_reframe_metrics_phase9a.py first")
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_prevalence_and_cohort_match_the_record():
    r = _result()
    assert (r["imaging"]["n"], r["imaging"]["n_anaemic"]) == (216, 91)
    assert (r["ppg"]["n"], r["ppg"]["n_anaemic"]) == (252, 18)
    for arm in ("imaging", "ppg"):
        assert r[arm]["thresholds"]["n_under_15"] == 0
        assert "NOT RECORDED" in r[arm]["thresholds"]["pregnancy_status"]


def test_ppg_plugin_sensitivity_reproduces_phase7_zero():
    """Phase 7 recorded sensitivity 0.00. Every PPG model must still show it."""
    r = _result()
    for k, m in r["ppg"]["models"].items():
        if k == "population_mean":
            continue
        assert m["plugin_point"]["sensitivity"] == 0.0, k
        assert m["plugin_point"]["n_anaemic_flagged"] == 0, k


def test_no_model_earns_useful():
    r = _result()
    verdicts = [c["screening_verdict"] for c in r["imaging"]["comparisons"].values()]
    verdicts += [c["screening_verdict"] for c in r["ppg"]["comparisons"].values()]
    verdicts += [v["screening_verdict"]
                 for v in r["imaging_cross_site"]["directions"].values()]
    assert "USEFUL" not in verdicts, f"a verdict changed: {verdicts}"


def test_the_within_site_effect_is_real_and_is_not_written_out():
    """The correction this phase forced. If this fails, the finding was rolled back."""
    r = _result()
    c = r["imaging"]["comparisons"]["colour_features_lab"]
    assert c["how_near_the_boundary"]["either_margin_cleared"] is True
    assert c["matched_sensitivity"]["specificity_difference"] >= scr.MARGIN
    assert c["matched_sensitivity"]["specificity_difference_ci"][0] > 0
    cnn = r["imaging"]["comparisons"]["image_cnn"]
    assert cnn["auroc_difference_ci"][0] > 0, "the AUROC advantage excludes zero"


def test_cross_site_fails_decisively_and_not_by_a_knife_edge():
    r = _result()
    d = r["imaging_cross_site"]["directions"]
    assert d["italy_to_india"]["cnn"]["sensitivity"] < 0.60, (
        "the cross-site sensitivity collapse is the binding reason for the verdict")
    assert d["india_to_italy"]["cnn"]["specificity"] < scr.SPEC_FLOOR
    for v in d.values():
        assert v["screening_verdict"] == "NOT USEFUL"


def test_pooled_auroc_is_decomposed_by_site():
    """The recorded 0.875 is pooled; the within-site figures must be on the record."""
    r = _result()
    ws = r["imaging"]["within_site"]
    assert ws["eyes_defy:India"]["image_cnn"]["auroc"] < 0.80
    assert ws["eyes_defy:Italy"]["image_cnn"]["auroc"] > 0.85
    india = ws["eyes_defy:India"]["comparisons"]["image_cnn"]["auroc_difference_ci"]
    assert india[0] < 0 < india[1], "within India the CNN advantage spans zero"


# --------------------------------------------------------------- report hygiene
def test_report_leads_with_the_baseline_comparison_not_auroc():
    if not REPORT.exists():
        pytest.skip("run scripts/screening_reframe_report_phase9a.py first")
    txt = REPORT.read_text(encoding="utf-8")
    head = txt[:txt.index("## 2.")]
    assert "THE COMPARISON THAT DECIDES IT" in head
    assert "demographic baseline" in head
    assert "CORRECTION" in head, "the correction must be in the lead, not buried"


def test_the_retired_phrase_is_not_reused_as_a_claim():
    """'moves no clinical threshold' is retired; it may only appear as quoted history."""
    claude = (paths.ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    for line in claude.splitlines():
        if "moves" in line and "no clinical threshold" in line:
            assert ('"' in line or "retired" in line or "corrected" in line), (
                f"the retired phrase is being asserted, not quoted: {line!r}")


def test_report_states_the_pregnancy_limitation():
    if not REPORT.exists():
        pytest.skip("run scripts/screening_reframe_report_phase9a.py first")
    txt = REPORT.read_text(encoding="utf-8").lower()
    assert "pregnancy status is not recorded" in txt
    assert "over-called anaemic" in txt
