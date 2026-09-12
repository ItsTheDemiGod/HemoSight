"""Progress readout for the detached selection-aware permutation run.

Reads only the checkpoint file, so it is safe to run at any time against a live run and
cannot disturb it. Reports what is complete, what the empirical p currently stands at,
and how long the remainder should take at the observed rate.

    .\\.venv\\Scripts\\python.exe scripts\\phase5_perm_status.py [--target 240]
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np

from hemosight.io import paths
from phase5_perm_extended import JSONL, read_checkpoint, summarise

OUT = paths.INTERIM / "phase5"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=240)
    ap.add_argument("--log", type=str, default=str(OUT / "perm_extended.log"))
    args = ap.parse_args()

    done = read_checkpoint()
    if not done:
        print(f"no permutations recorded yet at {JSONL}")
        print("if the run was just launched this is normal - one permutation is "
              "60 full CV runs")
        return 0

    harden = json.loads((OUT / "harden.json").read_text(encoding="utf-8"))
    real = float(harden["real_mae_seed_averaged"])
    draws = np.array(sorted(r["min_mae"] for r in done.values()))
    s = summarise(draws, real)

    secs = np.array([r.get("seconds", np.nan) for r in done.values()], dtype=float)
    secs = secs[np.isfinite(secs)]
    per = float(np.median(secs)) if len(secs) else float("nan")
    left = max(0, args.target - len(draws))

    mtime = JSONL.stat().st_mtime
    age = time.time() - mtime

    print(f"checkpoint      : {JSONL}")
    print(f"last written    : {time.strftime('%H:%M:%S', time.localtime(mtime))} "
          f"({age / 60:.1f} min ago)"
          + ("   <- STALLED? longer than one permutation" if age > 3 * per else ""))
    print(f"permutations    : {len(draws)} / {args.target}   ({left} remaining)")
    print(f"per permutation : {per / 60:.1f} min (median)")
    print(f"est. remaining  : {left * per / 3600:.2f} h")
    print()
    print(f"real MAE        : {real:.4f}  (seed-averaged, read from harden.json)")
    print(f"null            : mean {s['null_mean']:.4f}  SD {s['null_sd']:.4f}  "
          f"min {s['null_min']:.4f}")
    print(f"draws <= real   : {s['n_at_or_below_real']}")
    print(f"empirical p     : {s['p_empirical']:.5f}"
          + ("   (AT THE FLOOR 1/(n+1) - a bound, not a measurement)"
             if s["at_floor"] else "   (measured)"))
    z = s["z_parametric"]
    print(f"parametric z    : {z:.2f}" if z is not None
          else "parametric z    : n/a (needs >= 2 draws)")

    peaks = [r.get("peak_gpu_mb") for r in done.values() if r.get("peak_gpu_mb")]
    if peaks:
        print(f"peak GPU        : max {max(peaks):.0f} MB, median "
              f"{float(np.median(peaks)):.0f} MB per permutation")

    gaps = sorted(set(range(max(done) + 1)) - set(done))
    if gaps:
        print(f"missing indices : {gaps[:20]}{' ...' if len(gaps) > 20 else ''}")

    try:
        tail = open(args.log, encoding="utf-8",
                    errors="replace").read().splitlines()[-3:]
        print("\nlog tail:")
        for t in tail:
            print("  " + t)
    except OSError:
        print(f"\n(no log file at {args.log})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
