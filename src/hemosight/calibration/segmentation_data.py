"""Dataset for sclera / iris / pupil / periocular segmentation over SBVPI + MOBIUS.

The two sources encode masks completely differently and must be unified:

MOBIUS - one RGB mask per image, colour-coded (from its README):
    sclera RGB(255,0,0), iris RGB(0,255,0), pupil RGB(0,0,255), periocular RGB(0,0,0).
    Note "periocular" here means *everything else*, background included, so it is NOT
    a clean skin mask. 3,559 of 16,717 images are annotated.
    Files ending `_bad` are DELIBERATELY unusable images shipped for quality control.
    They are held out as a labelled test set for the quality score rather than binned.

SBVPI - separate binary masks per class: `_sclera`, `_periocular`, plus `_iris`,
    `_pupil`, `_vessels`, `_canthus`, `_eyelashes` on a 108-128 image subset.
    Its `_periocular` mask IS a genuine eye-region mask, so SBVPI is the better
    source for the periocular skin that N5's ITA computation will need.

Unified label space (index: name):
    0 background, 1 sclera, 2 iris, 3 pupil, 4 periocular
`_vessels` is loaded separately when present: it is ground truth for the vasculature
exclusion in Task 1, not a segmentation output class.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

from ..io import paths

CLASSES = ["background", "sclera", "iris", "pupil", "periocular"]
N_CLASSES = len(CLASSES)
SCLERA, IRIS, PUPIL, PERIOCULAR = 1, 2, 3, 4

MOBIUS_COLOURS = {SCLERA: (255, 0, 0), IRIS: (0, 255, 0), PUPIL: (0, 0, 255)}
_MOBIUS_RE = re.compile(r"^(?P<id>\d+)_(?P<phone>\d)(?P<light>[inp])_(?P<eye>[LR])(?P<gaze>\w)_(?P<n>\w+)$")
MOBIUS_PHONE = {"1": "Sony Xperia Z5 Compact", "2": "Apple iPhone 6s", "3": "Xiaomi Pocophone F1"}
MOBIUS_LIGHT = {"i": "indoor", "n": "natural", "p": "poor"}


@dataclass
class Sample:
    image_path: str
    mask_spec: dict  # {"kind": "mobius"|"sbvpi", ...}
    subject_id: str
    dataset: str
    phone: str | None = None
    lighting: str | None = None
    eye: str | None = None
    gaze: str | None = None
    is_bad: bool = False
    vessels_path: str | None = None


def parse_mobius_stem(stem: str) -> dict:
    m = _MOBIUS_RE.match(stem)
    if not m:
        return {}
    return {
        "subject": m.group("id"),
        "phone": MOBIUS_PHONE.get(m.group("phone")),
        "lighting": MOBIUS_LIGHT.get(m.group("light")),
        "eye": m.group("eye"),
        "gaze": m.group("gaze"),
        "is_bad": m.group("n") == "bad",
    }


def index_mobius() -> list[Sample]:
    out = []
    for mask in sorted((paths.MOBIUS / "Masks").rglob("*.png")):
        img = paths.MOBIUS / "Images" / mask.parent.name / f"{mask.stem}.jpg"
        if not img.exists():
            continue
        info = parse_mobius_stem(mask.stem)
        if not info:
            continue
        out.append(Sample(
            image_path=str(img), mask_spec={"kind": "mobius", "path": str(mask)},
            subject_id=f"mobius:{info['subject']}", dataset="mobius",
            phone=info["phone"], lighting=info["lighting"], eye=info["eye"],
            gaze=info["gaze"], is_bad=info["is_bad"],
        ))
    return out


def index_mobius_all() -> list[Sample]:
    """Every MOBIUS image, whether or not a mask exists.

    `index_mobius()` returns only the 3,559 annotated frames, which come from just 35
    of the 100 subjects - and those 35 are the subjects the segmentation model trained
    on. Using them for N1b would both waste two thirds of the population and evaluate
    the pipeline on its own training subjects.

    N1b needs no masks: the trained model supplies them. So it indexes everything, and
    `mask_spec` is left empty where no ground truth exists.
    """
    out = []
    root = paths.MOBIUS / "Images"
    for d in sorted((p for p in root.iterdir() if p.is_dir()),
                    key=lambda p: int(p.name) if p.name.isdigit() else 10**9):
        for img in sorted(d.glob("*.jpg")):
            info = parse_mobius_stem(img.stem)
            if not info:
                continue
            mask = paths.MOBIUS / "Masks" / d.name / f"{img.stem}.png"
            out.append(Sample(
                image_path=str(img),
                mask_spec=({"kind": "mobius", "path": str(mask)} if mask.exists() else {}),
                subject_id=f"mobius:{info['subject']}", dataset="mobius",
                phone=info["phone"], lighting=info["lighting"], eye=info["eye"],
                gaze=info["gaze"], is_bad=info["is_bad"],
            ))
    return out


def index_sbvpi() -> list[Sample]:
    out = []
    for d in sorted(p for p in paths.SBVPI.iterdir() if p.is_dir() and p.name.isdigit()):
        for img in sorted(d.glob("*.jpg")):
            spec = {"kind": "sbvpi"}
            for cls, suffix in ((SCLERA, "sclera"), (IRIS, "iris"),
                                (PUPIL, "pupil"), (PERIOCULAR, "periocular")):
                m = d / f"{img.stem}_{suffix}.png"
                if m.exists():
                    spec[str(cls)] = str(m)
            if str(SCLERA) not in spec:
                continue  # sclera is the class this phase exists for
            ves = d / f"{img.stem}_vessels.png"
            out.append(Sample(
                image_path=str(img), mask_spec=spec,
                subject_id=f"sbvpi:{d.name}", dataset="sbvpi",
                vessels_path=str(ves) if ves.exists() else None,
            ))
    return out


def _read_binary(path: str, shape: tuple[int, int]) -> np.ndarray:
    """Read an SBVPI binary mask.

    SBVPI masks are RGBA with the mask replicated across R, G and B and the alpha
    channel uniformly 255. Reading alpha therefore returns an all-True mask and
    silently labels the entire image as one class - so the colour channels are used,
    and alpha only as a fallback if they carry no signal.
    """
    m = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if m is None:
        return np.zeros(shape, dtype=bool)
    if m.ndim == 3:
        colour = m[..., :3].max(axis=2)
        m = colour if np.ptp(colour) > 0 else (m[..., 3] if m.shape[2] == 4 else colour)
    if m.shape[:2] != shape:
        m = cv2.resize(m, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return m > 127


def load_label(spec: dict, shape: tuple[int, int]) -> np.ndarray:
    """Build the unified integer label map at `shape`."""
    lab = np.zeros(shape, dtype=np.uint8)
    if spec["kind"] == "mobius":
        m = cv2.imread(spec["path"], cv2.IMREAD_COLOR)
        if m is None:
            return lab
        if m.shape[:2] != shape:
            m = cv2.resize(m, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
        rgb = m[:, :, ::-1]
        for cls, colour in MOBIUS_COLOURS.items():
            lab[(np.abs(rgb.astype(int) - np.array(colour)).sum(axis=2) < 60)] = cls
        # MOBIUS "periocular" is black = everything else, indistinguishable from
        # background, so it is deliberately NOT assigned class 4 here.
    else:
        # Paint largest region first so smaller structures overwrite it.
        for cls in (PERIOCULAR, SCLERA, IRIS, PUPIL):
            p = spec.get(str(cls))
            if p:
                lab[_read_binary(p, shape)] = cls
    return lab


class EyeSegDataset(Dataset):
    """Resized image/label pairs. Kept modest in size to fit the 8 GB budget."""

    def __init__(self, samples: list[Sample], size: int = 384, augment: bool = False):
        self.samples = samples
        self.size = size
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, i: int):
        s = self.samples[i]
        img = cv2.imread(s.image_path, cv2.IMREAD_COLOR)
        if img is None:
            img = np.zeros((self.size, self.size, 3), np.uint8)
        img = img[:, :, ::-1]
        lab = load_label(s.mask_spec, img.shape[:2])

        img = cv2.resize(img, (self.size, self.size), interpolation=cv2.INTER_AREA)
        lab = cv2.resize(lab, (self.size, self.size), interpolation=cv2.INTER_NEAREST)

        if self.augment:
            if np.random.rand() < 0.5:
                img, lab = img[:, ::-1].copy(), lab[:, ::-1].copy()
            # Photometric jitter only - this model must survive real device and
            # lighting variation, which is exactly what N1b then measures.
            if np.random.rand() < 0.7:
                g = np.random.uniform(0.7, 1.4)
                img = np.clip(((img / 255.0) ** g) * 255.0, 0, 255).astype(np.uint8)
            if np.random.rand() < 0.7:
                scale = np.random.uniform(0.85, 1.15, size=3)
                img = np.clip(img * scale, 0, 255).astype(np.uint8)

        x = torch.from_numpy(np.ascontiguousarray(img.transpose(2, 0, 1))).float() / 255.0
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        # MOBIUS marks skin as background; the loss must merge bg/periocular there.
        merge = s.dataset == "mobius"
        return ((x - mean) / std, torch.from_numpy(lab.astype(np.int64)),
                torch.tensor(merge), i)


def subject_split(samples: list[Sample], seed: int = 20260911,
                  val_frac: float = 0.2) -> tuple[list[int], list[int]]:
    """Split by SUBJECT, never by image - the Phase 1 rule applies here too."""
    subs = sorted({s.subject_id for s in samples})
    rng = np.random.default_rng(seed)
    rng.shuffle(subs)
    n_val = max(1, int(round(val_frac * len(subs))))
    val = set(subs[:n_val])
    tr = [i for i, s in enumerate(samples) if s.subject_id not in val]
    va = [i for i, s in enumerate(samples) if s.subject_id in val]
    return tr, va
