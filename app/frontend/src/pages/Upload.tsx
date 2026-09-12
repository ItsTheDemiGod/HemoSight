import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api, Submission } from "../api";
import { Notice, SectionTitle } from "../components/ui";
import { readSession, writeSession } from "../store";

/* Plain first, technical name second. Every optional column names the check it unlocks. */
const CONTRACT: [string, string, string, string][] = [
  ["subject_id", "required", "Who the row is about", "One id per person. Not a row number and not an image name: if the same person has several rows, they must share this id, or the checks cannot tell whether the model was tested on people it trained on."],
  ["y_true", "required", "The true value", "The reference measurement the model was trying to predict - here, haemoglobin from a blood test, in g/dL."],
  ["y_pred", "required", "The model's prediction", "What the model said for that person, made on data it was not trained on."],
  ["split", "optional", "Which rows were used for training", "train, calibration or test per row. Unlocks the two checks for people or pictures on both sides of the split."],
  ["age, sex, device, site", "optional", "Things a form would know", "Whichever you have. Unlocks the check that asks whether the model beats simply knowing these - and every one the data has should be included, because a model can learn any of them."],
  ["image_path", "optional", "Where the picture is", "The file each row came from. Unlocks duplicate detection by pixels."],
  ["group", "optional", "Your own grouping", "If you split the data by some unit of your own, name it here and it is checked against the one the data actually needs."],
  ["y_pred__<name>", "optional", "Other models you chose between", "If this model was picked as the best of several, include the others' predictions so the shuffled-labels test can price in that choice."],
  ["y_pred_seed__<k>", "optional", "The same model, re-run", "Predictions from the same model trained again with different random seeds. Three or more unlocks the check for luck of the seed."],
  ["any other numeric column", "optional", "Model inputs", "Treated as an input feature, to ask whether the inputs contain any information about the outcome at all."],
];

const SAMPLES: [string, string][] = [
  ["01_mixed_start_here.csv", "a mixed example with several faults - start here"],
  ["02_clean_no_injected_fault.csv", "a clean submission"],
  ["05_fault_model_is_a_sex_classifier.csv", "a model that is really detecting sex"],
  ["03_fault_duplicates_across_split.csv", "duplicate images across the split"],
];

export default function UploadPage() {
  const nav = useNavigate();
  const [csv, setCsv] = useState<File | null>(null);
  const [images, setImages] = useState<File | null>(null);
  const [imageDir, setImageDir] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sub, setSub] = useState<Submission | null>(null);
  const [preview, setPreview] = useState<{ columns: { name: string; dtype: string }[] } | null>(
    null
  );
  const [dragging, setDragging] = useState(false);

  // Mount only. The `!sub` guard that used to be here was the sole reason this effect
  // read `sub`, and therefore the sole reason it needed a suppression - and on mount
  // `sub` is always null, so the guard never did anything. Dropping it makes the empty
  // dependency array honest rather than silenced.
  useEffect(() => {
    const s = readSession();
    if (s.submissionId) {
      api.submission(s.submissionId).then(setSub).catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    if (sub) api.preview(sub.id).then(setPreview).catch(() => undefined);
  }, [sub]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) setCsv(f);
  }, []);

  async function send() {
    if (!csv) return;
    setBusy(true);
    setError("");
    try {
      const s = await api.upload(csv, images, imageDir);
      setSub(s);
      writeSession({ submissionId: s.id, runId: undefined });
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <SectionTitle
        index="02 — Upload"
        title="Upload your model's predictions"
        lede="A predictions file is one spreadsheet with a row per person: the true value, what the model predicted, and whatever else you know about that person. Three columns are required; every extra one unlocks a check. A column you leave out is not guessed: the check that needed it says it could not run, and names the column."
      />

      {!sub && (
        <>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`flex flex-col items-center justify-center border border-dashed
              px-6 py-14 text-center transition-colors ${
                dragging ? "border-ink bg-panel" : "border-rule"
              }`}
          >
            <p className="text-[15px]">
              {csv ? (
                <>
                  <span className="num">{csv.name}</span>{" "}
                  <span className="text-faint">({Math.round(csv.size / 1024)} KB)</span>
                </>
              ) : (
                "Drop a predictions CSV here"
              )}
            </p>
            <label className="btn-ghost mt-4 cursor-pointer">
              Choose file
              <input
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={(e) => setCsv(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>

          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <label className="block">
              <span className="label">Images — zip archive (optional)</span>
              <input
                type="file"
                accept=".zip"
                className="field mt-1.5 text-[13px]"
                onChange={(e) => setImages(e.target.files?.[0] ?? null)}
              />
            </label>
            <label className="block">
              <span className="label">…or a directory already on this machine</span>
              <input
                className="field mt-1.5 num text-[13px]"
                placeholder="C:\path\to\images"
                value={imageDir}
                onChange={(e) => setImageDir(e.target.value)}
              />
            </label>
          </div>
          <p className="prose-measure mt-3 text-[13px]">
            Images are only needed for the duplicate check. A local folder path avoids copying
            a whole image collection to upload it.
          </p>

          <div className="mt-6 border-l-2 border-rule pl-4">
            <div className="label">No file yet? Try a sample</div>
            <p className="prose-measure mt-1 text-[13px]">
              These are synthetic - made-up subjects with a known fault built in - so you can
              see what a result looks like before uploading anything of your own.
            </p>
            <ul className="mt-2 space-y-1 text-[13px]">
              {SAMPLES.map(([f, what]) => (
                <li key={f}>
                  <a className="num underline underline-offset-2" href={api.sampleUrl(f)} download>
                    {f}
                  </a>{" "}
                  <span className="text-muted">- {what}</span>
                </li>
              ))}
            </ul>
          </div>

          {error && <p className="mt-5 text-[13px] text-fail">{error}</p>}
          <button className="btn mt-7" disabled={!csv || busy} onClick={send}>
            {busy ? "Checking the file…" : "Upload"}
          </button>
        </>
      )}

      {sub && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex flex-wrap items-baseline justify-between gap-3 border-t border-ink pt-4">
            <div>
              <h2 className="text-[20px]">{sub.filename}</h2>
              <p className="num mt-1 text-[13px] text-muted">
                {sub.n_rows} rows · {sub.n_subjects} subjects ·{" "}
                {sub.summary.n_selection_candidates} candidate(s) ·{" "}
                {sub.summary.n_seed_replicates} seed replicate(s) ·{" "}
                {sub.summary.n_feature_columns} feature column(s)
              </p>
            </div>
            <button
              className="btn-ghost"
              onClick={() => {
                setSub(null);
                setCsv(null);
                writeSession({ submissionId: undefined });
              }}
            >
              Replace
            </button>
          </div>

          {sub.warnings.length > 0 && (
            <div className="mt-5 space-y-2">
              {sub.warnings.map((w, i) => (
                <Notice key={i} tone="warn">
                  {w}
                </Notice>
              ))}
            </div>
          )}

          <section className="mt-9">
            <h3 className="label">Columns recognised</h3>
            <p className="prose-measure mt-2 text-[13px]">
              Columns are matched by name. Anything numeric and unrecognised is treated as a
              model input feature.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {preview?.columns.map((c) => {
                const known =
                  ["subject_id", "y_true", "y_pred", "split", "age", "sex", "device", "site", "group", "image_path"].includes(
                    c.name
                  ) || c.name.startsWith("y_pred__") || c.name.startsWith("y_pred_seed__");
                return (
                  <span
                    key={c.name}
                    className={`border px-2 py-1 font-mono text-[11.5px] ${
                      known ? "border-ink text-ink" : "border-rule text-faint"
                    }`}
                    title={known ? "part of the contract" : `feature (${c.dtype})`}
                  >
                    {c.name}
                  </span>
                );
              })}
            </div>
          </section>

          <section className="mt-10">
            <h3 className="label">Which checks this file can support</h3>
            <p className="prose-measure mt-2 text-[13px]">
              A check listed as unavailable will be reported as <em>could not be checked</em>,
              with the missing column named. That is not a pass.
            </p>
            <div className="mt-4 grid gap-x-10 gap-y-1 sm:grid-cols-2">
              <div>
                {sub.available_checks.map((c) => (
                  <div key={c} className="num py-1 text-[13px]">
                    <span className="text-pass">available</span>{" "}
                    <span className="text-ink">{c}</span>
                  </div>
                ))}
              </div>
              <div>
                {Object.entries(sub.unavailable_checks).map(([c, why]) => (
                  <div key={c} className="py-1 text-[13px]">
                    <span className="num text-insufficient">unavailable</span>{" "}
                    <span className="num text-ink">{c}</span>
                    <div className="pl-2 text-[12.5px] text-muted">{why}</div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <button className="btn mt-9" onClick={() => nav("/run")}>
            Run the checks
          </button>
        </motion.div>
      )}

      <section className="mt-16">
        <h2 className="text-[17px]">What each column does</h2>
        <table className="mt-4 w-full text-[13px]">
          <thead>
            <tr className="label">
              <th scope="col" className="cell text-left font-normal">column</th>
              <th scope="col" className="cell text-left font-normal">needed?</th>
              <th scope="col" className="cell text-left font-normal">what it does</th>
            </tr>
          </thead>
          <tbody>
            {CONTRACT.map(([name, req, plain, what]) => (
              <tr key={name}>
                <td className="cell w-[200px] align-top">
                  <div>{plain}</div>
                  <div className="num text-[11.5px] text-faint">{name}</div>
                </td>
                <td className="cell w-[80px] align-top text-[11px] uppercase tracking-wider text-faint">
                  {req}
                </td>
                <td className="cell text-muted">{what}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
