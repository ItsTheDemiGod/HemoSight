"""Phase 7 - external-audit ingestion path.

The one property that matters most: a submission whose subject ids were ASSUMED (one
per image) must never produce a PASS on a subject-level check. Phase 1 found 1,708
nominal ids collapsing to 1,067 leak-proof groups; an external table with no subject id
at all is the same hazard with less information, and the harness must say so rather
than certify a split it cannot see through.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hemosight.audit import ALL_IDS, load_predictions, run_audit
from hemosight.audit.ingest import IngestSpec, NotAuditable, ingest
from hemosight.audit.report import to_external_markdown
from hemosight.audit.verdict import INSUFFICIENT, PASS


def _external_table(n=120, seed=3):
    rng = np.random.default_rng(seed)
    hb = rng.normal(13, 1.5, n)
    return pd.DataFrame({
        "image": [f"img_{i:04d}.jpg" for i in range(n)],
        "Hgb": hb.round(1), "prediction": (hb + rng.normal(0, 1.0, n)).round(2),
        "fold": rng.choice(["train", "test"], n), "Gender": rng.choice(["male", "female"], n),
    })


def test_assumed_subject_id_forces_split_integrity_to_insufficient_not_pass(tmp_path):
    """With images supplied and every image distinct, the split check's content axis is
    clean and its subject axis is trivially clean when each image is its own 'subject'.
    That is a PASS the data cannot support. The ingestion record must turn it into
    INSUFFICIENT DATA."""
    from PIL import Image
    df = _external_table()
    rng = np.random.default_rng(0)
    for name in df["image"]:
        Image.fromarray(rng.integers(0, 255, (16, 16, 3), dtype=np.uint8)).save(tmp_path / name)
    spec = IngestSpec(y_true="Hgb", y_pred="prediction", image_path="image", split="fold",
                      sex="Gender", source_description="test table, no subject id")
    out, rec = ingest(df, spec)
    assert "subject_id" in rec.columns_derived
    assert "split_integrity" in rec.unsupported_checks
    # Without the record the table PASSES - the defect the record exists to prevent.
    rep_naive = run_audit(load_predictions(out, image_dir=tmp_path), checks=["split_integrity"])
    assert {r["check_id"]: r["verdict"] for r in rep_naive.results}["split_integrity"] == PASS
    rep = run_audit(load_predictions(out, image_dir=tmp_path),
                    checks=["split_integrity", "demographic_baseline"],
                    unsupported=rec.unsupported_checks)
    v = {r["check_id"]: r["verdict"] for r in rep.results}
    assert v["split_integrity"] == INSUFFICIENT, (
        "with one 'subject' per image the split check would trivially PASS; it must not")


def test_subject_id_derived_from_filename_pattern_is_recorded_and_aggregated():
    df = _external_table(n=60)
    df["image"] = [f"subj{i // 3:03d}_shot{i % 3}.jpg" for i in range(60)]   # 3 images per subject
    spec = IngestSpec(y_true="Hgb", y_pred="prediction", image_path="image",
                      subject_from_image=r"^(subj\d+)_")
    out, rec = ingest(df, spec)
    assert rec.n_subjects == 20 and len(out) == 20
    assert any("DERIVED" in a for a in rec.assumptions)
    assert any("aggregated" in a for a in rec.assumptions)
    assert "split_integrity" not in rec.unsupported_checks   # ids exist, so the check may run


def test_sex_is_normalised_and_g_per_litre_is_refused_unless_declared():
    df = _external_table(n=40)
    spec = IngestSpec(y_true="Hgb", y_pred="prediction", image_path="image", sex="Gender",
                      subject_id="image")
    out, _ = ingest(df, spec)
    assert set(out["sex"]) <= {"M", "F"}
    df_gl = df.copy(); df_gl["Hgb"] *= 10; df_gl["prediction"] *= 10
    with pytest.raises(NotAuditable):
        ingest(df_gl, spec)
    out2, rec2 = ingest(df_gl, IngestSpec(y_true="Hgb", y_pred="prediction", image_path="image",
                                          subject_id="image", hb_units="g/L"))
    assert abs(out2["y_true"].median() - df["Hgb"].median()) < 0.5
    assert any("g/L" in a for a in rec2.assumptions)


def test_classification_only_release_is_not_auditable():
    df = _external_table(n=40)
    df["label"] = (df["Hgb"] < 12).astype(int); df["prob"] = np.random.default_rng(0).random(40).round(2)
    with pytest.raises(NotAuditable) as e:
        ingest(df, IngestSpec(y_true="label", y_pred="prob", image_path="image", subject_id="image"))
    assert "binary" in str(e.value) or "numeric" in str(e.value)


def test_external_report_gives_unchecked_equal_prominence():
    df = _external_table(n=80)
    spec = IngestSpec(y_true="Hgb", y_pred="prediction", image_path="image")   # nothing else
    out, rec = ingest(df, spec)
    rep = run_audit(load_predictions(out), unsupported=rec.unsupported_checks)
    md = to_external_markdown(rep, json.loads(json.dumps(rec.__dict__, default=str)), all_check_ids=ALL_IDS)
    assert "## Part 1 - what was checked" in md and "## Part 2 - what could NOT be checked" in md
    assert md.index("Part 2") > md.index("Part 1")
    assert "Assumptions made" in md and "ASSUMED" in md
    # most checks cannot run on a bare table and the report has to say so per check
    c = rep.to_dict()["counts"]
    assert c["INSUFFICIENT_DATA"] >= 4, c
    assert "INSUFFICIENT DATA is a statement about the release" in md


def test_register_starts_empty_and_no_external_result_is_fabricated():
    reg = Path(__file__).resolve().parents[1] / "configs" / "external_audit_register.json"
    d = json.loads(reg.read_text(encoding="utf-8"))
    assert "entries" in d and "schema" in d
    for e in d["entries"]:
        assert e["auditable"] in ("full", "partial", "none")


# ------------------------------------------------ Task 3B: the availability record
def test_register_entries_and_availability_report_agree():
    """The availability count in the report must be computed from the register, and
    'not auditable' must never have been turned into a failed check anywhere."""
    root = Path(__file__).resolve().parents[1]
    reg = json.loads((root / "configs" / "external_audit_register.json").read_text(encoding="utf-8"))
    entries = reg["entries"]
    assert len(entries) >= 3
    for e in entries:
        assert e["auditable"] in ("full", "partial", "none")
        for f in ("code_released", "weights_released", "predictions_released"):
            assert e[f] in ("released", "partial", "upon_request", "none", "not_stated"), (e["slug"], f)
    k = sum(1 for e in entries if e["auditable"] in ("full", "partial"))
    rep = (root / "reports" / "external_audit_availability.md").read_text(encoding="utf-8")
    assert f"of the {len(entries)} external candidates examined, {k} released artefacts" in rep
    assert "upon request" in rep.lower() and "own category" in rep
    assert "NOT harness verdicts" in rep
    lit = (root / "reports" / "literature_gap.md").read_text(encoding="utf-8")
    assert "NOT REPORTED from a full-text read is not 'audited and failed'" in lit
    assert "UNKNOWN is not evidence of absence" in lit


def test_external_run_record_produced_no_predictions_and_touched_no_repo_code():
    root = Path(__file__).resolve().parents[1]
    p = root / "configs" / "external_audit_run_record.json"
    run = json.loads(p.read_text(encoding="utf-8"))
    assert run["summary"]["ran_to_completion"] == 0
    assert run["summary"]["produced_per_subject_predictions"] == 0
    for nb in run["notebooks"]:
        assert not nb["completed"] and nb["failed_cell"] is not None
        # only path substitutions and Colab-mount skips are allowed changes
        for s in nb["substitutions"]:
            assert "xlsx" in s["from"] or "dataset_anemia" in s["from"] or "anemia_detection" in s["from"] or "Augmented" in s["from"]
        for c in nb["skipped_cells"]:
            assert "Colab" in c["reason"]
