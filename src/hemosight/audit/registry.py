"""The check catalogue and the runner.

One place that knows what checks exist, what each needs, what it costs, and which
phase of this project it came from. The front end reads this to build its check
picker; the report reads it for provenance; nothing hard-codes a list of eight.
"""

from __future__ import annotations

import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable

from . import (baselines, ceiling, duplicates, permutation, proxy, seeds,
               split_integrity, subgroups)
from .contract import AuditInput
from .jsonsafe import to_jsonable
from .prereg import EMPTY, PreRegistration
from .verdict import FAIL, INSUFFICIENT, PASS, CheckResult


@dataclass
class CheckSpec:
    check_id: str
    title: str
    run: Callable
    provenance: str
    phase: str
    needs: list[str]
    cost: str                  # "fast" | "slow"
    summary: str
    # The thresholds this check applies when none were declared in advance. Exposed so
    # the pre-registration screen can show a submitter what they are agreeing to before
    # they see any result, rather than after.
    defaults: dict = field(default_factory=dict)


CHECKS: list[CheckSpec] = [
    CheckSpec(
        duplicates.CHECK_ID, duplicates.TITLE, duplicates.run, duplicates.PROVENANCE,
        "Phase 1", ["images"], "slow",
        "MD5, dHash and pHash over the submitted images, then the question that "
        "actually invalidates a score: does any duplicate cross a split boundary?",
        {"max_duplicate_rate": 0.0, "allow_cross_split_duplicates": False}),
    CheckSpec(
        split_integrity.CHECK_ID, split_integrity.TITLE, split_integrity.run,
        split_integrity.PROVENANCE, "Phase 1", ["split"], "slow",
        "Whether the split respects connected components of (subject_id, content "
        "hash) rather than subject_id alone.",
        {"allow_subject_across_splits": False, "allow_group_undersplit": False}),
    CheckSpec(
        baselines.CHECK_ID, baselines.TITLE, baselines.run, baselines.PROVENANCE,
        "Phase 4", ["age|sex|device|site"], "fast",
        "Population mean, each demographic variable alone, and all of them together, "
        "on identical whole-subject folds, against the submitted model.",
        {"model_must_beat_best_demographic_by": 0.0}),
    CheckSpec(
        proxy.CHECK_ID, proxy.TITLE, proxy.run, proxy.PROVENANCE,
        "Phase 4 / 4.5", ["age|sex|device|site"], "fast",
        "How much of the model's advantage survives once a demographic variable is "
        "already in the model, plus a probe recovering that variable from the "
        "model's own output.",
        {"max_skill_explained_by_demographic": 0.75, "max_probe_margin": 0.10}),
    CheckSpec(
        permutation.CHECK_ID, permutation.TITLE, permutation.run,
        permutation.PROVENANCE, "Phase 4.5 / 5", [], "slow",
        "Empirical p against shuffled labels, in both selected-model-only and "
        "selection-aware constructions, with the floor 1/(n+1) always stated.",
        {"alpha": 0.05}),
    CheckSpec(
        seeds.CHECK_ID, seeds.TITLE, seeds.run, seeds.PROVENANCE,
        "Phase 5", ["y_pred_seed__*"], "fast",
        "Spread across independent re-runs of the same model, against the effect "
        "being claimed.",
        {"min_effect_to_seed_sd_ratio": 3.0}),
    CheckSpec(
        subgroups.CHECK_ID, subgroups.TITLE, subgroups.run, subgroups.PROVENANCE,
        "Phase 5", [], "fast",
        "Whether the model's advantage survives dropping the subjects it does best "
        "on, and whether it holds in every submitted subgroup.",
        {"min_retained_advantage_fraction": 0.5}),
    CheckSpec(
        ceiling.CHECK_ID, ceiling.TITLE, ceiling.run, ceiling.PROVENANCE,
        "Phase 4.5", ["feature columns"], "fast",
        "Mutual information and FDR-corrected correlations against a shuffled-target "
        "null: can this input contain the target at all?",
        {"min_features_above_null": 1, "fdr_q": 0.05}),
]

BY_ID = {c.check_id: c for c in CHECKS}
ALL_IDS = [c.check_id for c in CHECKS]


def catalogue() -> list[dict]:
    return [{k: v for k, v in asdict(c).items() if k != "run"} for c in CHECKS]


@dataclass
class AuditReport:
    created_at: str
    input_summary: dict
    results: list[dict]
    prereg: dict
    counts: dict = field(default_factory=dict)
    harness_version: str = "1.0"

    def to_dict(self) -> dict:
        # Coerced here, at the point the report leaves the analysis. Everything
        # downstream - the JSON column, the Markdown renderer, the report fingerprint -
        # then sees the same values, so a fingerprint computed in memory matches one
        # computed after a database round trip.
        return to_jsonable(asdict(self))


def run_audit(inp: AuditInput, checks: list[str] | None = None,
              prereg: PreRegistration | None = None, progress=None,
              options: dict | None = None,
              unsupported: dict[str, str] | None = None) -> AuditReport:
    """Run the selected checks and collect their verdicts.

    A check that raises is reported as INSUFFICIENT_DATA with the exception attached,
    never silently dropped: an audit that quietly omits a check it could not run is
    worse than one that says so.

    `unsupported` maps check ids to a reason they MUST return INSUFFICIENT DATA without
    running - used by the external-ingestion path when a column was assumed rather than
    supplied (e.g. subject_id := image id). A check run on an assumed column can return
    a PASS the data does not support; forcing it here is what keeps that from happening.
    """
    prereg = prereg or EMPTY
    ids = checks or ALL_IDS
    options = options or {}
    unsupported = unsupported or {}
    cache: dict = {}
    results: list[CheckResult] = []

    for n, cid in enumerate(ids):
        spec = BY_ID.get(cid)
        if spec is None:
            continue
        th, declared = prereg.for_check(cid)
        if progress:
            progress(n / max(1, len(ids)), f"{spec.title}")
        if cid in unsupported:
            results.append(CheckResult(
                check_id=cid, title=spec.title, verdict=INSUFFICIENT,
                headline="not run: the input carries an assumption this check cannot survive",
                explanation=("The ingestion record marks this check as unsupported: "
                             f"{unsupported[cid]}. Running it would have produced a verdict "
                             "about a column that was assumed, not supplied, so it was not run."),
                provenance=spec.provenance, missing=[unsupported[cid]],
                details={"forced_by_ingest": True}))
            continue
        try:
            r = spec.run(inp, thresholds=th, preregistered=declared,
                         cache=cache,
                         progress=(lambda f, m, _n=n, _t=len(ids):
                                   progress((_n + f) / max(1, _t), m))
                         if progress else None,
                         **options.get(cid, {}))
        except Exception as exc:                       # noqa: BLE001 - reported, not hidden
            r = CheckResult(
                check_id=cid, title=spec.title, verdict=INSUFFICIENT,
                headline=f"the check could not be completed: {type(exc).__name__}",
                explanation=("This check raised an exception and returned no verdict. "
                             "It is recorded here rather than dropped, because an audit "
                             "that silently omits a check overstates its own coverage."),
                provenance=spec.provenance, missing=["a completed run"],
                details={"exception": f"{type(exc).__name__}: {exc}",
                         "traceback": traceback.format_exc()[-2000:]})
        results.append(r)

    if progress:
        progress(1.0, "done")

    from .content import enrich
    dicts = [enrich(r.to_dict()) for r in results]
    counts = {
        "total": len(dicts),
        PASS: sum(1 for r in dicts if r["verdict"] == PASS),
        FAIL: sum(1 for r in dicts if r["verdict"] == FAIL),
        INSUFFICIENT: sum(1 for r in dicts if r["verdict"] == INSUFFICIENT),
        "preregistered_thresholds": sum(1 for r in dicts
                                        if r["threshold_preregistered"]),
    }
    return AuditReport(
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        input_summary=inp.summary(),
        results=sorted(dicts, key=lambda r: {FAIL: 0, INSUFFICIENT: 1,
                                             PASS: 2}[r["verdict"]]),
        prereg=prereg.to_dict(), counts=counts)
