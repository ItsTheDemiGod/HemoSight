"""Phase 1.5, Task 2: exhaustive search for uncropped / full-eye source images.

If uncropped originals exist anywhere on disk, N1c's data base widens far beyond
Eyes-Defy's 218 subjects. This script settles the question conclusively so it is
never re-litigated.

Three probes:
  1. FULL black-background scan of every CP-AnemiC and Ghana conjunctiva image
     (not a sample) - an uncropped photograph would have a low black fraction.
  2. Resolution census - an uncropped phone original would be megapixel-sized.
  3. Archive inventory, including a pure-Python RAR5 header parser so
     Fingernails.rar can be listed without extracting it (data/raw is read-only).

    .\\.venv\\Scripts\\python.exe scripts\\phase1_5_search_originals.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from hemosight.io import paths

Image.MAX_IMAGE_PIXELS = None


# --------------------------------------------------------------------------- #
# RAR5 header parsing (listing only - no decompression, nothing written)
# --------------------------------------------------------------------------- #
def _vint(buf: bytes, pos: int) -> tuple[int, int]:
    """RAR5 variable-length integer: 7 bits per byte, high bit = continue."""
    val, shift = 0, 0
    while pos < len(buf):
        b = buf[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, pos
        shift += 7
    raise ValueError("truncated vint")


def list_rar5(path: Path, limit: int = 100000) -> list[dict]:
    """Return [{name, unpacked_size, is_dir}] for a RAR5 archive."""
    data = path.read_bytes()
    sig = b"Rar!\x1a\x07\x01\x00"
    if not data.startswith(sig):
        raise ValueError(f"not a RAR5 archive: {path.name}")
    pos = len(sig)
    out: list[dict] = []
    while pos < len(data) and len(out) < limit:
        try:
            if pos + 4 > len(data):
                break
            pos += 4  # header CRC32
            hdr_size, pos = _vint(data, pos)
            hdr_start = pos
            htype, pos = _vint(data, pos)
            hflags, pos = _vint(data, pos)
            extra_size = 0
            data_size = 0
            if hflags & 0x0001:
                extra_size, pos = _vint(data, pos)
            if hflags & 0x0002:
                data_size, pos = _vint(data, pos)

            if htype in (2, 3):  # file header / service header
                _fflags, pos = _vint(data, pos)
                unp_size, pos = _vint(data, pos)
                _attr, pos = _vint(data, pos)
                if _fflags & 0x0002:
                    pos += 4  # mtime
                if _fflags & 0x0004:
                    pos += 4  # data CRC
                _comp, pos = _vint(data, pos)
                _host, pos = _vint(data, pos)
                name_len, pos = _vint(data, pos)
                name = data[pos:pos + name_len].decode("utf-8", "replace")
                if htype == 2:
                    out.append({"name": name, "unpacked_size": unp_size,
                                "is_dir": bool(_fflags & 0x0001)})
            pos = hdr_start + hdr_size + data_size
            if hdr_size == 0:
                break
        except Exception:
            break
    return out


# --------------------------------------------------------------------------- #
def black_fraction(path: Path, thresh: int = 12) -> float | None:
    try:
        with Image.open(path) as im:
            a = np.asarray(im.convert("RGB").resize((96, 96)))
        return float((a.max(axis=2) < thresh).mean())
    except Exception:
        return None


def main() -> int:
    paths.ensure_dirs()
    report: dict = {}

    # ---- probe 1 + 2: full scan of the two suspect datasets ------------------
    print("=== FULL scan (every image) ===")
    scan_rows = []
    for name in ("cp_anemic", "ghana_conj", "ghana_nail", "eyes_defy"):
        df = pd.read_csv(paths.MANIFESTS / f"{name}.csv")
        fr = []
        for i, p in enumerate(df.file_path):
            if i % 1000 == 0:
                print(f"  {name} {i}/{len(df)}", end="\r", flush=True)
            v = black_fraction(Path(p))
            if v is not None:
                fr.append(v)
        fr = np.array(fr)
        px = (df.width.astype("float") * df.height.astype("float"))
        row = {
            "dataset": name,
            "n_images": len(fr),
            "black_mean": round(float(fr.mean()), 4),
            "black_min": round(float(fr.min()), 4),
            "n_below_5pct_black": int((fr < 0.05).sum()),
            "n_below_20pct_black": int((fr < 0.20).sum()),
            "max_megapixels": round(float(px.max()) / 1e6, 3),
            "n_over_1MP": int((px > 1e6).sum()),
        }
        scan_rows.append(row)
        print(f"  {name:11s} n={row['n_images']:5d} black_mean={row['black_mean']:.3f} "
              f"black_MIN={row['black_min']:.3f} | <5% black: {row['n_below_5pct_black']} "
              f"| max {row['max_megapixels']:.2f} MP | >1MP: {row['n_over_1MP']}")
    report["full_scan"] = scan_rows

    # ---- probe 3: archives ---------------------------------------------------
    print("\n=== archives under data/raw ===")
    archives = []
    for pat in ("*.rar", "*.zip", "*.7z", "*.tar*", "*.gz", "*.zip.001"):
        archives += list(paths.RAW.rglob(pat))
    arch_report = []
    for a in sorted(set(archives)):
        rel = str(a.relative_to(paths.RAW))
        entry = {"archive": rel, "size_mb": round(a.stat().st_size / 1e6, 1)}
        if a.suffix.lower() == ".rar":
            try:
                items = list_rar5(a)
                exts: dict[str, int] = {}
                for it in items:
                    e = Path(it["name"]).suffix.lower()
                    exts[e] = exts.get(e, 0) + 1
                entry.update({
                    "listed_entries": len(items),
                    "extensions": exts,
                    "sample_names": [it["name"] for it in items[:5]],
                    "max_unpacked_size": max((it["unpacked_size"] for it in items), default=0),
                })
                print(f"  {rel}\n     entries={len(items)} exts={exts}")
                print(f"     sample={[it['name'] for it in items[:3]]}")
            except Exception as e:
                entry["error"] = f"{type(e).__name__}: {e}"
                print(f"  {rel}: parse failed - {e}")
        else:
            print(f"  {rel} ({entry['size_mb']} MB) - nus8 sensor data, not conjunctiva")
        arch_report.append(entry)
    report["archives"] = arch_report

    # ---- probe 4: any unexplored directory or non-image file -----------------
    print("\n=== directory structure of the two suspect datasets ===")
    struct_report = {}
    for label, root in (("ghana_conj", paths.GHANA_CONJ), ("cp_anemic", paths.CP_ANEMIC)):
        subdirs = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_dir()]
        nonimg = [str(p.relative_to(root)) for p in root.rglob("*")
                  if p.is_file() and p.suffix.lower() not in {".png", ".jpg", ".jpeg"}]
        struct_report[label] = {"subdirectories": subdirs, "non_image_files": nonimg}
        print(f"  {label}: subdirs={subdirs or 'NONE'} non_image_files={nonimg or 'NONE'}")
    report["structure"] = struct_report

    out = paths.INTERIM / "phase1_5_original_search.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nreport -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
