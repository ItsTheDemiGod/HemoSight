/* The one place that knows the wire format. */

export type Verdict = "PASS" | "FAIL" | "INSUFFICIENT_DATA";

export interface CheckSpec {
  check_id: string;
  title: string;
  provenance: string;
  phase: string;
  needs: string[];
  cost: "fast" | "slow";
  summary: string;
  /* The thresholds applied when none are declared in advance, shown on the
     pre-registration screen so a submitter sees them before any result. */
  defaults: Record<string, number | boolean>;
}

export interface CheckResult {
  check_id: string;
  title: string;
  verdict: Verdict;
  headline: string;
  explanation: string;
  provenance: string;
  measured: Record<string, unknown>;
  threshold: Record<string, unknown> | null;
  threshold_preregistered: boolean;
  missing: string[];
  details: Record<string, unknown>;
  seconds: number;
}

export interface AuditReport {
  created_at: string;
  input_summary: Record<string, any>;
  results: CheckResult[];
  prereg: Record<string, any>;
  counts: Record<string, number>;
  harness_version: string;
}

export interface Submission {
  id: string;
  filename: string;
  n_rows: number;
  n_subjects: number;
  summary: Record<string, any>;
  uploaded_at: string;
  warnings: string[];
  available_checks: string[];
  unavailable_checks: Record<string, string>;
}

export interface Run {
  id: string;
  submission_id: string;
  prereg_id: string | null;
  checks: string[];
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  report: AuditReport | null;
  error: string | null;
  thresholds_declared_in_advance: boolean | null;
  started_at: string;
  finished_at: string | null;
}

export interface PreReg {
  id: string;
  title: string;
  notes: string;
  thresholds: Record<string, Record<string, number>>;
  checks_planned: string[];
  fingerprint: string;
  declared_at: string;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`;
    try {
      const j = await r.json();
      if (j.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* the body was not JSON; the status line is all we have */
    }
    throw new Error(detail);
  }
  return (await r.json()) as T;
}

export const api = {
  checks: () => req<CheckSpec[]>("/api/checks"),
  caseStudy: () => req<any>("/api/case-study"),

  createPreReg: (body: {
    title: string;
    notes: string;
    thresholds: Record<string, Record<string, number>>;
    checks_planned: string[];
  }) =>
    req<PreReg>("/api/prereg", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  listPreReg: () => req<PreReg[]>("/api/prereg"),

  upload: (csv: File, images: File | null, imageDir: string) => {
    const fd = new FormData();
    fd.append("predictions", csv);
    if (images) fd.append("images", images);
    if (imageDir) fd.append("image_dir", imageDir);
    return req<Submission>("/api/submissions", { method: "POST", body: fd });
  },
  submission: (id: string) => req<Submission>(`/api/submissions/${id}`),
  preview: (id: string) =>
    req<{ columns: { name: string; dtype: string }[]; rows: any[] }>(
      `/api/submissions/${id}/preview`
    ),

  createRun: (body: {
    submission_id: string;
    checks: string[];
    prereg_id: string | null;
    options: Record<string, Record<string, number>>;
  }) =>
    req<Run>("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  run: (id: string) => req<Run>(`/api/runs/${id}`),
  runs: () => req<Run[]>("/api/runs"),
  reportMarkdownUrl: (id: string) => `/api/runs/${id}/report.md`,
  reportPdfUrl: (id: string) => `/api/runs/${id}/report.pdf`,
};
