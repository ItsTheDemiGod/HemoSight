"""Phase 5: consolidate the completed extended permutation run into harden.json.

A SEPARATE, DELIBERATE STEP, and deliberately not part of the runner. The runner reads
harden.json for the real MAE and writes only its own files, so it cannot move the number
it is testing against; `tests/test_phase5.py::test_extended_run_does_not_alter_the_
reported_p` enforces that. Consolidation is this script, run by hand once the run has
actually finished.

Nothing is deleted. The n=60 result stays in place with a pointer to what superseded it,
and the stale n=41 block from the killed first attempt is replaced with a note recording
why it was discarded rather than quietly overwritten.

    .\\.venv\\Scripts\\python.exe scripts\\permutation_consolidate_phase5.py [--apply]
"""

from __future__ import annotations

import argparse
import json
import time

from hemosight.io import paths

OUT = paths.INTERIM / "phase5"
HARDEN = OUT / "harden.json"
SUMMARY = OUT / "perm_selection_aware_summary.json"
TARGET = 240


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write harden.json; without it, print and change nothing")
    args = ap.parse_args()

    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    h = json.loads(HARDEN.read_text(encoding="utf-8"))

    if s["n"] < TARGET:
        print(f"REFUSING: the run is at {s['n']} of {TARGET} permutations. "
              "Consolidate only a finished run.")
        return 1
    if abs(s["real_mae"] - h["real_mae_seed_averaged"]) > 1e-9:
        print("REFUSING: the summary was computed against a different real MAE "
              f"({s['real_mae']} vs {h['real_mae_seed_averaged']}).")
        return 1

    old = h.get("permutation_selection_aware", {})
    new = dict(s)
    new["note"] = (
        "Extended run, 240 permutations, each re-running the full best-of-six selection "
        "(60 complete 10-fold CVs per permutation). Supersedes the n=60 result below, "
        "which is retained. This REPLACES a stale n=41 block from the first attempt, "
        "which was killed by an out-of-memory condition and whose draws were discarded "
        "rather than reused because its shuffles came from one sequentially consumed "
        "generator and could not be reproduced (DECISION LOG 2026-09-12).")
    new["elapsed_hours"] = 10.65

    h["permutation_selection_aware_extended"] = new
    h["permutation_selection_aware"] = {
        **old,
        "superseded_by": "permutation_selection_aware_extended",
        "note": ("The figure of record until 2026-09-12. Retained, not deleted: it is "
                 "what every result before that date was reported against."),
    }
    h["consolidated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    print(f"real MAE (unchanged)        {s['real_mae']:.6f}")
    print(f"n                           {old.get('n')} -> {s['n']}")
    print(f"null mean                   {old.get('null_mean'):.4f} -> {s['null_mean']:.4f}")
    print(f"null SD                     {old.get('null_sd'):.4f} -> {s['null_sd']:.4f}")
    print(f"null min                    {s['null_min']:.4f}")
    print(f"draws at or below real      {s['n_at_or_below_real']}")
    print(f"empirical p                 {old.get('p_empirical'):.5f} -> {s['p_empirical']:.5f}")
    print(f"p floor 1/(n+1)             {s['p_floor']:.5f}")
    print(f"still AT THE FLOOR?         {s['at_floor']}")
    print(f"parametric z                {old.get('z_parametric'):.2f} -> {s['z_parametric']:.2f}")

    if not args.apply:
        print("\ndry run; pass --apply to write harden.json")
        return 0
    HARDEN.write_text(json.dumps(h, indent=2, default=float), encoding="utf-8")
    print(f"\nwritten -> {HARDEN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
