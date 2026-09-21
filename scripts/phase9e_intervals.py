"""Phase 9E Part C - the intervals the cross-site rates were quoted without.

Phase 9D established that the magnitude of the cross-site penalty is poorly pinned down.
The reports nevertheless quote `italy_to_india` specificity 0.963 and `india_to_italy`
specificity 0.418 as bare numbers, because Phase 9A stored a CI for the cross-site
*sensitivity* only. This script computes the missing ones so the language pass has
something to attach, and so no cross-site rate is quoted bare anywhere.

**Nothing in Phase 9A is modified.** Its calls are rebuilt from the per-subject
predictions and the operating point it recorded, and the script asserts it reproduces
Phase 9A's point estimates and its recorded sensitivity intervals before reporting
anything new. The bootstrap is the identical scheme - 2,000 subject-level resamples,
seed 20260911.

    .\\.venv\\Scripts\\python.exe scripts\\phase9e_intervals.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hemosight.evaluation import screening as scr       # noqa: E402
from hemosight.io import paths                          # noqa: E402
from phase9a_screening import XS_PRED                   # noqa: E402

OUT = paths.INTERIM / "phase9e"
P9A = paths.INTERIM / "phase9a" / "screening.json"
TOL = 1e-9
CI_TOL = 5e-3


def rate_ci(truth: np.ndarray, call: np.ndarray, metric: str) -> dict:
    """Percentile CI on one rate, Phase 9A's own scheme."""
    ci = scr.bootstrap_ci(truth, call,
                          lambda t, c: scr.screening_metrics(t, c)[metric])
    return {"point": float(scr.screening_metrics(truth, call)[metric]),
            "lo": ci["lo"], "hi": ci["hi"], "n_boot": ci["n_boot"],
            "skipped": ci["skipped"]}


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    p9a = json.loads(P9A.read_text(encoding="utf-8"))["imaging_cross_site"]["directions"]
    xs = pd.read_csv(XS_PRED)

    R: dict = {"why": ("Phase 9A stored a CI for the cross-site sensitivity only; these "
                       "are the intervals for every other cross-site rate the reports "
                       "quote, so none is quoted bare"),
               "bootstrap": {"n_boot": scr.N_BOOT, "seed": scr.SEED,
                             "scheme": "subject-level percentile, identical to Phase 9A"},
               "reproduction": {}, "directions": {}}

    for direction, part in xs.groupby("direction"):
        part = part[part["split"] == "test"].reset_index(drop=True)
        yy = part["y_true"].to_numpy(float)
        mm = (part["sex"].astype(str).str.strip().str.upper() == "M").to_numpy()
        aa = part["age"].to_numpy(float)
        truth = yy < scr.who_threshold(mm, aa)
        rec = p9a[direction]["cnn"]
        call = part["y_pred"].to_numpy(float) < rec["cut_chosen_on_train_site_g_dl"]

        # --- reproduce Phase 9A before adding anything
        m = scr.screening_metrics(truth, call)
        for k in ("tp", "fp", "tn", "fn", "sensitivity", "specificity",
                  "n_anaemic_flagged", "referral_rate"):
            assert abs(float(m[k]) - float(rec[k])) < TOL, (direction, k, m[k], rec[k])
        sens = rate_ci(truth, call, "sensitivity")
        for i, side in enumerate(("lo", "hi")):
            assert abs(sens[side] - rec["sensitivity_ci"][i]) < CI_TOL, (direction, side)
        R["reproduction"][direction] = {
            "confusion_and_rates": "exact", "sensitivity_ci": "reproduced",
            "recorded_sensitivity_ci": rec["sensitivity_ci"],
            "reproduced_sensitivity_ci": [sens["lo"], sens["hi"]]}
        print(f"  {direction}: reproduced Phase 9A exactly "
              f"(tp {m['tp']}, fp {m['fp']}, tn {m['tn']}, fn {m['fn']}; "
              f"sens CI [{sens['lo']:.3f},{sens['hi']:.3f}])")

        d = {"n_test": int(len(truth)), "n_anaemic": int(truth.sum()),
             "n_non_anaemic": int((~truth).sum()),
             "operating_point_g_dl": float(rec["cut_chosen_on_train_site_g_dl"]),
             "counts": {k: int(m[k]) for k in ("tp", "fp", "tn", "fn")},
             "sensitivity": sens,
             "specificity": rate_ci(truth, call, "specificity"),
             "ppv": rate_ci(truth, call, "ppv"),
             "referral_rate": rate_ci(truth, call, "referral_rate")}
        # the count statement, which needs no interval at all
        d["observed_counts_statement"] = (
            f"flagged {m['tp']} of {int(truth.sum())} anaemic subjects and "
            f"{m['fp']} of {int((~truth).sum())} non-anaemic subjects")
        d["preferred_wording"] = (
            f"flagged {m['tp']} of {int(truth.sum())} anaemic subjects "
            f"(sensitivity {m['sensitivity']:.3f}, 95% CI "
            f"[{sens['lo']:.3f}, {sens['hi']:.3f}])")
        R["directions"][direction] = d
        print(f"    specificity {d['specificity']['point']:.3f} "
              f"[{d['specificity']['lo']:.3f}, {d['specificity']['hi']:.3f}]  "
              f"on {d['n_non_anaemic']} non-anaemic subjects")

    R["elapsed_s"] = time.time() - t0
    (OUT / "cross_site_intervals.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
    print(f"\nresults -> {OUT / 'cross_site_intervals.json'} ({R['elapsed_s']:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
