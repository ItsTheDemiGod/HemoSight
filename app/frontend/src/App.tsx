import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import Landing from "./pages/Landing";
import PreRegPage from "./pages/PreReg";
import UploadPage from "./pages/Upload";
import RunPage from "./pages/Run";
import ResultsPage from "./pages/Results";
import ReportPage from "./pages/Report";
import CaseStudy from "./pages/CaseStudy";

const NAV = [
  { to: "/", label: "Overview", n: "00" },
  { to: "/prereg", label: "Pre-registration", n: "01" },
  { to: "/upload", label: "Upload", n: "02" },
  { to: "/run", label: "Run", n: "03" },
  { to: "/results", label: "Results", n: "04" },
  { to: "/report", label: "Report", n: "05" },
  { to: "/case-study", label: "Case study", n: "06" },
];

export default function App() {
  const loc = useLocation();
  return (
    <div className="min-h-screen md:flex">
      <aside
        className="border-b border-rule bg-panel px-6 py-6 md:sticky md:top-0 md:h-screen
                   md:w-[236px] md:shrink-0 md:border-b-0 md:border-r md:px-6 md:py-8"
      >
        <NavLink to="/" className="block">
          <div className="font-serif text-[17px] leading-tight">HemoSight Audit</div>
          <div className="label mt-1">Methodological checks</div>
        </NavLink>

        <nav className="mt-8 flex flex-wrap gap-x-5 gap-y-1 md:block">
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
                        className="absolute -bottom-[2px] left-0 right-0 h-px bg-ink"
                        transition={{ type: "spring", stiffness: 420, damping: 34 }}
                      />
                    )}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <p className="mt-10 hidden max-w-[190px] text-[11.5px] leading-relaxed text-faint md:block">
          Built from the analysis pipeline of a project whose own haemoglobin model
          failed every pre-declared gate. Nothing here is a clinical validation.
        </p>
      </aside>

      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-[980px] px-6 py-10 md:px-12 md:py-14">
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
              </Routes>
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
