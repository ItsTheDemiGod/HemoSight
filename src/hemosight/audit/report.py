"""Rendering an audit report.

Markdown always; PDF when reportlab is installed, and a plain refusal when it is not
rather than a silently missing file.

The report is signed in the sense a local tool can honestly sign anything: a SHA-256
over the canonical report body, printed in the document. That detects an edited report.
It does not authenticate who produced it, and the document says which of the two it is.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .registry import AuditReport
from .verdict import FAIL, INSUFFICIENT, PASS

BADGE = {PASS: "PASS", FAIL: "FAIL", INSUFFICIENT: "INSUFFICIENT DATA"}
ORDER = {FAIL: 0, INSUFFICIENT: 1, PASS: 2}


def fingerprint(report: AuditReport) -> str:
    body = json.dumps(report.to_dict(), sort_keys=True, separators=(",", ":"),
                      default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _fmt_measured(m: dict) -> str:
    if not m:
        return ""
    rows = ["| quantity | value |", "| --- | --- |"]
    for k, v in m.items():
        rows.append(f"| {k} | {v} |")
    return "\n".join(rows)


def to_markdown(report: AuditReport, title: str = "HemoSight Audit report") -> str:
    d = report.to_dict()
    c = d["counts"]
    pre = d["prereg"]
    out: list[str] = []
    out.append(f"# {title}")
    out.append("")
    out.append(f"Generated {d['created_at']} by HemoSight Audit "
               f"{d['harness_version']}.")
    out.append("")
    out.append("> This report states what was measured and what could not be measured. "
               "An INSUFFICIENT DATA verdict is not a soft pass: it means the "
               "submission did not carry what the check needed, and no verdict was "
               "inferred.")
    out.append("")

    out.append("## Summary")
    out.append("")
    out.append(f"- **{c[FAIL]} FAIL**, {c[INSUFFICIENT]} INSUFFICIENT DATA, "
               f"{c[PASS]} PASS, of {c['total']} checks run.")
    out.append(f"- Thresholds declared in advance for {c['preregistered_thresholds']} "
               f"of {c['total']} checks.")
    s = d["input_summary"]
    out.append(f"- Input: {s['rows']} rows, {s['subjects']} subjects, "
               f"{s['n_selection_candidates']} selection candidate(s), "
               f"{s['n_seed_replicates']} seed replicate(s).")
    if s.get("warnings"):
        out.append("- Loader warnings: " + "; ".join(s["warnings"]))
    out.append("")

    out.append("### Pre-registration")
    out.append("")
    if pre.get("thresholds"):
        out.append(f"Declared **{pre['declared_at']}** as *{pre['title']}*, "
                   f"fingerprint `{pre['fingerprint'][:16]}...`.")
        out.append("")
        out.append("| check | thresholds |")
        out.append("| --- | --- |")
        for k, v in sorted(pre["thresholds"].items()):
            out.append(f"| {k} | {json.dumps(v)} |")
        if pre.get("notes"):
            out.append("")
            out.append(f"Notes: {pre['notes']}")
        out.append("")
        out.append("The fingerprint is tamper evidence over the declaration's own "
                   "content. It is not a trusted timestamp: it shows the declaration "
                   "has not been edited since it was written, not that it predates the "
                   "results.")
    else:
        out.append("**No thresholds were declared before these results were seen.** "
                   "Every verdict below was judged against this tool's defaults. That "
                   "is weaker evidence than a pre-declared threshold, and is recorded "
                   "here rather than left for a reader to notice.")
    out.append("")

    out.append("## Verdicts")
    out.append("")
    out.append("| check | verdict | measured | threshold declared in advance |")
    out.append("| --- | --- | --- | --- |")
    for r in sorted(d["results"], key=lambda r: ORDER[r["verdict"]]):
        out.append(f"| {r['title']} | **{BADGE[r['verdict']]}** | {r['headline']} | "
                   f"{'yes' if r['threshold_preregistered'] else 'no'} |")
    out.append("")

    out.append("## Findings")
    out.append("")
    out.append("Each finding is stated twice: in plain language first, then in the check's own "
               "technical wording. The two say the same thing; neither softens a caveat the "
               "other carries.")
    out.append("")
    for r in sorted(d["results"], key=lambda r: ORDER[r["verdict"]]):
        out.append(f"### {r['title']} - {BADGE[r['verdict']]}")
        out.append("")
        pl = r.get("plain")
        if pl:
            out.append(f"**In plain terms:** {pl['headline']}")
            out.append("")
            out.append(pl["what_it_means"])
            out.append("")
            todo = pl["what_to_do"]
            out.append(f"**What to do - {todo['category']}.** {todo['text']}")
            out.append("")
            out.append(f"*Why this happens:* {pl['mechanism']}")
            out.append("")
            out.append("**Technical statement:**")
            out.append("")
        out.append(f"**{r['headline']}**")
        out.append("")
        out.append(r["explanation"])
        out.append("")
        if pl:
            out.append(f"*Mechanism, computationally:* {pl['mechanism_technical']}")
            out.append("")
        if r.get("missing"):
            out.append("*Not measurable without:* " + ", ".join(r["missing"]))
            out.append("")
        if r.get("measured"):
            out.append(_fmt_measured(r["measured"]))
            out.append("")
        out.append(f"*Provenance:* {r['provenance']}")
        out.append("")
        if r.get("threshold"):
            out.append(f"*Threshold applied:* `{json.dumps(r['threshold'])}` "
                       f"({'pre-declared' if r['threshold_preregistered'] else 'tool default, supplied after the results'})")
            out.append("")

    out.append("## Scope and limits of this audit")
    out.append("")
    out.append(
        "- The checks operate on submitted predictions. They do not re-run the "
        "submitter's training, so anything that happened before the predictions were "
        "written - hyperparameters tuned against the test split, for instance - is "
        "outside their reach.\n"
        "- Demographic checks test the variables that were submitted. An unsubmitted "
        "confounder is untested, not absent.\n"
        "- A PASS is the absence of a specific detectable failure, not evidence that a "
        "model works. Statistical distinguishability is not clinical utility: the "
        "project that produced this tool holds one claim significant at z = -5.02 that "
        "improves on predicting a constant by 0.05 g/dL and separates no WHO severity "
        "band.\n"
        "- No output of this tool is a clinical validation, and nothing here should be "
        "described as diagnostic or approved.")
    out.append("")
    md = "\n".join(out)
    return md + f"\n---\n\nReport fingerprint (SHA-256): `{fingerprint(report)}`\n"


def to_pdf(report: AuditReport, path: str | Path,
           title: str = "HemoSight Audit report") -> Path:
    """Render a PDF. Raises RuntimeError if reportlab is not installed."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                        Spacer, Table, TableStyle)
        from reportlab.lib import colors
    except ImportError as exc:                      # pragma: no cover - env dependent
        raise RuntimeError(
            "PDF export needs reportlab (pip install reportlab). Markdown export is "
            "always available.") from exc

    d = report.to_dict()
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=body, fontSize=7.5, textColor=colors.grey)

    story = [Paragraph(title, styles["Title"]),
             Paragraph(f"Generated {d['created_at']} by HemoSight Audit "
                       f"{d['harness_version']}", small), Spacer(1, 6 * mm)]
    c = d["counts"]
    story.append(Paragraph(
        f"<b>{c[FAIL]} FAIL</b>, {c[INSUFFICIENT]} INSUFFICIENT DATA, {c[PASS]} PASS "
        f"of {c['total']} checks. Thresholds declared in advance for "
        f"{c['preregistered_thresholds']} of {c['total']}.", body))
    story.append(Spacer(1, 4 * mm))

    rows = [["check", "verdict", "measured"]]
    for r in sorted(d["results"], key=lambda r: ORDER[r["verdict"]]):
        rows.append([Paragraph(r["title"], body), Paragraph(BADGE[r["verdict"]], body),
                     Paragraph(r["headline"], body)])
    tbl = Table(rows, colWidths=[42 * mm, 28 * mm, 90 * mm])
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.extend([tbl, PageBreak()])

    for r in sorted(d["results"], key=lambda r: ORDER[r["verdict"]]):
        story.append(Paragraph(f"{r['title']} - {BADGE[r['verdict']]}",
                               styles["Heading3"]))
        pl = r.get("plain")
        if pl:
            story.append(Paragraph(f"<b>In plain terms:</b> {pl['headline']}", body))
            story.append(Paragraph(pl["what_it_means"], body))
            story.append(Paragraph(f"<b>What to do - {pl['what_to_do']['category']}.</b> "
                                   f"{pl['what_to_do']['text']}", body))
            story.append(Paragraph(f"<i>Why this happens:</i> {pl['mechanism']}", small))
            story.append(Paragraph("<b>Technical statement:</b>", body))
        story.append(Paragraph(f"<b>{r['headline']}</b>", body))
        story.append(Paragraph(r["explanation"], body))
        if pl:
            story.append(Paragraph(f"<i>Mechanism, computationally:</i> {pl['mechanism_technical']}", small))
        if r.get("measured"):
            mrows = [[Paragraph(str(k), small), Paragraph(str(v), small)]
                     for k, v in r["measured"].items()]
            mt = Table([["quantity", "value"]] + mrows, colWidths=[80 * mm, 60 * mm])
            mt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.extend([Spacer(1, 2 * mm), mt])
        story.append(Paragraph(f"Provenance: {r['provenance']}", small))
        story.append(Spacer(1, 5 * mm))

    story.append(Paragraph(f"Report fingerprint (SHA-256): {fingerprint(report)}",
                           small))
    SimpleDocTemplate(str(p), pagesize=A4, title=title).build(story)
    return p


def to_external_markdown(report: AuditReport, record: dict | None,
                         all_check_ids: list[str] | None = None,
                         title: str = "HemoSight external audit") -> str:
    """The external-audit report: what was checked and what could not be, at equal
    prominence, with the ingestion record's assumptions printed before any verdict.

    `record` is the IngestRecord (as a dict) that produced the submission; None means
    the submission arrived already in the contract's shape. `all_check_ids` lets the
    report list checks that were not selected at all, so coverage is never overstated.
    """
    d = report.to_dict()
    res = d["results"]
    checked = [r for r in res if r["verdict"] in (PASS, FAIL)]
    unchecked = [r for r in res if r["verdict"] == INSUFFICIENT]
    ran = {r["check_id"] for r in res}
    not_run = [i for i in (all_check_ids or []) if i not in ran]
    out: list[str] = []
    out.append(f"# {title}")
    out.append("")
    out.append(f"Generated {d['created_at']} by HemoSight Audit {d['harness_version']}.")
    out.append("")
    out.append(f"**Checked: {len(checked)} of {len(res)} selected checks returned a verdict. "
               f"Could not be checked: {len(unchecked)}"
               + (f"; not selected: {len(not_run)}" if not_run else "") + ".** "
               "The two halves of this report carry equal weight: a check that could not "
               "be run is a statement about what the released artefacts allow, not about "
               "the model.")
    out.append("")
    if record:
        out.append("## How the submission was brought into the contract")
        out.append("")
        out.append(f"- Source: {record.get('source_description') or '(not described)'}")
        out.append(f"- Rows in / out: {record.get('n_rows_in')} / {record.get('n_rows_out')}; "
                   f"subjects: {record.get('n_subjects')}")
        out.append(f"- Columns supplied: {', '.join(record.get('columns_supplied', []))}")
        if record.get("columns_derived"):
            out.append(f"- Columns DERIVED by the auditor: {', '.join(record['columns_derived'])}")
        if record.get("assumptions"):
            out.append("- **Assumptions made:**")
            for a in record["assumptions"]:
                out.append(f"  - {a}")
        if record.get("warnings"):
            out.append("- Ingestion warnings:")
            for w in record["warnings"]:
                out.append(f"  - {w}")
        out.append("")
    out.append("## Part 1 - what was checked")
    out.append("")
    if checked:
        out.append("| check | verdict | measured |")
        out.append("| --- | --- | --- |")
        for r in sorted(checked, key=lambda r: ORDER[r["verdict"]]):
            out.append(f"| {r['title']} | **{BADGE[r['verdict']]}** | {r['headline']} |")
    else:
        out.append("**No check returned a verdict.** Nothing in this report is a finding "
                   "about the model.")
    out.append("")
    out.append("## Part 2 - what could NOT be checked, and why")
    out.append("")
    if unchecked or not_run:
        out.append("| check | why not | what would be needed |")
        out.append("| --- | --- | --- |")
        for r in unchecked:
            out.append(f"| {r['title']} | {r['headline']} | "
                       f"{', '.join(r.get('missing') or ['-'])} |")
        for i in not_run:
            out.append(f"| {i} | not selected for this run | - |")
    else:
        out.append("Every check ran and returned a verdict.")
    out.append("")
    out.append("## Findings in detail")
    out.append("")
    for r in sorted(res, key=lambda r: ORDER[r["verdict"]]):
        out.append(f"### {r['title']} - {BADGE[r['verdict']]}")
        out.append("")
        out.append(f"**{r['headline']}**")
        out.append("")
        out.append(r["explanation"])
        out.append("")
        if r.get("missing"):
            out.append("*Not measurable without:* " + ", ".join(r["missing"]))
            out.append("")
        if r.get("measured"):
            out.append(_fmt_measured(r["measured"]))
            out.append("")
    out.append("## Scope")
    out.append("")
    out.append("- The checks operate on released predictions; nothing upstream of them is "
               "tested.")
    out.append("- INSUFFICIENT DATA is a statement about the release, not the model: a model "
               "whose artefacts do not allow a check is unaudited on that axis, not cleared.")
    out.append("- No output of this tool is a clinical validation.")
    out.append("")
    md = "\n".join(out)
    return md + f"\n---\n\nReport fingerprint (SHA-256): `{fingerprint(report)}`\n"
