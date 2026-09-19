import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Figure, VerdictMark } from "../components/ui";
import { Reveal, TodoMark } from "../components/disclosure";
import Particles from "../components/Particles";
import { Breakeven, Grid, HbSpectra, NoiseSignal, NullDistribution, Reticle, SpectralBand, Waveform } from "../components/visuals";
import { useGsap, useReveal } from "../motion/useGsap";
import { useMotion } from "../motion/MotionProvider";

/* The story unfolds on scroll: the problem, the failed attempt, what the tool does.
   With motion on, GSAP pins the visual and steps the narrative beside it; with motion
   off, the same steps are laid out statically, in order, with the same numbers. Every
   figure is read from the project's own result files or its logged results. */

const STEPS: { k: string; kicker: string; title: string; text: string; visual: "spectra" | "iso" | "noise" | "null" | "breakeven" }[] = [
  {
    k: "1", kicker: "The physics", visual: "spectra",
    title: "Haemoglobin has a colour.",
    text: "Oxygenated and deoxygenated haemoglobin absorb light differently across the visible band. That is why the inside of an eyelid looks paler in anaemia, and why a photograph might, in principle, measure it.",
  },
  {
    k: "2", kicker: "The signal", visual: "iso",
    title: "Measured on real eyelids: 0.84 ΔE per g/dL.",
    text: "On 215 photographed subjects, one gram per decilitre of haemoglobin shifts conjunctival colour by about 0.84 units of perceptual colour difference — after adjusting for sex, age and site, which carry a large share of the raw correlation.",
  },
  {
    k: "3", kicker: "The noise", visual: "noise",
    title: "A phone photograph carries 3.5 units of colour error.",
    text: "Across three phones and three lighting conditions, the same person's eyelid varies by 3.5 ΔE after the best available correction. Studio control brings that to 1.06 — just short of the 0.99 that would make the inversion viable.",
  },
  {
    k: "4", kicker: "The verdict", visual: "breakeven",
    title: "Not recoverable, then marginal, never viable.",
    text: "The pre-declared gate returns 3.5 g/dL of error for uncontrolled capture and 1.04 for a studio rig. The one controlled dataset with blood tests lands at 1.3 g/dL — the same band a form asking sex, age and site reaches at 1.27. Propagating the model's own parameter uncertainty leaves the uncontrolled verdict intact (95% interval 2.1–7.9 g/dL, entirely past the 2.0 line) and the studio number spanning every band (0.6–4.9).",
  },
  {
    k: "5", kicker: "The pulse", visual: "null",
    title: "Real, and useless.",
    text: "A neural network reading a fingertip pulse beat every one of 240 shuffled-label runs. It also lost to knowing the subject's sex by 0.28 g/dL and flagged none of the anaemic subjects. Both are true. Only a cheap-baseline comparison shows the second.",
  },
];

const EVIDENCE = [
  { value: "0.831 g/dL", caption: "how well sex alone predicted haemoglobin in this project's data. Every one of the six models it built did worse. A form beat the instrument." },
  { value: "419", caption: "identical images shared between two datasets published as independent sources. One was 87% contained inside the other." },
  { value: "1,708 → 1,067", caption: "nominal subject ids that collapsed to genuinely separate groups once identical images were linked. The gap is exactly what a subject-level split would have leaked." },
  { value: "0 of 3", caption: "external models examined that released enough to audit. Two released nothing runnable; one could not be located at all." },
];

const HOW = [
  { n: "1", title: "Upload your model's predictions", text: "One spreadsheet, a row per subject: the true value, the prediction, and — if you have them — the split and whatever a form would know about the person. Every extra column unlocks a check." },
  { n: "2", title: "Run the checks", text: "Eight questions a screening result has to survive: duplicates and shared people across the split, beating the obvious guess, beating shuffled labels, holding up across re-runs and subgroups, and whether the inputs carry any signal at all." },
  { n: "3", title: "Read the verdicts", text: "Pass, fail, or could not be checked — in plain words, the exact technical statement one click away, and what to do: fix the method, state a limitation, or stop." },
];

function StepVisual({ v }: { v: string }) {
  if (v === "spectra") return <HbSpectra className="h-auto w-full" />;
  if (v === "iso") return <HbSpectra className="h-auto w-full" highlight="iso" />;
  if (v === "noise") return <NoiseSignal className="h-auto w-full" />;
  if (v === "breakeven") return <Breakeven className="h-auto w-full" />;
  return <NullDistribution className="h-auto w-full" />;
}

export default function Landing() {
  const { enabled } = useMotion();
  const root = useRef<HTMLDivElement>(null);
  const hero = useRef<HTMLDivElement>(null);
  const story = useRef<HTMLDivElement>(null);
  const [cs, setCs] = useState<any>(null);
  const [active, setActive] = useState(0);

  useEffect(() => {
    api.caseStudy().then(setCs).catch(() => undefined);
  }, []);
  const claim = cs?.claim;
  const perm = cs?.checks?.find((c: any) => c.check_id === "permutation");
  const base = cs?.checks?.find((c: any) => c.check_id === "demographic_baseline");

  useReveal(root);

  /* Parallax: three hero layers at different rates, transform only, scrubbed to scroll. */
  useGsap((gsap) => {
    const h = hero.current;
    if (!h) return;
    const layers = [["[data-layer=back]", -60], ["[data-layer=mid]", -120], ["[data-layer=front]", -30]] as const;
    layers.forEach(([sel, y]) => {
      gsap.to(h.querySelector(sel), {
        y, ease: "none",
        scrollTrigger: { trigger: h, start: "top top", end: "bottom top", scrub: 0.6 },
      });
    });
  });

  /* Scrollytelling: pin the visual, step the narrative. Each step's entry swaps the
     visual and highlights the step; the visual crossfades (opacity only). */
  useGsap((gsap, ScrollTrigger) => {
    const s = story.current;
    if (!s) return;
    const mm = gsap.matchMedia();
    mm.add("(min-width: 768px)", () => {
      const pin = s.querySelector<HTMLElement>("[data-pin]");
      const steps = Array.from(s.querySelectorAll<HTMLElement>("[data-step]"));
      if (!pin || !steps.length) return;
      ScrollTrigger.create({ trigger: s, start: "top 12%", end: "bottom 88%", pin, pinSpacing: false });
      steps.forEach((st, i) => {
        ScrollTrigger.create({
          trigger: st, start: "top 55%", end: "bottom 55%",
          onEnter: () => setActive(i), onEnterBack: () => setActive(i),
        });
        const body = st.querySelector<HTMLElement>("[data-step-body]");
        if (body) {
          // never below 0.75: at that opacity every text token on the ground still clears AA
          gsap.fromTo(body, { opacity: 0.75, x: -6 }, {
            opacity: 1, x: 0, duration: 0.3, ease: "none",
            scrollTrigger: { trigger: st, start: "top 70%", end: "top 45%", scrub: true },
          });
        }
      });
    });
    return () => mm.revert();
  });

  return (
    <div ref={root}>
      {/* ------------------------------------------------------------------ hero */}
      <section ref={hero} className="relative -mx-6 -mt-10 overflow-hidden px-6 pb-16 pt-12 md:-mx-12 md:-mt-14 md:px-12 md:pb-24 md:pt-20">
        <div data-layer="back" className="pointer-events-none absolute inset-0 opacity-60">
          <Grid className="h-full w-full" />
        </div>
        <div data-layer="mid" className="pointer-events-none absolute right-0 top-0 w-[70%] max-w-[900px] opacity-[0.28] md:-right-10 md:top-6 md:w-[64%] md:opacity-60">
          <HbSpectra className="h-auto w-full" />
        </div>
        <Particles />
        <div data-layer="front" className="relative">
          <div className="label">HemoSight Audit</div>
          <h1 className="mt-4 max-w-[18ch] text-[40px] leading-[1.04] md:max-w-[15ch] md:text-[68px]">
            Is your screening model measuring what it claims?
          </h1>
          <p className="prose-measure mt-7 text-[17px] text-ink/90">
            Medical screening models often report very high accuracy, and the accuracy is
            often an artefact of how they were tested: the same patients on both sides of the
            split, duplicated images, a score a form asking the patient's sex could have
            matched. This tool takes a model's predictions and runs the checks that expose
            those artefacts.
          </p>
          <p className="prose-measure mt-3 text-[15px]">
            It came out of a research project whose own haemoglobin model failed every test it
            set itself. Nothing here is a clinical validation.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/upload" className="btn">Check a model</Link>
            <Link to="/case-study" className="btn-ghost">See a real result first</Link>
            <Link to="/glossary" className="btn-ghost">Glossary</Link>
          </div>
        </div>
        <Reticle size={120} className="pointer-events-none absolute bottom-6 right-6 hidden opacity-40 md:block" />
      </section>

      <SpectralBand />

      {/* ------------------------------------------------------------ scrollytelling */}
      <section ref={story} className="mt-14">
        <div className="reveal">
          <div className="label">The story, in five measured steps</div>
          <h2 className="mt-2 text-[28px] md:text-[36px]">Why a photograph cannot read blood — and what does.</h2>
        </div>
        <div className="mt-8 md:grid md:grid-cols-[1fr_1.1fr] md:gap-10">
          <div className="hidden md:order-2 md:block">
            <div data-pin className="glow-card border border-rule p-3 md:p-4">
              {enabled ? (
                <div className="relative aspect-[1200/520] w-full md:aspect-[4/2.6]">
                  {STEPS.map((s, i) => (
                    <div key={s.k} className="absolute inset-0 transition-opacity duration-500" style={{ opacity: active === i ? 1 : 0 }} aria-hidden={active !== i}>
                      <StepVisual v={s.visual} />
                    </div>
                  ))}
                </div>
              ) : (
                <StepVisual v={STEPS[active]?.visual ?? "spectra"} />
              )}
              <div className="mt-2 flex items-center justify-between text-[11px] text-faint">
                <span className="num">{STEPS[active]?.kicker}</span>
                <span className="num">{active + 1} / {STEPS.length}</span>
              </div>
            </div>
          </div>
          <div className="mt-8 md:order-1 md:mt-0">
            {STEPS.map((s, i) => (
              <article key={s.k} data-step className="border-l border-rule py-6 pl-5 md:min-h-[70vh] md:py-8 md:pl-6">
                <div className="label">{s.k} — {s.kicker}</div>
                <div data-step-body>
                  <h3 className="mt-2 text-[24px] leading-tight md:text-[30px]">{s.title}</h3>
                  <p className="prose-measure mt-3">{s.text}</p>
                </div>
                {/* phones: the figure travels with its step; no pinning */}
                <div className="mt-4 border border-rule bg-card p-2 md:hidden">
                  <StepVisual v={s.visual} />
                </div>
                {!enabled && i !== active && (
                  <button className="link mt-3 hidden text-[12.5px] md:inline" onClick={() => setActive(i)}>
                    Show this step's figure
                  </button>
                )}
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------- how it works */}
      <section className="mt-20 border-t border-rule pt-8">
        <h2 className="reveal text-[28px]">How it works</h2>
        <div className="mt-6 grid gap-6 md:grid-cols-3">
          {HOW.map((s) => (
            <div key={s.n} className="reveal glow-card border border-rule p-5">
              <div className="num text-[24px] text-accent">{s.n}</div>
              <h3 className="mt-2 text-[17px]">{s.title}</h3>
              <p className="mt-2 text-[13.5px] leading-relaxed text-muted">{s.text}</p>
            </div>
          ))}
        </div>
        <p className="reveal prose-measure mt-6 text-[13.5px]">
          Before you upload, you can{" "}
          <Link to="/prereg" className="link">write down the thresholds</Link>{" "}
          the checks will be judged against. Doing that first is what turns a number into a
          verdict, and the report records whether you did.
        </p>
      </section>

      {/* ---------------------------------------------------------- worked example */}
      <section className="mt-20 border-t border-rule pt-8">
        <h2 className="reveal text-[28px]">A real result, before you upload anything</h2>
        <p className="reveal prose-measure mt-3">
          The tool run on the project that built it: a neural network reading a fingertip
          pulse to estimate haemoglobin, 252 subjects. Two of the eight verdicts, exactly as the
          tool reports them.
        </p>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <article className="reveal glow-card border border-rule p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h3 className="text-[17px]">Better than shuffled labels</h3>
              <VerdictMark v="PASS" big />
            </div>
            <p className="mt-3 text-[14.5px] leading-snug">
              None of the shuffles scored as well as the real model, so it has learned something
              real.{" "}
              {claim ? (
                <>The p-value, {Number(claim.p_reported).toPrecision(2)}, is the smallest value {claim.p_n} permutations can produce; the true value may be smaller. It is a bound, not a measurement.</>
              ) : (
                "The p-value sits at the smallest value the number of permutations can produce; it is a bound, not a measurement."
              )}
            </p>
            <div className="mt-4 flex items-center gap-3"><span className="label">What to do</span><TodoMark category="REPORT IT" /></div>
            <p className="mt-2 text-[13px] text-muted">Report the p-value with its floor, and say whether the null re-ran the model selection. Significant is not the same as useful.</p>
            <div className="mt-4">
              <Reveal label="Technical statement">
                <p className="num text-[13px]">{perm?.measured ?? "selection-aware empirical p at the floor 1/(n+1), n = 240, z = -4.96"}</p>
              </Reveal>
            </div>
          </article>
          <article className="reveal glow-card border border-rule p-5">
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
            <div className="mt-4 flex items-center gap-3"><span className="label">What to do</span><TodoMark category="REPORT IT" /></div>
            <p className="mt-2 text-[13px] text-muted">No code change makes a model that loses to a demographic variable measure what it claims. The project reported it and closed the arm.</p>
            <div className="mt-4">
              <Reveal label="Technical statement">
                <p className="num text-[13px]">{base?.measured ?? "sex alone MAE 0.831 vs the PPG model at 1.190 and the population mean at 1.175"}</p>
              </Reveal>
            </div>
          </article>
        </div>
        <div className="reveal mt-6">
          <NullDistribution className="h-auto w-full max-w-[720px]" />
        </div>
        <p className="reveal prose-measure mt-3 text-[13.5px]">
          Both are true at once. The signal is real and it is useless: it improves on predicting
          a constant by about 0.05 g/dL, sex alone beats it six times over, and an error of
          1.1 g/dL separates no WHO severity band.{" "}
          <Link to="/case-study" className="link">All eight verdicts</Link>.
        </p>
      </section>

      {/* ------------------------------------------------------------ evidence */}
      <section className="mt-20 border-t border-rule pt-8">
        <h2 className="reveal text-[28px]">Why these checks</h2>
        <p className="reveal prose-measure mt-3">
          Each one exists because this project ran it on its own data and something turned up
          that no score, summary table or file listing would have shown.
        </p>
        <div className="mt-8 grid gap-8 sm:grid-cols-2">
          {EVIDENCE.map((e) => (
            <div key={e.value} className="reveal"><Figure value={e.value} caption={e.caption} /></div>
          ))}
        </div>
      </section>

      <div className="reveal mt-16"><Waveform className="h-auto w-full" /></div>

      <section className="mt-6 border-t border-rule pt-8">
        <h2 className="reveal text-[24px]">Where this came from</h2>
        <div className="reveal prose-measure mt-3 space-y-3">
          <p>
            HemoSight set out to estimate haemoglobin from photographs of the eye and from a
            fingertip pulse sensor. Six ways of doing it, across the two modalities, were tested
            against thresholds written down before each run. All six failed.
          </p>
          <p>
            What the project did build, and validated over five phases, is the apparatus that
            produced those verdicts, including the ones that refuted its own hypotheses. That
            apparatus is this tool. It is offered on the strength of the negative results, not
            in spite of them.
          </p>
        </div>
      </section>

      <section className="mt-14 border-t border-rule pt-8">
        <h2 className="reveal text-[18px]">What a pass does not mean</h2>
        <p className="reveal prose-measure mt-3">
          A pass means one specific failure was looked for and not found. It is not evidence
          that a model works, and it is never a clinical validation. The checks read the
          predictions you upload; they do not re-run your training, so a decision tuned against
          the test set is out of their reach, and a variable you did not upload is untested
          rather than absent. Every report says so.
        </p>
      </section>
    </div>
  );
}
