"""Tests for Phase 9E - the boundary statements.

Three jobs:
  * keep the required-n arithmetic honest, including the case the pre-declaration
    anticipated where the measured scaling slope cannot itself be trusted;
  * keep the guided-capture result labelled as an INTERPOLATION - the one thing that
    would do real damage if a later reader took it for a measurement;
  * keep the language pass from rotting, by asserting that the specific overstatements
    it removed do not come back.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from hemosight.evaluation import power as pw
from hemosight.io import paths

GUIDED = paths.INTERIM / "phase9e" / "guided_capture.json"
REQN = paths.INTERIM / "phase9e" / "required_n.json"
XSCI = paths.INTERIM / "phase9e" / "cross_site_intervals.json"
REPORT = paths.REPORTS / "phase9e_boundaries.md"
PHASE7 = paths.REPORTS / "phase7.md"
PHASE9A = paths.REPORTS / "phase9a_screening_metrics.md"


# --------------------------------------------------------------------- the maths
def test_required_group_n_inverts_the_mde():
    """Feeding the required n back through the SE scaling must land on the target."""
    n, mde_obs, target = 27, 0.3139, 0.10
    req = pw.required_group_n(n, mde_obs, target)
    assert req == pytest.approx(n * (mde_obs / target) ** 2)
    # SE shrinks as sqrt(n_obs / n_req), so the MDE at the required n is the target
    assert mde_obs * np.sqrt(n / req) == pytest.approx(target, rel=1e-9)


def test_required_group_n_is_monotone_and_respects_the_slope():
    assert pw.required_group_n(50, 0.20, 0.10) > pw.required_group_n(50, 0.15, 0.10)
    # a shallower slope means precision buys more slowly, so more subjects are needed
    assert (pw.required_group_n(27, 0.31, 0.10, slope=0.34)
            > pw.required_group_n(27, 0.31, 0.10, slope=0.50))


def test_required_group_n_rejects_nonsense():
    assert not np.isfinite(pw.required_group_n(27, float("nan"), 0.10))
    assert not np.isfinite(pw.required_group_n(27, 0.31, 0.0))


def test_total_n_for_group_uses_the_right_share():
    assert pw.total_n_for_group(266, 0.7158, "non_anaemic") == pytest.approx(266 / 0.2842,
                                                                             rel=1e-6)
    assert pw.total_n_for_group(120, 0.4213, "anaemic") == pytest.approx(120 / 0.4213,
                                                                         rel=1e-6)
    with pytest.raises(ValueError):
        pw.total_n_for_group(10, 0.5, "everyone")


def test_scaling_slope_recovers_a_known_rate():
    n = np.array([20, 40, 80, 160, 320], float)
    assert pw.scaling_slope(n, 0.7 / np.sqrt(n))["slope"] == pytest.approx(0.5, abs=1e-9)
    assert pw.scaling_slope(n, 0.7 / n ** 0.25)["slope"] == pytest.approx(0.25, abs=1e-9)
    assert not np.isfinite(pw.scaling_slope(np.array([10.0]), np.array([1.0]))["slope"])


# ------------------------------------------------------- the recorded Part B result
@pytest.mark.skipif(not REQN.exists(), reason="run scripts/phase9e_required_n.py")
def test_required_n_is_reported_for_the_group_that_carries_the_metric():
    """A specificity must be sized on non-anaemic subjects, a sensitivity on anaemic."""
    r = json.loads(REQN.read_text(encoding="utf-8"))["required"]
    for k, v in r.items():
        expected = "anaemic" if ("sensitivity" in k or "auroc" in k) else "non_anaemic"
        assert v["carrier_group"] == expected, k
        assert v["n_carrier_observed"] > 0
        assert v["headline_required_carrier_80"] > v["n_carrier_observed"], (
            f"{k}: an UNDERPOWERED comparison cannot need fewer subjects than it had")
        assert (v["headline_required_carrier_90"]
                > v["headline_required_carrier_80"]), k


@pytest.mark.skipif(not REQN.exists(), reason="run scripts/phase9e_required_n.py")
def test_both_slope_bases_are_kept_and_the_weak_fit_rule_is_applied_by_r2():
    """The headline may not be chosen by which answer is smaller."""
    r = json.loads(REQN.read_text(encoding="utf-8"))
    floor = r["method"]["fit_r2_floor"]
    for k, v in r["required"].items():
        assert v["measured_required_carrier_80"] > 0 and v["reference_required_carrier_80"] > 0, k
        assert v["slope_fit_is_trustworthy"] == (v["slope_fit_r2"] >= floor), k
        head = ("measured" if v["slope_fit_is_trustworthy"] else "reference")
        assert (v["headline_required_carrier_80"]
                == v[f"{head}_required_carrier_80"]), k
    # and on this data the rule did NOT simply pick the smaller number
    it = r["required"]["cross_site_italy_to_india"]
    assert it["headline_required_carrier_80"] < it["measured_required_carrier_80"]
    assert not it["slope_fit_is_trustworthy"]


@pytest.mark.skipif(not REQN.exists(), reason="run scripts/phase9e_required_n.py")
def test_phase9d_mdes_were_reproduced_before_anything_new_was_computed():
    r = json.loads(REQN.read_text(encoding="utf-8"))["reproduction"]
    assert r, "the reproduction block must not be empty"
    for k, v in r.items():
        assert v["ok"], k
        assert abs(v["recorded"] - v["reproduced"]) < 5e-3, k


# ------------------------------------------------------- the recorded Part A result
@pytest.mark.skipif(not GUIDED.exists(), reason="run scripts/phase9e_guided_capture.py")
def test_the_guided_capture_point_is_labelled_an_interpolation_everywhere():
    g = json.loads(GUIDED.read_text(encoding="utf-8"))
    assert "INTERPOLATION" in g["what_this_is"].upper()
    head = [r for r in g["gate_curve"] if r["is_headline"]]
    assert len(head) == 1 and not head[0]["is_measured_anchor"]
    # and in the two reader-facing places it appears
    for f in (REPORT, PHASE7):
        if f.exists():
            t = f.read_text(encoding="utf-8")
            assert "guided capture" in t.lower()
            assert "interpolat" in t.lower()


@pytest.mark.skipif(not GUIDED.exists(), reason="run scripts/phase9e_guided_capture.py")
def test_the_headline_point_is_the_declared_geometric_mean_of_the_measured_brackets():
    g = json.loads(GUIDED.read_text(encoding="utf-8"))
    lo = g["bracketing_measurements"]["lower"]["residual_dE2000"]
    hi = g["bracketing_measurements"]["upper"]["residual_dE2000"]
    assert g["headline_point"]["residual_dE2000"] == pytest.approx(np.sqrt(lo * hi))
    assert lo < g["headline_point"]["residual_dE2000"] < hi


@pytest.mark.skipif(not GUIDED.exists(), reason="run scripts/phase9e_guided_capture.py")
def test_the_fresh_banks_reproduce_the_measured_anchors():
    """If a different random draw moved the anchors, the interpolation would be noise."""
    g = json.loads(GUIDED.read_text(encoding="utf-8"))
    assert g["bank_draw_check"]["max_abs_difference_from_recorded"] < 0.05


@pytest.mark.skipif(not GUIDED.exists(), reason="run scripts/phase9e_guided_capture.py")
def test_no_point_in_the_interval_reaches_viable():
    g = json.loads(GUIDED.read_text(encoding="utf-8"))
    assert not g["interval_verdict"]["any_point_in_the_interval_reaches_VIABLE"]
    assert all(r["band"] != "VIABLE" for r in g["gate_curve"])


@pytest.mark.skipif(not GUIDED.exists(), reason="run scripts/phase9e_guided_capture.py")
def test_the_interpolated_point_carries_an_interval_not_just_a_number():
    g = json.loads(GUIDED.read_text(encoding="utf-8"))
    u = g["headline_uncertainty"]
    assert u["p2.5"] < u["median"] < u["p97.5"]
    assert u["n"] == 2048, "the Phase 9C prior draws, reused so the interval is comparable"


# --------------------------------------------------------- the Part C language pass
@pytest.mark.skipif(not XSCI.exists(), reason="run scripts/phase9e_intervals.py")
def test_every_cross_site_rate_has_an_interval_and_a_count_beside_it():
    d = json.loads(XSCI.read_text(encoding="utf-8"))["directions"]
    assert set(d) == {"italy_to_india", "india_to_italy"}
    for k, v in d.items():
        for m in ("sensitivity", "specificity", "ppv", "referral_rate"):
            assert v[m]["lo"] <= v[m]["point"] <= v[m]["hi"], (k, m)
        assert "of" in v["observed_counts_statement"]
        assert str(v["counts"]["tp"]) in v["preferred_wording"]


@pytest.mark.skipif(not PHASE9A.exists(), reason="run scripts/phase9a_report.py")
def test_the_cross_site_sensitivity_is_never_quoted_bare_in_the_report():
    """0.397 may appear, but not without an interval or a count in the same sentence."""
    t = PHASE9A.read_text(encoding="utf-8")
    for line in t.splitlines():
        if "0.397" in line:
            assert ("[0.278" in line or "27 of 68" in line or "41 of 68" in line
                    or "0.397 in one direction" in line), line


@pytest.mark.skipif(not PHASE7.exists(), reason="run scripts/phase7_report.py")
def test_the_retired_phase9a_phrase_is_not_asserted_in_the_phase7_report():
    """Phase 9A retired 'moves no clinical threshold'. It may be quoted while being
    retired; it may not be stated as a live conclusion."""
    t = PHASE7.read_text(encoding="utf-8")
    for line in t.splitlines():
        if "moves no clinical threshold" in line:
            assert "retired" in line, line


@pytest.mark.skipif(not PHASE7.exists(), reason="run scripts/phase7_report.py")
def test_the_studio_figure_is_never_quoted_without_its_interval_nearby():
    t = PHASE7.read_text(encoding="utf-8")
    assert "0.60, 4.90" in t or "[0.60, 4.90]" in t
    for line in t.splitlines():
        if "within 8% of viable" in line:
            assert "0.60, 4.90" in line, line


@pytest.mark.skipif(not REPORT.exists(), reason="run scripts/phase9e_report.py")
def test_the_report_does_not_weaken_the_adequately_powered_arms():
    t = REPORT.read_text(encoding="utf-8")
    assert "ADEQUATELY POWERED" in t
    assert "keep their full strength" in t
    assert "changes no verdict" in t or "No verdict" in t
