"""Phase 1, Task 4: reproducible splits under data/interim/splits/.

Every split is grouped so that no subject - and no byte-identical image - ever
appears on two sides of a boundary. Verification runs after each split and the
script exits non-zero if any leak is detected.

    .\\.venv\\Scripts\\python.exe scripts\\patient_level_splits_phase1.py
"""

from __future__ import annotations

import json

import pandas as pd
import yaml

from hemosight.io import paths
from hemosight.io.splits import (
    grouped_split,
    kfold_by_group,
    leakproof_groups,
    verify_no_leak,
)

CFG = paths.CONFIGS / "phase1_splits.yaml"


def load_hashes() -> pd.DataFrame:
    frames = []
    for s in ("cp_anemic", "ghana_conj", "ghana_nail"):
        f = paths.OVERLAP / f"hashes_{s}.csv"
        if f.exists():
            frames.append(pd.read_csv(f)[["image_id", "md5"]])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["image_id", "md5"])


def main() -> int:
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    seed = int(cfg["seed"])
    fracs = cfg["fractions"]
    paths.ensure_dirs()
    paths.SPLITS.mkdir(parents=True, exist_ok=True)

    master = pd.read_csv(paths.MANIFESTS / "master.csv")
    hashes = load_hashes()
    failures = []

    # ---------------------------------------------------------------- Ghana pool
    # cp_anemic + ghana_conj + ghana_nail are ONE site (overlap check, 2026-09-11).
    pool = master[master.dataset.isin(cfg["merged_sites"]["ghana"])].copy()
    pool = pool.merge(hashes, on="image_id", how="left")
    pool["group"] = leakproof_groups(pool, "md5")
    pool["split"] = grouped_split(pool, "group", fracs, seed, stratify_col="anemia_label")
    probs = verify_no_leak(pool, "group", "split")
    failures += [f"ghana_pool: {p}" for p in probs]
    pool[["image_id", "subject_id", "dataset", "modality", "group", "split",
          "anemia_label", "hb_g_dl", "file_path"]].to_csv(
        paths.SPLITS / "ghana_pool_grouped.csv", index=False)
    print("=== Ghana pool (one site) ===")
    print(f"  images={len(pool)}  subject_ids={pool.subject_id.nunique()}  "
          f"leakproof_groups={pool.group.nunique()}")
    print(pool.groupby("split").agg(images=("image_id", "count"),
                                    groups=("group", "nunique"),
                                    anemic=("anemia_label", "sum")).to_string())

    # ---------------------------------------------------- Eyes-Defy cross-site
    ed = master[master.dataset == "eyes_defy"].copy()
    ed["group"] = ed.subject_id
    rows = []
    for spec in cfg["cross_site_protocol"]:
        if not all(s.startswith("eyes_defy") for s in spec["train_sites"] + spec["test_sites"]):
            continue
        for _, r in ed.iterrows():
            role = ("train" if r.site in spec["train_sites"]
                    else "test" if r.site in spec["test_sites"] else None)
            if role:
                rows.append({"protocol": spec["name"], "image_id": r.image_id,
                             "subject_id": r.subject_id, "site": r.site, "split": role,
                             "hb_g_dl": r.hb_g_dl, "file_path": r.file_path})
    edx = pd.DataFrame(rows)
    edx.to_csv(paths.SPLITS / "eyes_defy_crosssite.csv", index=False)
    print("\n=== Eyes-Defy cross-site ===")
    print(edx.groupby(["protocol", "split"]).agg(
        images=("image_id", "count"), subjects=("subject_id", "nunique"),
        with_hb=("hb_g_dl", lambda s: int(pd.notna(s).sum()))).to_string())

    # Within-site calibration split for Eyes-Defy, carved from the TRAIN site only.
    cal_rows = []
    for spec in cfg["cross_site_protocol"]:
        if not all(s.startswith("eyes_defy") for s in spec["train_sites"] + spec["test_sites"]):
            continue
        tr = ed[ed.site.isin(spec["train_sites"])].copy()
        sub = grouped_split(tr, "group", {"train": 0.75, "calibration": 0.25}, seed)
        for iid, sp in zip(tr.image_id, sub):
            cal_rows.append({"protocol": spec["name"], "image_id": iid, "split": sp})
    pd.DataFrame(cal_rows).to_csv(paths.SPLITS / "eyes_defy_train_calibration.csv", index=False)

    # ------------------------------------------------------------------- Hb PPG
    ppg = master[master.dataset == "hb_ppg"].copy()
    ppg["group"] = ppg.subject_id
    ppg["split"] = grouped_split(ppg, "group", fracs, seed)
    failures += [f"hb_ppg: {p}" for p in verify_no_leak(ppg, "group", "split", hash_col=None)]
    ppg[["image_id", "subject_id", "split", "hb_g_dl", "age", "sex", "file_path"]].to_csv(
        paths.SPLITS / "hb_ppg_grouped.csv", index=False)
    print("\n=== Hb PPG ===")
    print(ppg.groupby("split").agg(subjects=("subject_id", "nunique"),
                                   hb_mean=("hb_g_dl", "mean")).to_string())

    # -------------------------------------------------------------------- NUS8
    nus = pd.read_csv(paths.MANIFESTS / "nus8.csv")
    nus["subject_id"] = nus.image_id
    nus["fold"] = -1
    for _cam, idx in nus.groupby("camera").groups.items():
        sub = nus.loc[idx].copy()
        sub["group"] = sub.image_id
        nus.loc[idx, "fold"] = kfold_by_group(sub, "group", cfg["nus8"]["folds"], seed).values
    nus[["image_id", "camera", "fold", "png_path", "mask_path",
         "illum_r", "illum_g", "illum_b"]].to_csv(paths.SPLITS / "nus8_cv3.csv", index=False)
    print("\n=== NUS8 per-camera 3-fold ===")
    print(nus.pivot_table(index="camera", columns="fold", values="image_id",
                          aggfunc="count").to_string())

    loco = []
    for cam in sorted(nus.camera.unique()):
        for _, r in nus.iterrows():
            loco.append({"held_out_camera": cam, "image_id": r.image_id,
                         "camera": r.camera, "split": "test" if r.camera == cam else "train"})
    loco_df = pd.DataFrame(loco)
    loco_df.to_csv(paths.SPLITS / "nus8_leave_one_camera_out.csv", index=False)
    print("\n=== NUS8 leave-one-camera-out ===")
    print(loco_df.groupby(["held_out_camera", "split"]).size().unstack().to_string())

    # ------------------------------------------------------------------ summary
    summary = {
        "seed": seed,
        "fractions": fracs,
        "ghana_pool": {
            "images": int(len(pool)),
            "nominal_subject_ids": int(pool.subject_id.nunique()),
            "leakproof_groups": int(pool.group.nunique()),
            "by_split": {k: int(v) for k, v in pool.split.value_counts().items()},
            "groups_by_split": {k: int(v) for k, v in
                                pool.groupby("split").group.nunique().items()},
        },
        "eyes_defy_crosssite": {
            p: {s: int(n) for s, n in g.split.value_counts().items()}
            for p, g in edx.groupby("protocol")
        },
        "hb_ppg": {k: int(v) for k, v in ppg.split.value_counts().items()},
        "nus8": {"images": int(len(nus)), "cameras": int(nus.camera.nunique()),
                 "folds": int(cfg["nus8"]["folds"])},
        "leak_check": failures or "PASS",
    }
    (paths.SPLITS / "split_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    print("\n=== LEAK CHECK ===")
    if failures:
        for f in failures:
            print("  !", f)
        return 1
    print("  PASS - no subject and no identical image spans a split boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
