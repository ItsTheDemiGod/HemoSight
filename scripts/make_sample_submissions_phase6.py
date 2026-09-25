"""Phase 6: materialise the Task 4 validation inputs as CSV files.

The validation script builds every submission in memory and never writes it, which is
fine for a test and useless for anyone who wants to click through the interface. This
writes the same frames to disk, using the SAME generator (`phase6_validate_harness.synth`)
under the same seeds, so a sample file is the input the validation actually measured
rather than a lookalike.

WHERE EACH FILE GOES, AND WHY IT IS NOT ALL ONE DIRECTORY.

  app/backend/sample_data/        SYNTHETIC submissions only. Generated from a seeded
                                  RNG, containing no real measurement of anything, so
                                  they are safe to track in git.

  data/interim/phase6/known_truth/   The two submissions derived from REAL data. These
                                  carry 41 PPG features and venous-blood haemoglobin for
                                  252 real subjects from Hb_PPG_Dataset, and file paths
                                  into the Ghana image pool. Eight of ten datasets in
                                  this project ship no licence file
                                  (reports/dataset_manifest.md), so their redistribution
                                  terms are unverified and committing dataset-derived
                                  measurements would be the same exposure that got
                                  reports/figures/ untracked in Phase 1.5. They are
                                  regenerated here instead, under data/, which is
                                  gitignored in full.

  data/interim/phase6/sample_images/  PNGs for the duplicate check, plus a zip for the
                                  archive-upload route. Binary, and
                                  tests/test_phase5.py::test_no_dataset_files_are_tracked_by_git
                                  fails the suite if a .png is ever tracked.

    .\\.venv\\Scripts\\python.exe scripts\\make_sample_submissions_phase6.py
"""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from hemosight.audit import load_predictions, run_audit
from hemosight.io import paths

sys.path.insert(0, str(paths.ROOT / "scripts"))
from validate_audit_harness_phase6 import FAULTS, case_seed, synth  # noqa: E402

SAMPLE = paths.ROOT / "app" / "backend" / "sample_data"
OUT = paths.INTERIM / "phase6"
IMAGES = OUT / "sample_images"
KNOWN = OUT / "known_truth"
N = 240

# Filenames are ordered so a directory listing reads as a suggested order of use.
SYNTHETIC = [
    ("02_clean_no_injected_fault.csv", "clean",
     "No fault. Every check should pass or decline; any FAIL here is a false positive."),
    ("03_fault_duplicates_across_split.csv", "duplicates_across_split",
     FAULTS["duplicates_across_split"][1]),
    ("04_fault_subject_in_train_and_test.csv", "subject_across_split",
     FAULTS["subject_across_split"][1]),
    ("05_fault_model_is_a_sex_classifier.csv", "demographic_proxy",
     FAULTS["demographic_proxy"][1]),
    ("06_fault_model_has_no_signal.csv", "no_signal",
     FAULTS["no_signal"][1]),
    ("07_fault_score_moves_with_the_seed.csv", "seed_unstable",
     FAULTS["seed_unstable"][1]),
    ("08_fault_effect_carried_by_8pct_of_subjects.csv", "few_subjects",
     FAULTS["few_subjects"][1]),
    ("09_control_genuine_signal.csv", "genuine_signal",
     "A real effect. The permutation test must NOT call this out."),
]


def build_mixed() -> pd.DataFrame:
    """One submission that exercises all eight checks and returns a mix of verdicts.

    Every other sample carries a single fault, which is right for testing a check and
    wrong for looking at the interface: a page of eight identical verdicts shows
    nothing about sorting, filtering or severity ordering. This one has images with a
    duplicate crossing the split, a subject on both sides, a second selection candidate
    so the selection-aware null is available, five seed replicates, demographics and
    input features - so every check has what it needs and the results page has
    something to order.
    """
    rng = np.random.default_rng(20260912)
    df = synth(N, rng, "genuine_signal", image_dir=IMAGES)

    # A second candidate the model was selected from -> selection-aware permutation.
    df["y_pred__runner_up"] = df["y_pred"] + rng.normal(0, 0.25, len(df))

    # Fault A: three train images copied byte-identically into the test side.
    extra = []
    for i in range(3):
        src = IMAGES / f"{df.subject_id.iloc[i]}.png"
        dst = IMAGES / f"mixed_leak{i}.png"
        dst.write_bytes(src.read_bytes())
        extra.append({**df.iloc[i].to_dict(), "subject_id": f"leak{i}",
                      "split": "test", "image_path": dst.name})

    # Fault B: five subjects appearing in both splits under their own ids.
    extra += [{**df.iloc[10 + i].to_dict(), "split": "test"} for i in range(5)]
    return pd.concat([df, pd.DataFrame(extra)], ignore_index=True)


def build_known_truth() -> list[tuple[str, pd.DataFrame, str]]:
    """The two real-data submissions whose verdicts are already on the record."""
    from ppg_hb_estimation_gate_phase4 import build_conditions, evaluate

    out = []

    # --- Phase 1: CP-AnemiC against the Ghana pool -------------------------
    frames = []
    for s in ("cp_anemic", "ghana_conj", "ghana_nail"):
        m = pd.read_csv(paths.MANIFESTS / f"{s}.csv")
        frames.append(pd.DataFrame({
            "subject_id": s + "::" + m.subject_id.astype(str),
            "y_true": np.arange(len(m), dtype=float) % 7 + 8.0,
            "y_pred": np.arange(len(m), dtype=float) % 7 + 8.0,
            "split": np.where(m.dataset == "cp_anemic", "test", "train"),
            "image_path": m.file_path,
        }))
    out.append(("phase1_ghana_pool_overlap.csv", pd.concat(frames, ignore_index=True),
                "Phase 1: 419 shared MD5 hashes, 1,708 ids -> 1,067 leak-proof groups. "
                "image_path points into data/raw, which is READ-ONLY; upload with no "
                "image directory and the paths resolve as absolute."))

    # --- Phase 4 / 4.5: the PPG feature model ------------------------------
    d = pd.read_csv(paths.INTERIM / "phase4" / "features.csv")
    d = d[np.isfinite(d.hb_g_dl)].reset_index(drop=True)
    y = d.hb_g_dl.to_numpy()
    cname, cols = next(iter(build_conditions(d).items()))
    X = d[cols].to_numpy(dtype=float)
    base = pd.DataFrame({
        "subject_id": d.subject_id.astype(str), "y_true": y,
        "age": d.age, "sex": np.where(d.sex.to_numpy() > 0.5, "M", "F"),
    })
    base = pd.concat([base, d[cols]], axis=1)

    ppg = base.copy()
    ppg.insert(2, "y_pred", np.array(evaluate(X, y, cname)["preds"], dtype=float))
    out.append(("phase4_ppg_features_only.csv", ppg,
                "Phase 4 Gate B: MAE 1.190 g/dL against sex alone at 0.831."))

    demo_cols = ["age", "sex", "height", "weight"]
    Xd = np.hstack([X, d[demo_cols].to_numpy(dtype=float)])
    both = base.copy()
    both.insert(2, "y_pred",
                np.array(evaluate(Xd, y, cname + "_plus_demographics")["preds"],
                         dtype=float))
    out.append(("phase4_ppg_plus_demographics.csv", both,
                "Phase 4 Task 3: MAE 0.824 g/dL, inside the pre-declared VIABLE band, "
                "and a sex classifier. The proxy probe is the check that says so."))
    return out


def main() -> int:
    SAMPLE.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    KNOWN.mkdir(parents=True, exist_ok=True)

    written: list[dict] = []

    # ---------------------------------------------------------- synthetic
    for name, kind, desc in SYNTHETIC:
        rng = np.random.default_rng(case_seed(kind))
        df = synth(N, rng, kind, image_dir=IMAGES)
        df.to_csv(SAMPLE / name, index=False)
        written.append({"file": name, "kind": kind, "rows": len(df),
                        "description": desc})
        print(f"  {name:48s} {len(df):5d} rows")

    mixed = build_mixed()
    mixed.to_csv(SAMPLE / "01_mixed_start_here.csv", index=False)
    written.insert(0, {
        "file": "01_mixed_start_here.csv", "kind": "mixed", "rows": len(mixed),
        "description": ("Several faults at once, and everything the optional checks "
                        "need. The one to upload first.")})
    print(f"  {'01_mixed_start_here.csv':48s} {len(mixed):5d} rows")

    # ------------------------------------------------------------- images
    zip_path = OUT / "sample_images.zip"
    pngs = sorted(IMAGES.glob("*.png"))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in pngs:
            z.write(p, p.name)
    print(f"\n  images: {len(pngs)} PNGs in {IMAGES}")
    print(f"  zip   : {zip_path} ({zip_path.stat().st_size / 1024:.0f} KB)")

    # -------------------------------------------------------- known truth
    print()
    for name, df, desc in build_known_truth():
        df.to_csv(KNOWN / name, index=False)
        written.append({"file": f"data/interim/phase6/known_truth/{name}",
                        "kind": "known-truth (real data, NOT tracked in git)",
                        "rows": len(df), "description": desc})
        print(f"  {name:48s} {len(df):5d} rows  -> {KNOWN}")

    # --------------------------------------------- measure, do not predict
    print("\n  running the harness on each synthetic sample to record what it returns")
    for w in written:
        if w["kind"].startswith("known-truth"):
            continue
        p = SAMPLE / w["file"]
        inp = load_predictions(p, image_dir=IMAGES)
        rep = run_audit(inp, options={"permutation": {"n_permutations": 400}})
        w["verdicts"] = {r["check_id"]: r["verdict"] for r in rep.results}
        w["counts"] = {k: rep.counts[k] for k in ("FAIL", "INSUFFICIENT_DATA", "PASS")}
        print(f"    {w['file']:48s} {w['counts']}")

    (SAMPLE / "manifest.json").write_text(
        json.dumps({"generated_by": "scripts/make_sample_submissions_phase6.py",
                    "n_subjects": N, "image_dir": str(IMAGES),
                    "image_zip": str(zip_path), "files": written},
                   indent=2), encoding="utf-8")
    write_readme(written, zip_path)
    print(f"\nsample data -> {SAMPLE}")
    return 0


def write_readme(written: list[dict], zip_path: Path) -> None:
    L = ["# Sample submissions for HemoSight Audit", "",
         "Generated by `scripts/make_sample_submissions_phase6.py`. Every file here is "
         "**synthetic** - a seeded RNG, no real measurement of anything - which is why "
         "it can be tracked in git.", "",
         "Two further submissions, derived from this project's REAL data and carrying "
         "verdicts already on the record in CLAUDE.md, are written to "
         "`data/interim/phase6/known_truth/` instead. They hold venous-blood "
         "haemoglobin and PPG features for 252 real subjects; eight of ten datasets in "
         "this project ship no licence file, so dataset-derived measurements are not "
         "committed. Run the script to regenerate them.", "",
         "## Images", "",
         f"The duplicate check needs pixels. {zip_path.name} and the loose PNGs live in "
         "`data/interim/phase6/` (binary artefacts are never tracked). On the upload "
         "screen either point the directory field at:", "",
         "```", str(zip_path.parent / "sample_images"), "```", "",
         f"or upload the archive `{zip_path}`.", "",
         "## Files", "",
         "| file | rows | what it contains | checks that do not pass |",
         "| --- | --- | --- | --- |"]
    for w in written:
        v = w.get("verdicts")
        if v:
            bad = [f"`{k}` {x.replace('_', ' ').lower()}"
                   for k, x in v.items() if x != "PASS"]
            cell = ", ".join(bad) if bad else "none - all eight pass"
        else:
            cell = "see CLAUDE.md"
        L.append(f"| `{w['file']}` | {w['rows']} | {w['description']} | {cell} |")
    L += ["", "Those verdicts were MEASURED by running the harness over each file, not "
          "predicted. They assume the image directory above is supplied; without it the "
          "duplicate check returns INSUFFICIENT DATA rather than a verdict.", "",
          "Three things in that table are worth reading carefully rather than treating "
          "as noise:", "",
          "- **A fault often trips more than one check, and that is correct.** "
          "Byte-identical images copied across the split (file 03) break the content "
          "axis of split integrity as well, because the leak-proof grouping joins "
          "subject ids to content hashes. A subject duplicated across the split (file "
          "04) points at the same image file twice, so the duplicate check sees it too. "
          "Neither is a spurious hit; they are the same fault seen from two directions.",
          "- **File 09 carries a real effect and still fails the demographic "
          "baseline.** On this seed, sex alone edges past the model. That is the "
          "borderline behaviour measured in `reports/phase6_audit_harness.md` section "
          "7.3: checks 3 and 7 compare point estimates with no uncertainty interval, so "
          "near the boundary the verdict moves with the sample. The check says so in "
          "its own explanation when the margin is narrow.",
          "- **File 06 returns INSUFFICIENT DATA from the proxy probe.** A model with "
          "no signal has no apparent skill for a demographic variable to account for, "
          "so the question has no answer rather than a negative one. That is the "
          "third verdict doing its job.", ""]
    (SAMPLE / "README.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
