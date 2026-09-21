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
    "predeclarations.md",
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


# --------------------------------------------------------------------------- #
# The pre-declaration rule (CLAUDE.md section 9, added 2026-09-21)
#
# CLAUDE.md was split down to ~76k on 2026-09-17 and was back over the 120k limit
# four phases later. The regrowth was per-phase pre-declaration blocks accumulating
# inline: load-bearing while a phase runs, pure evidence once it closes. The rule is
# that a closed phase's block moves verbatim to docs/archive/predeclarations.md and
# section 6 keeps a heading, one line of summary and a pointer.
# --------------------------------------------------------------------------- #
PREDECLARATIONS = "docs/archive/predeclarations.md"

# Lines that OPEN a pre-declaration block in CLAUDE.md section 6. Each must be
# followed closely by a pointer at the archive, never by the block itself.
PREDECL_OPENERS = (
    "#### PRE-DECLARED",
    "**Thresholds declared BEFORE running",
    "**TASK 0 GATE",
    "**GATE A",
    "**GATE A and GATE B thresholds",
    "**Same pre-declared thresholds",
)
POINTER_WINDOW = 6          # lines within which the pointer must appear


def _predecl_openers(lines: list[str]) -> list[int]:
    return [i for i, ln in enumerate(lines)
            if any(ln.startswith(o) for o in PREDECL_OPENERS)]


def test_closed_phase_predeclarations_are_not_inline():
    """A pre-declaration may stay inline only while its phase is ACTIVE.

    Every phase is closed (CURRENT STATE says so), so every opener in CLAUDE.md must
    be a heading-plus-pointer, not the block itself. If you are adding a NEW phase and
    this fails, that is correct behaviour while the phase is open - move the block to
    docs/archive/predeclarations.md when you close it, and leave the pointer.
    """
    txt = _claude_md()
    assert "Active phase: none" in txt, (
        "a phase is active; this test assumes all phases are closed - see "
        "CLAUDE.md CURRENT STATE and the pre-declaration rule in section 9")
    lines = txt.splitlines()
    openers = _predecl_openers(lines)
    assert openers, "expected pre-declaration headings in CLAUDE.md section 6"
    offenders = []
    for i in openers:
        window = "\n".join(lines[i:i + POINTER_WINDOW])
        if PREDECLARATIONS not in window:
            offenders.append(f"line {i + 1}: {lines[i][:70]}")
    assert not offenders, (
        "closed-phase pre-declaration block found inline in CLAUDE.md. Move it "
        f"VERBATIM to {PREDECLARATIONS} and leave a heading, one line of summary and a "
        "pointer. Moving it does not weaken it: what makes it a pre-declaration is the "
        f"commit that carried it, which git records permanently.\n  " +
        "\n  ".join(offenders))


def test_every_predeclaration_pointer_resolves():
    """A pointer must name a section that actually exists in the archive file."""
    import re
    archive = paths.ROOT / "docs" / "archive" / "predeclarations.md"
    assert archive.exists(), f"missing {PREDECLARATIONS}"
    body = archive.read_text(encoding="utf-8")
    sections = {int(m.group(1)) for m in re.finditer(r"^## (\d+)\. ", body, re.M)}
    assert sections, "predeclarations.md has no numbered sections"

    txt = _claude_md()
    cited = {int(m.group(1)) for m in re.finditer(
        r"predeclarations\.md`?\s*(?:§|section )(\d+)", txt)}
    assert cited, "CLAUDE.md cites no pre-declaration section"
    missing = sorted(cited - sections)
    assert not missing, (
        f"CLAUDE.md points at {PREDECLARATIONS} sections that do not exist: {missing}")

    # every block that was moved must still be pointed at from section 6
    n_openers = len(_predecl_openers(txt.splitlines()))
    assert len(sections) >= n_openers, (
        f"{len(sections)} archived pre-declarations against {n_openers} headings in "
        "CLAUDE.md - a block was moved without leaving its pointer, or vice versa")


def test_the_protocol_states_the_predeclaration_rule_and_why_it_is_not_a_weakening():
    """The rule, and the reason moving a pre-declaration cannot weaken it."""
    txt = _claude_md()
    protocol = txt[txt.index("## 9. WORKING PROTOCOL"):]
    assert PREDECLARATIONS in protocol, (
        "section 9 must route closed-phase pre-declarations to the archive")
    assert "active" in protocol.lower(), (
        "section 9 must say a pre-declaration stays inline only while its phase is active")
    # git, not file location, is what makes a pre-declaration one
    assert "committed before the run" in protocol, (
        "section 9 must state that what makes a declaration a PRE-declaration is that it "
        "was committed before the run, so moving it is never a weakening")
