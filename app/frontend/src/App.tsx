import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import PreRegPage from "./pages/PreReg";
import UploadPage from "./pages/Upload";
import RunPage from "./pages/Run";
import ResultsPage from "./pages/Results";
import ReportPage from "./pages/Report";
import CaseStudy from "./pages/CaseStudy";
import GlossaryPage from "./pages/Glossary";
import { MotionProvider, MotionToggle } from "./motion/MotionProvider";
import Cursor from "./components/Cursor";
import { SpectralBand } from "./components/visuals";

import Landing from "./pages/Landing";
/* Only GSAP is code-split (loaded when motion is on); the landing page itself is 17 kB
   and lazy-loading it cost a layout shift on the very first paint. */

const NAV = [
  { to: "/", label: "Start here", n: "00" },
  { to: "/prereg", label: "Declare thresholds", n: "01" },
  { to: "/upload", label: "Upload predictions", n: "02" },
  { to: "/run", label: "Run the checks", n: "03" },
  { to: "/results", label: "Results", n: "04" },
  { to: "/report", label: "Export report", n: "05" },
  { to: "/case-study", label: "Worked example", n: "06" },
  { to: "/glossary", label: "Glossary", n: "07" },
];

export default function App() {
  const loc = useLocation();
  return (
    <MotionProvider>
      <Cursor />
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[70] focus:bg-accent focus:px-3 focus:py-2 focus:text-paper"
      >
        Skip to content
      </a>
      <div className="min-h-screen md:flex">
        <aside
          className="border-b border-rule bg-panel px-6 py-6 md:sticky md:top-0 md:h-screen
                     md:w-[236px] md:shrink-0 md:border-b-0 md:border-r md:px-6 md:py-8"
        >
          <NavLink to="/" className="block">
            <div className="font-serif text-[17px] leading-tight">HemoSight Audit</div>
            <div className="label mt-1">Checks for screening models</div>
          </NavLink>

          <nav aria-label="Main" className="mt-8 flex flex-wrap gap-x-5 gap-y-1 md:block">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `group flex items-baseline gap-3 py-[5px] text-[13.5px] transition-colors ${
                    isActive ? "text-ink" : "text-faint hover:text-muted"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span className="num text-[10px]">{item.n}</span>
                    <span className="relative">
                      {item.label}
                      {isActive && (
                        <motion.span
                          layoutId="nav-underline"
                          className="absolute -bottom-[2px] left-0 right-0 h-px bg-accent"
                          transition={{ type: "spring", stiffness: 420, damping: 34 }}
                        />
                      )}
                    </span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="mt-8 hidden md:block">
            <MotionToggle />
          </div>

          {/* The disclaimer is part of the frame of every page, not a footer. */}
          <p
            role="note"
            className="mt-8 hidden max-w-[190px] border-l-2 border-insufficient pl-3 text-[11.5px] leading-relaxed text-muted md:block"
          >
            Built by a research project whose own haemoglobin model failed every test it set
            itself. <span className="text-ink">Nothing here is a clinical validation.</span>
          </p>
        </aside>

        <main id="main" className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-rule bg-panel px-6 py-3 text-[12px] text-muted md:hidden">
            <p role="note" className="border-l-2 border-insufficient pl-3 text-ink">
              Nothing here is a clinical validation.
            </p>
            <MotionToggle />
          </div>
          <div className="mx-auto min-h-screen max-w-[980px] px-6 py-10 md:px-12 md:py-14">
            <AnimatePresence mode="wait">
              <motion.div
                key={loc.pathname}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.18, ease: "easeOut" }}
              >
                  <Routes location={loc}>
                    <Route path="/" element={<Landing />} />
                    <Route path="/prereg" element={<PreRegPage />} />
                    <Route path="/upload" element={<UploadPage />} />
                    <Route path="/run" element={<RunPage />} />
                    <Route path="/results" element={<ResultsPage />} />
                    <Route path="/results/:runId" element={<ResultsPage />} />
                    <Route path="/report" element={<ReportPage />} />
                    <Route path="/report/:runId" element={<ReportPage />} />
                    <Route path="/case-study" element={<CaseStudy />} />
                    <Route path="/glossary" element={<GlossaryPage />} />
                  </Routes>
              </motion.div>
            </AnimatePresence>
          </div>
          <SpectralBand className="mx-auto max-w-[980px]" />
          <footer className="mx-auto max-w-[980px] px-6 py-6 text-[11.5px] text-faint md:px-12">
            Every visual on this site is generated from public tabulated physics or from this
            project's own aggregate results. No photograph or dataset image appears here.
          </footer>
        </main>
      </div>
    </MotionProvider>
  );
}
