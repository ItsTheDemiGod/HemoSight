"""Filename parsing for the Ghana datasets, where the subject identifier is encoded
in the filename and nowhere else.

Observed conventions in the Ghana conjunctiva set (all of these are real):

    Anemic-001 (10).png            plain series, subject 1, replicate 10
    Non-Anemic-204 - Copy.png      trailing " - Copy"
    Anemic-Conj-009png.png         doubled extension typo
    Anemic-Conj-N-001R.png         "N" sub-series, trailing letter
    Anemic-001FV.png               trailing letters after the number
    Anemic-211 (2)-i10vHz.png      random suffix appended by a dedup tool
    Non-anemic-Con-002 (2) - Copy.png

and in the fingernail set:

    Anemic-Fin-007 (10).png

The parse returns a SUBJECT key that deliberately ignores replicate markers, so all
images of one participant group together. Getting this wrong in the permissive
direction (splitting one participant across folds) is the leakage failure this
project must not commit, so `parse_ghana_name` errs toward merging.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# class-prefix, optional body-site series, optional "N" sub-series, subject number.
_PATTERN = re.compile(
    r"""^
    # Class label. The fingernail set contains two misspellings of "anemic" that
    # together cover 1625 files: "Non-Anrmic-FN" (1581) and "Anmeic-fn" (44).
    # These MUST be recognised - silently dropping "Non-Anrmic" would discard 1581
    # non-anemic files, and mis-parsing it as anemic would flip their labels.
    (?P<cls>non[-\s]?(?:anemic|anmeic|anrmic)|anemic|anmeic|anrmic)
    [-\s]+
    (?:(?P<series>conj|con|fin|fn)[-\s]+)?  # body-site series token, if present
    (?:(?P<sub>n)[-\s]+)?                # rare "N" sub-series
    (?P<num>\d+)                         # subject number
    (?P<rest>.*)$                        # replicate markers, suffixes, junk
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Replicate index: " (10)" anywhere in the tail.
_REPLICATE = re.compile(r"\((\d+)\)")

_SERIES_CANON = {"conj": "conj", "con": "conj", "fin": "fin", "fn": "fin", None: "plain"}


@dataclass(frozen=True)
class GhanaName:
    """Structured view of one Ghana filename."""

    cls: str  # "anemic" | "non-anemic"
    series: str  # "conj" | "fin" | "plain"
    sub_series: str | None  # "n" or None
    number: int
    replicate: int | None
    suffix: str  # leftover tail, kept verbatim for auditing
    is_copy: bool  # filename carried a " - Copy" marker

    @property
    def anemia_label(self) -> int:
        return 1 if self.cls == "anemic" else 0


def parse_ghana_name(stem: str) -> GhanaName | None:
    """Parse a Ghana filename stem. Returns None if it does not match at all."""
    # Strip a doubled extension typo such as "Anemic-145png".
    s = re.sub(r"png$", "", stem.strip(), flags=re.IGNORECASE) if stem.lower().endswith("png") else stem
    m = _PATTERN.match(s.strip())
    if m is None:
        return None
    rest = m.group("rest") or ""
    rep = _REPLICATE.search(rest)
    cls = "non-anemic" if m.group("cls").lower().replace(" ", "").replace("-", "").startswith("non") else "anemic"
    return GhanaName(
        cls=cls,
        series=_SERIES_CANON[(m.group("series") or "").lower() or None],
        sub_series=(m.group("sub") or "").lower() or None,
        number=int(m.group("num")),
        replicate=int(rep.group(1)) if rep else None,
        suffix=rest.strip(),
        is_copy=bool(re.search(r"-\s*copy", rest, re.IGNORECASE)),
    )


def ghana_subject_id(dataset: str, parsed: GhanaName, merge_series: bool) -> str:
    """Build the subject key.

    `merge_series` controls whether e.g. "Anemic-001" and "Anemic-Conj-001" are
    treated as the SAME participant. That question is settled empirically by the
    overlap check, not by assumption; the caller passes the answer in.
    """
    parts = [dataset, parsed.cls]
    if not merge_series:
        parts.append(parsed.series)
        if parsed.sub_series:
            parts.append(parsed.sub_series)
    parts.append(f"{parsed.number:03d}")
    return ":".join(parts)
