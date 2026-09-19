"""Phase 9C - propagate parameter uncertainty into the gate result.

Everything here was pre-declared in CLAUDE.md (Phase 9C, 2026-09-20) before this
script was first run: the parameter prior, the interpretation rule, the design size
and the seed. The script reports the nominal reproduction FIRST and refuses to
continue if the recorded point estimates do not come back.

Outputs: data/interim/phase9c/uncertainty.json (+ banks.npz, design.npz caches) and
histogram PNGs under reports/figures/phase9c/ (gitignored).

    .\\.venv\\Scripts\\python.exe scripts\\phase9c_uncertainty.py
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np

from hemosight.io import paths
from hemosight.simulation import uncertainty as U

OUT = paths.INTERIM / "phase9c"
FIG = paths.REPORTS / "figures" / "phase9c"
RESIDUALS = [U.RESIDUAL_3935, U.RESIDUAL_3456, U.RESIDUAL_1062]
LABELS = {U.RESIDUAL_3935: "3.935 (grey-world @25% FOV, Phase 3 gate)",
          U.RESIDUAL_3456: "3.456 (MOBIUS 3 phones x 3 lighting, uncontrolled)",
          U.RESIDUAL_1062: "1.062 (SBVPI studio)"}
REPRO_TOL = 1e-6


def load_or_build_banks() -> dict[float, np.ndarray]:
    f = OUT / "banks.npz"
    if f.exists():
        z = np.load(f)
        return {de: z[str(de)] for de in RESIDUALS}
    t = time.time()
    banks = U.build_banks()
    np.savez(f, **{str(de): b for de, b in banks.items()})
    print(f"perturbation banks regenerated in original RNG order: {time.time() - t:.0f} s")
    return banks


def quantile_in_prior(th: dict[str, float]) -> dict[str, float]:
    """Where each parameter of theta sits in its prior, 0 = low edge, 1 = high edge."""
    q = {}
    for p in U.PARAMS:
        v = th[p.key]
        if p.log:
            q[p.key] = (np.log(v) - np.log(p.lo)) / (np.log(p.hi) - np.log(p.lo))
        else:
            q[p.key] = (v - p.lo) / (p.hi - p.lo)
        q[p.key] = float(np.clip(q[p.key], 0.0, 1.0))
    return q


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-base", type=int, default=1024, help="Saltelli base sample (pre-declared 1024)")
    ap.add_argument("--reuse-design", action="store_true",
                    help="reuse data/interim/phase9c/design.npz instead of re-evaluating")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    fwd = U.ForwardTheta()
    banks = load_or_build_banks()

    # ------------------------------------------------------------ reproduction
    print("=== 0. Nominal theta must reproduce the recorded point estimates ===")
    nominal = dict(U.NOMINAL)
    nominal["melanin"] = 0.0          # the gate ran at exactly zero melanin
    repro = {}
    for de in RESIDUALS:
        got = U.gate_mae(fwd, nominal, banks[de])
        label, rec = U.RECORDED[de]
        diff = abs(got - rec)
        repro[str(de)] = {"label": label, "recorded": rec, "reproduced": got, "abs_diff": diff,
                          "ok": bool(diff < REPRO_TOL)}
        print(f"  {label:48s} recorded {rec:.6f}  reproduced {got:.6f}  |diff| {diff:.2e}")
    if not all(v["ok"] for v in repro.values()):
        print("REPRODUCTION FAILED - the run is invalid by the pre-declared rule")
        (OUT / "uncertainty.json").write_text(json.dumps({"reproduction": repro, "valid": False},
                                                         indent=2), encoding="utf-8")
        return 1

    # ------------------------------------------------------------ design
    A, B, AB = U.saltelli_design(args.n_base, U.SEED)
    d = len(U.PARAMS)
    n_eval = (d + 2) * args.n_base
    print(f"\n=== 1. Saltelli design: d={d}, base N={args.n_base}, {n_eval} evaluations "
          f"x {len(RESIDUALS)} residuals ===")
    cache = OUT / "design.npz"
    if args.reuse_design and cache.exists():
        z = np.load(cache)
        ev = {"thetaA": z["thetaA"], "thetaB": z["thetaB"],
              "fA": {de: z[f"fA_{de}"] for de in RESIDUALS},
              "fB": {de: z[f"fB_{de}"] for de in RESIDUALS},
              "fAB": {de: z[f"fAB_{de}"] for de in RESIDUALS}}
        if ev["thetaA"].shape[0] != args.n_base:
            print(f"  cached design has base N={ev['thetaA'].shape[0]}, not {args.n_base}")
            return 1
        print(f"  reused cached design ({cache})")
    else:
        t = time.time()
        ev = U.evaluate_design(lambda th: U.gate_mae_all(fwd, th, banks), A, B, AB, RESIDUALS)
        print(f"  evaluated in {time.time() - t:.0f} s")
        np.savez(cache, thetaA=ev["thetaA"], thetaB=ev["thetaB"],
                 **{f"fA_{de}": ev["fA"][de] for de in RESIDUALS},
                 **{f"fB_{de}": ev["fB"][de] for de in RESIDUALS},
                 **{f"fAB_{de}": ev["fAB"][de] for de in RESIDUALS})

    theta_mc = np.concatenate([ev["thetaA"], ev["thetaB"]])
    results: dict = {"valid": True, "reproduction": repro, "seed": U.SEED,
                     "n_base": args.n_base, "n_mc": int(theta_mc.shape[0]), "n_eval": n_eval,
                     "params": [{"key": p.key, "label": p.label, "nominal": p.nominal,
                                 "lo": p.lo, "hi": p.hi, "log_uniform": p.log, "status": p.status,
                                 "justification": p.justification} for p in U.PARAMS],
                     "residuals": {}}

    # ------------------------------------------------------------ distributions
    print("\n=== 2. Gate MAE as a distribution over the prior (self-consistent) ===")
    print(f"  {'residual':52s} {'median':>7s} {'2.5%':>7s} {'97.5%':>7s} {'>2.0':>6s} {'<1.0':>6s}  rule")
    mel_col = U.KEYS.index("melanin")
    low_mel = theta_mc[:, mel_col] <= 0.005
    for de in RESIDUALS:
        f = np.concatenate([ev["fA"][de], ev["fB"][de]])
        s = U.summarise(f)
        s_low = U.summarise(f[low_mel])
        counts, edges = np.histogram(f, bins=60)
        s["histogram"] = {"counts": counts.tolist(), "edges": edges.tolist()}
        s["conditional_melanin_le_0.005"] = s_low
        rec = U.RECORDED[de][1]
        s["point_estimate"] = rec
        s["point_estimate_percentile"] = float(np.mean(f <= rec) * 100)
        rule = ("ROBUST" if s["robust_at_2.0"] else "FRAGILE") + " at 2.0"
        if de == U.RESIDUAL_1062:
            rule += "; " + ("ROBUST" if s["robust_at_1.0"] else "FRAGILE") + " at 1.0"
        s["rule"] = rule
        # the most favourable draw and the draws below 2.0
        i_min = int(np.argmin(f))
        th_min = U.theta_dict(theta_mc[i_min])
        s["min_draw"] = {"mae": float(f[i_min]), "theta": th_min,
                         "quantile_in_prior": quantile_in_prior(th_min), "band": U.band(float(f[i_min]))}
        below = f < 2.0
        s["below_2.0"] = {"n": int(below.sum()), "fraction": float(below.mean())}
        if below.any():
            qs = np.array([list(quantile_in_prior(U.theta_dict(r)).values()) for r in theta_mc[below]])
            s["below_2.0"]["mean_quantile_in_prior"] = dict(zip(U.KEYS, qs.mean(axis=0).tolist()))
            s["below_2.0"]["melanin_max"] = float(theta_mc[below, mel_col].max())
        results["residuals"][str(de)] = s
        print(f"  {LABELS[de]:52s} {s['median']:7.3f} {s['p2.5']:7.3f} {s['p97.5']:7.3f} "
              f"{s['fraction_above_2.0']:6.3f} {s['fraction_below_1.0']:6.3f}  {rule}")
        print(f"  {'   conditional on melanin <= 0.005':52s} {s_low['median']:7.3f} "
              f"{s_low['p2.5']:7.3f} {s_low['p97.5']:7.3f} {s_low['fraction_above_2.0']:6.3f} "
              f"{s_low['fraction_below_1.0']:6.3f}  (n={s_low['n']})")

    # ------------------------------------------------------------ sensitivity
    print("\n=== 3. Sobol indices (Jansen), ranked by total index ===")
    results["sobol"] = {}
    for de in RESIDUALS:
        si = U.sobol_indices(ev["fA"][de], ev["fB"][de], ev["fAB"][de])
        order = np.argsort(si["total"])[::-1]
        si["ranked"] = [{"key": U.KEYS[i], "label": U.PARAMS[i].label, "status": U.PARAMS[i].status,
                         "S1": si["first_order"][i], "S1_ci": si["first_order_ci"][i],
                         "ST": si["total"][i], "ST_ci": si["total_ci"][i]} for i in order]
        results["sobol"][str(de)] = si
        print(f"  residual {LABELS[de]}  (variance {si['variance']:.4f})")
        for r in si["ranked"][:6]:
            print(f"    {r['label']:40s} ST {r['ST']:6.3f} [{r['ST_ci'][0]:.3f},{r['ST_ci'][1]:.3f}]  "
                  f"S1 {r['S1']:6.3f}  {r['status']}")

    print("\n=== 3b. One-at-a-time swing (others at nominal) ===")
    oat = U.one_at_a_time(lambda th: U.gate_mae_all(fwd, th, banks))
    results["oat"] = {}
    for de in RESIDUALS:
        rows = {k: {"grid": v["grid"], "values": [x[de] for x in v["values"]]} for k, v in oat.items()}
        for k in rows:
            rows[k]["swing"] = float(max(rows[k]["values"]) - min(rows[k]["values"]))
        results["oat"][str(de)] = rows
    top = sorted(results["oat"][str(U.RESIDUAL_3935)].items(), key=lambda kv: -kv[1]["swing"])[:6]
    for k, v in top:
        print(f"  {k:16s} swing {v['swing']:.3f} g/dL at 3.935  "
              f"(min {min(v['values']):.3f}, max {max(v['values']):.3f})")

    # ------------------------------------------------------------ mechanism
    print("\n=== 3c. Mechanism: colour signal per g/dL, and reflectance saturation ===")
    from scipy.stats import spearmanr
    rng_m = np.random.default_rng(U.SEED)
    idx = rng_m.choice(theta_mc.shape[0], 400, replace=False)
    hb_probe = np.array([4.0, 9.0, 13.0, 18.0])
    clip, span = [], []
    for i in idx:
        th = U.theta_dict(theta_mc[i])
        clip.append(float(np.mean(fwd.reflectance(hb_probe, th) >= 0.999)))
        lut2 = fwd.chroma_lut(th, np.array([4.0, 18.0]))
        span.append(float(np.linalg.norm(lut2[1] - lut2[0])))
    clip, span = np.array(clip), np.array(span)
    f3935 = np.concatenate([ev["fA"][U.RESIDUAL_3935], ev["fB"][U.RESIDUAL_3935]])[idx]
    nominal_clip = float(np.mean(fwd.reflectance(hb_probe, nominal) >= 0.999))
    rho = float(spearmanr(f3935, span).statistic)
    results["mechanism"] = {
        "n_probe": int(idx.size), "spearman_mae_vs_chroma_span": rho,
        "chroma_span_median": float(np.median(span)),
        "chroma_span_p2.5": float(np.percentile(span, 2.5)),
        "chroma_span_p97.5": float(np.percentile(span, 97.5)),
        "saturated_fraction_median": float(np.median(clip)),
        "saturated_fraction_at_nominal": nominal_clip,
        "fraction_of_draws_over_half_saturated": float(np.mean(clip > 0.5))}
    print(f"  spearman(gate MAE, chroma span 4->18 g/dL) = {rho:+.3f}")
    print(f"  chroma span: median {np.median(span):.4f} "
          f"[{np.percentile(span, 2.5):.4f}, {np.percentile(span, 97.5):.4f}]")
    print(f"  reflectance saturated at >=0.999: median {np.median(clip):.2f} of the (Hb, wl) grid; "
          f"at NOMINAL {nominal_clip:.2f}")

    # ------------------------------------------------------------ mismatch variant
    print("\n=== 4. Mismatch variant (LUT at nominal, truth at theta) - the Phase 3 Task 4 question ===")
    nominal_lut = nominal
    zero_bank = np.ones_like(banks[U.RESIDUAL_3935])
    mm = {"3.935": [], "0.0": []}
    t = time.time()
    for r in theta_mc:
        th = U.theta_dict(r)
        mm["3.935"].append(U.gate_mae(fwd, th, banks[U.RESIDUAL_3935], lut_theta=nominal_lut))
        mm["0.0"].append(U.gate_mae(fwd, th, zero_bank, lut_theta=nominal_lut))
    results["mismatch"] = {}
    for k, v in mm.items():
        v = np.array(v)
        s = U.summarise(v)
        s["conditional_melanin_le_0.005"] = U.summarise(v[low_mel])
        results["mismatch"][k] = s
        print(f"  residual {k:6s} median {s['median']:.3f}  95% [{s['p2.5']:.3f}, {s['p97.5']:.3f}]  "
              f">2.0 {s['fraction_above_2.0']:.3f}   | melanin<=0.005: median "
              f"{s['conditional_melanin_le_0.005']['median']:.3f}")
    print(f"  ({time.time() - t:.0f} s)")

    # ------------------------------------------------------------ figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
        for ax, de in zip(axes, RESIDUALS):
            f = np.concatenate([ev["fA"][de], ev["fB"][de]])
            ax.hist(f, bins=60, color="#555")
            ax.axvline(2.0, color="r", ls="--", lw=1)
            ax.axvline(1.0, color="orange", ls="--", lw=1)
            ax.axvline(U.RECORDED[de][1], color="k", lw=1.5)
            ax.set_title(f"residual {de:.3f} dE2000", fontsize=9)
            ax.set_xlabel("gate MAE g/dL")
        fig.tight_layout()
        fig.savefig(FIG / "gate_mae_histograms.png", dpi=130)
        results["figure"] = str(FIG / "gate_mae_histograms.png")
    except Exception as e:  # noqa: BLE001
        results["figure_error"] = repr(e)

    (OUT / "uncertainty.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nresults -> {OUT / 'uncertainty.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
