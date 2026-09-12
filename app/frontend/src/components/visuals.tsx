import { useId, useMemo } from "react";
import spectra from "../data/hb_spectra.json";
import band from "../data/spectral_band.json";
import nullDist from "../data/null_distribution.json";
import noise from "../data/noise_signal.json";
import breakeven from "../data/breakeven.json";

/* Every visual on the site is generated here from public tabulated physics (OMLC
   haemoglobin extinction; CIE colour matching) or from this project's own aggregate
   results. No photograph, no stock image, nothing derived from a dataset image.
   All SVG; colours come from the tokens. */

function path(xs: number[], ys: number[], W: number, H: number, pad = 0): string {
  const n = xs.length;
  const x = (i: number) => pad + (i / (n - 1)) * (W - 2 * pad);
  const y = (v: number) => H - pad - v * (H - 2 * pad);
  return xs.map((_, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(ys[i]).toFixed(1)}`).join(" ");
}

/* ---------------------------------------------------------------- Hb spectra hero */
export function HbSpectra({ className = "", glow = true, highlight }: { className?: string; glow?: boolean; highlight?: "hbo2" | "hb" | "iso" | null }) {
  const id = useId();
  const W = 1200, H = 520, pad = 24;
  const wl = spectra.wavelength_nm as number[];
  const d1 = useMemo(() => path(wl, spectra.hbo2_log10_norm as number[], W, H, pad), [wl]);
  const d2 = useMemo(() => path(wl, spectra.hb_log10_norm as number[], W, H, pad), [wl]);
  const xOf = (nm: number) => pad + ((nm - wl[0]) / (wl[wl.length - 1] - wl[0])) * (W - 2 * pad);
  const dimO = highlight === "hb" ? 0.25 : 1, dimH = highlight === "hbo2" ? 0.25 : 1;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={className} role="img"
         aria-label="Molar extinction of oxy- and deoxy-haemoglobin from 380 to 1000 nanometres, log scale">
      <defs>
        <filter id={`${id}-glow`} x="-5%" y="-20%" width="110%" height="140%">
          <feGaussianBlur stdDeviation="6" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <linearGradient id={`${id}-vis`} x1="0" x2="1">
          {(band.stops as { nm: number; rgb: number[] }[]).map((s) => (
            <stop key={s.nm} offset={`${((s.nm - wl[0]) / (wl[wl.length - 1] - wl[0])) * 100}%`}
                  stopColor={`rgb(${s.rgb.join(",")})`} stopOpacity="0.12" />
          ))}
          <stop offset={`${((700 - wl[0]) / (wl[wl.length - 1] - wl[0])) * 100 + 0.1}%`} stopColor="var(--bg-0)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* measurement grid */}
      {[0.25, 0.5, 0.75].map((f) => (
        <line key={f} x1={pad} x2={W - pad} y1={pad + f * (H - 2 * pad)} y2={pad + f * (H - 2 * pad)}
              stroke="var(--rule)" strokeWidth="1" />
      ))}
      {[400, 500, 600, 700, 800, 900, 1000].map((nm) => (
        <g key={nm}>
          <line x1={xOf(nm)} x2={xOf(nm)} y1={pad} y2={H - pad} stroke="var(--rule)" strokeWidth="1" />
          <text x={xOf(nm)} y={H - 6} fill="var(--faint)" fontSize="11" fontFamily="ui-monospace, monospace" textAnchor="middle">{nm}</text>
        </g>
      ))}
      {/* the visible band under the curves */}
      <rect x={pad} y={pad} width={xOf(700) - pad} height={H - 2 * pad} fill={`url(#${id}-vis)`} />
      {/* isosbestic points: where the two curves cross */}
      {(spectra.isosbestic_nm as number[]).map((nm) => (
        <line key={nm} x1={xOf(nm)} x2={xOf(nm)} y1={pad} y2={H - pad} stroke="var(--accent)"
              strokeOpacity={highlight === "iso" ? 0.7 : 0.18} strokeDasharray="2 6" strokeWidth="1" />
      ))}
      <path d={d1} fill="none" stroke="var(--hbo2)" strokeWidth="2.2" opacity={dimO}
            filter={glow ? `url(#${id}-glow)` : undefined} strokeLinejoin="round" />
      <path d={d2} fill="none" stroke="var(--hb)" strokeWidth="2.2" opacity={dimH}
            filter={glow ? `url(#${id}-glow)` : undefined} strokeLinejoin="round" />
      <text x={pad + 6} y={pad + 16} fill="var(--hbo2)" fontSize="12" fontFamily="ui-monospace, monospace">HbO₂</text>
      <text x={pad + 60} y={pad + 16} fill="var(--hb)" fontSize="12" fontFamily="ui-monospace, monospace">Hb</text>
      <text x={W - pad} y={pad + 16} fill="var(--faint)" fontSize="11" fontFamily="ui-monospace, monospace" textAnchor="end">
        molar extinction, log₁₀ · nm →
      </text>
    </svg>
  );
}

/* ------------------------------------------------------- spectral band divider */
export function SpectralBand({ className = "" }: { className?: string }) {
  const stops = band.stops as { nm: number; rgb: number[] }[];
  const grad = stops.map((s) => `rgb(${s.rgb.join(",")}) ${((s.nm - 380) / 320) * 100}%`).join(", ");
  return (
    <div aria-hidden="true" className={`h-px w-full ${className}`}
         style={{ background: `linear-gradient(90deg, ${grad})`, opacity: 0.55 }} />
  );
}

/* --------------------------------------------- null distribution vs the real value */
export function NullDistribution({ className = "" }: { className?: string }) {
  const W = 640, H = 240, pad = 28;
  const draws = nullDist.draws_mae as number[];
  const real = nullDist.real_mae, sex = nullDist.sex_alone_mae, pop = nullDist.population_mean_mae;
  const lo = Math.min(real - 0.02, ...draws), hi = Math.max(pop + 0.02, ...draws);
  const bins = 24;
  const counts = new Array(bins).fill(0);
  draws.forEach((v) => { counts[Math.min(bins - 1, Math.floor(((v - lo) / (hi - lo)) * bins))]++; });
  const maxC = Math.max(...counts);
  const x = (v: number) => pad + ((v - lo) / (hi - lo)) * (W - 2 * pad);
  const bw = (W - 2 * pad) / bins;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={className} role="img"
         aria-label={`Null distribution of ${draws.length} shuffled-label runs against the real error ${real}`}>
      {counts.map((c, i) => (
        <rect key={i} x={pad + i * bw + 1} width={bw - 2} y={H - pad - (c / maxC) * (H - 2 * pad - 30)}
              height={(c / maxC) * (H - 2 * pad - 30)} fill="var(--accent-dim)" opacity="0.8" />
      ))}
      <line x1={x(real)} x2={x(real)} y1={pad} y2={H - pad} stroke="var(--pass)" strokeWidth="2" />
      <text x={x(real) + 6} y={pad + 12} fill="var(--pass)" fontSize="11" fontFamily="ui-monospace, monospace">real {real}</text>
      <line x1={x(sex)} x2={x(sex)} y1={pad} y2={H - pad} stroke="var(--insufficient)" strokeWidth="1.5" strokeDasharray="4 4" />
      <text x={x(sex) + 6} y={pad + 28} fill="var(--insufficient)" fontSize="11" fontFamily="ui-monospace, monospace">sex alone {sex}</text>
      <line x1={x(pop)} x2={x(pop)} y1={pad} y2={H - pad} stroke="var(--faint)" strokeWidth="1" strokeDasharray="2 4" />
      <text x={x(pop) - 6} y={pad + 12} fill="var(--faint)" fontSize="11" fontFamily="ui-monospace, monospace" textAnchor="end">constant {pop}</text>
      <text x={W - pad} y={H - 8} fill="var(--faint)" fontSize="11" fontFamily="ui-monospace, monospace" textAnchor="end">
        MAE g/dL → · {draws.length} shuffles, none reached the real value: p ≤ {nullDist.p_empirical}, a floor
      </text>
    </svg>
  );
}

/* --------------------------------------------------------- noise vs signal ladder */
export function NoiseSignal({ className = "" }: { className?: string }) {
  const W = 640, H = 220, pad = 28, left = 190;
  const conds = noise.conditions as { label: string; residual_dE2000: number; gate_mae_g_dl: number; band: string }[];
  const maxR = Math.max(...conds.map((c) => c.residual_dE2000)) * 1.15;
  const x = (v: number) => left + (v / maxR) * (W - left - pad);
  const rowH = (H - 2 * pad) / conds.length;
  const sig = noise.signal_dE2000_per_g_dl, viable = noise.viable_residual;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={className} role="img"
         aria-label="Residual colour error per capture condition against the measured haemoglobin signal">
      {conds.map((c, i) => {
        const y = pad + i * rowH;
        const tone = c.band === "VIABLE" ? "var(--pass)" : c.band === "MARGINAL" ? "var(--insufficient)" : "var(--fail)";
        return (
          <g key={c.label}>
            <text x={left - 10} y={y + rowH / 2 + 4} fill="var(--muted)" fontSize="12" textAnchor="end" fontFamily="Inter, system-ui, sans-serif">{c.label}</text>
            <rect x={left} y={y + rowH * 0.25} width={x(c.residual_dE2000) - left} height={rowH * 0.5} fill={tone} opacity="0.85" />
            <text x={x(c.residual_dE2000) + 6} y={y + rowH / 2 + 4} fill="var(--ink)" fontSize="11" fontFamily="ui-monospace, monospace">
              {c.residual_dE2000.toFixed(2)} · {c.gate_mae_g_dl.toFixed(2)} g/dL · {c.band.toLowerCase()}
            </text>
          </g>
        );
      })}
      <line x1={x(sig)} x2={x(sig)} y1={pad - 8} y2={H - pad + 4} stroke="var(--accent)" strokeWidth="1.5" strokeDasharray="3 4" />
      <text x={x(sig)} y={pad - 12} fill="var(--accent)" fontSize="11" textAnchor="middle" fontFamily="ui-monospace, monospace">signal {sig}/g·dL⁻¹</text>
      <line x1={x(viable)} x2={x(viable)} y1={pad - 8} y2={H - pad + 4} stroke="var(--pass)" strokeWidth="1" strokeDasharray="2 4" />
      <text x={x(viable)} y={H - 6} fill="var(--pass)" fontSize="11" textAnchor="middle" fontFamily="ui-monospace, monospace">viable &lt; {viable}</text>
      <text x={W - pad} y={H - 6} fill="var(--faint)" fontSize="11" textAnchor="end" fontFamily="ui-monospace, monospace">residual ΔE2000 →</text>
    </svg>
  );
}

/* ------------------------------------------------------------- breakeven curve */
export function Breakeven({ className = "" }: { className?: string }) {
  const W = 640, H = 240, pad = 30;
  const scan = breakeven.scan as { residual: number; mae: number }[];
  const maxX = scan[scan.length - 1].residual, maxY = Math.max(...scan.map((s) => s.mae)) * 1.1;
  const x = (v: number) => pad + (v / maxX) * (W - 2 * pad);
  const y = (v: number) => H - pad - (v / maxY) * (H - 2 * pad);
  const d = scan.map((s, i) => `${i ? "L" : "M"}${x(s.residual).toFixed(1)},${y(s.mae).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={className} role="img" aria-label="Haemoglobin error against residual colour error, with the viable and marginal bands">
      <rect x={pad} y={y(1)} width={W - 2 * pad} height={H - pad - y(1)} fill="var(--pass)" opacity="0.08" />
      <rect x={pad} y={y(2)} width={W - 2 * pad} height={y(1) - y(2)} fill="var(--insufficient)" opacity="0.08" />
      <rect x={pad} y={pad} width={W - 2 * pad} height={y(2) - pad} fill="var(--fail)" opacity="0.06" />
      <text x={W - pad - 4} y={y(1) - 4} fill="var(--pass)" fontSize="10.5" textAnchor="end" fontFamily="ui-monospace, monospace">viable &lt; 1.0</text>
      <text x={W - pad - 4} y={y(2) - 4} fill="var(--insufficient)" fontSize="10.5" textAnchor="end" fontFamily="ui-monospace, monospace">marginal &lt; 2.0</text>
      <path d={d} fill="none" stroke="var(--accent)" strokeWidth="2" />
      {(breakeven.measured as { label: string; residual: number }[]).map((m) => (
        <g key={m.label}>
          <line x1={x(m.residual)} x2={x(m.residual)} y1={pad} y2={H - pad} stroke="var(--muted)" strokeDasharray="3 4" strokeWidth="1" />
          <text x={x(m.residual) + 5} y={pad + 12} fill="var(--muted)" fontSize="11" fontFamily="ui-monospace, monospace">{m.label} {m.residual}</text>
        </g>
      ))}
      <text x={W - pad} y={H - 8} fill="var(--faint)" fontSize="11" textAnchor="end" fontFamily="ui-monospace, monospace">residual ΔE2000 → · MAE g/dL ↑</text>
    </svg>
  );
}

/* ------------------------------------------------- abstract: grid, reticle, trace */
export function Grid({ className = "" }: { className?: string }) {
  const id = useId();
  return (
    <svg aria-hidden="true" className={className} width="100%" height="100%">
      <defs>
        <pattern id={`${id}-g`} width="48" height="48" patternUnits="userSpaceOnUse">
          <path d="M48 0H0V48" fill="none" stroke="var(--rule)" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id}-g)`} />
    </svg>
  );
}

export function Reticle({ size = 160, className = "" }: { size?: number; className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 100 100" width={size} height={size} className={className} fill="none" stroke="var(--accent)">
      <circle cx="50" cy="50" r="46" strokeOpacity="0.35" />
      <circle cx="50" cy="50" r="28" strokeOpacity="0.5" strokeDasharray="2 4" />
      <path d="M50 2v18M50 80v18M2 50h18M80 50h18" strokeOpacity="0.8" />
      <circle cx="50" cy="50" r="2" fill="var(--accent)" stroke="none" />
    </svg>
  );
}

/* A synthetic pulse-like trace: generated by a formula, not read from any recording. */
export function Waveform({ className = "" }: { className?: string }) {
  const W = 800, H = 120;
  const d = useMemo(() => {
    const pts: string[] = [];
    for (let i = 0; i <= 400; i++) {
      const t = i / 400;
      const beat = (t * 4) % 1;
      const v = Math.exp(-((beat - 0.18) ** 2) / 0.004) + 0.35 * Math.exp(-((beat - 0.42) ** 2) / 0.01);
      pts.push(`${i ? "L" : "M"}${(t * W).toFixed(1)},${(H - 16 - v * 80).toFixed(1)}`);
    }
    return pts.join(" ");
  }, []);
  return (
    <svg aria-hidden="true" viewBox={`0 0 ${W} ${H}`} className={className} fill="none">
      <path d={d} stroke="var(--accent)" strokeWidth="1.4" strokeOpacity="0.6" />
    </svg>
  );
}
