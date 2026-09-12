"""Phase 8A - the content model. Simplify the sentence, never the claim.

Every check must carry both layers, fully populated; the plain layer must never claim
more than the technical one (INSUFFICIENT is never a pass; a floor p is still a bound;
a narrow margin is still narrow); and no INSUFFICIENT wording may ever be rendered with
pass styling.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hemosight.audit import ALL_IDS, load_predictions, run_audit
from hemosight.audit.content import (CATEGORIES, CONTENT, GLOSSARY, MISSING_PLAIN, enrich,
                                     catalogue)
from hemosight.audit.report import to_markdown
from hemosight.audit.verdict import FAIL, INSUFFICIENT, PASS

ROOT = Path(__file__).resolve().parents[1]
PASS_WORDS = re.compile(r"\b(pass(ed|es)?|looks fine|fine|ok|okay|no problem)\b", re.I)


def _res(check_id, verdict, measured=None, missing=None):
    return {"check_id": check_id, "title": check_id, "verdict": verdict,
            "headline": "technical headline", "explanation": "technical explanation",
            "provenance": "p", "measured": measured or {}, "threshold": None,
            "threshold_preregistered": False, "missing": missing or [], "details": {},
            "seconds": 0.0}


# Measured dicts that exercise every branch of every plain headline.
MEASURED = {
    "duplicates": {FAIL: {"n_images": 100, "exact_duplicate_rate": 0.12,
                          "n_exact_duplicate_groups_crossing_a_split": 3,
                          "n_near_duplicate_groups_crossing_a_split": 1},
                   PASS: {"n_images": 100, "exact_duplicate_rate": 0.0}},
    "split_integrity": {FAIL: {"n_subjects": 50, "n_subjects_in_more_than_one_split": 4,
                               "nominal_subject_ids": 50, "leakproof_groups": 40},
                        PASS: {"n_subjects": 50, "n_subjects_in_more_than_one_split": 0}},
    "demographic_baseline": {FAIL: {"model_mae": 1.19, "best_single_demographic": "sex",
                                    "best_single_demographic_mae": 0.831,
                                    "model_advantage_over_best_single": -0.36, "margin_is_narrow": False},
                             PASS: {"model_mae": 0.65, "best_single_demographic": "sex",
                                    "best_single_demographic_mae": 0.81,
                                    "model_advantage_over_best_single": 0.02, "margin_is_narrow": True}},
    "proxy_probe": {FAIL: {"worst_demographic": "sex", "skill_explained_by_worst_demographic": 0.98,
                           "n_probes_above_base_rate": 1, "probe_ran_on": "the prediction vector (reported, not a finding)"},
                    PASS: {"worst_demographic": "age", "skill_explained_by_worst_demographic": 0.1,
                           "n_probes_above_base_rate": 0, "probe_ran_on": "a supplied representation"}},
    "permutation": {FAIL: {"p_empirical": 0.978, "n_permutations": 500, "p_floor": 0.002,
                           "p_is_at_the_floor": False, "construction": "selected-model-only", "n_candidates": 1},
                    PASS: {"p_empirical": 0.00415, "n_permutations": 240, "p_floor": 0.00415,
                           "p_is_at_the_floor": True, "construction": "selection-aware", "n_candidates": 6,
                           "draws_at_or_below_real": 0}},
    "seed_stability": {FAIL: {"n_seeds": 5, "mae_sd": 0.05, "claimed_effect": 0.04, "effect_to_seed_sd_ratio": 0.8},
                       PASS: {"n_seeds": 10, "mae_sd": 0.0069, "claimed_effect": 0.0815, "effect_to_seed_sd_ratio": 11.9}},
    "subgroup_robustness": {FAIL: {"n_subjects_dropped": 25, "retained_advantage_fraction": 0.41,
                                   "n_subgroups_where_model_loses_to_baseline": 1,
                                   "retained_fraction_is_near_the_threshold": True},
                            PASS: {"n_subjects_dropped": 25, "retained_advantage_fraction": 0.9,
                                   "n_subgroups_where_model_loses_to_baseline": 0,
                                   "retained_fraction_is_near_the_threshold": False}},
    "ceiling": {FAIL: {"n_features": 51, "n_features_above_mi_null_p95": 0},
                PASS: {"n_features": 12, "n_features_above_mi_null_p95": 4, "n_surviving_fdr_pearson": 2,
                       "n_surviving_fdr_spearman": 1}},
}


def test_every_check_has_every_content_field_populated():
    assert set(CONTENT) == set(ALL_IDS)
    for cid, c in CONTENT.items():
        for f in ("title_plain", "question_plain", "what_it_means_plain", "mechanism_plain",
                  "mechanism_technical", "provenance"):
            assert len(getattr(c, f).strip()) > (12 if f == "title_plain" else 40), (cid, f)
        assert c.glossary_terms and all(g in GLOSSARY for g in c.glossary_terms), (cid, c.glossary_terms)
        for v in (PASS, FAIL, INSUFFICIENT):
            r = _res(cid, v, MEASURED[cid].get(v), ["a split column"] if v == INSUFFICIENT else None)
            out = enrich(r)["plain"]
            assert len(out["headline"]) > 30, (cid, v, out["headline"])
            todo = out["what_to_do"]
            assert todo["category"] in CATEGORIES and len(todo["text"]) > 40, (cid, v)
    for c in catalogue():
        assert c["mechanism_plain"] and c["mechanism_technical"]


def test_insufficient_data_never_reads_as_a_pass():
    for cid in ALL_IDS:
        r = enrich(_res(cid, INSUFFICIENT, missing=["a split column"]))
        h = r["plain"]["headline"]
        assert h.lower().startswith("we could not check this"), (cid, h)
        assert not PASS_WORDS.search(h), (cid, h)
        assert "not be read as a pass" in r["plain"]["what_to_do"]["text"] or \
            r["plain"]["what_to_do"]["category"] == "FIXABLE", cid
    # the plain translations of the checks' own `missing` strings never soften them
    for k, v in MISSING_PLAIN.items():
        assert not PASS_WORDS.search(v), (k, v)


def test_the_floor_and_narrow_margin_caveats_survive_the_plain_layer():
    p = enrich(_res("permutation", PASS, MEASURED["permutation"][PASS]))["plain"]["headline"]
    assert "smallest p-value" in p and "true value may be smaller" in p and "bound, not a measurement" in p
    assert "priced in" in p                       # selection-aware stated
    p_only = enrich(_res("permutation", PASS, {**MEASURED["permutation"][PASS], "construction": "selected-model-only",
                                                 "n_candidates": 1}))["plain"]["headline"]
    assert "not priced in" in p_only
    b = enrich(_res("demographic_baseline", PASS, MEASURED["demographic_baseline"][PASS]))["plain"]["headline"]
    assert "margin is small" in b and "could flip" in b
    s = enrich(_res("subgroup_robustness", FAIL, MEASURED["subgroup_robustness"][FAIL]))["plain"]["headline"]
    assert "close to the threshold" in s and "not stable" in s


def test_what_to_do_is_never_a_way_to_make_a_failing_check_pass():
    forbidden = re.compile(r"(until (it|the check) passes|to pass the check|make (it|the check) pass|tune until)", re.I)
    for cid in ALL_IDS:
        for v in (PASS, FAIL, INSUFFICIENT):
            r = enrich(_res(cid, v, MEASURED[cid].get(v), ["a split column"] if v == INSUFFICIENT else None))
            text = r["plain"]["what_to_do"]["text"]
            # "do not tune until it passes" is the one permitted use of the phrase
            stripped = re.sub(r"do not tune until it passes", "", text, flags=re.I)
            assert not forbidden.search(stripped), (cid, v, text)
    # STOP and REPORT IT are the categories for every FAIL except the fixable-by-method ones
    fixable_fail = {"duplicates", "split_integrity"}
    for cid in ALL_IDS:
        cat = enrich(_res(cid, FAIL, MEASURED[cid][FAIL]))["plain"]["what_to_do"]["category"]
        assert (cat == "FIXABLE") == (cid in fixable_fail), (cid, cat)


def test_insufficient_wording_is_never_paired_with_pass_styling():
    """Structural: the one place verdict colour is assigned maps INSUFFICIENT_DATA to
    its own class, and nothing in the pages styles an insufficient verdict as pass."""
    ui = (ROOT / "app/frontend/src/components/ui.tsx").read_text(encoding="utf-8")
    m = re.search(r"INSUFFICIENT_DATA:\s*\"([^\"]+)\"", ui.split("VERDICT_CLASS")[1])
    assert m and "insufficient" in m.group(1) and "pass" not in m.group(1)
    for page in (ROOT / "app/frontend/src/pages").glob("*.tsx"):
        src = page.read_text(encoding="utf-8")
        for line in src.splitlines():
            if "INSUFFICIENT" in line and "text-pass" in line:
                pytest.fail(f"{page.name}: {line.strip()}")


def test_markdown_export_carries_both_layers():
    rng = np.random.default_rng(1)
    n = 80
    y = rng.normal(13, 1.5, n)
    df = pd.DataFrame({"subject_id": [f"s{i}" for i in range(n)], "y_true": y,
                       "y_pred": y + rng.normal(0, 1, n),
                       "sex": rng.choice(["M", "F"], n), "age": rng.integers(20, 70, n)})
    rep = run_audit(load_predictions(df), checks=["demographic_baseline", "permutation", "split_integrity"],
                    options={"permutation": {"n_permutations": 60}})
    for r in rep.results:
        assert "plain" in r and r["plain"]["headline"]
    md = to_markdown(rep)
    assert "In plain terms:" in md and "Technical statement:" in md and "What to do - " in md
    assert "Mechanism, computationally:" in md
    # a check that could not run says so in plain words and keeps the technical statement
    ins = [r for r in rep.results if r["verdict"] == INSUFFICIENT]
    assert ins, "split_integrity should be insufficient without a split column"
    assert ins[0]["plain"]["headline"].startswith("We could not check this")
    assert json.dumps(rep.to_dict())   # still JSON-safe with the plain layer attached
