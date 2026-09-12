"""Pre-registration: thresholds declared before the results are seen.

WHY THIS IS PART OF THE TOOL AND NOT A CONVENTION. Every gate in this project was
declared in CLAUDE.md with a date before the script that tested it was run - the Phase 3
bands, the Phase 2.5 feasibility gate, the Phase 4 Gate A and B thresholds. That is the
only reason results like "3.417 g/dL against a >2.0 NOT RECOVERABLE threshold" can be
read as a verdict rather than as a number with an interpretation attached afterwards.
Phase 2.5 and Phase 3.5 both refuted their own hypotheses, and the pre-declaration is
what makes those refutations credible rather than post-hoc.

A pre-registration here records the thresholds, a timestamp, and a fingerprint over the
canonical form. The report then states, per check, whether the threshold it was judged
against was declared in advance or supplied afterwards. Neither is forbidden. Only one
of them is evidence.

The fingerprint is a SHA-256 over the canonical JSON. It detects an edited
pre-registration, which is the honest limit of what a local file can promise: it is a
tamper-evidence mechanism, not a trusted timestamp, and the report says so rather than
implying a guarantee it cannot give.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class PreRegistration:
    """Thresholds and their declaration time."""

    title: str
    thresholds: dict[str, dict] = field(default_factory=dict)
    notes: str = ""
    declared_at: str = field(default_factory=_now)
    checks_planned: list[str] = field(default_factory=list)
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.fingerprint:
            self.fingerprint = self.compute_fingerprint()

    def canonical(self) -> str:
        body = {"title": self.title, "thresholds": self.thresholds,
                "notes": self.notes, "declared_at": self.declared_at,
                "checks_planned": sorted(self.checks_planned)}
        return json.dumps(body, sort_keys=True, separators=(",", ":"))

    def compute_fingerprint(self) -> str:
        return hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()

    def intact(self) -> bool:
        return self.fingerprint == self.compute_fingerprint()

    def for_check(self, check_id: str) -> tuple[dict, bool]:
        """Return (thresholds, declared_in_advance) for one check."""
        if check_id in self.thresholds:
            return dict(self.thresholds[check_id]), True
        return {}, False

    def declared_before(self, results_uploaded_at: str) -> bool:
        """Whether the declaration predates the results it judges."""
        try:
            a = datetime.strptime(self.declared_at, "%Y-%m-%dT%H:%M:%SZ")
            b = datetime.strptime(results_uploaded_at, "%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError):
            return False
        return a <= b

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: str | Path) -> "PreRegistration":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**d)


EMPTY = PreRegistration(title="(none declared)", notes=(
    "No thresholds were declared before these results were seen. Every verdict below "
    "was judged against this tool's defaults, which is weaker evidence than a "
    "pre-declared threshold and is recorded as such."))
