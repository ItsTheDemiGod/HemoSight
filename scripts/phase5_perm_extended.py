"""Phase 5, TASK 1 (extended): drive the selection-aware permutation null to n >= 240.

WHY THIS EXISTS. The reported empirical p for the project's only positive claim is
0.0164, which is the FLOOR 1/(60+1) at n=60 permutations, not a measured value - zero of
the 60 null draws reached the real MAE, so the test could only report the smallest
number the sample size allows. At n=240 the floor drops to 0.0041, so if the real value
still sits below every draw the bound is four times tighter, and if a draw finally lands
at or below it the p becomes a measurement rather than a bound. Either outcome is a
better statement than the one on record.

WHAT THE NULL IS. Each permutation shuffles haemoglobin ACROSS SUBJECTS and then re-runs
the FULL best-of-six selection - three architectures x two channel sets, each with its
own complete 10-fold subject-disjoint CV - taking the minimum MAE. That is the correct
null for a claim produced by a best-of-six selection: it prices in the selection step
rather than correcting for it afterwards. It costs 60 full CV runs per permutation.

RESUMABILITY. A permutation's shuffled labels are drawn from `default_rng(PERM_SEED + i)`
and depend on NOTHING ELSE - no sequentially consumed generator, no prior permutation.
Permutation i is therefore the same experiment whether it runs first or after a restart,
which is what makes the JSONL checkpoint sound rather than merely convenient. Each
completed permutation is appended and fsynced immediately; a restart reads the file,
skips the indices already present and continues.

    .\\.venv\\Scripts\\python.exe -u scripts\\phase5_perm_extended.py --target 240
    .\\.venv\\Scripts\\python.exe -u scripts\\phase5_perm_extended.py --limit 1   # probe

This script NEVER edits the reported result. It writes only its own JSONL; consolidation
into harden.json is a separate, deliberate step once the run is complete.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import time

import numpy as np
import psutil
import torch

from hemosight.io import paths
from hemosight.ppg import cv

OUT = paths.INTERIM / "phase5"
JSONL = OUT / "perm_selection_aware.jsonl"
SUMMARY = OUT / "perm_selection_aware_summary.json"
PERM_SEED = 770000          # namespace for the label shuffles; see RESUMABILITY above
TRAIN_SEED_BASE = cv.SEED + 5000


def permuted_labels(y: np.ndarray, i: int) -> np.ndarray:
    """Permutation i's shuffled haemoglobin vector. A pure function of (y, i)."""
    return np.random.default_rng(PERM_SEED + i).permutation(y)


def read_checkpoint(path=JSONL) -> dict[int, dict]:
    """Completed permutations, keyed by index. Tolerates a torn last line."""
    done: dict[int, dict] = {}
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue                      # a partial line from a killed process
        if "i" in r and "min_mae" in r:
            done[int(r["i"])] = r
    return done


def append(path, rec: dict) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, default=float) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def summarise(draws: np.ndarray, real: float) -> dict:
    n = len(draws)
    if n == 0:
        return {"n": 0, "real_mae": real}
    at_or_below = int(np.sum(draws <= real))
    return {
        "n": n,
        "null_mean": float(draws.mean()),
        "null_sd": float(draws.std()),
        "null_min": float(draws.min()),
        "real_mae": real,
        "n_at_or_below_real": at_or_below,
        "p_empirical": float((at_or_below + 1) / (n + 1)),
        "p_floor": float(1 / (n + 1)),
        "at_floor": at_or_below == 0,
        "z_parametric": (float((real - draws.mean()) / max(draws.std(), 1e-12))
                         if n > 1 else None),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=240,
                    help="total permutations wanted, counting those already on disk")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after this many NEW permutations (0 = no limit)")
    ap.add_argument("--train-batch", type=int, default=cv.TRAIN_BATCH)
    ap.add_argument("--eval-batch", type=int, default=cv.EVAL_BATCH)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = psutil.Process()

    vm = psutil.virtual_memory()
    print(f"host={platform.node()} pid={os.getpid()} device={dev} "
          f"ram_total={vm.total / 1e9:.1f} GB ram_available={vm.available / 1e9:.1f} GB",
          flush=True)
    if dev == "cuda":
        props = torch.cuda.get_device_properties(0)
        print(f"gpu={props.name} total={props.total_memory / 1e6:.0f} MB "
              f"allocated_at_start={torch.cuda.memory_allocated() / 1e6:.1f} MB",
              flush=True)
    print(f"train_batch={args.train_batch} eval_batch={args.eval_batch}", flush=True)

    # The real statistic is NOT recomputed here. It is read from the completed hardening
    # run so this script cannot, by construction, move the number it is testing against.
    harden = json.loads((OUT / "harden.json").read_text(encoding="utf-8"))
    real = float(harden["real_mae_seed_averaged"])
    real_single = float(harden["seed_stability"]["mean"])
    print(f"real MAE (seed-averaged) = {real:.4f}   "
          f"(mean over 10 single seeds = {real_single:.4f})", flush=True)

    data = cv.load_data()
    X0, sid0, subs0, y0 = data[cv.SELECTED[1]]
    print(f"subjects={len(subs0)}  windows(660)={len(X0)}  "
          f"windows(four)={len(data['four'][0])}", flush=True)

    done = read_checkpoint()
    print(f"checkpoint: {len(done)} permutations already complete -> {JSONL}",
          flush=True)

    todo = [i for i in range(args.target) if i not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"running {len(todo)} permutations, {len(cv.CONFIGS)} configs x "
          f"{cv.N_SPLITS} folds each\n", flush=True)

    t_start = time.time()
    for k, i in enumerate(todo):
        if dev == "cuda":
            torch.cuda.reset_peak_memory_stats()
        t0 = time.time()
        yp = permuted_labels(y0, i)
        by_sub = {int(s): float(v) for s, v in zip(subs0, yp)}
        per_config = {}
        for arch, tag in cv.CONFIGS:
            Xc, sidc, subc, _ = data[tag]
            yc = np.array([by_sub.get(int(s), np.nan) for s in subc])
            ok = np.isfinite(yc)
            sel = np.isin(sidc, subc[ok])
            pred = cv.fit_predict(arch, Xc[sel], sidc[sel], subc[ok], yc[ok], dev,
                                  TRAIN_SEED_BASE + i,
                                  train_batch=args.train_batch,
                                  eval_batch=args.eval_batch)
            per_config[f"{arch}_{tag}"] = float(np.mean(np.abs(pred - yc[ok])))
            del Xc, sidc, subc, yc, ok, sel, pred
            cv.free(dev)
        rec = {
            "i": i,
            "min_mae": float(min(per_config.values())),
            "argmin": min(per_config, key=per_config.get),
            "per_config": per_config,
            "seconds": round(time.time() - t0, 1),
            "peak_gpu_mb": round(cv.peak_mb(), 1),
            "reserved_gpu_mb": round(cv.reserved_mb(), 1),
            # Host RSS is recorded too: the cause of the kill was never confirmed to be
            # GPU memory, and a host-side leak would show here as a rising trend.
            "host_rss_mb": round(proc.memory_info().rss / 1e6, 1),
            "train_batch": args.train_batch,
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        append(JSONL, rec)
        done[i] = rec

        draws = np.array(sorted(r["min_mae"] for r in done.values()))
        s = summarise(draws, real)
        rate = (time.time() - t_start) / (k + 1)
        left = len(todo) - (k + 1)
        print(f"[{len(draws)}/{args.target}] perm {i}: min={rec['min_mae']:.4f} "
              f"({rec['argmin']})  null_mean={s['null_mean']:.4f}  "
              f"p_emp={s['p_empirical']:.5f}  peak={rec['peak_gpu_mb']:.0f}MB  "
              f"{rec['seconds']:.0f}s  eta={left * rate / 3600:.2f}h", flush=True)

    draws = np.array(sorted(r["min_mae"] for r in read_checkpoint().values()))
    final = summarise(draws, real)
    if len(draws):
        final["real_mae_single_seed_mean"] = real_single
        final["p_empirical_vs_single_seed_real"] = float(
            (int(np.sum(draws <= real_single)) + 1) / (len(draws) + 1))
    SUMMARY.write_text(json.dumps(final, indent=2, default=float), encoding="utf-8")
    print("\n" + json.dumps(final, indent=2, default=float), flush=True)
    print(f"\nelapsed {(time.time() - t_start) / 3600:.2f} h", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
