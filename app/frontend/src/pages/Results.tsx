import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api, CheckResult, Run, Verdict } from "../api";
import { KeyValue, Notice, SectionTitle, VerdictMark, formatValue } from "../components/ui";
import { Reveal, Term, TodoMark } from "../components/disclosure";
import { readSession } from "../store";

const ORDER: Record<Verdict, number> = { FAIL: 0, INSUFFICIENT_DATA: 1, PASS: 2 };
type SortKey = "severity" | "title" | "duration";

export default function ResultsPage() {
  const { runId } = useParams();
  const nav = useNavigate();
  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState<boolean>(() => Boolean(runId || readSession().runId));
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<Set<Verdict>>(
    new Set(["FAIL", "INSUFFICIENT_DATA", "PASS"] as Verdict[])
  );
  const [sort, setSort] = useState<SortKey>("severity");
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    const id = runId || readSession().runId;
    if (!id) return;
    api
      .run(id)
      .then(setRun)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [runId]);

  const results = useMemo(() => {
    const rs = run?.report?.results ?? [];
    const kept = rs.filter((r) => filter.has(r.verdict));
    const cmp: Record<SortKey, (a: CheckResult, b: CheckResult) => number> = {
      severity: (a, b) => ORDER[a.verdict] - ORDER[b.verdict] || a.title.localeCompare(b.title),
      title: (a, b) => a.title.localeCompare(b.title),
      duration: (a, b) => b.seconds - a.seconds,
    };
    return [...kept].sort(cmp[sort]);
  }, [run, filter, sort]);

  if (error) return <Notice tone="warn">{error}</Notice>;
  if (loading)
    return (
      <div className="min-h-[70vh]" aria-busy="true">
        <SectionTitle index="04 — Results" title="Reading the run…" />
      </div>
    );
  if (!run)
    return (
      <div>
        <SectionTitle index="04 — Results" title="No run to show" />
        <button className="btn" onClick={() => nav("/upload")}>
          Start an audit
        </button>
      </div>
    );
  if (!run.report)
    return (
      <div>
        <SectionTitle index="04 — Results" title="This run has not finished" />
        <Notice>
          Status <span className="num">{run.status}</span> — {run.message}
        </Notice>
        <Link className="btn mt-6" to="/run">
          Back to the run
        </Link>
      </div>
    );

  const c = run.report.counts;
  const pre = run.report.prereg;
  const hasPre = pre && Object.keys(pre.thresholds || {}).length > 0;

  return (
    <div>
      <SectionTitle
        index="04 — Results"
        title={`${c.FAIL} check${c.FAIL === 1 ? "" : "s"} failed, ${c.INSUFFICIENT_DATA} could not be checked, ${c.PASS} passed`}
        lede="Failures first. Each check says in plain words what happened and what to do about it; the exact technical statement is one click away. A check that could not be run is not a pass: it means your file did not include what that check needs, and nothing was inferred from what could not be measured."
      />

      {!hasPre && (
        <Notice tone="warn">
          No thresholds were declared before these results were seen, so every verdict below
          was judged against this tool's defaults. A threshold chosen after seeing the numbers
          is an interpretation, not a test; the exported report says so.
        </Notice>
      )}

      {/* -------------------------------------------------------------- controls */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-ink pt-4">
        <div className="flex flex-wrap gap-2">
          {(["FAIL", "INSUFFICIENT_DATA", "PASS"] as Verdict[]).map((v) => {
            const on = filter.has(v);
            const n = c[v] ?? 0;
            return (
              <button
                key={v}
                onClick={() => {
                  const s = new Set(filter);
                  on ? s.delete(v) : s.add(v);
                  setFilter(s);
                }}
                className={`border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.12em]
                  transition-colors ${
                    on
                      ? v === "FAIL"
                        ? "border-fail text-fail"
                        : v === "INSUFFICIENT_DATA"
                        ? "border-insufficient text-insufficient"
                        : "border-pass text-pass"
                      : "border-rule text-faint"
                  }`}
              >
                {v.replace("_", " ").toLowerCase()} · {n}
              </button>
            );
          })}
        </div>
        <label className="flex items-center gap-2 text-[12.5px] text-muted">
          <span className="label">sort</span>
          <select
            className="border border-rule bg-panel text-ink px-2 py-1 text-[12.5px]"
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
          >
            <option value="severity">severity</option>
            <option value="title">name</option>
            <option value="duration">time taken</option>
          </select>
        </label>
      </div>

      {/* ---------------------------------------------------------------- cards */}
      <motion.div layout className="mt-2">
        <AnimatePresence initial={false}>
          {results.map((r) => (
            <motion.article
              key={r.check_id}
              layout
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
              className="rule overflow-hidden py-6"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <h2 className="text-[19px]">{r.plain?.title ?? r.title}</h2>
                <VerdictMark v={r.verdict} big />
              </div>
              {r.plain && <p className="mt-1 text-[13px] text-muted">{r.plain.question}</p>}

              {/* Plain layer: the default view. */}
              <p className="mt-3 text-[15.5px] leading-snug">{r.plain?.headline ?? r.headline}</p>
              {r.plain && r.verdict !== "INSUFFICIENT_DATA" && (
                <p className="prose-measure mt-3">{r.plain.what_it_means}</p>
              )}

              {r.plain && (
                <div className="mt-4 border-l-2 border-rule pl-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="label">What to do</span>
                    <TodoMark category={r.plain.what_to_do.category} />
                  </div>
                  <p className="prose-measure mt-2 text-[13.5px]">{r.plain.what_to_do.text}</p>
                  <p className="mt-1 text-[12px] text-faint">{r.plain.what_to_do.category_plain}</p>
                </div>
              )}

              {r.plain && r.verdict !== "INSUFFICIENT_DATA" && (
                <div className="mt-4">
                  <Reveal label="Why this happens">
                    <p className="prose-measure text-[13.5px]">{r.plain.mechanism}</p>
                  </Reveal>
                </div>
              )}

              {/* Technical layer: one click away, never removed. */}
              <div className="mt-4">
                <Reveal label="Technical statement" hideLabel="Hide technical statement">
                  <p className="text-[14px] leading-snug num">{r.headline}</p>
                  <p className="prose-measure mt-2 text-[13.5px]">{r.explanation}</p>
                  {r.plain && (
                    <p className="prose-measure mt-3 text-[13px] text-muted">
                      <span className="label">Mechanism, computationally.</span>{" "}
                      {r.plain.mechanism_technical}
                    </p>
                  )}
                  {r.missing.length > 0 && (
                    <p className="mt-3 text-[13px] text-insufficient">
                      Not measurable without: <span className="num">{r.missing.join(", ")}</span>
                    </p>
                  )}
                  {r.plain && r.plain.glossary_terms.length > 0 && (
                    <p className="mt-3 text-[12px] text-faint">
                      Terms:{" "}
                      {r.plain.glossary_terms.map((g, i) => (
                        <span key={g}>
                          {i > 0 && ", "}
                          <Term t={g} />
                        </span>
                      ))}
                    </p>
                  )}
                </Reveal>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1 text-[12px] text-faint">
                <span className="num">{r.provenance}</span>
                <span className="num">{r.seconds.toFixed(1)}s</span>
                <span className={r.threshold_preregistered ? "text-pass" : "text-insufficient"}>
                  {r.threshold_preregistered
                    ? "threshold declared before the results"
                    : "threshold not declared in advance (tool default)"}
                </span>
                {Object.keys(r.measured).length > 0 && (
                  <button
                    className="underline underline-offset-2 hover:text-ink"
                    onClick={() => setOpen(open === r.check_id ? null : r.check_id)}
                  >
                    {open === r.check_id ? "hide measurements" : "measurements"}
                  </button>
                )}
              </div>

              <AnimatePresence initial={false}>
                {open === r.check_id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.22, ease: "easeOut" }}
                    className="overflow-hidden"
                  >
                    <div className="mt-4 grid gap-6 lg:grid-cols-2">
                      <KeyValue rows={Object.entries(r.measured)} />
                      <div>
                        <div className="label">threshold applied</div>
                        <pre className="mt-2 overflow-x-auto border border-rule bg-panel text-ink p-3 text-[11.5px]">
                          {JSON.stringify(r.threshold ?? {}, null, 2)}
                        </pre>
                        {"details" in r && (
                          <>
                            <div className="label mt-4">detail</div>
                            <pre className="mt-2 max-h-[280px] overflow-auto border border-rule bg-panel text-ink p-3 text-[11.5px]">
                              {JSON.stringify(r.details, null, 2).slice(0, 4000)}
                            </pre>
                          </>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.article>
          ))}
        </AnimatePresence>
      </motion.div>

      {results.length === 0 && (
        <p className="mt-8 text-[14px] text-muted">
          Every check is filtered out. Re-enable a verdict above.
        </p>
      )}

      <section className="mt-12 flex flex-wrap gap-3">
        <Link className="btn" to={`/report/${run.id}`}>
          Export the report
        </Link>
        <Link className="btn-ghost" to="/run">
          Run more checks
        </Link>
      </section>

      <section className="mt-12 border-t border-rule pt-5">
        <div className="label">input as read</div>
        <p className="num mt-2 text-[12.5px] text-muted">
          {formatValue(run.report.input_summary.rows)} rows ·{" "}
          {formatValue(run.report.input_summary.subjects)} subjects · target mean{" "}
          {formatValue(run.report.input_summary.y_true_mean)} sd{" "}
          {formatValue(run.report.input_summary.y_true_sd)}
        </p>
      </section>
    </div>
  );
}
