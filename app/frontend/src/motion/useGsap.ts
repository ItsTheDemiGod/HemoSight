import { useEffect, useRef } from "react";
import { useMotion } from "./MotionProvider";

/* GSAP + ScrollTrigger handle scroll-driven sequences; Framer Motion keeps component
   state transitions. GSAP is loaded lazily and only when motion is enabled, so the
   main bundle carries none of it and a reduced-motion visitor never downloads it. */

type Gsap = typeof import("gsap")["gsap"];
type ST = typeof import("gsap/ScrollTrigger")["ScrollTrigger"];

let loader: Promise<{ gsap: Gsap; ScrollTrigger: ST }> | null = null;

export function loadGsap() {
  if (!loader) {
    loader = Promise.all([import("gsap"), import("gsap/ScrollTrigger")]).then(([g, s]) => {
      g.gsap.registerPlugin(s.ScrollTrigger);
      return { gsap: g.gsap, ScrollTrigger: s.ScrollTrigger };
    });
  }
  return loader;
}

/* Run `setup(gsap, ScrollTrigger)` once GSAP is available and motion is on; the
   returned cleanup (or the gsap.context revert) runs on unmount or when motion
   is switched off, which also restores every element to its static state. */
export function useGsap(
  setup: (g: Gsap, st: ST) => void | (() => void),
  key: unknown = null
) {
  const { enabled } = useMotion();
  // The latest setup lives in a ref so the effect depends only on `enabled` and the
  // caller's key, not on the function identity - no suppression needed.
  const setupRef = useRef(setup);
  setupRef.current = setup;
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let cleanup: void | (() => void);
    let ctx: { revert: () => void } | null = null;
    loadGsap().then(({ gsap, ScrollTrigger }) => {
      if (cancelled) return;
      ctx = gsap.context(() => {
        cleanup = setupRef.current(gsap, ScrollTrigger);
      });
    });
    return () => {
      cancelled = true;
      if (cleanup) cleanup();
      if (ctx) ctx.revert();
    };
  }, [enabled, key]);
}

/* Staggered reveal for every `.reveal` element under `root` as it enters the viewport.
   With motion off the `.reveal` class has no effect (see index.css), so nothing is
   ever hidden from a reduced-motion visitor. */
export function useReveal(root: React.RefObject<HTMLElement>) {
  useGsap((gsap, ScrollTrigger) => {
    const el = root.current;
    if (!el) return;
    const items = Array.from(el.querySelectorAll<HTMLElement>(".reveal"));
    items.forEach((item, i) => {
      gsap.to(item, {
        opacity: 1,
        y: 0,
        duration: 0.6,
        ease: "power2.out",
        delay: (i % 4) * 0.08,
        scrollTrigger: { trigger: item, start: "top 88%", once: true },
      });
    });
    return () => ScrollTrigger.getAll().forEach((t) => t.kill());
  }, root);
}
