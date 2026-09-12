import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Run } from "../api";
import { Notice, SectionTitle, VerdictMark } from "../components/ui";
import { readSession } from "../store";

export default function ReportPage() {
  const { runId } = useParams();
  const [run, setRun] = useState<Run | null>(null);
  const [md, setMd] = useState("");
  const [pdfNote, setPdfNote] = useState("");

  const id = runId || readSession().runId;

  useEffect(() => {
    if (!id) return;
    api.run(id).then(setRun).catch(() => undefined);
    fetch(api.reportMarkdownUrl(id))
      .then((r) => (r.ok ? r.text() : ""))
      .then(setMd)
      .catch(() => undefined);
  }, [id]);

  async function tryPdf() {
    if (!id) return;
    const r = await fetch(api.reportPdfUrl(id));
    if (r.ok) {
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit_${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setPdfNote("");
    } else {
      const j = await r.json().catch(() => ({ detail: `${r.status}` }));
      setPdfNote(String(j.detail));
    }
  }

  function downloadMd() {
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit_${id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!id || !run?.report)
    return (
      <div>
        <SectionTitle index="05 — Report" title="No completed run to export" />
        <Link className="btn" to="/upload">
          Start an audit
        </Link>
      </div>
    );

  const c = run.report.counts;
  const pre = run.report.prereg;
  const hasPre = Object.keys(pre?.thresholds || {}).length > 0;

  return (
    <div>
      <SectionTitle
        index="05 — Report"
        title="Audit report"
        lede="A document that states what was measured, what could not be measured, and whether the thresholds were declared before the results were seen."
      />

      <div className="flex flex-wrap gap-3">
        <button className="btn" onClick={downloadMd} disabled={!md}>
          Download Markdown
        </button>
        <button className="btn-ghost" onClick={tryPdf}>
          Download PDF
        </button>
        <a className="btn-ghost" href={api.reportMarkdownUrl(id)} target="_blank" rel="noreferrer">
          Open raw
        </a>
      </div>
      {pdfNote && (
        <div className="mt-4">
          <Notice tone="warn">{pdfNote}</Notice>
        </div>
      )}

      <section className="mt-10 border border-ink p-6">
        <div className="label">summary</div>
        <p className="mt-2 text-[16px]">
          <span className="num text-fail">{c.FAIL}</span> fail ·{" "}
          <span className="num text-insufficient">{c.INSUFFICIENT_DATA}</span> insufficient
          data · <span className="num text-pass">{c.PASS}</span> pass, of{" "}
          <span className="num">{c.total}</span> checks.
        </p>
        <p className="prose-measure mt-3 text-[13.5px]">
          Thresholds declared in advance for{" "}
          <span className="num">{c.preregistered_thresholds}</span> of{" "}
          <span className="num">{c.total}</span> checks.
          {hasPre ? (
            <>
              {" "}
              Declaration <span className="num">{pre.title}</span> dated{" "}
              <span className="num">{pre.declared_at}</span>, fingerprint{" "}
              <span className="num">{String(pre.fingerprint).slice(0, 16)}…</span>
            </>
          ) : (
            " No pre-registration accompanied this run."
          )}
        </p>

        <table className="mt-6 w-full text-[13px]">
          <tbody>
            {run.report.results.map((r) => (
              <tr key={r.check_id}>
                <td className="cell w-[210px]">{r.title}</td>
                <td className="cell w-[120px]">
                  <VerdictMark v={r.verdict} />
                </td>
                <td className="cell text-muted">{r.headline}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="mt-10">
        <h2 className="text-[17px]">Document preview</h2>
        <pre className="mt-4 max-h-[560px] overflow-auto border border-rule bg-white p-5 text-[11.5px] leading-relaxed">
          {md || "…"}
        </pre>
      </section>
    </div>
  );
}
