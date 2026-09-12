import { motion } from "framer-motion";
import { ReactNode } from "react";
import type { Verdict } from "../api";

/* Shared vocabulary. Verdicts are the only place colour is used, so that a reader
   scanning the page sees severity before they read a word. */

export const VERDICT_LABEL: Record<Verdict, string> = {
  FAIL: "Fail",
  INSUFFICIENT_DATA: "Insufficient data",
  PASS: "Pass",
};

const VERDICT_CLASS: Record<Verdict, string> = {
  FAIL: "text-fail border-fail",
  INSUFFICIENT_DATA: "text-insufficient border-insufficient",
  PASS: "text-pass border-pass",
};

export function VerdictMark({ v, big = false }: { v: Verdict; big?: boolean }) {
  return (
    <span
      className={`inline-flex items-center border-l-[3px] pl-2 font-mono uppercase
        tracking-[0.12em] ${VERDICT_CLASS[v]} ${big ? "text-[13px]" : "text-[11px]"}`}
    >
      {VERDICT_LABEL[v]}
    </span>
  );
}

export function SectionTitle({
  index,
  title,
  lede,
}: {
  index?: string;
  title: string;
  lede?: string;
}) {
  return (
    <header className="mb-8">
      {index && <div className="label mb-2">{index}</div>}
      <h1 className="text-[28px] leading-tight">{title}</h1>
      {lede && <p className="prose-measure mt-3">{lede}</p>}
    </header>
  );
}

export function Figure({
  value,
  caption,
  tone = "ink",
}: {
  value: string;
  caption: string;
  tone?: "ink" | "fail" | "pass";
}) {
  const c = tone === "fail" ? "text-fail" : tone === "pass" ? "text-pass" : "text-ink";
  return (
    <div className="border-t border-ink pt-3">
      <div className={`num text-[26px] leading-none ${c}`}>{value}</div>
      <div className="prose-measure mt-2 text-[13px]">{caption}</div>
    </div>
  );
}

export function Progress({ value, label }: { value: number; label: string }) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="label">{label}</span>
        <span className="num text-[12px] text-muted">{Math.round(value * 100)}%</span>
      </div>
      <div className="h-[3px] w-full bg-rule">
        <motion.div
          className="h-full bg-ink"
          initial={false}
          animate={{ width: `${Math.max(2, value * 100)}%` }}
          transition={{ type: "tween", ease: "easeOut", duration: 0.4 }}
        />
      </div>
    </div>
  );
}

export function Notice({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "warn";
  children: ReactNode;
}) {
  return (
    <div
      className={`border-l-2 py-2 pl-4 text-[13.5px] ${
        tone === "warn" ? "border-insufficient text-insufficient" : "border-rule text-muted"
      }`}
    >
      {children}
    </div>
  );
}

export function KeyValue({ rows }: { rows: [string, unknown][] }) {
  return (
    <table className="w-full text-[13px]">
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k}>
            <td className="cell w-1/2 font-mono text-[12px] text-muted">{k}</td>
            <td className="cell num">{formatValue(v)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return String(v);
    return Math.abs(v) < 0.001 ? v.toExponential(2) : v.toFixed(4);
  }
  if (Array.isArray(v)) return v.length ? v.join(", ") : "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 text-[13px] text-muted">
      <motion.span
        className="block h-2 w-2 rounded-full bg-ink"
        animate={{ opacity: [1, 0.2, 1] }}
        transition={{ repeat: Infinity, duration: 1.2, ease: "easeInOut" }}
      />
      {label}
    </div>
  );
}
