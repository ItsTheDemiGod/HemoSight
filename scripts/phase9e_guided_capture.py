"""Phase 9E Part A - the guided-capture regime, the one regime nobody measured.

Phase 7 measured three capture conditions: uncontrolled (MOBIUS, 3 phones x 3 lighting,
3.456 dE2000), one phone and one lighting cell with gaze varying (1.981), and a studio
rig (1.062). **A deployed screening app operates in none of them.** Its guided capture is
one phone in one session with a live overlay enforcing framing and distance and a quality
gate rejecting blurred or badly exposed frames before the shutter - more controlled than
the second condition, less than the third. That is exactly the interval in which the gate
crosses out of NOT RECOVERABLE, and exactly where Phase 9C found the verdict fragile.

**This script does not close the gap.** Closing it needs data, which section 3 of
CLAUDE.md forbids permanently. It states the gap as a bounded quantity: the gate is run
across the whole bracketing interval and the Phase 9C prior is propagated at the
pre-declared headline point, so the interpolated number carries an interval from the
start.

Everything here is an INTERPOLATION BETWEEN TWO MEASURED POINTS. No capture in the
guided-capture regime was measured, by this project or by anyone whose data it holds.

Pre-declared in CLAUDE.md (Phase 9E, 2026-09-21), before this ran: the bracketing pair,
the headline point (the geometric mean, 1.450 dE2000), the labelling rule, and that fresh
banks are drawn for the grid with the anchors re-run on them so the bank draw is visibly
not doing the work.

    .\\.venv\\Scripts\\python.exe scripts\\phase9e_guided_capture.py
"""

from __future__ import annotations

import json
import time

import numpy as np

from hemosight.io import paths
from hemosight.simulation import uncertainty as U

OUT = paths.INTERIM / "phase9e"
P9C = paths.INTERIM / "phase9c"
BANK_SEED = 20260921            # fresh: no original RNG order exists at an unmeasured residual

LOWER = U.RESIDUAL_1062         # SBVPI studio, measured
UPPER = U.RESIDUAL_1981         # MOBIUS one phone + one lighting cell, gaze varying, measured
HEADLINE = float(np.sqrt(LOWER * UPPER))        # 1.450, declared before the gate was run
GRID = sorted({LOWER, 1.20, HEADLINE, 1.70, UPPER})
VIABLE_RESIDUAL = 0.9864568030176174            # Phase 7 Part C breakeven, read not retyped


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    fwd = U.ForwardTheta()
    nominal = dict(U.NOMINAL)
    nominal["melanin"] = 0.0        # the gate ran at exactly zero melanin

    R: dict = {
        "declared_in": "CLAUDE.md Phase 9E section, committed before this ran",
        "what_this_is": ("an INTERPOLATION between two measured residuals, not a "
                         "measurement of guided capture. No guided-capture image exists "
                         "in this project and none will: section 3 forbids collecting "
                         "data."),
        "bracketing_measurements": {
            "lower": {"residual_dE2000": LOWER, "condition": "SBVPI studio rig",
                      "source": "Phase 7 Task 1, measured",
                      "recorded_gate_mae": U.RECORDED[LOWER][1]},
            "upper": {"residual_dE2000": UPPER,
                      "condition": "MOBIUS, one phone and one lighting cell, gaze varying",
                      "source": "Phase 7 Task 1, measured",
                      "recorded_gate_mae": 2.026920021110283}},
        "headline_point": {"residual_dE2000": HEADLINE,
                           "rule": "geometric mean of the two bracketing residuals, "
                                   "declared before the gate was run at it"},
        "bank_seed": BANK_SEED, "grid": GRID}

    # ------------------------------------------------------ fresh banks for the grid
    print("=== 1. Fresh perturbation banks for the interpolation grid ===")
    rng = np.random.default_rng(BANK_SEED)
    banks = {de: U.perturbation_bank(rng, de) for de in GRID}
    print(f"  {len(GRID)} banks of {banks[GRID[0]].shape[0]} perturbations "
          f"({time.time() - t0:.0f}s)")

    # ------------------------------------------------- the gate across the interval
    print("\n=== 2. The gate at nominal theta, across the bracketing interval ===")
    curve = []
    for de in GRID:
        mae = U.gate_mae(fwd, nominal, banks[de])
        row = {"residual_dE2000": float(de), "mae_g_dl": mae, "band": U.band(mae),
               "is_measured_anchor": bool(de in (LOWER, UPPER)),
               "is_headline": bool(de == HEADLINE)}
        if row["is_measured_anchor"]:
            rec = (U.RECORDED[LOWER][1] if de == LOWER else 2.026920021110283)
            row["recorded_on_the_original_bank"] = rec
            row["difference_from_recorded"] = float(mae - rec)
        curve.append(row)
        tag = ("  <- MEASURED anchor" if row["is_measured_anchor"] else
               "  <- HEADLINE interpolation" if row["is_headline"] else "")
        print(f"  residual {de:.3f} -> MAE {mae:.3f} g/dL  {row['band']:16s}{tag}")
    R["gate_curve"] = curve

    anchors = [r for r in curve if r["is_measured_anchor"]]
    R["bank_draw_check"] = {
        "max_abs_difference_from_recorded": float(max(abs(r["difference_from_recorded"])
                                                      for r in anchors)),
        "reading": ("the two measured anchors re-run on the FRESH banks land within this "
                    "of their recorded values, so the interpolated points are not an "
                    "artefact of a different random draw")}
    print(f"  anchors on fresh banks differ from recorded by at most "
          f"{R['bank_draw_check']['max_abs_difference_from_recorded']:.3f} g/dL")

    # --------------------------------------------- does any point in the interval pass?
    bands = {r["band"] for r in curve}
    R["interval_verdict"] = {
        "bands_spanned_at_nominal_theta": sorted(bands),
        "residual_required_for_VIABLE": VIABLE_RESIDUAL,
        "best_bracketing_residual": LOWER,
        "any_point_in_the_interval_reaches_VIABLE": bool(LOWER < VIABLE_RESIDUAL),
        "reading": ("VIABLE needs a residual below "
                    f"{VIABLE_RESIDUAL:.3f} dE2000, which is below the BEST measured "
                    f"condition in the whole project ({LOWER:.3f}, a studio rig). No "
                    "point in the guided-capture interval reaches VIABLE at nominal "
                    "parameters, including its most favourable end.")}
    print(f"\n  bands across the interval at nominal theta: {sorted(bands)}")
    print(f"  {R['interval_verdict']['reading']}")

    # ------------------------------ the Phase 9C prior, propagated at the headline point
    print("\n=== 3. Phase 9C parameter prior propagated at the headline residual ===")
    cache = P9C / "design.npz"
    if not cache.exists():
        print(f"  MISSING {cache} - run scripts/phase9c_uncertainty.py first")
        return 1
    z = np.load(cache)
    theta_mc = np.concatenate([z["thetaA"], z["thetaB"]])
    print(f"  reusing Phase 9C's own {theta_mc.shape[0]} prior draws (seed {U.SEED}), "
          f"so the interval is directly comparable to the recorded ones")
    hb_idx = U._TRUTH_IDX
    mel_col = U.KEYS.index("melanin")
    # Phase 9C propagated the prior at the studio residual (the LOWER bracket) already.
    # The UPPER bracket never had one, and the report forbids quoting a gate MAE without
    # an interval, so it is propagated here too.
    R["uncertainty"] = {}
    for de in (HEADLINE, UPPER):
        print(f"  propagating at residual {de:.3f} ...", flush=True)
        f = np.empty(theta_mc.shape[0])
        bank = banks[de]
        for i, row in enumerate(theta_mc):
            if i % 512 == 0:
                print(f"    {i}/{theta_mc.shape[0]} ({time.time() - t0:.0f}s)", flush=True)
            lut = fwd.chroma_lut(U.theta_dict(row))
            f[i] = U.errors_from_lut(lut, lut[hb_idx], bank).mean()
        s = U.summarise(f)
        point = next(r["mae_g_dl"] for r in curve if r["residual_dE2000"] == de)
        s["point_estimate_at_nominal"] = point
        s["point_estimate_percentile"] = float(np.mean(f <= point) * 100)
        s["rule"] = (("ROBUST" if s["robust_at_2.0"] else "FRAGILE") + " at 2.0; "
                     + ("ROBUST" if s["robust_at_1.0"] else "FRAGILE") + " at 1.0")
        counts, edges = np.histogram(f, bins=60)
        s["histogram"] = {"counts": counts.tolist(), "edges": edges.tolist()}
        s["conditional_melanin_le_0.005"] = U.summarise(f[theta_mc[:, mel_col] <= 0.005])
        s["is_measured_residual"] = bool(de == UPPER)
        R["uncertainty"][str(de)] = s
        print(f"  residual {de:.3f}: median {s['median']:.3f}, 95% "
              f"[{s['p2.5']:.3f}, {s['p97.5']:.3f}]; VIABLE {s['fraction_below_1.0']:.3f} / "
              f"MARGINAL {s['fraction_in_1_2']:.3f} / NOT RECOVERABLE "
              f"{s['fraction_above_2.0']:.3f} - {s['rule']}")
    s = R["uncertainty"][str(HEADLINE)]
    R["headline_uncertainty"] = s

    # ------------------------------------------------------------ the boundary statement
    R["boundary_statement"] = {
        "named": "the guided-capture gap",
        "what_is_unmeasured": ("one phone, one session, a live framing and distance "
                               "overlay, and a quality gate that rejects blurred or "
                               "badly exposed frames before the shutter"),
        "why_it_cannot_be_closed_here": ("it requires capturing images under that "
                                         "protocol; CLAUDE.md section 3 forbids "
                                         "collecting data, permanently"),
        "bracketed_by": [LOWER, UPPER],
        "interpolated_band_at_nominal": U.band(point),
        "interpolated_band_under_the_prior": s["rule"],
        "status": "the project's PRIMARY future-work item"}

    R["elapsed_s"] = time.time() - t0
    (OUT / "guided_capture.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
    print(f"\nresults -> {OUT / 'guided_capture.json'} ({R['elapsed_s']:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
