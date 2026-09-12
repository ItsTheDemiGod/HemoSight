"""Background execution for the long checks.

Duplicate detection hashes every image and the permutation test refits nothing but
still iterates thousands of times; neither belongs in a request. A thread pool is the
right size of machinery here - the work is one process, one machine, and a handful of
concurrent audits. Progress is written to the Run row so a reload or a second browser
tab sees the same state, rather than living in a module-level dict that a restart loses.
"""

from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor

from hemosight.audit import load_predictions, run_audit
from hemosight.audit.prereg import EMPTY, PreRegistration

from .db import SessionLocal
from .models import PreRegistrationRow, Run, Submission, utcnow

EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audit")


def _set(run_id: str, **fields) -> None:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if run is None:
            return
        for k, v in fields.items():
            setattr(run, k, v)
        db.commit()


def execute(run_id: str) -> None:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if run is None:
            return
        sub = db.get(Submission, run.submission_id)
        pre_row = db.get(PreRegistrationRow, run.prereg_id) if run.prereg_id else None
        checks = list(run.checks or [])
        options = dict(run.options or {})
        csv_path, image_dir = sub.csv_path, sub.image_dir
        declared_first = (None if pre_row is None
                          else bool(pre_row.declared_at <= sub.uploaded_at))

    _set(run_id, status="running", progress=0.0, message="loading submission",
         thresholds_declared_in_advance=declared_first)

    try:
        inp = load_predictions(csv_path, image_dir=image_dir)
        prereg = EMPTY
        if pre_row is not None:
            prereg = PreRegistration(
                title=pre_row.title, thresholds=pre_row.thresholds or {},
                notes=pre_row.notes or "",
                declared_at=pre_row.declared_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                checks_planned=pre_row.checks_planned or [],
                fingerprint=pre_row.fingerprint)

        def progress(f: float, msg: str) -> None:
            _set(run_id, progress=float(max(0.0, min(1.0, f))), message=str(msg)[:200])

        report = run_audit(inp, checks=checks or None, prereg=prereg,
                           progress=progress, options=options)
        _set(run_id, status="done", progress=1.0, message="complete",
             report=report.to_dict(), finished_at=utcnow())
    except Exception as exc:                       # noqa: BLE001 - surfaced to the client
        _set(run_id, status="error", message=f"{type(exc).__name__}: {exc}",
             error=traceback.format_exc()[-4000:], finished_at=utcnow())


def submit(run_id: str) -> None:
    EXECUTOR.submit(execute, run_id)
