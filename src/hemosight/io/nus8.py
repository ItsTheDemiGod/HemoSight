"""NUS 8-camera colour-constancy benchmark reader.

This module is the ONLY place that opens the ground-truth .mat files. Everything
downstream reads the manifest CSV, so no other code needs scipy.io or has to know
the .mat layout.

Each per-camera .mat holds:
    darkness_level          scalar, per camera (black level)
    saturation_level        scalar, per camera
    all_image_names         (N,)   image stems
    groundtruth_illuminants (N,3)  RGB illuminant vector per image
    CC_coords               (N,4)  colorchecker bounding box, used to MASK OUT the
                                   chart before estimating an illuminant - failing
                                   to do so leaks the answer into the input.

Six of the eight cameras are extracted on this machine. SamsungNX2000's per-camera
groundtruth.mat/ directory is empty; paths.resolve_nus8_gt falls back to
raw_downloads/. See CLAUDE.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.io import loadmat

from . import paths


def read_camera(camera_dir: str) -> pd.DataFrame:
    """Return one row per image for a single NUS camera."""
    gt = loadmat(paths.resolve_nus8_gt(camera_dir), squeeze_me=True, struct_as_record=False)

    names = [str(n).strip() for n in np.atleast_1d(gt["all_image_names"])]
    illum = np.atleast_2d(np.asarray(gt["groundtruth_illuminants"], dtype=float))
    cc = np.atleast_2d(np.asarray(gt["CC_coords"]))
    dark = float(np.asarray(gt["darkness_level"]).ravel()[0])
    sat = float(np.asarray(gt["saturation_level"]).ravel()[0])

    if not (len(names) == len(illum) == len(cc)):
        raise ValueError(
            f"{camera_dir}: length mismatch names={len(names)} illum={len(illum)} cc={len(cc)}"
        )

    png_dir = paths.NUS8 / camera_dir / "png" / "PNG"
    mask_dir = paths.NUS8 / camera_dir / "mask" / "CHECKER"

    rows = []
    for i, name in enumerate(names):
        png = png_dir / f"{name}.PNG"
        if not png.exists():  # extraction casing varies
            alt = list(png_dir.glob(f"{name}.*"))
            png = alt[0] if alt else png
        mask = mask_dir / f"{name}_mask.txt"
        color = mask_dir / f"{name}_color.txt"
        r, g, b = illum[i]
        rows.append(
            {
                "image_id": f"nus8:{camera_dir}:{name}",
                "camera": camera_dir,
                "camera_short": paths.NUS8_CAMERAS[camera_dir],
                "png_path": str(png),
                "mask_path": str(mask) if mask.exists() else None,
                "color_path": str(color) if color.exists() else None,
                "illum_r": float(r),
                "illum_g": float(g),
                "illum_b": float(b),
                "darklevel": dark,
                "saturation_level": sat,
                # Stored as a compact string so the CSV stays one row per image.
                "cc_coords": ",".join(str(int(v)) for v in np.asarray(cc[i]).ravel()),
                "png_exists": png.exists(),
                "mask_exists": mask.exists(),
            }
        )
    return pd.DataFrame(rows)


def build_nus8_manifest() -> pd.DataFrame:
    """All six extracted cameras, concatenated."""
    frames = []
    for cam in paths.NUS8_CAMERAS:
        df = read_camera(cam)
        frames.append(df)
        print(
            f"  {cam:26s} {len(df):4d} images | png missing={int((~df.png_exists).sum()):3d} "
            f"| mask missing={int((~df.mask_exists).sum()):3d} "
            f"| dark={df.darklevel.iloc[0]:.0f} sat={df.saturation_level.iloc[0]:.0f}"
        )
    return pd.concat(frames, ignore_index=True)
