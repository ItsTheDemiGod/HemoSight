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
    for r in sorted(d["results"], key=lambda r: ORDER[r["verdict"]]):
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
        story.append(Paragraph(f"<b>{r['headline']}</b>", body))
        story.append(Paragraph(r["explanation"], body))
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
