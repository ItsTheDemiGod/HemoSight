"""Tests for the Phase 5 consolidation and reproducibility package."""

from __future__ import annotations

import json

from hemosight.io import paths


def test_reproduction_plan_references_only_existing_scripts():
    """Every stage in the entry point must point at a script that exists."""
    import sys

    sys.path.insert(0, str(paths.ROOT / "scripts"))
    from reproduce_all import STAGES

    missing = [s.script for s in STAGES
               if not (paths.ROOT / "scripts" / s.script).exists()]
    assert not missing, f"reproduce_all references missing scripts: {missing}"
    assert len(STAGES) >= 30


def test_reproduction_plan_declares_runtimes():
    import sys

    sys.path.insert(0, str(paths.ROOT / "scripts"))
    from reproduce_all import STAGES

    assert all(s.minutes > 0 for s in STAGES), "every stage needs a runtime estimate"
    assert any(s.slow for s in STAGES), "slow stages must be flagged for --fast"


def test_no_dataset_files_are_tracked_by_git():
    """The project's standing rule: nothing from data/ ever enters version control."""
    import subprocess

    out = subprocess.run(["git", "ls-files"], cwd=paths.ROOT,
                         capture_output=True, text=True).stdout.splitlines()
    assert not [f for f in out if f.startswith("data/")], "data/ must never be tracked"
    assert not [f for f in out if f.startswith("reports/figures/")], (
        "dataset-derived figures must never be tracked - licences are unverified")
    binary = [f for f in out
              if f.lower().endswith((".png", ".jpg", ".jpeg", ".mat", ".npz", ".pt"))]
    assert not binary, f"binary/dataset artefacts tracked: {binary[:5]}"


def test_seed_is_frozen_in_config():
    import yaml

    cfg = yaml.safe_load((paths.CONFIGS / "phase1_splits.yaml").read_text(encoding="utf-8"))
    assert cfg["seed"] == 20260911


def test_literature_table_does_not_overclaim():
    """The literature counts must carry their own caveat, since the sample is tiny."""
    p = paths.REPORTS / "literature_gap.md"
    if not p.exists():
        return
    txt = p.read_text(encoding="utf-8")
    assert "too small to support" in txt.lower()
    assert "UNKNOWN is not evidence of absence" in txt


def test_dataset_manifest_states_every_licence():
    """Until 2026-09-12 this asserted the word UNVERIFIED was present. Phase 6.5
    verified every source (4 CC BY 4.0, 2 custom no-redistribution agreements, 2 with
    no licence stated), so the test now asserts each of those states is written down
    and that nothing has quietly reverted to an assumption."""
    p = paths.REPORTS / "dataset_manifest.md"
    if not p.exists():
        return
    txt = p.read_text(encoding="utf-8")
    assert "verified 2026-09-12" in txt, "licence status must be stated, not assumed"
    assert txt.count("CC BY 4.0") >= 4
    assert "CUSTOM AGREEMENT" in txt and "NONE STATED" in txt
    assert "research use assumed" not in txt


def test_hardening_reports_empirical_p_not_only_z():
    """If the hardening ran, it must report an empirical p-value, not just a z."""
    f = paths.INTERIM / "phase5" / "harden.json"
    if not f.exists():
        return
    d = json.loads(f.read_text(encoding="utf-8"))
    for key in ("permutation_selected_only", "permutation_selection_aware"):
        if key in d:
            assert "p_empirical" in d[key], f"{key} must report an empirical p-value"
            assert "z_parametric" in d[key]


def _perm_module():
    import sys
    sys.path.insert(0, str(paths.ROOT / "scripts"))
    import phase5_perm_extended
    return phase5_perm_extended


def test_permutation_labels_depend_only_on_the_index():
    """Resume is only sound if permutation i is the same experiment after a restart.

    The first extended run was killed at n=41 and could not be continued, because its
    shuffles came from one sequentially consumed generator: permutation i depended on
    every permutation before it. These must be reproducible from the index alone.
    """
    import numpy as np
    m = _perm_module()
    y = np.arange(40, dtype=float)
    assert np.array_equal(m.permuted_labels(y, 7), m.permuted_labels(y, 7))
    assert not np.array_equal(m.permuted_labels(y, 7), m.permuted_labels(y, 8))
    # Drawing 8 first must not change what 7 produces.
    m.permuted_labels(y, 8)
    assert np.array_equal(m.permuted_labels(y, 7),
                          np.random.default_rng(m.PERM_SEED + 7).permutation(y))
    # A shuffle, not a resample: the multiset of labels is preserved exactly.
    assert np.array_equal(np.sort(m.permuted_labels(y, 7)), y)


def test_checkpoint_reader_survives_a_torn_final_line(tmp_path):
    """A process killed mid-write leaves a partial line; it must not block resume."""
    m = _perm_module()
    f = tmp_path / "perm.jsonl"
    f.write_text('{"i": 0, "min_mae": 1.2}\n{"i": 1, "min_mae": 1.19}\n{"i": 2, "min_',
                 encoding="utf-8")
    done = m.read_checkpoint(f)
    assert set(done) == {0, 1}, "the torn line must be dropped, the good ones kept"


def test_extended_permutation_summary_is_honest_about_the_floor():
    """An empirical p equal to 1/(n+1) is a bound. It must be labelled as one."""
    import numpy as np
    m = _perm_module()
    s = m.summarise(np.array([1.19, 1.20, 1.21]), real=1.1124)
    assert s["at_floor"] is True and s["p_empirical"] == s["p_floor"]
    s2 = m.summarise(np.array([1.10, 1.20, 1.21]), real=1.1124)
    assert s2["at_floor"] is False and s2["n_at_or_below_real"] == 1


def test_extended_run_does_not_alter_the_reported_p():
    """The standing p = 0.0164 stands until the extended run is consolidated by hand.

    The extended runner READS harden.json for the real MAE - so it cannot move the
    number it is testing against - and writes only its own JSONL and summary.
    """
    src = (paths.ROOT / "scripts" / "phase5_perm_extended.py").read_text(encoding="utf-8")
    assert 'harden.json' in src, "the real MAE must be read from the hardening run"
    for line in src.splitlines():
        if "harden.json" in line:
            assert not any(w in line for w in ("write_text", "open(", "dump")),                 f"the extended runner must never write harden.json: {line.strip()}"

    f = paths.INTERIM / "phase5" / "harden.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        if "permutation_selection_aware" in d:
            assert d["permutation_selection_aware"]["n"] >= 60
