import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "../api";
import { Figure, VerdictMark } from "../components/ui";
import { Reveal, TodoMark } from "../components/disclosure";

/* Orientation in five seconds: what this is, who it is for, what to do next.
   Every number on this page is either read live from the project's artefacts
   (the worked example) or is a figure recorded in its results log. */

const EVIDENCE = [
  {
    value: "0.831 g/dL",
    caption:
      "how well the subject's sex alone predicted haemoglobin in this project's data. Every one of the six models it built — two modalities, three deep architectures — did worse. A form beat the instrument.",
  },
  {
    value: "419",
    caption:
      "identical images shared between two datasets published as independent sources. One was 87% contained inside the other. A model tested across them would have been tested on its own training pictures.",
  },
  {
    value: "1,708 → 1,067",
    caption:
      "nominal subject ids that collapsed to genuinely separate groups once identical images were linked. The gap is exactly what a subject-level split would have leaked.",
  },
  {
    value: "0 of 5",
    caption:
      "papers in this project's own literature sample that reported a simple demographic baseline next to their score. The same count reported a duplicate check. A small sample — but the checks exist because of what they caught here.",
  },
];

const STEPS = [
  {
    n: "1",
    title: "Upload your model's predictions",
    text: "One spreadsheet: a row per subject with the true value, the model's prediction, and — if you have them — which rows were used for training, plus age, sex, device or site. Every extra column unlocks a check; a missing one simply means that check cannot run.",
  },
  {
    n: "2",
    title: "Run the checks",
    text: "Eight questions a screening result has to survive: were duplicates or the same people on both sides of the split, does the model beat the obvious guess, is it better than shuffled labels, does it hold up across re-runs and subgroups, and is there any signal in the inputs at all.",
  },
  {
    n: "3",
    title: "Read the verdicts",
    text: "Each check returns pass, fail, or could not be checked, in plain words, with the exact technical statement one click away, and says what to do — which is sometimes to fix the method, sometimes to state a limitation, and sometimes to stop.",
  },
];

export default function Landing() {
  const [cs, setCs] = useState<any>(null);
  useEffect(() => {
    api.caseStudy().then(setCs).catch(() => undefined);
  }, []);
  const claim = cs?.claim;
  const perm = cs?.checks?.find((c: any) => c.check_id === "permutation");
  const base = cs?.checks?.find((c: any) => c.check_id === "demographic_baseline");

  return (
    <div>
      <div className="label">HemoSight Audit</div>
      <h1 className="mt-3 max-w-[22ch] text-[40px] leading-[1.08] md:text-[52px]">
        Is your screening model measuring what it claims?
      </h1>
      <p className="prose-measure mt-6 text-[16px]">
        Medical screening models often report very high accuracy, and the accuracy is often an
        artefact of how they were tested: the same patients on both sides of the split,
        duplicated images, a score that a form asking the patient's sex could have matched.
        This tool takes a model's predictions and runs the checks that expose those artefacts.
        It is for anyone who has a model to check, and anyone who wants to understand what a
        reported score does and does not mean.
      </p>
      <p className="prose-measure mt-4 text-[15px] text-muted">
        It came out of a research project whose own haemoglobin model failed every test it
        set itself. The checks are the ones that decided that. Nothing here is a clinical
        validation.
      </p>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link to="/upload" className="btn">
          Check a model
        </Link>
        <Link to="/case-study" className="btn-ghost">
          See a real result first
        </Link>
        <Link to="/glossary" className="btn-ghost">
          Glossary
        </Link>
      </div>

      {/* ---------------------------------------------------------- how it works */}
      <section className="mt-16 border-t border-ink pt-6">
        <h2 className="text-[20px]">How it works</h2>
        <div className="mt-6 grid gap-8 md:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.n}>
              <div className="num text-[22px] text-faint">{s.n}</div>
              <h3 className="mt-2 text-[16px]">{s.title}</h3>
              <p className="mt-2 text-[13.5px] leading-relaxed text-muted">{s.text}</p>
            </div>
          ))}
        </div>
        <p className="prose-measure mt-6 text-[13.5px] text-muted">
          Before you upload, you can{" "}
          <Link to="/prereg" className="underline underline-offset-2">
            write down the thresholds
          </Link>{" "}
          the checks will be judged against. Doing that first is what turns a number into a
          verdict, and the report records whether you did.
        </p>
      </section>

      {/* ---------------------------------------------------------- worked example */}
      <section className="mt-16 border-t border-rule pt-6">
        <h2 className="text-[20px]">A real result, before you upload anything</h2>
        <p className="prose-measure mt-3">
          This is the tool run on the project that built it: a neural network reading a
          fingertip pulse signal to estimate haemoglobin, 252 subjects, tested the way the
          checks require. Two of the eight verdicts, exactly as the tool reports them.
        </p>

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <article className="border border-rule p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h3 className="text-[17px]">Better than shuffled labels</h3>
              <VerdictMark v="PASS" big />
            </div>
            <p className="mt-3 text-[14.5px] leading-snug">
              The model's error is lower than what shuffled labels produce, so it has learned
              something real.{" "}
              {claim ? (
                <>
                  The p-value, {Number(claim.p_reported).toPrecision(2)}, is the smallest value{" "}
                  {claim.p_n} permutations can produce; the true value may be smaller. It is a
                  bound, not a measurement.
                </>
              ) : (
                "The p-value sits at the smallest value the number of permutations can produce; it is a bound, not a measurement."
              )}
            </p>
            <div className="mt-4 flex items-center gap-3">
              <span className="label">What to do</span>
              <TodoMark category="REPORT IT" />
            </div>
            <p className="mt-2 text-[13px] text-muted">
              Report the p-value with its floor, and say whether the null re-ran the model
              selection. Significant is not the same as useful.
            </p>
            <div className="mt-4">
              <Reveal label="Technical statement">
                <p className="num text-[13px]">
                  {perm?.measured ??
                    "selection-aware empirical p at the floor 1/(n+1), n = 240, z = -4.96"}
                </p>
              </Reveal>
            </div>
          </article>

          <article className="border border-rule p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h3 className="text-[17px]">Beating the obvious guess</h3>
              <VerdictMark v="FAIL" big />
            </div>
            <p className="mt-3 text-[14.5px] leading-snug">
              Knowing only the subject's sex predicts haemoglobin better than the model does
              (error 0.83 g/dL versus the model's 1.11). Men naturally carry more haemoglobin
              than women, so a model that has effectively learned to detect sex looks like it
              detects blood.
            </p>
            <div className="mt-4 flex items-center gap-3">
              <span className="label">What to do</span>
              <TodoMark category="REPORT IT" />
            </div>
            <p className="mt-2 text-[13px] text-muted">
              No code change makes a model that loses to a demographic variable measure what
              it claims. The project reported it and closed the arm.
            </p>
            <div className="mt-4">
              <Reveal label="Technical statement">
                <p className="num text-[13px]">
                  {base?.measured ??
                    "sex alone MAE 0.831 vs the PPG model at 1.190 and the population mean at 1.175"}
                </p>
              </Reveal>
            </div>
          </article>
        </div>

        <p className="prose-measure mt-5 text-[13.5px] text-muted">
          Both are true at once. The signal is real and it is useless: it improves on
          predicting a constant by about 0.05 g/dL, sex alone beats it six times over, and an
          error of 1.1 g/dL separates no WHO severity band.{" "}
          <Link to="/case-study" className="underline underline-offset-2">
            All eight verdicts
          </Link>
          .
        </p>
      </section>

      {/* ------------------------------------------------------ why these checks */}
      <section className="mt-16 border-t border-rule pt-6">
        <h2 className="text-[20px]">Why these checks</h2>
        <p className="prose-measure mt-3">
          Each one exists because this project ran it on its own data and something turned up
          that no score, summary table or file listing would have shown.
        </p>
        <div className="mt-7 grid gap-8 sm:grid-cols-2">
          {EVIDENCE.map((e, i) => (
            <motion.div
              key={e.value}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * i, duration: 0.3, ease: "easeOut" }}
            >
              <Figure value={e.value} caption={e.caption} />
            </motion.div>
          ))}
        </div>
      </section>

      {/* ---------------------------------------------------------- the admission */}
      <section className="mt-16 border-t border-rule pt-6">
        <h2 className="text-[20px]">Where this came from</h2>
        <div className="prose-measure mt-3 space-y-3">
          <p>
            HemoSight set out to estimate haemoglobin from photographs of the eye and from a
            fingertip pulse sensor. Six ways of doing it, across the two modalities, were
            tested against thresholds written down before each run. All six failed. The
            photograph route is a closed negative result with a measured mechanism; the pulse
            route is not viable.
          </p>
          <p>
            What the project did build, and validated over five phases, is the apparatus that
            produced those verdicts, including the ones that refuted its own hypotheses. That
            apparatus is this tool. It is offered on the strength of the negative results, not
            in spite of them.
          </p>
        </div>
      </section>

      <section className="mt-14 border-t border-rule pt-6">
        <h2 className="text-[17px]">What a pass does not mean</h2>
        <p className="prose-measure mt-3">
          A pass means one specific failure was looked for and not found. It is not evidence
          that a model works, and it is never a clinical validation. The checks read the
          predictions you upload; they do not re-run your training, so a decision tuned
          against the test set is out of their reach, and a variable you did not upload is
          untested rather than absent. Every report says so.
        </p>
      </section>
    </div>
  );
}
