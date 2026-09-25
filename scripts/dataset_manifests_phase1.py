"""Phase 1, Task 3: build one manifest per dataset plus a master manifest.

Writes to data/interim/manifests/. Reads data/raw/ only.

    .\\.venv\\Scripts\\python.exe scripts\\dataset_manifests_phase1.py
"""

from __future__ import annotations

import time

import pandas as pd

from hemosight.io import paths
from hemosight.io.manifests import ALL_COLUMNS, BUILDERS


def main() -> int:
    paths.ensure_dirs()
    frames = {}
    for name, build in BUILDERS.items():
        t0 = time.time()
        print(f"building {name} ...", end=" ", flush=True)
        df = build()
        out = paths.MANIFESTS / f"{name}.csv"
        paths.assert_raw_readonly(out)
        df.to_csv(out, index=False)
        frames[name] = df
        print(
            f"{len(df):6d} rows | {df.subject_id.nunique():5d} subjects "
            f"| hb={df.hb_g_dl.notna().sum():5d} | {time.time()-t0:5.1f}s -> {out.name}"
        )

    master = pd.concat(frames.values(), ignore_index=True)[ALL_COLUMNS]
    out = paths.MANIFESTS / "master.csv"
    master.to_csv(out, index=False)

    print("\n=== MASTER ===")
    print(f"rows={len(master)}  subjects={master.subject_id.nunique()}")
    print("\nby dataset:")
    g = master.groupby("dataset").agg(
        images=("image_id", "count"),
        subjects=("subject_id", "nunique"),
        with_hb=("hb_g_dl", lambda s: int(s.notna().sum())),
        hb_min=("hb_g_dl", "min"),
        hb_max=("hb_g_dl", "max"),
    )
    print(g.to_string())

    print("\nsubject_id provenance:")
    print(master.groupby(["dataset", "subject_id_source"]).size().to_string())

    print("\nmodality:")
    print(master.modality.value_counts().to_string())

    # Integrity checks that must hold before anything downstream trusts the manifest.
    problems = []
    if master.image_id.duplicated().any():
        d = master.image_id[master.image_id.duplicated()].head().tolist()
        problems.append(f"duplicate image_id: {d}")
    if master.file_path.duplicated().any():
        problems.append(f"duplicate file_path: {int(master.file_path.duplicated().sum())}")
    hb = master.hb_g_dl.dropna()
    if len(hb) and not ((hb > 1) & (hb < 25)).all():
        problems.append(f"hb_g_dl outside 1-25 g/dL: {hb[(hb <= 1) | (hb >= 25)].tolist()[:5]}")
    unparsed = int(master.notes.fillna("").str.contains("UNPARSED_FILENAME").sum())
    if unparsed:
        problems.append(f"unparsed filenames: {unparsed}")

    print("\nintegrity:", "OK" if not problems else "PROBLEMS")
    for p in problems:
        print("  !", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
