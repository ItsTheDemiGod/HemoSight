"""HemoSight Audit - the methodological checks of Phases 1-5, generalised.

This project cannot ship a haemoglobin estimator. Six representations across two
modalities were tested against thresholds declared before each run, and all six failed:
see the FINAL STATUS table in CLAUDE.md. What it can ship is the apparatus that
produced those verdicts, because the apparatus turned out to be the contribution.

The motivating evidence is in the project's own records. Its literature survey found
0 of 5 applicable sources reporting a demographic baseline and 0 reporting a duplicate
check (reports/literature_gap.md, deliberately under-claimed). Its own duplicate check
found 419 MD5 hashes shared between two datasets distributed as independent sources,
and 52.7% / 50.8% internal redundancy inside two others. Its own demographic baseline
found that sex alone beat every model it built.

Each check here wraps the Phase 1-5 implementation rather than reimplementing it:
hashing is hemosight.io.hashing, grouping is hemosight.io.splits, the baseline
estimator is Phase 4 Gate B's, the FDR correction is Phase 4.5's - imported by the
Phase 4.5 script itself so the two cannot drift.

    from hemosight.audit import load_predictions, run_audit, to_markdown

    inp = load_predictions("predictions.csv", image_dir="images/")
    report = run_audit(inp)
    print(to_markdown(report))
"""

from .contract import AuditInput, ContractError, load_predictions
from .prereg import PreRegistration
from .registry import CHECKS, ALL_IDS, AuditReport, catalogue, run_audit
from .report import to_markdown, to_pdf
from .verdict import FAIL, INSUFFICIENT, PASS, CheckResult

__all__ = [
    "AuditInput", "AuditReport", "CheckResult", "ContractError", "PreRegistration",
    "CHECKS", "ALL_IDS", "catalogue", "load_predictions", "run_audit", "to_markdown",
    "to_pdf", "PASS", "FAIL", "INSUFFICIENT",
]
