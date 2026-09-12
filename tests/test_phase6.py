"""Tests for Phase 6 - the HemoSight Audit harness.

The tool judges other people's evidence, so the properties that make it trustworthy
are asserted here rather than left to inspection: that it never infers a verdict it
cannot support, that its p-values carry their floor, that its permutations are
reproducible from an index, and that the report keeps its own limits attached.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from hemosight.audit import (ALL_IDS, ContractError, load_predictions, run_audit,
                             to_markdown)
from hemosight.audit.permutation import permuted_labels
from hemosight.audit.registry import BY_ID, catalogue
from hemosight.audit.stats import benjamini_hochberg, empirical_p
from hemosight.audit.verdict import FAIL, INSUFFICIENT, PASS
from hemosight.io import paths

VERDICTS = {PASS, FAIL, INSUFFICIENT}


def _frame(n: int = 120, seed: int = 0, with_demographics: bool = True,
           with_features: bool = True) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    sex = rng.integers(0, 2, n)
    sig = rng.normal(0, 1, n)
    y = 13.0 + 1.2 * sex + 0.8 * sig + rng.normal(0, 0.6, n)
    df = pd.DataFrame({
        "subject_id": [f"s{i:04d}" for i in range(n)],
        "y_true": y,
        "y_pred": 13.0 + 0.9 * sex + 0.7 * sig + rng.normal(0, 0.7, n),
    })
    if with_demographics:
        df["sex"] = np.where(sex == 1, "M", "F")
        df["age"] = rng.integers(18, 75, n)
    if with_features:
        df["signal_feature"] = sig + rng.normal(0, 0.3, n)
    return df


# --------------------------------------------------------------------- contract
def test_the_contract_refuses_a_table_it_cannot_audit():
    bad = pd.DataFrame({"subject_id": ["a"], "y_true": [1.0]})
    with pytest.raises(ContractError):
        load_predictions(bad)


def test_a_one_row_per_subject_table_is_flagged_not_rejected():
    inp = load_predictions(_frame(30))
    assert any("one row per subject_id" in w for w in inp.warnings)
    assert inp.n == 30


def test_the_submitted_model_is_always_a_selection_candidate():
    """A best-of-one selection is still a selection; naming it keeps the two
    permutation constructions directly comparable."""
    inp = load_predictions(_frame(40))
    assert "submitted" in inp.candidates


# ---------------------------------------------------------------------- verdicts
def test_every_check_returns_a_verdict_from_the_vocabulary_with_provenance():
    inp = load_predictions(_frame(120))
    report = run_audit(inp, options={"permutation": {"n_permutations": 200}})
    assert len(report.results) == len(ALL_IDS)
    for r in report.results:
        assert r["verdict"] in VERDICTS, r
        assert r["provenance"], f"{r['check_id']} must name where it came from"
        assert r["explanation"], f"{r['check_id']} must explain what it means"


def test_insufficient_data_is_returned_rather_than_a_verdict_being_inferred():
    """The rule reports/literature_gap.md applies to the literature applies here:
    UNKNOWN is not evidence of absence, so a missing column produces no verdict."""
    inp = load_predictions(_frame(80, with_demographics=False, with_features=False))
    report = run_audit(inp, checks=["demographic_baseline", "proxy_probe", "ceiling",
                                    "duplicates", "split_integrity", "seed_stability"])
    for r in report.results:
        assert r["verdict"] == INSUFFICIENT, f"{r['check_id']} inferred a verdict"
        assert r["missing"], f"{r['check_id']} must say what was missing"


def test_a_check_that_raises_is_reported_not_dropped(monkeypatch):
    """An audit that silently omits a check overstates its own coverage."""
    def boom(*a, **k):
        raise RuntimeError("deliberate")

    monkeypatch.setattr(BY_ID["subgroup_robustness"], "run", boom)
    report = run_audit(load_predictions(_frame(40)), checks=["subgroup_robustness"])
    assert len(report.results) == 1
    assert report.results[0]["verdict"] == INSUFFICIENT
    assert "deliberate" in report.results[0]["details"]["exception"]


# ------------------------------------------------------------------- statistics
def test_an_empirical_p_at_the_floor_is_labelled_as_a_bound():
    """p = 0.0164 at n=60 was 1/(60+1), the smallest number the sample size allowed."""
    s = empirical_p(np.full(60, 1.20), real=1.1124)
    assert s["at_floor"] is True
    assert s["p_empirical"] == s["p_floor"] == pytest.approx(1 / 61)
    s2 = empirical_p(np.array([1.10, 1.20, 1.21]), real=1.1124)
    assert s2["at_floor"] is False and s2["n_at_or_below_real"] == 1


def test_a_permutation_count_too_small_to_reach_alpha_declines_to_run():
    inp = load_predictions(_frame(60))
    r = run_audit(inp, checks=["permutation"],
                  options={"permutation": {"n_permutations": 10}}).results[0]
    assert r["verdict"] == INSUFFICIENT
    assert r["measured"]["p_floor"] == pytest.approx(1 / 11, abs=1e-5)


def test_permutation_labels_depend_only_on_the_index():
    """Reproducibility of permutation i is what makes any resumable or re-runnable
    permutation test meaningful; see the DECISION LOG, 2026-09-12."""
    y = np.arange(30, dtype=float)
    subs = np.array([f"s{i}" for i in range(30)])
    assert np.array_equal(permuted_labels(y, subs, 5), permuted_labels(y, subs, 5))
    assert not np.array_equal(permuted_labels(y, subs, 5), permuted_labels(y, subs, 6))
    assert np.array_equal(np.sort(permuted_labels(y, subs, 5)), y)


def test_permutation_shuffles_across_subjects_not_rows():
    """A subject contributing many rows must move as one, or the null is wrong."""
    y = np.array([10.0, 10.0, 12.0, 12.0, 14.0, 14.0])
    subs = np.array(["a", "a", "b", "b", "c", "c"])
    out = permuted_labels(y, subs, 3)
    assert out[0] == out[1] and out[2] == out[3] and out[4] == out[5]
    assert sorted(set(out)) == [10.0, 12.0, 14.0]


def test_benjamini_hochberg_is_shared_with_the_phase_4_5_script():
    """Re-homed, not duplicated: two copies of a correction drift invisibly."""
    src = (paths.ROOT / "scripts" / "phase4_5_ceiling.py").read_text(encoding="utf-8")
    assert "from hemosight.audit.stats import benjamini_hochberg" in src
    assert "def benjamini_hochberg(" not in src
    rej, adj = benjamini_hochberg(np.array([0.001, 0.04, 0.5, 0.9]))
    assert rej[0] and not rej[-1] and (adj >= np.array([0.001, 0.04, 0.5, 0.9])).all()


# ---------------------------------------------------------------------- registry
def test_the_catalogue_is_complete_and_carries_its_defaults():
    cat = catalogue()
    assert len(cat) == len(ALL_IDS) == 8
    assert len({c["check_id"] for c in cat}) == 8
    for c in cat:
        assert c["phase"] and c["summary"] and c["provenance"]
        assert isinstance(c["defaults"], dict)
        assert "run" not in c, "the catalogue must be serialisable"


# ------------------------------------------------------------------------ report
def test_the_report_keeps_its_own_limits_attached():
    """The scope paragraph is load-bearing. A report that drops it overstates itself."""
    report = run_audit(load_predictions(_frame(80)), checks=["subgroup_robustness"])
    md = to_markdown(report)
    assert "do not re-run the submitter's training" in md
    assert "not evidence that a model works" in md
    assert "clinical validation" in md
    assert "Report fingerprint" in md


def test_a_report_without_a_preregistration_says_so():
    report = run_audit(load_predictions(_frame(60)), checks=["subgroup_robustness"])
    md = to_markdown(report)
    assert "No thresholds were declared before these results were seen" in md
    assert report.counts["preregistered_thresholds"] == 0


def test_preregistered_thresholds_are_recorded_per_check():
    from hemosight.audit import PreRegistration

    pr = PreRegistration(title="t",
                         thresholds={"subgroup_robustness":
                                     {"min_retained_advantage_fraction": 0.9}})
    assert pr.intact()
    report = run_audit(load_predictions(_frame(80)), checks=["subgroup_robustness"],
                       prereg=pr)
    r = report.results[0]
    assert r["threshold_preregistered"] is True
    assert r["threshold"]["min_retained_advantage_fraction"] == 0.9


def test_an_edited_preregistration_is_detectable():
    from hemosight.audit import PreRegistration

    pr = PreRegistration(title="t", thresholds={"permutation": {"alpha": 0.05}})
    assert pr.intact()
    pr.thresholds["permutation"]["alpha"] = 0.5
    assert not pr.intact(), "a changed declaration must not still verify"


# -------------------------------------------------------------------- the audit
def test_the_audit_package_never_writes_under_data_raw():
    """data/raw is READ-ONLY. The harness reads pixels from it and nothing more."""
    for p in (paths.ROOT / "src" / "hemosight" / "audit").glob("*.py"):
        src = p.read_text(encoding="utf-8")
        for verb in ("write_text(", "to_csv(", "np.save(", 'open('):
            for line in src.splitlines():
                if verb in line and "RAW" in line:
                    raise AssertionError(f"{p.name} writes under RAW: {line.strip()}")


def test_harness_validation_reproduced_the_recorded_verdicts():
    """If the validation has been run, it must still agree with the project's record."""
    f = paths.INTERIM / "phase6" / "harness_validation.json"
    if not f.exists():
        pytest.skip("run scripts/phase6_validate_harness.py first")
    d = json.loads(f.read_text(encoding="utf-8"))
    s = d["summary"]
    assert s["agreement_rate"] == 1.0, [c for c in d["cases"] if not c["ok"]]
    assert s["sensitivity"] == 1.0
    assert s["false_positive"]["false_positive_rate"] < 0.10


def test_the_case_study_does_not_alter_the_reported_p():
    """p = 0.0164 stands until the extended run is consolidated by hand."""
    src = (paths.ROOT / "app" / "backend" / "main.py").read_text(encoding="utf-8")
    assert "harden.json" in src
    for line in src.splitlines():
        if "harden.json" in line:
            assert not any(w in line for w in ("write_text", "dump")), line.strip()


# ------------------------------------------------------- JSON column boundary
# Regression cover for the 500 on POST /api/submissions. `AuditInput.summary()` put
# numpy.bool_ into a JSON column; the driver raised "Object of type bool is not JSON
# serializable", which is confusing because numpy.bool_ prints as "bool" and is NOT a
# subclass of it. The fix is a coercion at the boundary, so these tests check the
# boundary rather than the one field that happened to fail.

HOSTILE_PAYLOAD = {
    "np_int": np.int64(7),
    "np_float": np.float64(1.5),
    "np_bool": np.bool_(True),
    "np_bool_false": np.bool_(False),
    "ndarray": np.array([1, 2, 3]),
    "ndarray_2d": np.array([[1.0, 2.0], [3.0, 4.0]]),
    "nan": float("nan"),
    "np_nan": np.float64("nan"),
    "inf": float("inf"),
    "neg_inf": float("-inf"),
    "nested": {"deeper": [np.int32(1), np.float32(2.5), np.bool_(False)]},
    "plain": "unchanged",
    "none": None,
}

EXPECTED_PAYLOAD = {
    "np_int": 7, "np_float": 1.5, "np_bool": True, "np_bool_false": False,
    "ndarray": [1, 2, 3], "ndarray_2d": [[1.0, 2.0], [3.0, 4.0]],
    "nan": None, "np_nan": None, "inf": None, "neg_inf": None,
    "nested": {"deeper": [1, 2.5, False]},
    "plain": "unchanged", "none": None,
}


def _app_module(name: str):
    import importlib
    import sys as _sys
    if str(paths.ROOT) not in _sys.path:
        _sys.path.insert(0, str(paths.ROOT))
    return importlib.import_module(name)


def test_to_jsonable_coerces_numpy_arrays_and_non_finite_floats():
    from hemosight.audit.jsonsafe import to_jsonable

    out = to_jsonable(HOSTILE_PAYLOAD)
    assert out == EXPECTED_PAYLOAD
    json.dumps(out, allow_nan=False)          # would raise on NaN/Inf surviving
    assert type(out["np_bool"]) is bool and type(out["np_int"]) is int


def test_bool_is_not_flattened_into_an_integer():
    """bool is a subclass of int; testing int first would turn True into 1."""
    from hemosight.audit.jsonsafe import to_jsonable

    assert to_jsonable(np.bool_(True)) is True
    assert to_jsonable(True) is True
    assert to_jsonable(1) == 1 and type(to_jsonable(1)) is int


def test_a_submission_persists_a_numpy_payload_and_reads_back():
    """The exact failure: a JSON column receiving values NumPy produced."""
    db_mod = _app_module("app.backend.db")
    models = _app_module("app.backend.models")

    sid = "regress_" + models.new_id()
    with db_mod.SessionLocal() as s:
        s.add(models.Submission(id=sid, filename="numpy.csv", csv_path="",
                                n_rows=1, n_subjects=1,
                                summary=dict(HOSTILE_PAYLOAD),
                                column_map={"n": np.int64(3)}))
        s.commit()                                  # raised TypeError before the fix
    try:
        with db_mod.SessionLocal() as s:
            back = s.get(models.Submission, sid)
            assert back.summary == EXPECTED_PAYLOAD
            assert back.column_map == {"n": 3}
            json.dumps(back.summary, allow_nan=False)
    finally:
        with db_mod.SessionLocal() as s:
            row = s.get(models.Submission, sid)
            if row is not None:
                s.delete(row)
                s.commit()


def test_a_run_report_containing_numpy_persists():
    """Run.report is the second JSON column that receives analysis output."""
    db_mod = _app_module("app.backend.db")
    models = _app_module("app.backend.models")

    sid, rid = "regress_" + models.new_id(), "regress_" + models.new_id()
    with db_mod.SessionLocal() as s:
        s.add(models.Submission(id=sid, filename="x.csv", csv_path=""))
        s.commit()
        s.add(models.Run(id=rid, submission_id=sid, checks=["permutation"],
                         options={"permutation": {"n_permutations": np.int64(10)}},
                         report={"counts": {"FAIL": np.int64(1)},
                                 "results": [{"measured": dict(HOSTILE_PAYLOAD)}]}))
        s.commit()
    try:
        with db_mod.SessionLocal() as s:
            back = s.get(models.Run, rid)
            assert back.report["counts"]["FAIL"] == 1
            assert back.report["results"][0]["measured"] == EXPECTED_PAYLOAD
            assert back.options == {"permutation": {"n_permutations": 10}}
    finally:
        with db_mod.SessionLocal() as s:
            for model, key in ((models.Run, rid), (models.Submission, sid)):
                row = s.get(model, key)
                if row is not None:
                    s.delete(row)
            s.commit()


def test_every_json_column_uses_the_coercing_type():
    """A plain JSON column added later would reintroduce the defect silently."""
    src = (paths.ROOT / "app" / "backend" / "models.py").read_text(encoding="utf-8")
    for line in src.splitlines():
        if "mapped_column(" in line and "JSON" in line:
            assert "SafeJSON" in line, f"plain JSON column: {line.strip()}"


def test_audit_input_has_returns_a_real_bool_not_a_numpy_one():
    """The origin of the 500: `notna().any()` is numpy.bool_, not bool."""
    inp = load_predictions(_frame(40))
    for col in ("sex", "split", "image_path", "age"):
        v = inp.has(col)
        assert type(v) is bool, f"{col} -> {type(v)}"
    json.dumps(inp.summary(), allow_nan=False)


def test_the_report_payload_is_json_safe_end_to_end():
    """to_dict() is the analysis boundary; nothing NumPy may cross it."""
    report = run_audit(load_predictions(_frame(80)),
                       checks=["demographic_baseline", "subgroup_robustness",
                               "permutation"],
                       options={"permutation": {"n_permutations": 200}})
    json.dumps(report.to_dict(), allow_nan=False)


def test_the_upload_endpoint_accepts_the_sample_submission():
    """The reported repro, as an HTTP call."""
    csv = paths.ROOT / "app" / "backend" / "sample_data" / "01_mixed_start_here.csv"
    images = paths.INTERIM / "phase6" / "sample_images"
    if not csv.exists():
        pytest.skip("run scripts/phase6_make_sample_data.py first")
    from fastapi.testclient import TestClient
    main = _app_module("app.backend.main")

    client = TestClient(main.app, raise_server_exceptions=False)
    with open(csv, "rb") as fh:
        r = client.post("/api/submissions",
                        files={"predictions": (csv.name, fh, "text/csv")},
                        data={"image_dir": str(images)} if images.is_dir() else {})
    assert r.status_code == 200, r.text[:500]
    body = r.json()
    assert body["n_rows"] > 0
    json.dumps(body, allow_nan=False)


# --------------------------------------------------- frontend polling hygiene
# The Run page polls a background job. A poll loop that does not stop - on unmount, on
# completion, or when the backend stops answering - is the defect class that the
# 2026-09-12 responsiveness investigation went looking for, and two instances of it were
# measured and fixed. These guard the structure of the fix from the Python suite, which
# runs whether or not node is installed.

FRONTEND = None


def _frontend():
    global FRONTEND
    FRONTEND = paths.ROOT / "app" / "frontend"
    if not (FRONTEND / "src").is_dir():
        pytest.skip("frontend sources not present")
    return FRONTEND


def test_pages_do_not_hand_roll_a_polling_loop():
    """Polling goes through src/polling.ts, which is unit-tested; pages do not."""
    fe = _frontend()
    for p in (fe / "src" / "pages").glob("*.tsx"):
        src = p.read_text(encoding="utf-8")
        for bad in ("setInterval", "requestAnimationFrame"):
            assert bad not in src, (
                f"{p.name} schedules its own loop with {bad}; use pollUntilSettled from "
                "src/polling.ts so the stop conditions stay tested")


def test_the_poller_stops_on_failure_and_never_overlaps():
    """The two measured defects, asserted against the source of the fix."""
    fe = _frontend()
    src = (fe / "src" / "polling.ts").read_text(encoding="utf-8")
    assert "maxConsecutiveFailures" in src, "a failing backend must end the loop"
    assert "onGiveUp" in src, "giving up must be reportable to the interface"
    assert "cancelled" in src, "unmount must stop an in-flight cycle"
    # The call, not the word: the module's own comment explains why setInterval was
    # abandoned, and that explanation is worth keeping.
    assert "setInterval(" not in src, (
        "setInterval does not wait for the previous request; that is what allowed five "
        "concurrent polls against a slow backend")


def test_exhaustive_deps_is_enforced_and_not_suppressed():
    """The original defect sat behind an eslint-disable comment, with no lint run."""
    fe = _frontend()
    cfg = (fe / ".eslintrc.cjs")
    assert cfg.exists(), "no eslint configuration"
    text = cfg.read_text(encoding="utf-8")
    assert '"react-hooks/exhaustive-deps": "error"' in text

    offenders = [p.name for p in (fe / "src").rglob("*.ts*")
                 if "exhaustive-deps" in p.read_text(encoding="utf-8")
                 and "eslint-disable" in p.read_text(encoding="utf-8")]
    assert not offenders, f"exhaustive-deps suppressed in: {offenders}"


def test_the_frontend_declares_lint_and_test_scripts():
    fe = _frontend()
    pkg = json.loads((fe / "package.json").read_text(encoding="utf-8"))
    assert "lint" in pkg["scripts"] and "test" in pkg["scripts"]
    assert (fe / "src" / "polling.test.ts").exists(), "the poller must stay tested"


# ------------------------------------------------ pre-registration title validation
def test_a_one_character_preregistration_title_is_rejected():
    """Two rows titled "t" and one "e2e" reached the development database during
    Phase 6 (audit 2026-09-12). The schema now refuses titles under 8 characters,
    after stripping whitespace, so a smoke test cannot leave a record that looks like
    a declaration."""
    from fastapi.testclient import TestClient
    main = _app_module("app.backend.main")
    client = TestClient(main.app, raise_server_exceptions=False)
    body = {"thresholds": {"permutation": {"alpha": 0.05}}, "checks_planned": ["permutation"]}
    for bad in ("t", "e2e", "   short  ", ""):
        r = client.post("/api/prereg", json={"title": bad, **body})
        assert r.status_code == 422, (bad, r.status_code, r.text[:200])
    r = client.post("/api/prereg", json={"title": "  PPG audit, declared in advance  ", **body})
    assert r.status_code == 200, r.text[:300]
    assert r.json()["title"] == "PPG audit, declared in advance"
    # The endpoint writes to the configured database; remove the row so the test does
    # not leave behind exactly the kind of record it exists to prevent.
    db_mod = _app_module("app.backend.db")
    models = _app_module("app.backend.models")
    with db_mod.SessionLocal() as s:
        row = s.get(models.PreRegistrationRow, r.json()["id"])
        if row is not None:
            s.delete(row)
            s.commit()
