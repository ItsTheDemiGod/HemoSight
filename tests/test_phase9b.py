"""Tests for Phase 9B, the widened literature methodology audit.

Two jobs: keep the answer categories from collapsing into verdicts, and keep the
report's framing pinned to what the counts support.
"""

from __future__ import annotations

import json

import pytest

from hemosight.audit import literature as lit
from hemosight.io import paths

RESULT = paths.INTERIM / "phase9b" / "literature_audit.json"
REPORT = paths.REPORTS / "literature_gap.md"


# ------------------------------------------------------------------ categories
def test_every_value_is_one_of_the_five_categories():
    for p in lit.PAPERS:
        for crit in lit.CRITERIA:
            assert crit in p["scores"], (p["key"], crit)
            v = p["scores"][crit]["value"]
            assert lit.base_category(v) in lit.CATEGORIES, (p["key"], crit, v)
            assert p["scores"][crit]["detail"].strip(), (p["key"], crit, "detail is empty")


def test_no_paper_is_recorded_as_failing_a_check():
    """This audit measures what is REPORTED. 'NO' and 'FAIL' are not answers here; the
    project's one measured NO lives on the Phase 5 dataset rows, never on a paper."""
    for p in lit.PAPERS:
        for crit in lit.CRITERIA:
            v = p["scores"][crit]["value"]
            head = v.split(" - ", 1)[0].strip().upper()
            assert head not in ("NO", "FAIL", "FAILED"), (p["key"], crit, v)
            assert "FAIL" not in v.upper(), (p["key"], crit, v)


def test_base_category_rejects_anything_else():
    with pytest.raises(ValueError):
        lit.base_category("NO - measured")
    with pytest.raises(ValueError):
        lit.base_category("PARTIAL")


def test_unobtained_papers_are_full_text_unavailable_and_not_scored():
    for x in lit.IDENTIFIED_NOT_OBTAINED:
        assert x["status"].startswith("FULL TEXT UNAVAILABLE"), x["short"]
    assert all(p["obtained"] for p in lit.PAPERS), "unobtained papers must not carry scores"


# ------------------------------------------------------------------ counts
def test_counts_recount_from_the_records():
    c = lit.counts()
    for crit in lit.CRITERIA:
        assert sum(c[crit].values()) == len(lit.obtained())
        assert c[crit]["FULL TEXT UNAVAILABLE"] == 0
    # The two counts the report leans on hardest.
    assert c["demographic_baseline"]["YES"] == 0
    assert c["demographic_baseline"]["UNKNOWN"] == 0, "every full text was read"
    assert c["per_site_reporting"]["YES"] == 0
    assert c["per_site_reporting"]["NOT REPORTED"] == len(lit.multi_site_papers())
    assert c["dedup_check"]["YES"] == 0


def test_obtainability_arithmetic():
    ob = lit.obtainability()
    assert ob["identified"] == ob["full_text_obtained"] + ob["not_obtained"]
    assert ob["not_obtained"] == ob["not_obtained_unlocated"] + ob["not_obtained_not_sought"]
    assert ob["full_text_obtained"] == 7


def test_json_on_disk_matches_the_module():
    if not RESULT.exists():
        pytest.skip("run scripts/phase9b_literature_audit.py first")
    d = json.loads(RESULT.read_text(encoding="utf-8"))
    assert d["counts"] == lit.counts()
    assert d["obtainability"] == lit.obtainability()
    assert d["n_full_text"] == len(lit.obtained())


# ------------------------------------------------------------------ the report
def test_report_states_sample_size_and_what_it_is():
    if not REPORT.exists():
        pytest.skip("run scripts/phase9b_literature_audit.py first")
    txt = REPORT.read_text(encoding="utf-8")
    n = len(lit.obtained())
    ob = lit.obtainability()
    assert f"**Sample: {n} papers, full text read.**" in txt
    assert "convenience sample" in txt and "not a systematic review" in txt
    assert (f"**{ob['identified']} papers identified, {ob['full_text_obtained']} full texts "
            "obtained**") in txt
    # The Phase 5 caveats, already test-enforced, must survive the extension.
    assert "UNKNOWN is not evidence of absence" in txt
    assert "too small to support" in txt.lower()
    assert "NOT REPORTED from a full-text read is not 'audited and failed'" in txt
    assert "No paper is recorded as failing a check" in txt


def test_report_does_not_make_a_field_level_claim():
    if not REPORT.exists():
        pytest.skip("run scripts/phase9b_literature_audit.py first")
    sec = REPORT.read_text(encoding="utf-8")
    sec = sec[sec.index("## Phase 9B"):]
    # The counts are stated with the sample as the denominator, never the field.
    n = len(lit.obtained())
    assert f"Demographic baseline: 0 of {n} report one" in sec
    assert "not about the field" in sec
    assert "NOT supported" in sec
    # The overlap section draws no conclusion about any paper's result.
    assert "no conclusion about its reported accuracy is drawn" in sec
    assert "0 of 7" in sec  # papers treating overlapping collections as independent


def test_claim_was_narrowed_and_the_original_wording_kept():
    """Task 5: the claim follows the counts. The old sentence survives verbatim in the
    superseded-claims archive and CLAUDE.md carries the narrowed one."""
    claude = (paths.ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    sup = (paths.ROOT / "docs" / "archive" / "superseded_claims.md").read_text(encoding="utf-8")
    assert "a literature that frequently omits it" in sup
    assert "narrowed 2026-09-20" in claude
    # The unbannered original must not stand anywhere in CLAUDE.md.
    for line in claude.splitlines():
        if "frequently omits it" in line:
            assert "narrowed" in line or "~~" in line, line
