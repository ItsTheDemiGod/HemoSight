"""Single entry point: reproduce the entire HemoSight result set from raw data.

    .\\.venv\\Scripts\\python.exe scripts\\reproduce_all.py            # everything
    .\\.venv\\Scripts\\python.exe scripts\\reproduce_all.py --fast     # skip slow stages
    .\\.venv\\Scripts\\python.exe scripts\\reproduce_all.py --list     # show the plan

Every stage is deterministic given the frozen seed in `configs/phase1_splits.yaml`
(20260911), with two documented exceptions noted in the STAGES table below.

RUNTIME on the reference machine (RTX 4060 8 GB, Python 3.12):
    fast subset   ~10 minutes   (MEASURED: 22/22 stages in 10.3 min)
    full          ~12 hours, dominated by the Phase 5 permutation tests (270 CV runs)

REPRODUCTION FIDELITY, verified after a clean --fast run:
    Phase 3 gate MAE          3.893  exact
    Phase 4 four-wavelength   1.190  exact
    Phase 4 sex-alone         0.831  exact
    Phase 4.5 permutation p   0.978  exact
    Phase 2 yellowing 10%     4.40   exact
    Phase 4.5 best deep MAE   1.111 vs 1.113 reported - within the measured seed SD
                              (0.0069), the only stage that does not reproduce bit-exact

Nothing here writes to `data/raw/`, which is read-only throughout.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass

from hemosight.io import paths


@dataclass
class Stage:
    name: str
    script: str
    minutes: float          # approximate, reference machine
    slow: bool = False
    note: str = ""


STAGES = [
    Stage("Phase 1  manifests", "phase1_manifests.py", 1.5,
          note="reads data/raw only; deterministic"),
    Stage("Phase 1  overlap check", "phase1_overlap.py", 12, slow=True,
          note="MD5/pHash/dHash + GPU embeddings; caches to data/interim/overlap"),
    Stage("Phase 1  splits", "phase1_splits.py", 0.2,
          note="seed 20260911; leak check fails the script on violation"),
    Stage("Phase 1.5 label arbitration", "phase1_5_label_arbitration.py", 0.3,
          note="writes hb_label_trusted into every manifest"),
    Stage("Phase 1.5 original search", "phase1_5_search_originals.py", 6, slow=True,
          note="full scan of 9,450 images + RAR5 header parse"),
    Stage("Phase 1  audit report", "phase1_audit.py", 1.5),
    Stage("Phase 1  summary report", "phase1_summary.py", 0.2),
    Stage("Phase 1  figures", "phase1_figures.py", 0.5,
          note="writes reports/figures (gitignored: dataset-derived pixels)"),
    Stage("Phase 1.5 remediation report", "phase1_5_remediation_report.py", 0.1),
    Stage("Phase 2  segmentation training", "phase2_train_segmentation.py", 160, slow=True,
          note="NON-DETERMINISTIC: cuDNN autotune. Sclera IoU reproduces to ~0.005"),
    Stage("Phase 2  N1a nus8", "phase2_nus8_n1a.py", 90, slow=True,
          note="deterministic; classical baselines over 1,265 16-bit PNGs"),
    Stage("Phase 2  N1b self-consistency", "phase2_n1b_selfconsistency.py", 50, slow=True),
    Stage("Phase 2  segmentation eval", "phase2_eval_segmentation.py", 25, slow=True),
    Stage("Phase 2  sensitivity", "phase2_sensitivity.py", 5),
    Stage("Phase 2  report + figures", "phase2_report.py", 0.2),
    Stage("Phase 2  figures", "phase2_figures.py", 0.3),
    Stage("Phase 2.5 census", "phase2_5_census.py", 12, slow=True),
    Stage("Phase 2.5 evaluation", "phase2_5_evaluate.py", 67, slow=True),
    Stage("Phase 2.5 report", "phase2_5_report.py", 0.1),
    Stage("Phase 2.5 figures", "phase2_5_figures.py", 0.2),
    Stage("Phase 3  Task 0 gate", "phase3_task0_gate.py", 3,
          note="deterministic; uses sourced optical constants"),
    Stage("Phase 3  empirical signal", "phase3_empirical_signal.py", 1.5,
          note="MEASURES the colour-per-g/dL signal from 215 Eyes-Defy subjects; deterministic (seed 20260911); replaces a hard-coded 0.70 (Phase 6.5)"),
    Stage("Phase 3  report", "phase3_report.py", 0.1),
    Stage("Phase 3.5 cancellation", "phase3_5_task1_cancellation.py", 34, slow=True),
    Stage("Phase 3.5 stability", "phase3_5_task3_stability.py", 20, slow=True),
    Stage("Phase 3.5 report", "phase3_5_report.py", 0.1),
    Stage("Phase 4  Gate A", "phase4_gate_a.py", 0.5,
          note="caches data/interim/phase4/features.csv"),
    Stage("Phase 4  Gate B + baselines", "phase4_gate_b.py", 0.5),
    Stage("Phase 4  report", "phase4_report.py", 0.1),
    Stage("Phase 4.5 deep sweep", "phase4_5_deep.py", 3,
          note="NON-DETERMINISTIC: cuDNN. MAE reproduces to ~0.01 (seed SD measured)"),
    Stage("Phase 4.5 ceiling", "phase4_5_ceiling.py", 4),
    Stage("Phase 4.5 report", "phase4_5_report.py", 0.1),
    Stage("Phase 5  hardening", "phase5_harden.py", 220, slow=True,
          note="260 permutation runs; the dominant cost of a full reproduction"),
    Stage("Phase 5  final results", "phase5_final_report.py", 0.2),
    # Phase 6 is CPU and disk only. The harness validation is included because it is a
    # RESULT - the harness's own sensitivity and false-positive rate - and results in
    # this project are reproducible or they are not reported. The extended Phase 5
    # permutation run is deliberately NOT a stage: it is a ~10 h GPU job whose figure
    # has not been consolidated, and adding it before then would misrepresent the plan.
    Stage("Phase 6  sample submissions", "phase6_make_sample_data.py", 0.6,
          note="regenerates app/backend/sample_data (tracked, synthetic) and the "
               "real-data known-truth inputs under data/ (not tracked)"),
    Stage("Phase 6  audit harness validation", "phase6_validate_harness.py", 1.2,
          note="MEASURED 58 s: hashes 9,232 images, injects 7 known faults, runs 20 "
               "clean replicates; CPU and disk only"),
    Stage("Phase 6  audit harness report", "phase6_report.py", 0.2),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="skip stages marked slow")
    ap.add_argument("--list", action="store_true", help="print the plan and exit")
    ap.add_argument("--from", dest="start", default=None, help="resume at this stage name")
    args = ap.parse_args()

    stages = [s for s in STAGES if not (args.fast and s.slow)]
    if args.start:
        idx = next((i for i, s in enumerate(stages) if args.start.lower() in s.name.lower()), 0)
        stages = stages[idx:]

    total = sum(s.minutes for s in stages)
    print(f"HemoSight reproduction: {len(stages)} stages, ~{total:.0f} min "
          f"({total/60:.1f} h) on the reference machine")
    print(f"repo root : {paths.ROOT}")
    print(f"raw data  : {paths.RAW}  (READ-ONLY)\n")
    if args.list:
        for s in stages:
            print(f"  {'[slow] ' if s.slow else '       '}{s.name:34s} "
                  f"{s.minutes:6.1f} min  {s.note}")
        return 0

    t0 = time.time()
    failed = []
    for i, s in enumerate(stages, 1):
        print(f"[{i}/{len(stages)}] {s.name} ... ", end="", flush=True)
        st = time.time()
        r = subprocess.run([sys.executable, str(paths.ROOT / "scripts" / s.script)],
                           capture_output=True, text=True)
        el = time.time() - st
        if r.returncode == 0:
            print(f"ok ({el/60:.1f} min)")
        else:
            print(f"FAILED ({el/60:.1f} min)")
            print("   " + (r.stderr.strip().splitlines() or ["<no stderr>"])[-1])
            failed.append(s.name)
    print(f"\ntotal {(time.time()-t0)/60:.1f} min; "
          f"{len(stages)-len(failed)}/{len(stages)} stages ok")
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
