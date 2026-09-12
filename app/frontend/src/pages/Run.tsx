import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api, CheckSpec, PreReg, Run, Submission } from "../api";
import { Notice, Progress, SectionTitle, Spinner } from "../components/ui";
import { isSettled, pollUntilSettled, type PollHandle } from "../polling";
import { readSession, writeSession } from "../store";

export default function RunPage() {
  const nav = useNavigate();
  const [specs, setSpecs] = useState<CheckSpec[]>([]);
  const [sub, setSub] = useState<Submission | null>(null);
  const [prereg, setPrereg] = useState<PreReg | null>(null);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [perms, setPerms] = useState("1000");
  const [embedding, setEmbedding] = useState(false);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState("");
  // Polling gave up while the job was still unsettled. Distinct from run.status ===
  // "error", which is the SERVER reporting a failed job: here the job may well still be
  // running and we simply stopped watching it.
  const [pollFailed, setPollFailed] = useState(false);
  const poll = useRef<PollHandle | null>(null);

  useEffect(() => {
    const s = readSession();
    api.checks().then(setSpecs);
    if (s.submissionId) {
      api
        .submission(s.submissionId)
        .then((x) => {
          setSub(x);
          setChosen(new Set(x.available_checks));
        })
        .catch(() => setError("the stored submission is no longer available"));
    }
    if (s.preregId) {
      api.listPreReg().then((all) => setPrereg(all.find((p) => p.id === s.preregId) ?? null));
    }
    // Navigating away from a running job and back used to strand the user: the
    // component remounted with no run, so it never polled again and never moved on,
    // while the job finished on the server unnoticed. Pick it back up.
    if (s.runId) {
      api.run(s.runId).then(setRun).catch(() => undefined);
    }
    return () => {
      poll.current?.cancel();
      poll.current = null;
    };
  }, []);

  // Depends on the run ID alone. Keying it on status as well restarted the loop on
  // every transition, and the disable comment that used to sit here was hiding the
  // fact that `run` itself was a dependency the effect quietly read.
  const runId = run?.id;
  const runSettled = run ? isSettled(run.status) : true;

  useEffect(() => {
    if (!runId || runSettled) return;
    const handle = pollUntilSettled<Run>({
      fetchJob: () => api.run(runId),
      onUpdate: (r) => {
        setRun(r);
        if (r.status === "done") {
          writeSession({ runId: r.id });
          nav(`/results/${r.id}`);
        }
      },
      onGiveUp: (message) => {
        setError(message);
        setPollFailed(true);
      },
    });
    poll.current = handle;
    return () => {
      handle.cancel();
      if (poll.current === handle) poll.current = null;
    };
  }, [runId, runSettled, nav]);

  async function start() {
    if (!sub) return;
    setError("");
    setPollFailed(false);
    try {
      const options: Record<string, Record<string, number>> = {};
      if (chosen.has("permutation")) {
        const n = Number(perms);
        if (Number.isFinite(n) && n > 0) options.permutation = { n_permutations: n };
      }
      if (chosen.has("duplicates") && embedding) {
        options.duplicates = { embedding: 1 } as unknown as Record<string, number>;
      }
      const r = await api.createRun({
        submission_id: sub.id,
        checks: [...chosen],
        prereg_id: prereg?.id ?? null,
        options,
      });
      poll.current?.cancel();          // never leave an earlier loop running
      setRun(r);
      writeSession({ runId: r.id });
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    }
  }

  if (!sub) {
    return (
      <div>
        <SectionTitle index="03 — Run" title="No submission loaded" />
        <button className="btn" onClick={() => nav("/upload")}>
          Upload predictions
        </button>
      </div>
    );
  }

  const floor = 1 / (Number(perms) + 1);

  return (
    <div>
      <SectionTitle
        index="03 — Run"
        title="Choose the checks"
        lede="Long checks run as background jobs. Duplicate detection hashes every image; the permutation test iterates the null thousands of times. Progress below is live and survives a reload."
      />

      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 border-t border-ink pt-3 text-[13px]">
        <span className="num">{sub.filename}</span>
        <span className="num text-muted">
          {sub.n_rows} rows · {sub.n_subjects} subjects
        </span>
        <span className="text-muted">
          {prereg ? (
            <>
              pre-registration <span className="num">{prereg.title}</span> declared{" "}
              <span className="num">{prereg.declared_at}</span>
            </>
          ) : (
            <span className="text-insufficient">
              no pre-registration — the report will record that
            </span>
          )}
        </span>
      </div>

      <div className="mt-8">
        {specs.map((c) => {
          const unavailable = sub.unavailable_checks[c.check_id];
          const on = chosen.has(c.check_id);
          return (
            <div key={c.check_id} className="rule py-4">
              <label className="flex items-start gap-4">
                <input
                  type="checkbox"
                  className="mt-1.5 accent-ink"
                  disabled={!!unavailable}
                  checked={on && !unavailable}
                  onChange={(e) => {
                    const s = new Set(chosen);
                    e.target.checked ? s.add(c.check_id) : s.delete(c.check_id);
                    setChosen(s);
                  }}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-x-3">
                    <span className={unavailable ? "text-faint" : ""}>{c.title}</span>
                    <span className="num text-[11px] text-faint">{c.phase}</span>
                    {c.cost === "slow" && (
                      <span className="label text-faint">background job</span>
                    )}
                    {prereg?.thresholds?.[c.check_id] && (
                      <span className="label text-pass">threshold pre-declared</span>
                    )}
                  </div>
                  <p className="prose-measure mt-1 text-[13px]">{c.summary}</p>
                  {unavailable && (
                    <p className="mt-1 text-[12.5px] text-insufficient">{unavailable}</p>
                  )}
                </div>
              </label>
            </div>
          );
        })}
      </div>

      <section className="mt-8 grid gap-6 sm:grid-cols-2">
        <div>
          <label className="label">Permutations</label>
          <input
            className="field mt-1.5 num w-[160px]"
            value={perms}
            onChange={(e) => setPerms(e.target.value)}
          />
          <p className="prose-measure mt-2 text-[13px]">
            The smallest empirical p obtainable is 1/(n+1) ={" "}
            <span className="num">{floor.toFixed(5)}</span>. Below about 19 permutations the
            test cannot reach the conventional 0.05 at all, and the check declines rather than
            running.
          </p>
        </div>
        <div>
          <label className="label">Embedding nearest neighbours</label>
          <label className="mt-2 flex items-center gap-2 text-[13px]">
            <input
              type="checkbox"
              className="accent-ink"
              checked={embedding}
              onChange={(e) => setEmbedding(e.target.checked)}
            />
            run the semantic duplicate signal
          </label>
          <p className="prose-measure mt-2 text-[13px]">
            Off by default. It is the only signal that catches a re-shot or re-cropped image,
            and it is also the only one that loads a neural network.
          </p>
        </div>
      </section>

      {error && <p className="mt-5 text-[13px] text-fail">{error}</p>}

      {!run || run.status === "error" || pollFailed ? (
        <button className="btn mt-9" disabled={!chosen.size} onClick={start}>
          Run {chosen.size} check{chosen.size === 1 ? "" : "s"}
        </button>
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-9">
          <Progress value={run.progress} label={run.status} />
          <div className="mt-3">
            <Spinner label={run.message} />
          </div>
        </motion.div>
      )}

      {run?.status === "error" && (
        <div className="mt-5">
          <Notice tone="warn">
            The run failed: <span className="num">{run.message}</span>
          </Notice>
        </div>
      )}

      {pollFailed && run && run.status !== "error" && (
        <div className="mt-5">
          <Notice tone="warn">
            Progress updates stopped, so the live view above was taken down rather than
            left animating over a number that is no longer being refreshed. The job
            itself may still be running on the server - reload this page to pick it back
            up, or open the results directly at{" "}
            <span className="num">/results/{run.id}</span>.
          </Notice>
        </div>
      )}
    </div>
  );
}
