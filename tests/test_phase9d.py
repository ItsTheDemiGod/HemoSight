"""Tests for Phase 9D, the power analysis.

Two jobs: keep the MDE arithmetic and the pre-declared verdict rule honest, and keep
retrospective power out of the codebase - the one thing this phase promised not to do.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from hemosight.evaluation import power as pw
from hemosight.evaluation import screening as scr
from hemosight.io import paths

RESULT = paths.INTERIM / "phase9d" / "power.json"
REPORT = paths.REPORTS / "phase9d_power.md"


# ------------------------------------------------------------------ the maths
def test_multipliers_are_the_declared_ones():
    assert pw.multiplier(0.80) == pytest.approx(2.802, abs=5e-4)
    assert pw.multiplier(0.90) == pytest.approx(3.242, abs=5e-4)


def test_mde_is_linear_in_se_and_larger_at_higher_power():
    assert pw.mde(0.05, 0.80) == pytest.approx(2.802 * 0.05, abs=1e-4)
    assert pw.mde(0.10, 0.80) == pytest.approx(2 * pw.mde(0.05, 0.80))
    assert pw.mde(0.05, 0.90) > pw.mde(0.05, 0.80)


def test_paired_se_is_exact_and_beats_unpaired_when_errors_correlate():
    rng = np.random.default_rng(0)
    a = rng.normal(size=400)
    b = a * 0.8 + rng.normal(scale=0.3, size=400)      # strongly correlated
    r = pw.paired_mean_se(a, b)
    assert r["se_paired"] == pytest.approx(np.std(a - b, ddof=1) / np.sqrt(400))
    assert r["se_paired"] < r["se_unpaired_for_reference"]
    assert 0.0 < r["pairing_variance_saving"] < 1.0
    assert r["observed_difference"] == pytest.approx(a.mean() - b.mean())


def test_power_at_a_prespecified_effect_matches_the_mde_definition():
    """power_at(MDE(80%)) must be 80% - the two are inverses of one another."""
    se = 0.04
    assert pw.power_at(pw.mde(se, 0.80), se) == pytest.approx(0.80, abs=1e-3)
    assert pw.power_at(pw.mde(se, 0.90), se) == pytest.approx(0.90, abs=1e-3)


def test_verdict_applies_the_pre_declared_rule_at_the_boundary():
    assert pw.verdict(0.10, 0.10) == "ADEQUATELY POWERED"     # <= is adequate
    assert pw.verdict(0.1001, 0.10) == "UNDERPOWERED"
    assert pw.verdict(float("nan"), 0.10) == "INDETERMINATE"


def test_who_boundary_translation():
    assert pw.NARROWEST_WHO_BAND_G_DL == 1.0
    assert not pw.moves_a_who_boundary(0.18)
    assert not pw.moves_a_who_boundary(0.99)
    assert pw.moves_a_who_boundary(1.0)


def test_subjects_moved_is_a_plain_count():
    assert pw.subjects_moved(0.116, 125) == pytest.approx(14.5)


# ------------------------------------------- the error this phase must not make
def test_retrospective_power_is_absent_from_the_module():
    """Phase 9D's central methodological promise, enforced rather than stated.

    `power_at` takes a caller-supplied effect size and is used only with the
    pre-declared yardstick; there must be no helper that reaches for an observed
    effect on its own.
    """
    forbidden = ("observed_power", "post_hoc_power", "retrospective_power",
                 "achieved_power", "observed_effect_power")
    for name in forbidden:
        assert not hasattr(pw, name), f"{name} must not exist in hemosight.evaluation.power"
    src = (paths.ROOT / "src" / "hemosight" / "evaluation" / "power.py").read_text(
        encoding="utf-8")
    assert "NOT compute" in src or "does NOT" in src, "the module must say what it refuses"


# ------------------------------------------------------------------ the results
def _result():
    if not RESULT.exists():
        pytest.skip("run scripts/power_analysis_phase9d.py first")
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_records_that_retrospective_power_was_not_computed():
    d = _result()
    assert "NOT COMPUTED" in d["method"]["retrospective_power"]
    assert d["method"]["multiplier_80"] == pytest.approx(pw.multiplier(0.80))


def test_every_block_is_internally_consistent():
    d = _result()

    def walk(node):
        if isinstance(node, dict):
            if "se" in node and "mde_80" in node:
                assert node["mde_80"] == pytest.approx(pw.mde(node["se"], 0.80), rel=1e-9)
                assert node["mde_90"] == pytest.approx(pw.mde(node["se"], 0.90), rel=1e-9)
                assert node["mde_90"] > node["mde_80"]
                assert node["verdict"] == pw.verdict(node["mde_80"],
                                                     node["clinical_yardstick"])
                assert node["power_at_the_yardstick"] == pytest.approx(
                    pw.power_at(node["clinical_yardstick"], node["se"]), rel=1e-9)
            for v in node.values():
                walk(v)

    walk(d["arms"])


def test_the_screening_yardstick_is_the_phase9a_margin_not_a_new_one():
    d = _result()
    s = d["arms"]["imaging_screening"]["image_cnn"]["specificity_at_matched_sensitivity"]
    assert s["clinical_yardstick"] == scr.MARGIN == 0.10
    assert "Phase 9A" in s["yardstick_source"]


def test_cross_site_is_reported_per_direction_and_never_pooled():
    d = _result()
    cs = d["arms"]["imaging_cross_site"]
    assert set(cs) == {"italy_to_india", "india_to_italy"}
    for k, v in cs.items():
        assert v["n"] == v["n_anaemic"] + v["n_non_anaemic"], k
        assert v["n"] < d["arms"]["imaging_screening"]["image_cnn"]["n"], (
            "a cross-site direction must use a fraction of the cohort")
    assert "pooled" not in json.dumps(cs).lower()


def test_the_verdicts_that_the_write_up_depends_on():
    """The four statements CLAUDE.md and final_results.md now carry."""
    d = _result()
    a = d["arms"]
    assert a["imaging_regression"]["verdict"] == "ADEQUATELY POWERED"
    assert a["ppg"]["mae_vs_sex_alone"]["verdict"] == "ADEQUATELY POWERED"
    assert (a["imaging_screening"]["image_cnn"]["specificity_at_matched_sensitivity"]
            ["verdict"] == "UNDERPOWERED")
    for k in ("italy_to_india", "india_to_italy"):
        assert (a["imaging_cross_site"][k]["specificity_at_matched_sensitivity"]["verdict"]
                == "UNDERPOWERED"), k
    # the least powered comparison in the project
    worst = max(a["imaging_cross_site"],
                key=lambda k: a["imaging_cross_site"][k][
                    "specificity_at_matched_sensitivity"]["mde_80"])
    assert worst == "italy_to_india"


def test_report_states_what_was_and_was_not_computed():
    if not REPORT.exists():
        pytest.skip("run scripts/power_analysis_report_phase9d.py first")
    txt = REPORT.read_text(encoding="utf-8")
    assert "NOT computed" in txt
    assert "retrospective" in txt.lower() and "post-hoc" in txt.lower()
    assert "minimum detectable effect" in txt.lower()
    assert "ADEQUATELY POWERED" in txt and "UNDERPOWERED" in txt
    # the load-bearing admission must be present
    assert "least powered" in txt
