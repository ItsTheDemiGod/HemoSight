"""Canonical locations for every dataset on disk.

`data/raw/` is READ-ONLY. Nothing in this package may open a path under RAW for
writing. All derived artefacts go to `data/interim/` or `data/processed/`.

Folder names in `data/raw/` are verbatim as downloaded, including the double space
in the Ghana conjunctiva folder name. They are recorded here once so no other module
has to reproduce them.
"""

from __future__ import annotations

from pathlib import Path

# Repository root, resolved from this file: src/hemosight/io/paths.py -> up 4.
ROOT = Path(__file__).resolve().parents[3]

RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
SYNTHETIC = ROOT / "data" / "synthetic"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
TABLES = REPORTS / "tables"
CONFIGS = ROOT / "configs"

MANIFESTS = INTERIM / "manifests"
SPLITS = INTERIM / "splits"
OVERLAP = INTERIM / "overlap"

# --- dataset roots -------------------------------------------------------------
# NOTE the two spaces in "Using  Conjunctiva" - that is the folder as distributed.
GHANA_CONJ = RAW / (
    "Application of Machine Learning in Detecting Iron Deficiency Anemia Using "
    " Conjunctiva image Dataset from Ghana"
)
GHANA_NAIL = (
    RAW
    / "Detection of Anemia using Colour of the Fingernails Image Datasets from Ghana"
    / "Detection of Anemia using Colour of the Fingernails Image Datasets from Ghana"
    / "Fingernails"
)
CP_ANEMIC = RAW / "CP-AnemiC dataset"
CP_ANEMIC_SHEET = CP_ANEMIC / "Anemia_Data_Collection_Sheet.xlsx"

EYES_DEFY = RAW / "dataset anemia"  # confirmed Eyes-Defy-Anemia; see CLAUDE.md
HB_PPG = RAW / "Hb_PPG_Dataset"
HB_PPG_SHEET = HB_PPG / "subject information.xlsx"

SBVPI = RAW / "SBVPI" / "SBVPI"
SBVPI_META = RAW / "SBVPI" / "SBVPI_Gender_Age_Colour.txt"
MOBIUS = RAW / "MOBIUS"
# SCIN was DELETED in Phase 1.5 (DECISION LOG 2026-09-11): it shipped no data, is
# dermatology imagery with no conjunctiva and no Hb, and has no subject overlap with
# any dataset here. N5 no longer depends on it. Do not re-add.

NUS8 = RAW / "nus8"
NUS8_RAW_DOWNLOADS = NUS8 / "raw_downloads"

# Camera folder -> (short name used in the published .mat files).
# SamsungNX2000's groundtruth.mat/ folder is EMPTY on this machine; its ground truth
# is read from raw_downloads/ instead. See resolve_nus8_gt().
NUS8_CAMERAS = {
    "Canon EOS-1Ds Mark III": "Canon1DsMkIII",
    "Canon600D": "Canon600D",
    "Fujifilm X-M1": "FujifilmXM1",
    "NikonD5200": "NikonD5200",
    "Olympus E-PL6": "OlympusEPL6",
    "SamsungNX2000": "SamsungNX2000",
}


def resolve_nus8_gt(camera_dir: str) -> Path:
    """Return the ground-truth .mat for a NUS camera folder.

    Prefers the per-camera `groundtruth.mat/` directory. Falls back to
    `raw_downloads/` because SamsungNX2000's directory was never populated during
    extraction. Raises if neither location has a file.
    """
    short = NUS8_CAMERAS[camera_dir]
    local = NUS8 / camera_dir / "groundtruth.mat"
    if local.is_dir():
        hits = sorted(local.glob("*.mat"))
        if hits:
            return hits[0]
    hits = sorted(NUS8_RAW_DOWNLOADS.glob(f"{short}_gt*.mat"))
    if hits:
        return hits[0]
    raise FileNotFoundError(f"No ground-truth .mat found for NUS camera {camera_dir!r}")


def ensure_dirs() -> None:
    """Create the derived-data directories. `data/` is gitignored in full, so these
    do not survive a clone and must be created on demand."""
    for d in (INTERIM, PROCESSED, SYNTHETIC, MANIFESTS, SPLITS, OVERLAP, FIGURES, TABLES):
        d.mkdir(parents=True, exist_ok=True)


def assert_raw_readonly(path: Path) -> None:
    """Guard against accidental writes under data/raw/."""
    p = Path(path).resolve()
    if RAW.resolve() in p.parents or p == RAW.resolve():
        raise PermissionError(f"data/raw is READ-ONLY; refusing to write to {p}")
