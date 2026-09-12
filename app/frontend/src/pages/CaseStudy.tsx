import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../api";
import { Figure, Notice, SectionTitle, VerdictMark } from "../components/ui";
import { Reveal } from "../components/disclosure";
import type { ContentCatalogue } from "../api";
import type { Verdict } from "../api";

interface CaseCheck {
  check_id: string;
  verdict: Verdict;
  phase: string;
  measured: string;
  what_it_caught: string;
}

export default function CaseStudy() {
  const [data, setData] = useState<any>(null);
  const [content, setContent] = useState<ContentCatalogue | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .caseStudy()
      .then(setData)
      .catch((e) => setErr(String(e)));
    api.content().then(setContent).catch(() => undefined);
  }, []);

  if (err) return <Notice tone="warn">{err}</Notice>;
  if (!data) return <p className="text-[14px] text-muted">Reading the project's artefacts…</p>;

  const checks: CaseCheck[] = data.checks ?? [];
  const v = data.harness_validation ?? {};
  const ext = data.status?.extended_permutation;

  return (
    <div>
      <SectionTitle
        index="06 — Worked example"
        title="The tool, run on the project that built it"
        lede="A real audit of a real model: the project's own attempt to estimate haemoglobin from a fingertip pulse signal. Every verdict below is on the project's record, and the figures are read from its result files rather than retyped."
      />

      <section className="grid gap-8 sm:grid-cols-3">
        <Figure value="6 of 6" caption="model representations failed their pre-declared gate, across two modalities." tone="fail" />
        <Figure value="1" caption="claim survived hardening — and is clinically useless." />
        <Figure
          value={v.sensitivity != null ? `${Math.round(v.sensitivity * 100)}%` : "—"}
          caption="of injected faults caught by this harness in its own validation."
          tone="pass"
        />
      </section>

      <section className="mt-14">
        <h2 className="text-[20px]">What each check found</h2>
        <p className="prose-measure mt-2 text-[13.5px] text-muted">
          Plain summary first; the measured figure is one click away.
        </p>
        <div className="mt-2">
          {checks.map((c, i) => (
            <motion.div
              key={c.check_id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.04 * i, duration: 0.28 }}
              className="rule py-5"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <div className="flex items-baseline gap-3">
                  <span className="text-[16px]">
                    {content?.checks.find((k) => k.check_id === c.check_id)?.title_plain ?? c.check_id}
                  </span>
                  <span className="num text-[11px] text-faint">{c.phase}</span>
                </div>
                <VerdictMark v={c.verdict} />
              </div>
              <p className="prose-measure mt-2 text-[14px]">{c.what_it_caught}</p>
              <div className="mt-2">
                <Reveal label="Measured figure">
                  <p className="num text-[13px]">{c.measured}</p>
                </Reveal>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="mt-14 border border-ink p-6">
        <h2 className="text-[18px]">The one surviving claim, stated in full</h2>
        <p className="prose-measure mt-3 text-ink">{data.claim?.surviving_positive}</p>
        <p className="prose-measure mt-3">
          <strong className="text-ink">Mandatory clause.</strong> {data.claim?.mandatory_clause}
        </p>
        <p className="prose-measure mt-3">
          The reported empirical p is{" "}
          <span className="num text-ink">{Number(data.claim?.p_reported).toFixed(4)}</span> at n
          = <span className="num text-ink">{data.claim?.p_n}</span> permutations. That number is
          the <em>floor</em> 1/(n+1): zero null draws reached the real value, so the test
          reported the smallest p its sample size allowed. It is a bound, not a measurement, and
          this tool refuses to let a report print one without the other.
        </p>
        {ext && (
          <div className="mt-4">
            <Notice>
              An extended run is in progress at{" "}
              <span className="num">{ext.permutations_complete}</span> of{" "}
              <span className="num">{ext.target}</span> permutations. {ext.note}
            </Notice>
          </div>
        )}
      </section>

      <section className="mt-14">
        <h2 className="text-[20px]">The harness audited itself</h2>
        <p className="prose-measure mt-3">
          A tool that judges other people's evidence has to be held to the standard it applies.
          It was run against this project's own data, where every verdict was already on the
          record; against synthetic inputs carrying one known defect each; and against clean
          inputs with no defect at all, to count how often it cries wolf.
        </p>
        <table className="mt-5 w-full text-[13px]">
          <tbody>
            <tr>
              <td className="cell">Known-truth verdicts reproduced</td>
              <td className="cell num">
                {v.reproduced ?? "—"} / {v.known_truth_cases ?? "—"}
              </td>
            </tr>
            <tr>
              <td className="cell">Injected faults caught (sensitivity)</td>
              <td className="cell num">
                {v.faults_caught ?? "—"} / {v.fault_cases ?? "—"}
              </td>
            </tr>
            <tr>
              <td className="cell">False positives on clean inputs</td>
              <td className="cell num">
                {v.false_positive?.false_fail_total ?? "—"} of{" "}
                {v.false_positive?.check_runs ?? "—"} check-runs
                {v.false_positive?.false_positive_rate != null &&
                  ` (${(v.false_positive.false_positive_rate * 100).toFixed(2)}%)`}
              </td>
            </tr>
          </tbody>
        </table>
        {Array.isArray(v.not_validated_end_to_end) && v.not_validated_end_to_end.length > 0 && (
          <div className="mt-5 space-y-2">
            {v.not_validated_end_to_end.map((s: string, i: number) => (
              <Notice key={i} tone="warn">
                Not validated end to end: {s}
              </Notice>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
