"""Tests for Phase 9C, the parameter-uncertainty propagation.

Two jobs: keep the propagation tied to the machinery it propagates (if the
parameterised forward drifts from `forward.layered_reflectance`, or the banks stop
reproducing the recorded point estimates, the intervals mean nothing), and keep the
pre-declared interpretation rule from being quietly restated.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from hemosight.io import paths
from hemosight.simulation import constants as C
from hemosight.simulation import uncertainty as U
from hemosight.simulation.forward import layered_reflectance

RESULT = paths.INTERIM / "phase9c" / "uncertainty.json"
REPORT = paths.REPORTS / "phase9c_uncertainty.md"


# ------------------------------------------------------- the model is the same
def test_parameterised_forward_equals_the_gate_forward_at_nominal():
    """theta = NOMINAL must reproduce forward.layered_reflectance exactly."""
    fwd = U.ForwardTheta()
    th = dict(U.NOMINAL)
    th["melanin"] = 0.0
    for hb in (4.0, 9.0, 13.0, 18.0):
        a = layered_reflectance(C.WAVELENGTHS_NM, hb, 0.75, 0.06, 0.0)
        b = fwd.reflectance(np.array([hb]), th)[0]
        assert np.allclose(a, b, rtol=0, atol=1e-12), hb


def test_nominal_matches_the_constants_module():
    """The nominals are read off the gate, not chosen. If a constant changes, this fails."""
    assert U.NOMINAL["sto2"] == 0.75            # gate call signature
    assert U.NOMINAL["bvf_stroma"] == 0.06      # gate call signature
    layers = {l.name: l for l in C.DEFAULT_LAYERS}
    assert U.NOMINAL["t_epi_um"] == pytest.approx(layers["epithelium"].thickness_cm * 1e4)
    assert U.NOMINAL["t_stroma_um"] == pytest.approx(layers["stroma_vascular"].thickness_cm * 1e4)
    assert U.NOMINAL["t_tarsal_um"] == pytest.approx(layers["tarsal_plate"].thickness_cm * 1e4)
    assert U.NOMINAL["bvf_epi"] == pytest.approx(layers["epithelium"].blood_volume_fraction)
    assert U.NOMINAL["bvf_tarsal"] == pytest.approx(layers["tarsal_plate"].blood_volume_fraction)
    assert U.NOMINAL["deep_weight"] == U.DEEP_WEIGHT_NOMINAL


def test_melanin_power_law_reproduces_the_library_curve_at_nominal():
    wl = C.WAVELENGTHS_NM
    from hemosight.simulation.optical_data import melanin_absorption
    lib = melanin_absorption(wl)
    fit = U.melanin_mu_a(wl, U.MELANIN_K_NOMINAL, 1.0 + 1e-9)   # forces the power-law branch
    assert np.abs(np.log(fit) - np.log(lib)).max() < 1e-3


def test_every_parameter_range_brackets_its_nominal_and_is_labelled():
    for p in U.PARAMS:
        assert p.lo <= p.nominal <= p.hi or p.key == "melanin", p.key
        assert p.status in ("SOURCED", "SOURCED-GENERIC", "UNSOURCED"), p.key
        assert p.justification.strip(), p.key
        if p.log:
            assert p.lo > 0, p.key


def test_ranges_are_at_least_as_wide_as_the_phase3_task4_envelope():
    """Pre-declared: the Task 4 tolerances are the STARTING envelope, never narrower."""
    d = {p.key: p for p in U.PARAMS}
    assert d["bvf_stroma"].lo <= 0.06 * 0.7 and d["bvf_stroma"].hi >= 0.06 * 1.3
    assert d["sto2"].lo <= 0.60 and d["sto2"].hi >= 1.00
    for k, nom in (("t_stroma_um", 200.0), ("t_tarsal_um", 800.0)):
        assert d[k].lo <= 0.8 * nom and d[k].hi >= 2.0 * nom, k


# ------------------------------------------------------- the run is valid
def _result():
    if not RESULT.exists():
        pytest.skip("run scripts/phase9c_uncertainty.py first")
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_the_run_reproduced_the_recorded_point_estimates():
    """The pre-declared validity condition. Without it the intervals are not about the gate."""
    d = _result()
    assert d["valid"] is True
    assert set(d["reproduction"]) == {str(k) for k in U.RECORDED}
    for k, v in d["reproduction"].items():
        assert v["ok"], (k, v)
        assert v["abs_diff"] < 1e-6, (k, v)
        assert v["recorded"] == pytest.approx(U.RECORDED[float(k)][1])


def test_the_interpretation_rule_is_applied_as_declared():
    """ROBUST iff the whole 95% interval is on one side of the threshold."""
    d = _result()
    for k, s in d["residuals"].items():
        expect_2 = (s["p2.5"] > 2.0) or (s["p97.5"] < 2.0)
        assert s["robust_at_2.0"] == expect_2, k
        expect_1 = (s["p2.5"] > 1.0) or (s["p97.5"] < 1.0)
        assert s["robust_at_1.0"] == expect_1, k
        assert "ROBUST" in s["rule"] or "FRAGILE" in s["rule"]
        # the interval must bracket its own median, and the point estimate is kept
        assert s["p2.5"] <= s["median"] <= s["p97.5"], k
        assert s["point_estimate"] == pytest.approx(U.RECORDED[float(k)][1])


def test_the_sample_size_is_the_pre_declared_one():
    d = _result()
    assert d["seed"] == 20260911
    assert d["n_base"] == 1024
    assert d["n_mc"] == 2048
    assert d["n_eval"] == (len(U.PARAMS) + 2) * 1024


def test_sobol_totals_are_reported_for_every_parameter_and_ranked():
    d = _result()
    for k, si in d["sobol"].items():
        assert len(si["total"]) == len(U.PARAMS) == len(si["ranked"]), k
        tot = [r["ST"] for r in si["ranked"]]
        assert tot == sorted(tot, reverse=True), k
        assert all(r["status"] in ("SOURCED", "SOURCED-GENERIC", "UNSOURCED") for r in si["ranked"])


# ------------------------------------------------------- the record
def test_report_keeps_the_point_estimate_beside_the_interval():
    if not REPORT.exists():
        pytest.skip("run scripts/phase9c_report.py first")
    txt = REPORT.read_text(encoding="utf-8")
    for rec in ("3.893", "3.471", "1.040"):
        assert rec in txt, f"the point estimate {rec} must be retained, not replaced"
    assert "95%" in txt
    assert "ROBUST" in txt or "FRAGILE" in txt
    # the verification item must be reported either way, never silently dropped
    assert "Efron" in txt and "Zhivov" in txt


def test_claude_md_carries_the_interval_beside_the_point_estimate():
    txt = (paths.ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "3.893" in txt, "the point estimate stays on the record"
    assert "Phase 9C" in txt
    # A bare gate number with no uncertainty pointer anywhere would mean the
    # propagation was recorded and then not used.
    assert "phase9c_uncertainty.md" in txt
