import { useEffect, useRef } from "react";
import { useMotion } from "../motion/MotionProvider";

/* A small measurement reticle that follows the pointer and opens up near anything
   interactive. Rules that keep it an instrument and not a game:
   - only with motion on, only for a fine pointer (mouse), never on touch;
   - pointer-events: none, so it can never intercept a click;
   - it is driven by pointer movement and hides on any keyboard interaction, so it
     never sits over a focus indicator;
   - the native cursor is hidden only while the reticle is live (html[data-cursor]),
     and restored the instant it is not. */

const INTERACTIVE = "a, button, [role=button], input, select, textarea, label, summary";

export default function Cursor() {
  const { enabled } = useMotion();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    const root = document.documentElement;
    const fine = window.matchMedia("(pointer: fine)").matches;
    if (!enabled || !fine || !el) {
      root.setAttribute("data-cursor", "native");
      return;
    }
    root.setAttribute("data-cursor", "native");
    let x = -100, y = -100, tx = -100, ty = -100, raf = 0, near = false, shown = false;

    const tick = () => {
      x += (tx - x) * 0.35; y += (ty - y) * 0.35;
      el.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%) scale(${near ? 1.6 : 1})`;
      raf = (Math.abs(tx - x) > 0.2 || Math.abs(ty - y) > 0.2) ? requestAnimationFrame(tick) : 0;
    };
    const show = () => { if (!shown) { shown = true; el.style.opacity = "1"; root.setAttribute("data-cursor", "custom"); } };
    const hide = () => { if (shown) { shown = false; el.style.opacity = "0"; root.setAttribute("data-cursor", "native"); } };
    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") { hide(); return; }
      tx = e.clientX; ty = e.clientY;
      const t = e.target as Element | null;
      near = !!(t && t.closest && t.closest(INTERACTIVE));
      el.dataset.near = near ? "1" : "0";
      show();
      if (!raf) raf = requestAnimationFrame(tick);
    };
    const onKey = () => hide();            // keyboard use: never obscure a focus ring
    const onLeave = () => hide();
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("keydown", onKey);
    document.addEventListener("mouseleave", onLeave);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("mouseleave", onLeave);
      if (raf) cancelAnimationFrame(raf);
      root.setAttribute("data-cursor", "native");
    };
  }, [enabled]);

  if (!enabled) return null;
  return (
    <div
      ref={ref}
      aria-hidden="true"
      className="pointer-events-none fixed left-0 top-0 z-[60] h-6 w-6 opacity-0 transition-opacity duration-150"
      style={{ transform: "translate3d(-100px,-100px,0)" }}
    >
      <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="var(--accent)" strokeWidth="1">
        <circle cx="12" cy="12" r="7" opacity="0.9" />
        <path d="M12 1v5M12 18v5M1 12h5M18 12h5" />
        <circle cx="12" cy="12" r="1" fill="var(--accent)" stroke="none" />
      </svg>
    </div>
  );
}
