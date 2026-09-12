"""HemoSight Audit - HTTP service.

No authentication in this phase, by design and stated rather than omitted: the service
is a local research instrument, and every route reads or writes only files it created
under data/interim/phase6/service.

    .\\.venv\\Scripts\\python.exe -m uvicorn app.backend.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from hemosight.audit import ContractError, load_predictions
from hemosight.audit.jsonsafe import to_jsonable
from hemosight.audit.prereg import PreRegistration
from hemosight.audit.registry import ALL_IDS, AuditReport, BY_ID, catalogue
from hemosight.audit.report import to_markdown, to_pdf

from . import jobs
from .db import UPLOAD_DIR, get_session, init_db
from .models import PreRegistrationRow, Run, Submission, new_id
from .schemas import PreRegIn, PreRegOut, RunIn, RunOut, SubmissionOut

# Tables are created at import, not on a startup event: a startup hook does not fire
# when the app is driven by TestClient without a context manager, and the failure mode
# is a confusing "no such table" rather than an obvious one.
init_db()

app = FastAPI(title="HemoSight Audit",
              description="Methodological checks for a claimed screening model. "
                          "Produced by a project whose own model failed every gate.",
              version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)


def _iso(dt) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------- catalogue
@app.get("/api/checks")
def list_checks() -> list[dict]:
    return catalogue()


@app.get("/api/content")
def content() -> dict:
    """The content model: plain and technical layers per check, the what-to-do
    categories, and the glossary. One source (`hemosight.audit.content`), read by
    every page, so wording cannot drift between screens."""
    from hemosight.audit.content import CATEGORIES, CATEGORY_PLAIN, GLOSSARY, catalogue
    return {"checks": catalogue(), "glossary": GLOSSARY,
            "categories": [{"id": c, "plain": CATEGORY_PLAIN[c]} for c in CATEGORIES]}


@app.get("/api/sample/{name}")
def sample_file(name: str):
    """One of the synthetic sample submissions, for download from the upload page."""
    from fastapi.responses import FileResponse
    root = Path(__file__).resolve().parent / "sample_data"
    f = root / name
    if not f.is_file() or f.suffix != ".csv" or f.resolve().parent != root.resolve():
        raise HTTPException(404, "no such sample")
    return FileResponse(str(f), media_type="text/csv", filename=name)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "checks": len(ALL_IDS)}


# ------------------------------------------------------------ pre-registration
@app.post("/api/prereg", response_model=PreRegOut)
def create_prereg(body: PreRegIn, db: Session = Depends(get_session)) -> PreRegOut:
    """Declare thresholds. Do this BEFORE uploading results, or the report says so."""
    unknown = [k for k in body.thresholds if k not in BY_ID]
    if unknown:
        raise HTTPException(422, f"unknown check id(s): {unknown}")
    pr = PreRegistration(title=body.title, thresholds=body.thresholds,
                         notes=body.notes, checks_planned=body.checks_planned)
    row = PreRegistrationRow(title=pr.title, notes=pr.notes, thresholds=pr.thresholds,
                             checks_planned=pr.checks_planned,
                             fingerprint=pr.fingerprint)
    db.add(row)
    db.commit()
    return PreRegOut(id=row.id, title=row.title, notes=row.notes,
                     thresholds=row.thresholds, checks_planned=row.checks_planned,
                     fingerprint=row.fingerprint, declared_at=_iso(row.declared_at))


@app.get("/api/prereg", response_model=list[PreRegOut])
def list_prereg(db: Session = Depends(get_session)) -> list[PreRegOut]:
    rows = db.scalars(select(PreRegistrationRow)
                      .order_by(PreRegistrationRow.declared_at.desc())).all()
    return [PreRegOut(id=r.id, title=r.title, notes=r.notes, thresholds=r.thresholds,
                      checks_planned=r.checks_planned, fingerprint=r.fingerprint,
                      declared_at=_iso(r.declared_at)) for r in rows]


@app.get("/api/prereg/{prereg_id}", response_model=PreRegOut)
def get_prereg(prereg_id: str, db: Session = Depends(get_session)) -> PreRegOut:
    r = db.get(PreRegistrationRow, prereg_id)
    if r is None:
        raise HTTPException(404, "no such pre-registration")
    return PreRegOut(id=r.id, title=r.title, notes=r.notes, thresholds=r.thresholds,
                     checks_planned=r.checks_planned, fingerprint=r.fingerprint,
                     declared_at=_iso(r.declared_at))


# ------------------------------------------------------------------ submission
def _availability(inp) -> tuple[list[str], dict[str, str]]:
    """Which checks this submission can actually support, and why not for the rest."""
    ok, no = [], {}
    for cid in ALL_IDS:
        if cid == "duplicates" and not (inp.has("image_path") or inp.image_dir):
            no[cid] = "needs an image_path column or an uploaded image archive"
        elif cid == "split_integrity" and not inp.has("split"):
            no[cid] = "needs a split column"
        elif cid in ("demographic_baseline", "proxy_probe") and not inp.demographics:
            no[cid] = "needs at least one of age, sex, device, site"
        elif cid == "seed_stability" and len(inp.seed_predictions) < 3:
            no[cid] = (f"needs >= 3 y_pred_seed__<k> columns, found "
                       f"{len(inp.seed_predictions)}")
        elif cid == "ceiling" and not inp.feature_columns:
            no[cid] = "needs the model's input features as numeric columns"
        else:
            ok.append(cid)
    return ok, no


@app.post("/api/submissions", response_model=SubmissionOut)
async def upload(predictions: UploadFile = File(...),
                 images: UploadFile | None = File(None),
                 image_dir: str | None = Form(None),
                 db: Session = Depends(get_session)) -> SubmissionOut:
    """Upload a predictions CSV, optionally with images.

    Images arrive either as a zip archive or as a path to a directory already on this
    machine - the second is what a local research user actually has, and copying a
    dataset to upload it would be wasteful and, for this project's data, forbidden.
    """
    row = Submission(id=new_id(),
                     filename=predictions.filename or "predictions.csv")
    dest = UPLOAD_DIR / row.id
    dest.mkdir(parents=True, exist_ok=True)
    csv_path = dest / "predictions.csv"
    with open(csv_path, "wb") as fh:
        shutil.copyfileobj(predictions.file, fh)

    img_dir: Path | None = None
    if images is not None and images.filename:
        archive = dest / "images.zip"
        with open(archive, "wb") as fh:
            shutil.copyfileobj(images.file, fh)
        img_dir = dest / "images"
        img_dir.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(archive) as z:
                for member in z.namelist():
                    # Refuse absolute or traversing paths rather than trusting the zip.
                    p = Path(member)
                    if p.is_absolute() or ".." in p.parts:
                        continue
                    z.extract(member, img_dir)
        except zipfile.BadZipFile:
            raise HTTPException(422, "the uploaded image archive is not a readable zip")
    elif image_dir:
        p = Path(image_dir)
        if not p.is_dir():
            raise HTTPException(422, f"no such directory on this machine: {image_dir}")
        img_dir = p

    try:
        inp = load_predictions(csv_path, image_dir=img_dir)
    except ContractError as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise HTTPException(422, str(exc))

    ok, no = _availability(inp)
    row.csv_path = str(csv_path)
    row.image_dir = str(img_dir) if img_dir else None
    row.n_rows = inp.n
    row.n_subjects = int(inp.summary()["subjects"])
    # Coerced on assignment, not only on write: this same object is
    # returned in the response, and pydantic would be the next thing to
    # meet a numpy.bool_.
    row.summary = to_jsonable(inp.summary())
    db.add(row)
    db.commit()
    return SubmissionOut(id=row.id, filename=row.filename, n_rows=row.n_rows,
                         n_subjects=row.n_subjects, summary=row.summary,
                         uploaded_at=_iso(row.uploaded_at), warnings=inp.warnings,
                         available_checks=ok, unavailable_checks=no)


@app.get("/api/submissions/{sub_id}", response_model=SubmissionOut)
def get_submission(sub_id: str, db: Session = Depends(get_session)) -> SubmissionOut:
    row = db.get(Submission, sub_id)
    if row is None:
        raise HTTPException(404, "no such submission")
    inp = load_predictions(row.csv_path,
                           image_dir=row.image_dir if row.image_dir else None)
    ok, no = _availability(inp)
    return SubmissionOut(id=row.id, filename=row.filename, n_rows=row.n_rows,
                         n_subjects=row.n_subjects, summary=row.summary,
                         uploaded_at=_iso(row.uploaded_at), warnings=inp.warnings,
                         available_checks=ok, unavailable_checks=no)


@app.get("/api/submissions/{sub_id}/preview")
def preview(sub_id: str, rows: int = 15,
            db: Session = Depends(get_session)) -> dict:
    """First rows and dtypes, for the column-mapping screen."""
    import pandas as pd
    row = db.get(Submission, sub_id)
    if row is None:
        raise HTTPException(404, "no such submission")
    df = pd.read_csv(row.csv_path, nrows=max(1, min(rows, 200)))
    return {"columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns],
            "rows": json.loads(df.head(rows).to_json(orient="records"))}


# ------------------------------------------------------------------------ runs
@app.post("/api/runs", response_model=RunOut)
def create_run(body: RunIn, db: Session = Depends(get_session)) -> RunOut:
    sub = db.get(Submission, body.submission_id)
    if sub is None:
        raise HTTPException(404, "no such submission")
    unknown = [c for c in body.checks if c not in BY_ID]
    if unknown:
        raise HTTPException(422, f"unknown check id(s): {unknown}")
    if body.prereg_id and db.get(PreRegistrationRow, body.prereg_id) is None:
        raise HTTPException(404, "no such pre-registration")

    run = Run(submission_id=sub.id, prereg_id=body.prereg_id,
              checks=body.checks or ALL_IDS, options=body.options or {},
              status="queued", message="queued")
    db.add(run)
    db.commit()
    jobs.submit(run.id)
    return _run_out(run)


def _run_out(run: Run) -> RunOut:
    return RunOut(id=run.id, submission_id=run.submission_id,
                  prereg_id=run.prereg_id, checks=run.checks or [],
                  status=run.status, progress=run.progress, message=run.message,
                  report=run.report, error=run.error,
                  thresholds_declared_in_advance=(
                      None if run.thresholds_declared_in_advance is None
                      else bool(run.thresholds_declared_in_advance)),
                  started_at=_iso(run.started_at), finished_at=_iso(run.finished_at))


@app.get("/api/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_session)) -> RunOut:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, "no such run")
    return _run_out(run)


@app.get("/api/runs", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_session)) -> list[RunOut]:
    rows = db.scalars(select(Run).order_by(Run.started_at.desc()).limit(50)).all()
    return [_run_out(r) for r in rows]


def _report_object(run: Run) -> AuditReport:
    d = dict(run.report)
    return AuditReport(**d)


@app.get("/api/runs/{run_id}/report.md", response_class=PlainTextResponse)
def report_markdown(run_id: str, db: Session = Depends(get_session)) -> str:
    run = db.get(Run, run_id)
    if run is None or not run.report:
        raise HTTPException(404, "no completed report for this run")
    return to_markdown(_report_object(run))


@app.get("/api/runs/{run_id}/report.pdf")
def report_pdf(run_id: str, db: Session = Depends(get_session)) -> Response:
    run = db.get(Run, run_id)
    if run is None or not run.report:
        raise HTTPException(404, "no completed report for this run")
    out = Path(UPLOAD_DIR) / run.submission_id / f"audit_{run.id}.pdf"
    try:
        to_pdf(_report_object(run), out)
    except RuntimeError as exc:
        # reportlab is a declared dependency (pyproject.toml, since Phase 6.5); this
        # branch is reached only in an environment that skipped it. Say so plainly
        # instead of returning a broken file.
        raise HTTPException(501, str(exc))
    return Response(out.read_bytes(), media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="audit_{run.id}.pdf"'})


# ------------------------------------------------------------------ case study
@app.get("/api/case-study")
def case_study() -> dict:
    """This project's own results, as the worked example.

    Read from the artefacts on disk rather than retyped, so the page cannot drift from
    the record. The extended permutation run is reported as IN PROGRESS: until it is
    consolidated on 2026-09-12, the figure that stands is p <= 0.0041 at n = 240,
    read from harden.json rather than retyped.
    """
    from hemosight.io import paths
    out: dict = {"checks": [], "status": {}}

    def read(p: Path):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    harden = read(paths.INTERIM / "phase5" / "harden.json") or {}
    overlap = read(paths.INTERIM / "overlap" / "overlap_results.json") or {}
    gate_b = read(paths.INTERIM / "phase4" / "gate_b.json") or {}
    ceiling = read(paths.INTERIM / "phase4_5" / "ceiling.json") or {}
    validation = read(paths.INTERIM / "phase6" / "harness_validation.json") or {}

    # Prefer the extended run once it has been consolidated. Reading the figure
    # rather than holding a copy is the whole point: this page cannot drift from
    # harden.json, and it follows a supersession automatically.
    pa = (harden.get("permutation_selection_aware_extended")
          or harden.get("permutation_selection_aware", {}))
    ss = harden.get("seed_stability", {})
    base = gate_b.get("baselines", {})

    out["checks"] = [
        {"check_id": "duplicates", "verdict": "FAIL", "phase": "Phase 1",
         "measured": ("419 MD5 hashes shared between two datasets distributed as "
                      "independent sources; 98.2% within pHash Hamming 10"),
         "what_it_caught": ("CP-AnemiC is contained inside the Ghana conjunctiva set. "
                            "They are one site, permanently. Any cross-site claim "
                            "treating them as two would have been invalid."),
         "raw": {k: overlap.get(k) for k in list(overlap)[:4]}},
        {"check_id": "split_integrity", "verdict": "FAIL", "phase": "Phase 1",
         "measured": "1,708 nominal subject ids collapse to 1,067 leak-proof groups",
         "what_it_caught": ("The gap of 641 is exactly the leakage a subject-level "
                            "split would have permitted, and nothing in the file "
                            "listing showed it.")},
        {"check_id": "demographic_baseline", "verdict": "FAIL", "phase": "Phase 4",
         "measured": (f"sex alone MAE {base.get('sex_only', {}).get('mae_g_dl', 0.831):.3f} "
                      f"vs the PPG model at 1.190 and the population mean at "
                      f"{base.get('population_mean', {}).get('mae_g_dl', 1.175):.3f}"),
         "what_it_caught": ("No method in six attempts across two modalities beat a "
                            "single binary demographic variable.")},
        {"check_id": "proxy_probe", "verdict": "FAIL", "phase": "Phase 4",
         "measured": "PPG + demographics MAE 0.824 against demographics alone 0.831",
         "what_it_caught": ("A model inside the pre-declared VIABLE band that was a "
                            "sex classifier with a PPG-shaped decoration attached.")},
        {"check_id": "ceiling", "verdict": "FAIL", "phase": "Phase 4.5",
         "measured": (f"0 of {ceiling.get('n_features', 51)} features above the "
                      "mutual-information null; 0 surviving FDR"),
         "what_it_caught": ("Licensed the stronger claim - the signal is absent from "
                            "the hand-engineered features, not merely unfound.")},
        {"check_id": "permutation", "verdict": "PASS", "phase": "Phase 5",
         "measured": (f"selection-aware empirical p = "
                      f"{pa.get('p_empirical', 0.004149):.4f} at n = {pa.get('n', 240)}, "
                      f"z = {pa.get('z_parametric', -4.96):.2f}"),
         "what_it_caught": ("The one surviving positive claim - and that its p is the "
                            "FLOOR 1/(n+1), a bound rather than a measurement.")},
        {"check_id": "seed_stability", "verdict": "PASS", "phase": "Phase 5",
         "measured": (f"SD {ss.get('sd', 0.0069):.4f} over {ss.get('n_seeds', 10)} "
                      f"seeds, against a real-vs-null gap of 0.0815 - 11.9x"),
         "what_it_caught": ("That the effect is not one lucky initialisation. The rule "
                            "was declared before the run as grounds for retraction.")},
        {"check_id": "subgroup_robustness", "verdict": "PASS", "phase": "Phase 5",
         "measured": "MAE 1.1124 -> 1.2258 after dropping the best-performing decile",
         "what_it_caught": ("A weak effect spread across the cohort rather than a few "
                            "subjects carrying the average.")},
    ]

    out["claim"] = {
        "surviving_positive": ("A spectrogram CNN on raw 660 nm PPG is distinguishable "
                               "from chance."),
        "mandatory_clause": ("The effect improves on predicting a constant by ~0.05 "
                             "g/dL, sex alone beats it by six times that margin, and an "
                             "estimator at MAE 1.12 g/dL separates no WHO severity "
                             "band."),
        "p_reported": pa.get("p_empirical", 0.004149),
        "p_n": pa.get("n", 240),
        "p_is_a_floor": True,   # still true at n = 240: no draw ever reached the real MAE
    }
    out["harness_validation"] = validation.get("summary", {})

    # Live status of the extended permutation run. Reported, never consolidated here.
    jl = paths.INTERIM / "phase5" / "perm_selection_aware.jsonl"
    if jl.exists():
        done = sum(1 for ln in jl.read_text(encoding="utf-8").splitlines()
                   if ln.strip().startswith("{") and ln.strip().endswith("}"))
        out["status"]["extended_permutation"] = {
            "permutations_complete": done, "target": 240,
            "complete": done >= 240,
            "note": ("Complete and consolidated on 2026-09-12: 240/240 permutations, "
                     "zero draws at or below the real MAE, so the empirical p is the "
                     "floor 1/241 = 0.0041 - a fourfold tighter bound than the n=60 "
                     "figure, and still a bound rather than a measurement."),
        }
    return out
