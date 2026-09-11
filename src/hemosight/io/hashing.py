"""Exact and perceptual image hashing for duplicate / overlap detection.

Three independent signals, deliberately chosen to fail in different ways:

* MD5 over file bytes - catches byte-identical redistribution only. Zero false
  positives, but blind to any resize, recrop or recompression.
* dHash - horizontal-gradient hash. Robust to brightness/contrast and mild
  compression, sensitive to crop and rotation.
* pHash - DCT-based. More robust to scaling and compression than dHash, and the
  better single choice for "same photo, saved twice differently".

Agreement between signals is what makes an overlap claim credible; any one alone is
arguable. Distances are Hamming distances over 64-bit hashes (0 = identical).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.fft import dct

Image.MAX_IMAGE_PIXELS = None


def md5_file(path: Path, chunk: int = 1 << 20) -> str:
    """MD5 over raw file bytes."""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def _gray(path: Path, size: tuple[int, int]) -> np.ndarray | None:
    try:
        with Image.open(path) as im:
            im = im.convert("L").resize(size, Image.Resampling.LANCZOS)
            return np.asarray(im, dtype=np.float64)
    except Exception:
        return None


def dhash(path: Path, hash_size: int = 8) -> int | None:
    """Difference hash: compare each pixel to its right-hand neighbour."""
    a = _gray(path, (hash_size + 1, hash_size))
    if a is None:
        return None
    bits = a[:, 1:] > a[:, :-1]
    return int("".join("1" if b else "0" for b in bits.flatten()), 2)


def phash(path: Path, hash_size: int = 8, highfreq_factor: int = 4) -> int | None:
    """Perceptual hash: low-frequency DCT coefficients against their median."""
    img_size = hash_size * highfreq_factor
    a = _gray(path, (img_size, img_size))
    if a is None:
        return None
    d = dct(dct(a, axis=0, norm="ortho"), axis=1, norm="ortho")
    low = d[:hash_size, :hash_size]
    # Exclude the DC term from the median: it encodes mean brightness, not structure.
    med = np.median(low.flatten()[1:])
    bits = low > med
    return int("".join("1" if b else "0" for b in bits.flatten()), 2)


def hamming(a: int, b: int) -> int:
    return int(a ^ b).bit_count()


def hamming_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pairwise Hamming distances between two arrays of uint64 hashes.

    Returns an (len(a), len(b)) uint8 matrix. Uses a 16-bit popcount lookup so a
    few thousand x few thousand comparison stays fast without a GPU.
    """
    lut = np.array([bin(i).count("1") for i in range(1 << 16)], dtype=np.uint8)
    a = np.asarray(a, dtype=np.uint64)[:, None]
    b = np.asarray(b, dtype=np.uint64)[None, :]
    x = np.bitwise_xor(a, b)
    out = np.zeros(x.shape, dtype=np.uint8)
    for shift in (0, 16, 32, 48):
        out += lut[((x >> np.uint64(shift)) & np.uint64(0xFFFF)).astype(np.uint32)]
    return out
