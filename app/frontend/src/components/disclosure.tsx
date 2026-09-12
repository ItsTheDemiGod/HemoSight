import { ReactNode, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Link } from "react-router-dom";
import type { TodoCategory } from "../api";

/* Layered disclosure. Plain language is the default view; the technical layer is one
   click away and never removed. Nothing here restyles verdicts or changes layout beyond
   what the new content structurally needs. */

export function Reveal({
  label,
  hideLabel,
  children,
  defaultOpen = false,
}: {
  label: string;
  hideLabel?: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        type="button"
        className="text-[12.5px] underline underline-offset-2 text-muted hover:text-ink"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {open ? hideLabel ?? `Hide ${label.toLowerCase()}` : label}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="mt-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* The what-to-do category is never a verdict colour: it is a course of action, and
   two of the three are "do not try to make this pass". */
export const TODO_LABEL: Record<TodoCategory, string> = {
  FIXABLE: "Fixable",
  "REPORT IT": "Report it",
  STOP: "Stop",
};

export function TodoMark({ category }: { category: TodoCategory }) {
  return (
    <span className="inline-block border border-ink px-2 py-[2px] font-mono text-[10.5px] uppercase tracking-[0.12em]">
      {TODO_LABEL[category]}
    </span>
  );
}

/* A term that genuinely cannot be avoided links to its glossary entry. */
export function Term({ t, children }: { t: string; children?: ReactNode }) {
  return (
    <Link
      to={`/glossary#${encodeURIComponent(t)}`}
      className="underline decoration-dotted underline-offset-2 hover:text-ink"
      title={`${t} — see the glossary`}
    >
      {children ?? t}
    </Link>
  );
}
