"""Cheap per-image property extraction.

Uses PIL header reads (no full decode) so tens of thousands of files can be probed
in a reasonable time. Decoding is only done when a caller explicitly asks for it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import ExifTags, Image

Image.MAX_IMAGE_PIXELS = None  # these are ordinary photographs, not slide scans

_EXIF_WANTED = {
    "Make": "exif_make",
    "Model": "exif_model",
    "DateTimeOriginal": "exif_datetime",
    "LensModel": "exif_lens",
    "ISOSpeedRatings": "exif_iso",
    "FNumber": "exif_fnumber",
    "ExposureTime": "exif_exposure",
    "Software": "exif_software",
    "WhiteBalance": "exif_whitebalance",
}
_TAG_BY_NAME = {v: k for k, v in ExifTags.TAGS.items()}


@dataclass
class ImageMeta:
    file_path: str
    file_name: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    mode: str | None = None  # PIL colour mode, e.g. RGB, RGBA, L
    format: str | None = None  # PNG / JPEG
    icc_profile: bool = False
    jpeg_quality: int | None = None  # estimated, JPEG only
    exif_make: str | None = None
    exif_model: str | None = None
    exif_datetime: str | None = None
    exif_lens: str | None = None
    exif_iso: str | None = None
    exif_fnumber: str | None = None
    exif_exposure: str | None = None
    exif_software: str | None = None
    exif_whitebalance: str | None = None
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _estimate_jpeg_quality(img: Image.Image) -> int | None:
    """Rough JPEG quality from the luminance quantisation table.

    Compares the table against the IJG standard table scaled by quality. Returns the
    best-matching quality, or None when no table is exposed. This is an estimate and
    is reported as such - it is used to detect recompression, not to grade fidelity.
    """
    qt = getattr(img, "quantization", None)
    if not qt:
        return None
    std_lum = [
        16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99,
    ]
    table = list(qt.get(0, []))
    if len(table) < 64:
        return None
    best, best_err = None, float("inf")
    for q in range(1, 101):
        scale = 5000 / q if q < 50 else 200 - 2 * q
        err = 0.0
        for s, t in zip(std_lum, table[:64]):
            want = max(1, min(255, (s * scale + 50) // 100))
            err += (want - t) ** 2
        if err < best_err:
            best, best_err = q, err
    return best


def probe(path: Path) -> ImageMeta:
    """Read one image's properties without decoding pixel data."""
    p = Path(path)
    try:
        size = p.stat().st_size
    except OSError as e:
        return ImageMeta(str(p), p.name, 0, error=f"stat: {e}")

    meta = ImageMeta(str(p), p.name, size)
    try:
        with Image.open(p) as img:
            meta.width, meta.height = img.size
            meta.mode = img.mode
            meta.format = img.format
            meta.icc_profile = bool(img.info.get("icc_profile"))
            if img.format == "JPEG":
                meta.jpeg_quality = _estimate_jpeg_quality(img)
            exif = img.getexif()
            if exif:
                for name, field in _EXIF_WANTED.items():
                    tag = _TAG_BY_NAME.get(name)
                    if tag is None:
                        continue
                    val = exif.get(tag)
                    if val is None:
                        # DateTimeOriginal etc. live in the Exif IFD.
                        try:
                            val = exif.get_ifd(ExifTags.IFD.Exif).get(tag)
                        except Exception:
                            val = None
                    if val is not None:
                        setattr(meta, field, str(val).strip("\x00 ").strip() or None)
    except Exception as e:  # corrupt or unreadable file - record, never crash the audit
        meta.error = f"{type(e).__name__}: {e}"
    return meta
