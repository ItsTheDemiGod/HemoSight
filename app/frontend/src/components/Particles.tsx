import { useEffect, useRef } from "react";
import { useMotion } from "../motion/MotionProvider";

/* A slow, sparse field of points on a canvas: atmosphere, not a screensaver.
   - density is set by area, capped low; motion is a few pixels per second;
   - it draws only while on screen (IntersectionObserver) and while the tab is visible;
   - it does not exist at all when motion is off: the component renders nothing, so
     there is no canvas, no observer and no frame loop to pause. */

const DENSITY = 1 / 26000;   // points per px^2 -> ~45 on a 1440x820 hero
const MAX_POINTS = 70;
const SPEED = 6;             // px per second

interface P { x: number; y: number; vx: number; vy: number; r: number; a: number }

export default function Particles({ className = "" }: { className?: string }) {
  const { enabled } = useMotion();
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!enabled || !canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let pts: P[] = [];
    let w = 0, h = 0, dpr = 1;
    let raf = 0;
    let visible = true;
    let last = performance.now();
    const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "currentColor";

    const size = () => {
      const rect = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = Math.max(1, Math.floor(rect.width));
      h = Math.max(1, Math.floor(rect.height));
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const n = Math.min(MAX_POINTS, Math.round(w * h * DENSITY));
      pts = Array.from({ length: n }, () => {
        const ang = Math.random() * Math.PI * 2;
        return { x: Math.random() * w, y: Math.random() * h,
                 vx: Math.cos(ang) * SPEED, vy: Math.sin(ang) * SPEED,
                 r: 0.6 + Math.random() * 1.1, a: 0.25 + Math.random() * 0.45 };
      });
    };

    const frame = (t: number) => {
      raf = 0;
      if (!visible) return;
      const dt = Math.min(0.05, (t - last) / 1000);
      last = t;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = accent;
      for (const p of pts) {
        p.x += p.vx * dt; p.y += p.vy * dt;
        if (p.x < -4) p.x = w + 4; else if (p.x > w + 4) p.x = -4;
        if (p.y < -4) p.y = h + 4; else if (p.y > h + 4) p.y = -4;
        ctx.globalAlpha = p.a;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(frame);
    };
    const start = () => { if (!raf && visible) { last = performance.now(); raf = requestAnimationFrame(frame); } };
    const stop = () => { if (raf) cancelAnimationFrame(raf); raf = 0; };

    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting && document.visibilityState === "visible";
      visible ? start() : stop();
    }, { threshold: 0.02 });
    io.observe(canvas);
    const onVis = () => { visible = document.visibilityState === "visible"; visible ? start() : stop(); };
    document.addEventListener("visibilitychange", onVis);
    const ro = new ResizeObserver(size);
    ro.observe(canvas);
    size();
    start();
    return () => { stop(); io.disconnect(); ro.disconnect(); document.removeEventListener("visibilitychange", onVis); };
  }, [enabled]);

  if (!enabled) return null;
  return <canvas ref={ref} aria-hidden="true" className={`pointer-events-none absolute inset-0 h-full w-full ${className}`} />;
}
