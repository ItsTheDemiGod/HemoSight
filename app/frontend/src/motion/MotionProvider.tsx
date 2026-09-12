import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

/* One switch for every decorative motion in the app.
   enabled = (the OS does not ask for reduced motion) AND (the in-app toggle is on).
   The state is stamped on <html> as data-motion="on|off" so CSS can follow it, and the
   custom cursor stamps data-cursor="custom|native" so the native cursor is restored the
   moment the reticle is not in use. Everything decorative reads `enabled`; nothing
   decorative runs when it is false. */

interface MotionState {
  enabled: boolean;
  osReduced: boolean;
  userOn: boolean;
  setUserOn: (v: boolean) => void;
}

const Ctx = createContext<MotionState>({ enabled: false, osReduced: true, userOn: false, setUserOn: () => undefined });
const KEY = "hemosight.motion";

function readUser(): boolean {
  try {
    const v = localStorage.getItem(KEY);
    return v === null ? true : v === "on";
  } catch {
    return true;
  }
}

export function MotionProvider({ children }: { children: ReactNode }) {
  const [osReduced, setOsReduced] = useState<boolean>(() =>
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
  const [userOn, setUserOnState] = useState<boolean>(readUser);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setOsReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  const setUserOn = useCallback((v: boolean) => {
    setUserOnState(v);
    try {
      localStorage.setItem(KEY, v ? "on" : "off");
    } catch {
      /* storage may be unavailable; the toggle still works for this page */
    }
  }, []);

  const enabled = !osReduced && userOn;
  useEffect(() => {
    document.documentElement.setAttribute("data-motion", enabled ? "on" : "off");
  }, [enabled]);

  const value = useMemo(() => ({ enabled, osReduced, userOn, setUserOn }), [enabled, osReduced, userOn, setUserOn]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useMotion(): MotionState {
  return useContext(Ctx);
}

export function MotionToggle() {
  const { enabled, osReduced, userOn, setUserOn } = useMotion();
  return (
    <div className="text-[12px] text-muted">
      <label className="flex cursor-pointer items-center gap-2">
        <input
          type="checkbox"
          className="accent-accent"
          checked={userOn}
          disabled={osReduced}
          onChange={(e) => setUserOn(e.target.checked)}
          aria-describedby="motion-note"
        />
        <span>Motion {enabled ? "on" : "off"}</span>
      </label>
      <p id="motion-note" className="mt-1 text-[11px] leading-snug text-faint">
        {osReduced
          ? "Your system asks for reduced motion; animation, parallax and the particle field are off."
          : "Turns off parallax, scroll animation, particles and the custom cursor. Nothing else changes."}
      </p>
    </div>
  );
}
