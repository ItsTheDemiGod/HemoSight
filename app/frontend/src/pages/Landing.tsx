import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Figure } from "../components/ui";

const EVIDENCE = [
  {
    value: "0 of 5",
    caption:
      "applicable sources in this project's own literature survey reported a demographic baseline. The same count reported a duplicate check.",
  },
  {
    value: "419",
    caption:
      "MD5 hashes shared between two datasets distributed as independent sources. 87.3% of one was byte-identical to a file in the other.",
  },
  {
    value: "52.7% / 50.8%",
    caption:
      "internal redundancy inside two collections whose headline file counts therefore overstate them by about twofold.",
  },
  {
    value: "0.831",
    caption:
      "g/dL MAE from sex alone — beating every one of the six model representations this project built across two modalities.",
  },
];

const CHECKS = [
  ["Leakage and duplicates", "Phase 1", "Does any duplicate cross a train/test boundary?"],
  ["Split integrity", "Phase 1", "Is the grouping connected components, or subject id alone?"],
  ["Demographic baseline", "Phase 4", "Does one demographic variable match the model?"],
  ["Proxy probe", "Phase 4 / 4.5", "Is the skill the demographic in disguise?"],
  ["Permutation test", "Phase 4.5 / 5", "Empirical p, with its floor stated."],
  ["Seed stability", "Phase 5", "Is the effect bigger than re-running the model?"],
  ["Subgroup robustness", "Phase 5", "Does the advantage survive dropping the best decile?"],
  ["Ceiling analysis", "Phase 4.5", "Could this input contain the target at all?"],
];

export default function Landing() {
  return (
    <div>
      <div className="label">HemoSight Audit</div>
      <h1 className="mt-3 max-w-[20ch] text-[40px] leading-[1.08] md:text-[52px]">
        Eight checks a screening claim should survive.
      </h1>
      <p className="prose-measure mt-6 text-[16px]">
        Upload a model's held-out predictions. The tool runs the methodological checks that
        decided each phase of this project, and returns a verdict per check with the measured
        quantity and what it means. Where the submission does not carry what a check needs, it
        says <em>insufficient data</em> and stops — it never infers a verdict it cannot support.
      </p>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link to="/prereg" className="btn">
          Declare thresholds first
        </Link>
        <Link to="/upload" className="btn-ghost">
          Upload predictions
        </Link>
        <Link to="/case-study" className="btn-ghost">
          See it on this project's own data
        </Link>
      </div>

      {/* ---------------------------------------------------------- the admission */}
      <section className="mt-16 border-t border-ink pt-6">
        <h2 className="text-[20px]">This came out of a project that failed.</h2>
        <div className="prose-measure mt-3 space-y-3">
          <p>
            HemoSight set out to estimate haemoglobin from photographs and from
            four-wavelength PPG. Six representations across two modalities were tested against
            thresholds declared before each run, and all six failed. The imaging arm is a
            closed negative result with a measured mechanism; the PPG arm is not viable.
          </p>
          <p>
            One claim survived: a spectrogram CNN on raw 660 nm PPG is distinguishable from
            chance. It is also useless. The effect improves on predicting a constant by about
            0.05 g/dL, sex alone beats it by six times that margin, and an estimator at MAE
            1.12 g/dL separates no WHO severity band. That clause travels with the claim
            everywhere it appears, including here.
          </p>
          <p>
            What the project did build, and validated over five phases, is the apparatus that
            produced those verdicts — including the ones that refuted its own hypotheses. That
            apparatus is this tool. It is offered on the strength of the negative results, not
            in spite of them.
          </p>
        </div>
      </section>

      {/* ------------------------------------------------------ motivating evidence */}
      <section className="mt-14">
        <h2 className="text-[20px]">Why these checks and not others</h2>
        <p className="prose-measure mt-3">
          Each one exists because this project ran it and something turned up that no file
          listing, summary table or reported score would have shown.
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

      {/* ---------------------------------------------------------- the catalogue */}
      <section className="mt-14">
        <h2 className="text-[20px]">The catalogue</h2>
        <table className="mt-5 w-full text-[13.5px]">
          <thead>
            <tr className="label">
              <th className="cell text-left font-normal">check</th>
              <th className="cell text-left font-normal">from</th>
              <th className="cell text-left font-normal">asks</th>
            </tr>
          </thead>
          <tbody>
            {CHECKS.map(([name, phase, asks]) => (
              <tr key={name}>
                <td className="cell">{name}</td>
                <td className="cell num text-[12px] text-muted">{phase}</td>
                <td className="cell text-muted">{asks}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="mt-14 border-t border-rule pt-6">
        <h2 className="text-[17px]">What a pass does not mean</h2>
        <p className="prose-measure mt-3">
          A pass is the absence of a specific detectable failure. It is not evidence that a
          model works, and it is never a clinical validation. The checks read submitted
          predictions: they do not re-run anyone's training, so a hyperparameter tuned against
          the test split is outside their reach, and an unsubmitted confounder is untested
          rather than absent. Those limits are printed in every report this tool produces.
        </p>
      </section>
    </div>
  );
}
