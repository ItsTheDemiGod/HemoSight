import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, CheckSpec, PreReg } from "../api";
import { Notice, SectionTitle } from "../components/ui";
import { readSession, writeSession } from "../store";

/* Thresholds are declared here, before results are uploaded. The screen is
   deliberately placed first in the navigation: if you have already seen the numbers,
   a threshold is an interpretation, and the report will say so. */

type Draft = Record<string, Record<string, string>>;

export default function PreRegPage() {
  const nav = useNavigate();
  const [checks, setChecks] = useState<CheckSpec[]>([]);
  const [draft, setDraft] = useState<Draft>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState<PreReg | null>(null);
  const [existing, setExisting] = useState<PreReg[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.checks().then((cs) => {
      setChecks(cs);
      const d: Draft = {};
      cs.forEach((c) => {
        d[c.check_id] = {};
        Object.entries(c.defaults || {}).forEach(([k, v]) => {
          d[c.check_id][k] = String(v);
        });
      });
      setDraft(d);
      setSelected(new Set(cs.map((c) => c.check_id)));
    });
    api.listPreReg().then(setExisting).catch(() => undefined);
  }, []);

  async function submit() {
    setError("");
    const thresholds: Record<string, Record<string, number>> = {};
    for (const cid of selected) {
      const entries = Object.entries(draft[cid] || {});
      if (!entries.length) continue;
      const obj: Record<string, number> = {};
      for (const [k, raw] of entries) {
        const v = raw.trim().toLowerCase();
        if (v === "true" || v === "false") obj[k] = v === "true" ? 1 : 0;
        else if (v !== "" && !Number.isNaN(Number(v))) obj[k] = Number(v);
      }
      thresholds[cid] = obj;
    }
    try {
      const pr = await api.createPreReg({
        title: title.trim().length >= 8 ? title.trim() : "Untitled pre-registration",
        notes,
        thresholds,
        checks_planned: [...selected],
      });
      setSaved(pr);
      writeSession({ preregId: pr.id, checks: [...selected] });
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    }
  }

  const session = readSession();

  return (
    <div>
      <SectionTitle
        index="01 — Declare thresholds"
        title="Write down what would count as a failure before you see the numbers"
        lede="A threshold chosen after the result is known is an interpretation, not a test: whatever the number turned out to be, a line can be drawn just past it. Declaring the line first is what makes a verdict a verdict. This step is optional, and the report records whether you took it."
      />

      <div className="mb-8 border-l-2 border-rule pl-4">
        <div className="label">Why this matters - the project's own experience</div>
        <p className="prose-measure mt-2 text-[13.5px]">
          Before every experiment, this project wrote into its log what result would count
          as viable, marginal or a failure - for instance, that a haemoglobin error above
          2.0 g/dL would mean the photograph approach was not recoverable. The experiment
          then returned 3.9 g/dL. Because the line had been drawn first, that was a refutation
          and the work stopped; drawn afterwards, it would have been a number to argue about.
          That 3.9 was later re-reported with the uncertainty of the assumptions behind it —
          a 95% interval of 2.4 to 8.0 g/dL, still entirely past the line that had been drawn.
          Two of the project's own hypotheses were refuted this way, and both refutations
          held up.
        </p>
        <p className="prose-measure mt-2 text-[13.5px] text-muted">
          Below, each check shows the threshold it applies by default. Change any of them,
          untick checks you will not run, give the declaration a title, and save it. It is
          fingerprinted so it cannot be edited quietly afterwards.
        </p>
      </div>

      {saved ? (
        <div className="border border-ink p-6">
          <div className="label">Declared {saved.declared_at}</div>
          <h2 className="mt-2 text-[20px]">{saved.title}</h2>
          <p className="prose-measure mt-3">
            Fingerprint <span className="num">{saved.fingerprint.slice(0, 32)}…</span>
          </p>
          <Notice>
            The fingerprint is a checksum of this declaration's own text. It shows the
            declaration has not been edited since it was written. It does not prove when it
            was written, and the report says so rather than implying a guarantee it cannot give.
          </Notice>
          <div className="mt-6 flex gap-3">
            <button className="btn" onClick={() => nav("/upload")}>
              Upload results
            </button>
            <button className="btn-ghost" onClick={() => setSaved(null)}>
              Declare another
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="label">Title</span>
              <input
                className="field mt-1.5"
                value={title}
                placeholder="e.g. Conjunctiva Hb estimator v3, held-out site"
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label className="block">
              <span className="label">Notes</span>
              <input
                className="field mt-1.5"
                value={notes}
                placeholder="What is being claimed, and on what data"
                onChange={(e) => setNotes(e.target.value)}
              />
            </label>
          </div>

          <div className="mt-10 space-y-0">
            {checks.map((c) => {
              const on = selected.has(c.check_id);
              return (
                <div key={c.check_id} className="rule py-5">
                  <div className="flex items-start gap-4">
                    <input
                      type="checkbox"
                      checked={on}
                      className="mt-1.5 accent-ink"
                      onChange={(e) => {
                        const s = new Set(selected);
                        e.target.checked ? s.add(c.check_id) : s.delete(c.check_id);
                        setSelected(s);
                      }}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline gap-x-3">
                        <span className={on ? "text-[15px]" : "text-[15px] text-faint"}>
                          {c.title}
                        </span>
                        <span className="num text-[11px] text-faint">{c.phase}</span>
                      </div>
                      <p className="prose-measure mt-1 text-[13px]">{c.summary}</p>

                      {on && Object.keys(draft[c.check_id] || {}).length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-4">
                          {Object.entries(draft[c.check_id]).map(([k, v]) => (
                            <label key={k} className="block">
                              <span className="label">{k}</span>
                              <input
                                className="field mt-1 w-[190px] num text-[13px]"
                                value={v}
                                onChange={(e) =>
                                  setDraft({
                                    ...draft,
                                    [c.check_id]: {
                                      ...draft[c.check_id],
                                      [k]: e.target.value,
                                    },
                                  })
                                }
                              />
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {error && (
            <p className="mt-4 text-[13px] text-fail">{error}</p>
          )}
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button className="btn" onClick={submit}>
              Declare and lock
            </button>
            <button className="btn-ghost" onClick={() => nav("/upload")}>
              Skip — the report will record that no thresholds were declared
            </button>
          </div>
        </>
      )}

      {existing.length > 0 && (
        <section className="mt-14">
          <h2 className="text-[17px]">Earlier declarations</h2>
          <table className="mt-4 w-full text-[13px]">
            <tbody>
              {existing.slice(0, 8).map((p) => (
                <tr key={p.id}>
                  <td className="cell num text-[12px] text-muted">{p.declared_at}</td>
                  <td className="cell">{p.title}</td>
                  <td className="cell num text-[11px] text-faint">
                    {p.fingerprint.slice(0, 12)}…
                  </td>
                  <td className="cell text-right">
                    <button
                      className="btn-ghost"
                      onClick={() => {
                        writeSession({ preregId: p.id });
                        nav("/upload");
                      }}
                    >
                      {session.preregId === p.id ? "in use" : "use"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
