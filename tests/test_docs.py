"""Tests for the project's own documentation invariants.

CLAUDE.md is loaded into every session's context. On 2026-09-17 it had grown to
233,820 characters against a 150,000-character limit and was being silently
truncated - sessions were reading a partial record with no indication of what was
missing. The evidentiary record was split into docs/archive/; these tests keep the
arrangement from regressing.
"""

from __future__ import annotations

from hemosight.io import paths

# Well under the 150k load limit, so there is room for the phases still to come.
CLAUDE_MD_MAX_CHARS = 120_000

ARCHIVE_FILES = (
    "decision_log.md",
    "results_log.md",
    "superseded_claims.md",
    "corrections.md",
    "README.md",
)


def _claude_md() -> str:
    return (paths.ROOT / "CLAUDE.md").read_text(encoding="utf-8")


def test_claude_md_fits_in_context():
    """CLAUDE.md must stay small enough to load in full, never truncated.

    If this fails, SPLIT - move content into docs/archive/ and leave a pointer.
    Never delete anything to get under the limit: the logs are append-only and the
    file is the project's evidentiary record.
    """
    n = len(_claude_md())
    assert n <= CLAUDE_MD_MAX_CHARS, (
        f"CLAUDE.md is {n:,} characters, over the {CLAUDE_MD_MAX_CHARS:,} limit. "
        "Move content to docs/archive/ and point at it - do not delete anything."
    )


def test_the_archive_exists_and_is_pointed_at():
    """Every archive file must exist, and CLAUDE.md must point at each one."""
    txt = _claude_md()
    archive = paths.ROOT / "docs" / "archive"
    for name in ARCHIVE_FILES:
        assert (archive / name).exists(), f"missing archive file: docs/archive/{name}"
    for name in ARCHIVE_FILES:
        if name == "README.md":
            continue
        assert f"docs/archive/{name}" in txt, (
            f"CLAUDE.md must point at docs/archive/{name}")


def test_the_logs_kept_every_entry():
    """The counts recorded at the split. These only ever go up."""
    archive = paths.ROOT / "docs" / "archive"
    dec = (archive / "decision_log.md").read_text(encoding="utf-8")
    res = (archive / "results_log.md").read_text(encoding="utf-8")

    n_dec = sum(1 for line in dec.splitlines() if line.startswith("### "))
    n_res = sum(1 for line in res.splitlines() if line.startswith("### "))
    assert n_dec >= 81, f"decision log has {n_dec} entries, was 81 at the split"
    assert n_res >= 48, f"results log has {n_res} entries, was 48 at the split"

    # The section headings are retained so existing "section 7 / 8" references resolve.
    assert "## 7. DECISION LOG" in dec
    assert "## 8. RESULTS LOG" in res


def test_claude_md_keeps_only_the_session_header():
    """The logs live in the archive; CLAUDE.md carries pointers, not entries."""
    txt = _claude_md()
    for required in ("## CURRENT STATE", "## THE ARCHIVE", "## 9. WORKING PROTOCOL",
                     "## 6. PHASE PLAN", "## 2. THE NOVELTY CLAIMS"):
        assert required in txt, f"CLAUDE.md must keep {required}"

    # A dated log entry in CLAUDE.md means someone appended to the wrong file.
    dated = [line for line in txt.splitlines()
             if line.startswith("### 20") and " — " in line or line.startswith("### 20") and " - " in line]
    assert not dated, (
        "dated log entries belong in docs/archive/, not CLAUDE.md: "
        f"{dated[:3]}")


def test_the_working_protocol_routes_new_entries_to_the_archive():
    """Future sessions must be told where to append."""
    txt = _claude_md()
    protocol = txt[txt.index("## 9. WORKING PROTOCOL"):]
    assert "docs/archive/decision_log.md" in protocol
    assert "docs/archive/results_log.md" in protocol
    assert "docs/archive/corrections.md" in protocol
    assert "docs/archive/superseded_claims.md" in protocol
    assert "append" in protocol.lower()
    # The never-delete rule must be stated as covering the archive too.
    assert "append-only" in protocol or "append only" in protocol.lower()
    assert str(CLAUDE_MD_MAX_CHARS // 1000) in protocol or "120,000" in protocol
