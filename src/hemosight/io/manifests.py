"""Unified manifest construction across every dataset.

One row per measurement (image, or PPG recording). Every builder returns the same
schema so the master manifest is a plain concatenation.

Three rules govern every builder:

1. NEVER fabricate a value. Missing stays missing (NaN), never zero, never imputed.
2. `subject_id` must be a real participant identifier wherever one is recoverable.
   Where it is not, it falls back to `image_id` and `subject_id_source` records that,
   so the fallback fraction can be reported rather than hidden.
3. Hemoglobin is normalised to g/dL. Every unit conversion is logged by the caller.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import paths
from .naming import parse_ghana_name

SCHEMA = [
    "image_id",
    "subject_id",
    "dataset",
    "site",
    "modality",
    "file_path",
    "hb_g_dl",
    "anemia_label",
    "age",
    "sex",
    "device_model",
    "width",
    "height",
    "notes",
]

# Extra provenance columns carried alongside the required schema.
EXTRA = [
    "subject_id_source",  # "true" | "fallback"
    "anemia_label_source",  # "provided" | "filename" | "derived_who" | None
    "severity",
    "hospital",
    "region",
    "age_units",
    "mask_paths",
]

# Datasets whose haemoglobin labels were REJECTED by the Phase 1.5 arbitration
# (scripts/ghana_label_arbitration_phase1_5.py, DECISION LOG 2026-09-11). CP-AnemiC's Hb
# conflicts on byte-identical images - one image carries up to 10 different values,
# spread as wide as 7.1 g/dL - and the Ghana sets ship no Hb at all. The whole pool is
# BINARY-LABEL-ONLY.
#
# This lives in the builder, not in a post-hoc patch script, so a manifest rebuild can
# never silently restore an untrusted Hb value.
BINARY_LABEL_ONLY_DATASETS = frozenset({"cp_anemic", "ghana_conj", "ghana_nail"})

HB_UNTRUSTED_REASON = (
    "Phase1.5 arbitration: BINARY-LABEL-ONLY. CP-AnemiC Hb conflicts on duplicated "
    "images; Ghana ships no Hb. Excluded from every Hb regression task."
)

EXTRA += ["hb_label_trusted", "hb_label_untrusted_reason"]

ALL_COLUMNS = SCHEMA + EXTRA

# WHO haemoglobin thresholds for non-pregnant adults, used ONLY where a dataset
# supplies Hb but no label. Recorded as anemia_label_source="derived_who".
WHO_ADULT = {"M": 13.0, "F": 12.0}


def _blank(n: int) -> dict:
    return {c: [None] * n for c in ALL_COLUMNS}


def _finalise(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in ALL_COLUMNS:
        if c not in df.columns:
            df[c] = None
    df = df[ALL_COLUMNS]
    df["hb_g_dl"] = pd.to_numeric(df["hb_g_dl"], errors="coerce")
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    for c in ("width", "height", "anemia_label"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    # Hard trust flag. An Hb value is usable only if it exists AND its dataset survived
    # the Phase 1.5 arbitration. Downstream code must filter on hb_label_trusted.
    binary_only = df["dataset"].isin(BINARY_LABEL_ONLY_DATASETS)
    df["hb_label_trusted"] = df["hb_g_dl"].notna() & ~binary_only
    df["hb_label_untrusted_reason"] = pd.Series(
        [HB_UNTRUSTED_REASON if b else None for b in binary_only],
        index=df.index, dtype="object",
    )
    return df


def trusted_hb(df: pd.DataFrame) -> pd.DataFrame:
    """Rows usable for Hb regression. Use this instead of `df.hb_g_dl.notna()`."""
    if "hb_label_trusted" not in df.columns:
        raise KeyError(
            "manifest lacks hb_label_trusted - rebuild it with scripts/dataset_manifests_phase1.py"
        )
    return df[df["hb_label_trusted"].astype(bool)]


def _decimal_comma(value) -> float | None:
    """Parse a number that may use a European decimal comma.

    Italy.xlsx stores 15 of its 123 haemoglobin values as strings like "15,1".
    A plain pd.to_numeric turns these into NaN and silently drops 15 subjects.
    A literal "_" means the value was not available and stays missing.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s in {"", "_", "-", "/", "n/a", "NA"}:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# CP-AnemiC
# --------------------------------------------------------------------------- #
def build_cp_anemic(probe_images: bool = True) -> pd.DataFrame:
    """CP-AnemiC: 710 conjunctiva images, one spreadsheet row per IMAGE_ID.

    The sheet has one row per image and no participant column, so a participant
    contributing two images cannot be detected. subject_id is therefore the image id
    and is marked as a fallback. Hospital is a genuine within-dataset site variable.
    """
    from .imagemeta import probe

    sheet = pd.read_excel(paths.CP_ANEMIC_SHEET).rename(columns={"Age(Months)": "age_months"})
    meta = {str(r["IMAGE_ID"]).strip(): r for r in sheet.to_dict("records")}

    rows = []
    for label_dir, provided in (("Anemic", 1), ("Non-anemic", 0)):
        for f in sorted((paths.CP_ANEMIC / label_dir).glob("*.png")):
            key = f.stem
            m = meta.get(key)
            im = probe(f) if probe_images else None
            row = m if m is not None else {}
            age_months = row.get("age_months")
            rows.append(
                {
                    "image_id": f"cp_anemic:{key}",
                    "subject_id": f"cp_anemic:{key}",
                    "dataset": "cp_anemic",
                    "site": f"cp_anemic:{row.get('HOSPITAL', 'unknown')}",
                    "modality": "conjunctiva",
                    "file_path": str(f),
                    "hb_g_dl": row.get("HB_LEVEL"),
                    "anemia_label": provided,
                    "age": (age_months / 12.0) if age_months is not None and pd.notna(age_months) else None,
                    "sex": {"Male": "M", "Female": "F"}.get(row.get("GENDER")),
                    "device_model": (im.exif_model if im else None),
                    "width": im.width if im else None,
                    "height": im.height if im else None,
                    "notes": (
                        f"folder={label_dir}"
                        + (f"; age_months={age_months}" if age_months is not None and pd.notna(age_months) else "")
                        + ("; NO_SHEET_ROW" if m is None else "")
                    ),
                    "subject_id_source": "fallback",  # sheet has no participant column
                    "anemia_label_source": "provided",
                    "severity": row.get("Severity"),
                    "hospital": row.get("HOSPITAL"),
                    "region": row.get("REGION"),
                    "age_units": "years (converted from months)",
                }
            )
    return _finalise(rows)


# --------------------------------------------------------------------------- #
# Ghana conjunctiva / fingernail
# --------------------------------------------------------------------------- #
def _build_ghana(root: Path, dataset: str, modality: str, merge_series: bool,
                 probe_images: bool) -> pd.DataFrame:
    from .imagemeta import probe

    rows = []
    for f in sorted(root.glob("*.png")):
        g = parse_ghana_name(f.stem)
        if g is None:
            rows.append(
                {
                    "image_id": f"{dataset}:{f.stem}",
                    "subject_id": f"{dataset}:{f.stem}",
                    "dataset": dataset,
                    "site": "ghana",
                    "modality": modality,
                    "file_path": str(f),
                    "notes": "UNPARSED_FILENAME",
                    "subject_id_source": "fallback",
                }
            )
            continue
        im = probe(f) if probe_images else None
        # Subject key: class + number, series optionally merged. Replicate markers
        # ("(3)", "- Copy", random suffixes) are deliberately excluded.
        parts = [dataset, g.cls]
        if not merge_series:
            parts.append(g.series)
            if g.sub_series:
                parts.append(g.sub_series)
        parts.append(f"{g.number:03d}")
        rows.append(
            {
                "image_id": f"{dataset}:{f.stem}",
                "subject_id": ":".join(parts),
                "dataset": dataset,
                "site": "ghana",
                "modality": modality,
                "file_path": str(f),
                "hb_g_dl": None,  # this dataset ships no haemoglobin values
                "anemia_label": g.anemia_label,
                "age": None,
                "sex": None,
                "device_model": (im.exif_model if im else None),
                "width": im.width if im else None,
                "height": im.height if im else None,
                "notes": (
                    f"series={g.series}"
                    + (f"; sub={g.sub_series}" if g.sub_series else "")
                    + (f"; replicate={g.replicate}" if g.replicate else "")
                    + ("; copy_marker" if g.is_copy else "")
                ),
                "subject_id_source": "true",  # participant number is in the filename
                "anemia_label_source": "filename",
            }
        )
    return _finalise(rows)


def build_ghana_conj(merge_series: bool = False, probe_images: bool = True) -> pd.DataFrame:
    return _build_ghana(paths.GHANA_CONJ, "ghana_conj", "conjunctiva", merge_series, probe_images)


def build_ghana_nail(merge_series: bool = False, probe_images: bool = True) -> pd.DataFrame:
    return _build_ghana(paths.GHANA_NAIL, "ghana_nail", "nail", merge_series, probe_images)


# --------------------------------------------------------------------------- #
# Eyes-Defy-Anemia
# --------------------------------------------------------------------------- #
def build_eyes_defy(probe_images: bool = True) -> pd.DataFrame:
    """Eyes-Defy-Anemia: one folder per participant, two sites (India, Italy).

    Each folder holds one source photograph (.jpg) plus palpebral / forniceal
    segmentation masks (.png). Only the photograph becomes a manifest row; the masks
    are recorded in `mask_paths`. Labels come from the per-site spreadsheet, which
    has no anemia column, so the label is derived with WHO adult thresholds and
    marked as such.
    """
    from .imagemeta import probe

    rows = []
    for site in ("India", "Italy"):
        root = paths.EYES_DEFY / site
        sheet = pd.read_excel(root / f"{site}.xlsx")
        by_num = {int(r.Number): r for r in sheet.itertuples() if pd.notna(r.Number)}
        for d in sorted((p for p in root.iterdir() if p.is_dir()),
                        key=lambda p: int(p.name) if p.name.isdigit() else 10**9):
            if not d.name.isdigit():
                continue
            num = int(d.name)
            m = by_num.get(num)
            jpgs = sorted(d.glob("*.jpg"))
            masks = sorted(d.glob("*_palpebral.png")) + sorted(d.glob("*_forniceal.png"))
            hb = _decimal_comma(getattr(m, "Hgb", None)) if m is not None else None
            sex = str(getattr(m, "Gender", "")).strip().upper()[:1] if m is not None else None
            sex = sex if sex in {"M", "F"} else None
            label = None
            if hb is not None and sex in WHO_ADULT:
                label = int(hb < WHO_ADULT[sex])
            note = getattr(m, "Note", None) if m is not None else None
            for f in jpgs:
                im = probe(f) if probe_images else None
                rows.append(
                    {
                        "image_id": f"eyes_defy:{site}:{num:03d}:{f.stem}",
                        "subject_id": f"eyes_defy:{site}:{num:03d}",
                        "dataset": "eyes_defy",
                        "site": f"eyes_defy:{site}",
                        "modality": "conjunctiva",
                        "file_path": str(f),
                        "hb_g_dl": hb,
                        "anemia_label": label,
                        "age": getattr(m, "Age", None) if m is not None else None,
                        "sex": sex,
                        "device_model": (im.exif_model if im else None),
                        "width": im.width if im else None,
                        "height": im.height if im else None,
                        "notes": (
                            f"n_masks={len(masks)}"
                            + (f"; sheet_note={str(note).strip()}" if note is not None and pd.notna(note) else "")
                            + ("; HB_NOT_AVAILABLE" if hb is None else "")
                        ),
                        "subject_id_source": "true",  # folder is the participant
                        "anemia_label_source": "derived_who" if label is not None else None,
                        "age_units": "years",
                        "mask_paths": "|".join(str(x) for x in masks),
                    }
                )
    return _finalise(rows)


# --------------------------------------------------------------------------- #
# Hb PPG
# --------------------------------------------------------------------------- #
def build_hb_ppg() -> pd.DataFrame:
    """Hb_PPG_Dataset: 252 subjects, one CSV each, four-wavelength PPG.

    UNIT CONVERSION: the spreadsheet reports haemoglobin in g/L. Every value is
    divided by 10 to reach g/dL. This is the only dataset needing it.
    """
    sheet = pd.read_excel(paths.HB_PPG_SHEET).rename(
        columns={"Hemoglobin (g/L)": "hb_gl", "Age (year)": "age_years"}
    )
    rows = []
    for r in sheet.to_dict("records"):
        sid = int(r["ID"])
        csv = paths.HB_PPG / "data_csv" / f"{sid}.csv"
        hb_gl = pd.to_numeric(r.get("hb_gl"), errors="coerce")
        hb = float(hb_gl) / 10.0 if pd.notna(hb_gl) else None
        sex = str(r.get("Gender", "")).strip().lower()
        sex = {"male": "M", "female": "F"}.get(sex)
        label = int(hb < WHO_ADULT[sex]) if (hb is not None and sex in WHO_ADULT) else None
        rows.append(
            {
                "image_id": f"hb_ppg:{sid:03d}",
                "subject_id": f"hb_ppg:{sid:03d}",
                "dataset": "hb_ppg",
                "site": "hb_ppg",
                "modality": "ppg",
                "file_path": str(csv),
                "hb_g_dl": hb,
                "anemia_label": label,
                "age": pd.to_numeric(r.get("age_years"), errors="coerce"),
                "sex": sex,
                "device_model": "4-wavelength PPG (660/730/850/940 nm), 200 Hz",
                "width": None,
                "height": None,
                "notes": (
                    f"hb_source_g_per_L={hb_gl}; converted_to_g_dL_by_/10"
                    + ("" if csv.exists() else "; CSV_MISSING")
                ),
                "subject_id_source": "true",
                "anemia_label_source": "derived_who" if label is not None else None,
                "age_units": "years",
            }
        )
    return _finalise(rows)


# --------------------------------------------------------------------------- #
# Sclera segmentation sets (no haemoglobin; used for Phase 2)
# --------------------------------------------------------------------------- #
def build_sbvpi(probe_images: bool = True) -> pd.DataFrame:
    from .imagemeta import probe

    meta_rows = []
    if paths.SBVPI_META.exists():
        for line in paths.SBVPI_META.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            meta_rows.append(parts if len(parts) >= 3 else None)

    rows = []
    for d in sorted((p for p in paths.SBVPI.iterdir() if p.is_dir()),
                    key=lambda p: int(p.name) if p.name.isdigit() else 10**9):
        if not d.name.isdigit():
            continue
        sid = int(d.name)
        info = meta_rows[sid - 1] if 0 < sid <= len(meta_rows) and meta_rows[sid - 1] else None
        for f in sorted(d.glob("*.jpg")):
            im = probe(f) if probe_images else None
            masks = sorted(d.glob(f"{f.stem}_*.png"))
            rows.append(
                {
                    "image_id": f"sbvpi:{sid:03d}:{f.stem}",
                    "subject_id": f"sbvpi:{sid:03d}",
                    "dataset": "sbvpi",
                    "site": "sbvpi",
                    "modality": "sclera",
                    "file_path": str(f),
                    "age": (info[1] if info and info[1].isdigit() else None),
                    "sex": (info[0].upper() if info else None),
                    "device_model": (im.exif_model if im else None),
                    "width": im.width if im else None,
                    "height": im.height if im else None,
                    "notes": f"eye_colour={info[2] if info else 'NA'}; n_masks={len(masks)}",
                    "subject_id_source": "true",
                    "age_units": "years",
                    "mask_paths": "|".join(str(x) for x in masks),
                }
            )
    return _finalise(rows)


# MOBIUS filename grammar, per its README: <ID>_<phone><light>_<Eye><gaze>_<number>.jpg
_MOBIUS_PHONE = {
    "1": "Sony Xperia Z5 Compact",
    "2": "Apple iPhone 6s",
    "3": "Xiaomi Pocophone F1",
}
_MOBIUS_LIGHT = {"i": "indoor", "n": "natural", "p": "poor"}
_MOBIUS_RE = re.compile(r"^(?P<id>\d+)_(?P<phone>\d)(?P<light>[inp])_(?P<eye>[LR])(?P<gaze>\w*)_")


def _parse_mobius_name(stem: str) -> tuple[str | None, str | None, str | None, str | None]:
    m = _MOBIUS_RE.match(stem)
    if m is None:
        return None, None, None, None
    return (
        _MOBIUS_PHONE.get(m.group("phone")),
        _MOBIUS_LIGHT.get(m.group("light")),
        m.group("eye"),
        m.group("gaze") or None,
    )


def build_mobius(probe_images: bool = True) -> pd.DataFrame:
    """MOBIUS: 16,717 eye images from 100 subjects, 3 phones, 3 lighting conditions.

    The README documents the filename grammar `<ID>_<phone><light>_<Eye><gaze>_<n>.jpg`,
    so device and illumination are recoverable per image even though EXIF is absent.
    That makes MOBIUS the only human dataset here with real device diversity.
    Only 3,559 images (35 subjects) carry segmentation masks.
    """
    from .imagemeta import probe

    info = {}
    csv = paths.MOBIUS / "data.csv"
    if csv.exists():
        d = pd.read_csv(csv)
        for r in d.itertuples():
            info[str(r.ID)] = r

    mask_index: dict[str, list[str]] = {}
    for m in (paths.MOBIUS / "Masks").rglob("*.png"):
        mask_index.setdefault(re.sub(r"_[a-z]+$", "", m.stem), []).append(str(m))

    rows = []
    for d in sorted((p for p in (paths.MOBIUS / "Images").iterdir() if p.is_dir()),
                    key=lambda p: int(p.name) if p.name.isdigit() else 10**9):
        sid = d.name
        r = info.get(sid)
        for f in sorted(d.glob("*.jpg")):
            im = probe(f) if probe_images else None
            masks = mask_index.get(f.stem, [])
            phone, light, eye, gaze = _parse_mobius_name(f.stem)
            rows.append(
                {
                    "image_id": f"mobius:{sid}:{f.stem}",
                    "subject_id": f"mobius:{sid}",
                    "dataset": "mobius",
                    "site": "mobius",
                    "modality": "sclera",
                    "file_path": str(f),
                    "age": getattr(r, "age", None) if r is not None else None,
                    "sex": (str(getattr(r, "gender", "")).upper()[:1] or None) if r is not None else None,
                    # Device comes from the filename grammar, not EXIF (which is absent).
                    "device_model": phone or (im.exif_model if im else None),
                    "width": im.width if im else None,
                    "height": im.height if im else None,
                    "notes": f"n_masks={len(masks)}; lighting={light}; eye={eye}; gaze={gaze}",
                    "subject_id_source": "true",
                    "age_units": "years",
                    "mask_paths": "|".join(masks),
                }
            )
    return _finalise(rows)


BUILDERS = {
    "cp_anemic": build_cp_anemic,
    "ghana_conj": build_ghana_conj,
    "ghana_nail": build_ghana_nail,
    "eyes_defy": build_eyes_defy,
    "hb_ppg": build_hb_ppg,
    "sbvpi": build_sbvpi,
    "mobius": build_mobius,
}
