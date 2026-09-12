"""The verdict vocabulary shared by every audit check.

Three outcomes, and INSUFFICIENT_DATA is a first-class one rather than a polite
failure. This project's own literature table refuses to read UNKNOWN as absence
(`reports/literature_gap.md`, DECISION LOG 2026-09-11); a tool that audits other
people's evidence has to hold itself to the same rule. A check that lacks the column,
the seeds or the images it needs says so and stops. It never infers a verdict from
what it could not measure.

A check also records whether the threshold it was judged against was declared BEFORE
the results were seen. That distinction is what made this project's own gate results
defensible, and an audit report that cannot show it is a weaker document.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

PASS = "PASS"
FAIL = "FAIL"
INSUFFICIENT = "INSUFFICIENT_DATA"

Verdict = Literal["PASS", "FAIL", "INSUFFICIENT_DATA"]


@dataclass
class CheckResult:
    """One check's finding: a verdict, the number behind it, and what it means."""

    check_id: str
    title: str
    verdict: Verdict
    headline: str                       # the measured quantity, one line
    explanation: str                    # what it means, in plain language
    provenance: str                     # where in Phases 1-5 this check came from
    measured: dict[str, Any] = field(default_factory=dict)
    threshold: dict[str, Any] | None = None
    threshold_preregistered: bool = False
    missing: list[str] = field(default_factory=list)   # why INSUFFICIENT_DATA
    details: dict[str, Any] = field(default_factory=dict)
    seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def insufficient(check_id: str, title: str, provenance: str, missing: list[str],
                 explanation: str) -> CheckResult:
    """Build the INSUFFICIENT_DATA result, naming exactly what was absent."""
    return CheckResult(
        check_id=check_id, title=title, verdict=INSUFFICIENT,
        headline="not measurable from the submitted input",
        explanation=explanation, provenance=provenance, missing=list(missing),
    )


class Timer:
    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *exc):
        self.seconds = time.time() - self.t0
        return False
