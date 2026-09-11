"""Tests for the Phase 1 pieces where a silent bug would corrupt every downstream
result: filename parsing (which assigns class labels and subject ids) and the
leak-proof grouping (which is the only guard against split leakage)."""

from __future__ import annotations

import pandas as pd
import pytest

from hemosight.io.naming import parse_ghana_name
from hemosight.io.splits import grouped_split, leakproof_groups, verify_no_leak


@pytest.mark.parametrize(
    "stem,cls,series,number",
    [
        ("Anemic-001 (10)", "anemic", "plain", 1),
        ("Non-Anemic-204 - Copy", "non-anemic", "plain", 204),
        ("Anemic-Conj-009png", "anemic", "conj", 9),
        ("Non-anemic-Con-002 (2) - Copy", "non-anemic", "conj", 2),
        ("Anemic-Fin-007 (10)", "anemic", "fin", 7),
        ("Anemic-FN-001 (2)", "anemic", "fin", 1),
        ("Anemic-211 (2)-i10vHz", "anemic", "plain", 211),
        ("Anemic-001FV", "anemic", "plain", 1),
        # The two source-data misspellings. Getting these wrong would mislabel 1625
        # files, 1581 of them flipped from non-anemic to anemic.
        ("Non-Anrmic-FN-0011 (2)", "non-anemic", "fin", 11),
        ("Anmeic-fn-0001", "anemic", "fin", 1),
    ],
)
def test_ghana_name_parsing(stem, cls, series, number):
    g = parse_ghana_name(stem)
    assert g is not None, f"failed to parse {stem!r}"
    assert g.cls == cls
    assert g.series == series
    assert g.number == number


def test_misspelling_does_not_flip_label():
    """'Non-Anrmic' must never be read as anemic."""
    assert parse_ghana_name("Non-Anrmic-FN-0011").anemia_label == 0
    assert parse_ghana_name("Anmeic-fn-0001").anemia_label == 1


def test_replicate_markers_collapse_to_one_subject():
    stems = ["Anemic-042", "Anemic-042 (2)", "Anemic-042 (6) - Copy", "Anemic-042 (3)-xY7q"]
    parsed = [parse_ghana_name(s) for s in stems]
    assert all(p is not None for p in parsed)
    assert len({(p.cls, p.series, p.number) for p in parsed}) == 1


def test_leakproof_groups_merge_across_subject_ids():
    """Two different subject ids sharing one md5 must land in a single group."""
    df = pd.DataFrame({
        "subject_id": ["a", "b", "c", "d"],
        "md5": ["SAME", "SAME", "other", "third"],
    })
    g = leakproof_groups(df)
    assert g.iloc[0] == g.iloc[1], "identical images must share a group"
    assert g.iloc[2] != g.iloc[0]
    assert g.nunique() == 3


def test_leakproof_groups_chain_transitively():
    """a~b via hash H1 and b~c via H2 must put a, b and c in one group."""
    df = pd.DataFrame({
        "subject_id": ["a", "b", "b", "c"],
        "md5": ["H1", "H1", "H2", "H2"],
    })
    assert leakproof_groups(df).nunique() == 1


def test_grouped_split_never_splits_a_group():
    rng = pd.DataFrame({
        "subject_id": [f"s{i//3}" for i in range(60)],
        "md5": [f"h{i}" for i in range(60)],
    })
    rng["group"] = leakproof_groups(rng)
    rng["split"] = grouped_split(rng, "group", {"train": 0.6, "calibration": 0.2, "test": 0.2}, 1)
    assert verify_no_leak(rng, "group", "split") == []
    assert set(rng.split) <= {"train", "calibration", "test"}


def test_grouped_split_is_deterministic():
    df = pd.DataFrame({"subject_id": [f"s{i}" for i in range(40)], "md5": [None] * 40})
    df["group"] = leakproof_groups(df)
    a = grouped_split(df, "group", {"train": 0.7, "test": 0.3}, 7)
    b = grouped_split(df, "group", {"train": 0.7, "test": 0.3}, 7)
    assert a.equals(b)


def test_verify_no_leak_detects_a_planted_leak():
    df = pd.DataFrame({
        "subject_id": ["a", "a"],
        "md5": ["H", "H"],
        "group": ["g", "g"],
        "split": ["train", "test"],  # deliberate violation
    })
    problems = verify_no_leak(df, "group", "split")
    assert problems, "a group spanning two splits must be reported"


# --- Phase 1.5: the haemoglobin trust flag -----------------------------------

def test_binary_only_datasets_never_yield_trusted_hb():
    """The Ghana pool must never produce a trusted Hb value, even if a row somehow
    carries one. Guards the Phase 1.5 arbitration against a silent regression."""
    from hemosight.io.manifests import _finalise

    rows = [
        # A Ghana row with an Hb value planted in it - must still be untrusted.
        {"image_id": "a", "subject_id": "a", "dataset": "cp_anemic", "hb_g_dl": 9.9},
        {"image_id": "b", "subject_id": "b", "dataset": "ghana_conj", "hb_g_dl": 12.0},
        {"image_id": "c", "subject_id": "c", "dataset": "ghana_nail", "hb_g_dl": 8.0},
        {"image_id": "d", "subject_id": "d", "dataset": "eyes_defy", "hb_g_dl": 11.5},
        {"image_id": "e", "subject_id": "e", "dataset": "hb_ppg", "hb_g_dl": 14.0},
        # Missing Hb is never "trusted" either.
        {"image_id": "f", "subject_id": "f", "dataset": "eyes_defy", "hb_g_dl": None},
    ]
    df = _finalise(rows)
    trusted = dict(zip(df.image_id, df.hb_label_trusted))
    assert trusted == {"a": False, "b": False, "c": False,
                       "d": True, "e": True, "f": False}


def test_trusted_hb_helper_filters_and_requires_the_column():
    import pandas as pd

    from hemosight.io.manifests import _finalise, trusted_hb

    df = _finalise([
        {"image_id": "a", "subject_id": "a", "dataset": "cp_anemic", "hb_g_dl": 9.9},
        {"image_id": "d", "subject_id": "d", "dataset": "eyes_defy", "hb_g_dl": 11.5},
    ])
    assert list(trusted_hb(df).image_id) == ["d"]

    with pytest.raises(KeyError):
        trusted_hb(pd.DataFrame({"hb_g_dl": [1.0]}))


def test_untrusted_rows_carry_a_reason():
    from hemosight.io.manifests import _finalise

    df = _finalise([
        {"image_id": "a", "subject_id": "a", "dataset": "ghana_conj", "hb_g_dl": None},
        {"image_id": "d", "subject_id": "d", "dataset": "eyes_defy", "hb_g_dl": 11.5},
    ])
    reasons = dict(zip(df.image_id, df.hb_label_untrusted_reason))
    assert reasons["a"] and "BINARY-LABEL-ONLY" in reasons["a"]
    assert reasons["d"] is None
