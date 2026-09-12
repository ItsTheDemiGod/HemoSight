import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, ContentCatalogue } from "../api";
import { Notice, SectionTitle } from "../components/ui";

/* Every term that genuinely cannot be avoided in a default view links here. The
   definitions come from the server's content model, so they are the same ones the
   exported report and the results page use. */

export default function GlossaryPage() {
  const [content, setContent] = useState<ContentCatalogue | null>(null);
  const [err, setErr] = useState("");
  const loc = useLocation();

  useEffect(() => {
    api.content().then(setContent).catch((e) => setErr(String(e)));
  }, []);

  useEffect(() => {
    if (!content || !loc.hash) return;
    const el = document.getElementById(decodeURIComponent(loc.hash.slice(1)));
    el?.scrollIntoView({ block: "start" });
  }, [content, loc.hash]);

  if (err) return <Notice tone="warn">{err}</Notice>;
  if (!content) return <p className="text-[14px] text-muted">Loading the glossary…</p>;

  const terms = Object.entries(content.glossary).sort(([a], [b]) =>
    a.toLowerCase().localeCompare(b.toLowerCase())
  );

  return (
    <div>
      <SectionTitle
        index="Glossary"
        title="The words the checks cannot avoid"
        lede="Plain language is the default everywhere in this tool. Where a technical term has no honest plain substitute, it links here."
      />
      <dl className="mt-4">
        {terms.map(([t, d]) => (
          <div key={t} id={t} className="rule py-4 scroll-mt-6">
            <dt className="num text-[14px]">{t}</dt>
            <dd className="prose-measure mt-1 text-[14px]">{d}</dd>
          </div>
        ))}
      </dl>

      <section className="mt-14 border-t border-rule pt-6">
        <h2 className="text-[17px]">What to do — the three categories</h2>
        <p className="prose-measure mt-3">
          Every failed check names one of three responses. None of them is a way to make the
          check pass. This project's own history is the reason: across five phases, the
          correct response to a failed gate was never "fix it", it was "stop".
        </p>
        <dl className="mt-4">
          {content.categories.map((c) => (
            <div key={c.id} className="rule py-4">
              <dt className="font-mono text-[11px] uppercase tracking-[0.12em]">{c.id}</dt>
              <dd className="prose-measure mt-1 text-[14px]">{c.plain}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
