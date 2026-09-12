"""Attaching pixels to rows, once, for every check that needs them.

Two checks read images - duplicate detection and split integrity - and hashing a
corpus twice in one audit run is the kind of waste that makes a tool unusable on
anything real. Both go through here, and the result is cached per run.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from hemosight.io.hashing import dhash, md5_file, phash

from .contract import AuditInput

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def resolve_paths(inp: AuditInput) -> tuple[pd.DataFrame, list[str]]:
    """Attach a file path to every row it can be attached to, honestly.

    Two routes. An explicit image_path column is authoritative. A bare directory is
    matched by filename stem against subject_id, which is a guess - so the match rate
    is reported rather than assumed, and a caller can decline on a poor one instead of
    auditing a third of the data and calling it the whole.
    """
    notes: list[str] = []
    df = inp.df.copy()

    if inp.has("image_path"):
        base = inp.image_dir
        paths = []
        for p in df["image_path"].astype(str):
            q = Path(p)
            if not q.is_absolute() and base is not None:
                q = base / p
            paths.append(str(q) if q.exists() else "")
        df["_path"] = paths
        found = int((df["_path"] != "").sum())
        notes.append(f"image_path column: {found}/{len(df)} files found on disk")
        return df[df["_path"] != ""].reset_index(drop=True), notes

    if inp.image_dir is None:
        return df.iloc[0:0].assign(_path=pd.Series(dtype=str)), [
            "no image_path column and no image directory"]

    files = [p for p in Path(inp.image_dir).rglob("*")
             if p.suffix.lower() in IMAGE_SUFFIXES]
    by_stem: dict[str, list[Path]] = {}
    for p in files:
        by_stem.setdefault(p.stem, []).append(p)
    rows = []
    for r in df.itertuples(index=False):
        d = dict(r._asdict())
        for p in by_stem.get(str(d["subject_id"]), []):
            rows.append({**d, "_path": str(p)})
    matched = pd.DataFrame(rows)
    n_sub = 0 if matched.empty else int(matched.subject_id.nunique())
    notes.append(f"directory scan: {len(files)} image files, matched to {n_sub} of "
                 f"{df.subject_id.nunique()} subjects by filename stem")
    if matched.empty:
        matched = df.iloc[0:0].assign(_path=pd.Series(dtype=str))
    return matched, notes


def hash_frame(inp: AuditInput, cache: dict | None = None,
               progress=None) -> tuple[pd.DataFrame, list[str]]:
    """Rows with md5/phash/dhash attached. Empty frame if no pixels are reachable."""
    if cache is not None and "hash_frame" in cache:
        return cache["hash_frame"]

    df, notes = resolve_paths(inp)
    if len(df):
        md5s, ph, dh = [], [], []
        for i, p in enumerate(df["_path"]):
            q = Path(p)
            md5s.append(md5_file(q))
            ph.append(phash(q))
            dh.append(dhash(q))
            if progress and i % 200 == 0:
                progress(min(0.65, 0.05 + 0.6 * i / len(df)),
                         f"hashing {i}/{len(df)} images")
        df = df.assign(md5=md5s, phash=ph, dhash=dh)
    else:
        df = df.assign(md5=pd.Series(dtype=str), phash=pd.Series(dtype="object"),
                       dhash=pd.Series(dtype="object"))

    out = (df, notes)
    if cache is not None:
        cache["hash_frame"] = out
    return out
