import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api, Submission } from "../api";
import { Notice, SectionTitle } from "../components/ui";
import { readSession, writeSession } from "../store";

const CONTRACT: [string, string, string][] = [
  ["subject_id", "required", "The unit of independence. Never a row or image id."],
  ["y_true", "required", "Reference measurement."],
  ["y_pred", "required", "The model's held-out prediction."],
  ["split", "optional", "Unlocks leakage and split integrity."],
  ["age, sex, device, site", "optional", "Unlocks the demographic baseline and proxy probe."],
  ["group", "optional", "Your own claimed grouping unit, checked against the one the data needs."],
  ["image_path", "optional", "Unlocks duplicate detection over pixels."],
  ["y_pred__<name>", "optional", "A candidate the model was selected from — enables the selection-aware null."],
  ["y_pred_seed__<k>", "optional", "The same model under another seed. Three or more enables seed stability."],
  ["any other numeric column", "optional", "Treated as a model input feature for the ceiling analysis."],
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
        title="One table of held-out predictions"
        lede="Every optional column unlocks a specific check. A column you do not supply is not assumed away: the check that needed it returns insufficient data and says which column was missing."
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
            A local path is usually the right answer for research data: it avoids copying a
            corpus to upload it, and this project's own raw data is read-only by rule.
          </p>

          {error && <p className="mt-5 text-[13px] text-fail">{error}</p>}
          <button className="btn mt-7" disabled={!csv || busy} onClick={send}>
            {busy ? "Validating…" : "Upload and validate"}
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
            <h3 className="label">Column mapping</h3>
            <p className="prose-measure mt-2 text-[13px]">
              Columns are matched by name against the contract. Anything numeric and
              unrecognised is treated as a model input feature.
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
            <h3 className="label">What this submission can support</h3>
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
            Choose checks
          </button>
        </motion.div>
      )}

      <section className="mt-16">
        <h2 className="text-[17px]">The input contract</h2>
        <table className="mt-4 w-full text-[13px]">
          <tbody>
            {CONTRACT.map(([name, req, what]) => (
              <tr key={name}>
                <td className="cell num w-[210px]">{name}</td>
                <td className="cell w-[90px] text-[11px] uppercase tracking-wider text-faint">
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
