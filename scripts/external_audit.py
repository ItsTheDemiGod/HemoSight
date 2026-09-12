"""External-audit path: ingest a third party's released predictions, run the harness,
write the two-part external report, and record the attempt in the register.

    python scripts/external_audit.py ingest --source their.csv --spec spec.json --out data/interim/phase7/external/<slug>
    python scripts/external_audit.py run    --dir data/interim/phase7/external/<slug> [--images DIR] [--checks a,b,c]
    python scripts/external_audit.py register --slug <slug> --paper "..." --links "..." \\
           --predictions {released,partial,none} --subject-ids {yes,no} --splits {yes,no} \\
           --demographics {yes,partial,no} --images {yes,no} --auditable {full,partial,none} --notes "..."

`spec.json` is an IngestSpec (see hemosight.audit.ingest); every field in it is a
statement by the auditor about the source and is copied into the report verbatim.

This script builds the path. It does NOT fabricate submissions. The register
(`configs/external_audit_register.json`) starts empty and is filled one attempted
audit at a time, including the ones where nothing auditable was released - that
outcome is a finding, not a failure to find one.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hemosight.audit import ALL_IDS, load_predictions, run_audit         # noqa: E402
from hemosight.audit.ingest import IngestSpec, NotAuditable, ingest_file  # noqa: E402
from hemosight.audit.report import to_external_markdown                  # noqa: E402

REGISTER = ROOT / "configs" / "external_audit_register.json"
REGISTER_FIELDS = ["slug", "date", "paper", "links", "kind", "code_released", "weights_released",
                   "predictions_released", "subject_ids", "splits", "demographics", "images",
                   "data_availability_statement", "code_availability_statement", "auditable",
                   "checks_possible", "notes"]
# "upon_request" is its own category: neither released nor unavailable. It is widely
# documented that this phrasing rarely results in an actual transfer; nothing is claimed
# here about any specific authors that was not tested.
AVAIL = ["released", "partial", "upon_request", "none", "not_stated"]


def cmd_ingest(a) -> int:
    spec = IngestSpec(**json.loads(Path(a.spec).read_text(encoding="utf-8")))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        df, rec = ingest_file(a.source, spec)
    except NotAuditable as exc:
        (out / "not_auditable.json").write_text(json.dumps(
            {"missing": exc.missing, "note": exc.note, "spec": asdict(spec)}, indent=2),
            encoding="utf-8")
        print(f"NOT AUDITABLE: missing {exc.missing} {exc.note}")
        print(f"recorded in {out / 'not_auditable.json'}; add it to the register with "
              f"`register --auditable none`")
        return 2
    df.to_csv(out / "predictions.csv", index=False)
    rec.to_json(out / "ingest_record.json")
    print(f"ingested {rec.n_rows_in} rows -> {rec.n_rows_out} rows, {rec.n_subjects} subjects")
    for s in rec.assumptions:
        print("  ASSUMPTION:", s)
    for w in rec.warnings:
        print("  warning:", w)
    if rec.unsupported_checks:
        print("  checks forced to INSUFFICIENT DATA:", ", ".join(rec.unsupported_checks))
    return 0


def cmd_run(a) -> int:
    d = Path(a.dir)
    rec = json.loads((d / "ingest_record.json").read_text(encoding="utf-8")) \
        if (d / "ingest_record.json").exists() else None
    inp = load_predictions(d / "predictions.csv", image_dir=a.images)
    checks = a.checks.split(",") if a.checks else None
    rep = run_audit(inp, checks=checks, unsupported=(rec or {}).get("unsupported_checks"))
    md = to_external_markdown(rep, rec, all_check_ids=ALL_IDS,
                              title=f"HemoSight external audit - {d.name}")
    (d / "external_audit.md").write_text(md, encoding="utf-8")
    (d / "report.json").write_text(json.dumps(rep.to_dict(), indent=2, default=str),
                                   encoding="utf-8")
    c = rep.to_dict()["counts"]
    print(f"{c['FAIL']} FAIL, {c['INSUFFICIENT_DATA']} INSUFFICIENT DATA, {c['PASS']} PASS "
          f"of {c['total']}; report -> {d / 'external_audit.md'}")
    return 0


def cmd_register(a) -> int:
    reg = json.loads(REGISTER.read_text(encoding="utf-8")) if REGISTER.exists() else \
        {"schema": REGISTER_FIELDS, "entries": []}
    entry = {"slug": a.slug, "date": str(date.today()), "paper": a.paper, "links": a.links,
             "kind": a.kind, "code_released": a.code, "weights_released": a.weights,
             "predictions_released": a.predictions, "subject_ids": a.subject_ids,
             "splits": a.splits, "demographics": a.demographics, "images": a.images,
             "data_availability_statement": a.data_statement,
             "code_availability_statement": a.code_statement,
             "auditable": a.auditable, "checks_possible": a.checks_possible, "notes": a.notes}
    reg["entries"] = [e for e in reg["entries"] if e["slug"] != a.slug] + [entry]
    REGISTER.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    # regenerate the markdown register
    L = ["# External audit register\n\n",
         "One row per candidate paper or released model. `auditable = none` is a measured "
         "outcome about what the field releases, and is reported with the same weight as "
         "an audit that ran. Generated by `scripts/external_audit.py register`; source of "
         "truth `configs/external_audit_register.json`.\n\n"]
    if not reg["entries"]:
        L.append("_No attempts recorded yet._\n")
    else:
        L.append("| slug | kind | code | weights | predictions | subject ids | splits | demographics | auditable | checks possible |\n")
        L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for e in reg["entries"]:
            L.append("| " + " | ".join(str(e.get(k, "")) for k in
                                      ("slug", "kind", "code_released", "weights_released",
                                       "predictions_released", "subject_ids", "splits", "demographics",
                                       "auditable", "checks_possible")) + " |\n")
        L.append("\n### Availability statements, verbatim\n\n")
        for e in reg["entries"]:
            L.append(f"* **{e['slug']}** - {e['paper']} ({e['links']})\n")
            L.append(f"  - data: {e.get('data_availability_statement') or 'not stated'}\n")
            L.append(f"  - code: {e.get('code_availability_statement') or 'not stated'}\n")
            if e.get("notes"):
                L.append(f"  - notes: {e['notes']}\n")
        n = len(reg["entries"]); na = sum(1 for e in reg["entries"] if e["auditable"] == "none")
        L.append(f"\n**{na} of {n} candidates released nothing auditable.**\n")
    (ROOT / "reports" / "external_audit_register.md").write_text("".join(L), encoding="utf-8")
    print(f"registered {a.slug}; {len(reg['entries'])} entries")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ingest"); s.add_argument("--source", required=True); s.add_argument("--spec", required=True)
    s.add_argument("--out", required=True); s.set_defaults(fn=cmd_ingest)
    s = sub.add_parser("run"); s.add_argument("--dir", required=True); s.add_argument("--images")
    s.add_argument("--checks"); s.set_defaults(fn=cmd_run)
    s = sub.add_parser("register")
    for f in ("slug", "paper", "links"):
        s.add_argument(f"--{f}", required=True)
    s.add_argument("--kind", choices=["published_paper", "preprint", "code_repository", "unlocated"], required=True)
    s.add_argument("--code", choices=AVAIL, required=True)
    s.add_argument("--weights", choices=AVAIL, required=True)
    s.add_argument("--predictions", choices=AVAIL, required=True)
    s.add_argument("--data-statement", dest="data_statement", default="")
    s.add_argument("--code-statement", dest="code_statement", default="")
    s.add_argument("--subject-ids", dest="subject_ids", choices=["yes", "no", "derivable", "n/a"], required=True)
    s.add_argument("--splits", choices=["yes", "partial", "no", "n/a"], required=True)
    s.add_argument("--demographics", choices=["yes", "partial", "no", "n/a"], required=True)
    s.add_argument("--images", choices=["yes", "no", "n/a"], required=True)
    s.add_argument("--auditable", choices=["full", "partial", "none"], required=True)
    s.add_argument("--checks-possible", dest="checks_possible", default="")
    s.add_argument("--notes", default="")
    s.set_defaults(fn=cmd_register)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
