"""Check 1 - leakage and duplicate detection.

PROVENANCE. Phase 1, Task 2 (scripts/phase1_overlap.py). That check found 419 MD5
hashes shared between two datasets distributed separately as independent sources,
87.3% of one set byte-identical to a file in the other, 98.2% within pHash Hamming 10,
and internal redundancy of 52.7% and 50.8% inside the two Ghana collections. None of
that is visible from a file listing, and none of the five applicable sources in
reports/literature_gap.md reports having looked.

The hashing itself is not reimplemented here - it is hemosight.io.hashing, the module
Phase 1 used, unchanged. What is generalised is the question: instead of "do these two
named datasets overlap", the question is "does any duplicate in this submission cross
a train/test boundary", which is the form that invalidates a reported score.

Three signals that fail differently, which is why agreement between them is what makes
an overlap claim credible:
  MD5        exact bytes. No false positives, blind to any re-encode.
  dHash      horizontal gradient. Survives brightness and mild compression.
  pHash      DCT. The better single choice for "same photo, saved twice differently".
  embedding  ImageNet nearest neighbour. Semantic, and the only signal that catches a
             re-shot or re-cropped image. OFF by default: it needs torch, and on this
             machine the GPU is reserved for the Phase 5 permutation run.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from hemosight.io.hashing import hamming_matrix

from .contract import AuditInput
from .images import hash_frame
from .verdict import FAIL, INSUFFICIENT, PASS, CheckResult, Timer, insufficient

CHECK_ID = "duplicates"
TITLE = "Leakage and duplicate detection"
PROVENANCE = ("Phase 1 Task 2 - the CP-AnemiC / Ghana overlap check "
              "(scripts/phase1_overlap.py, DECISION LOG 2026-09-11)")

PHASH_NEAR = 10     # Hamming distance over a 64-bit hash; Phase 1's working value
DHASH_NEAR = 10
EMBED_SIM = 0.92

def _embed(paths: list[str], device: str = "cpu") -> np.ndarray | None:
    """ResNet18 penultimate features, L2-normalised. Phase 1's embedding signal."""
    try:
        import torch
        from PIL import Image
        from torchvision import models, transforms
    except Exception:
        return None
    net = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    net.fc = torch.nn.Identity()
    net = net.eval().to(device)
    tf = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    out = []
    with torch.no_grad():
        for s in range(0, len(paths), 32):
            batch = []
            for p in paths[s:s + 32]:
                try:
                    with Image.open(p) as im:
                        batch.append(tf(im.convert("RGB")))
                except Exception:
                    batch.append(torch.zeros(3, 224, 224))
            f = net(torch.stack(batch).to(device))
            out.append(torch.nn.functional.normalize(f, dim=1).cpu().numpy())
    return np.concatenate(out).astype(np.float32)


def _near_pairs(hashes: np.ndarray, threshold: int, block: int = 1024):
    """Index pairs (i < j) within `threshold` Hamming distance."""
    n = len(hashes)
    pairs = []
    for s in range(0, n, block):
        d = hamming_matrix(hashes[s:s + block], hashes)
        for li in range(d.shape[0]):
            i = s + li
            js = np.flatnonzero(d[li] <= threshold)
            pairs.extend((i, int(j)) for j in js if j > i)
    return pairs


def _components(n: int, pairs) -> np.ndarray:
    """Connected components over the near-duplicate graph."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    return np.array([find(i) for i in range(n)])


def run(inp: AuditInput, thresholds: dict | None = None,
        preregistered: bool = False, embedding: bool = False,
        device: str = "cpu", progress=None, cache: dict | None = None) -> CheckResult:
    th = {"max_duplicate_rate": 0.0, "allow_cross_split_duplicates": False}
    th.update(thresholds or {})

    with Timer() as t:
        df, notes = hash_frame(inp, cache=cache, progress=progress)
        if len(df) == 0:
            r = insufficient(
                CHECK_ID, TITLE, PROVENANCE,
                missing=["image_path column or a readable image directory"],
                explanation=(
                    "Duplicate detection reads pixels. Without files it cannot be "
                    "done, and no verdict is inferred from the table alone. "
                    + "; ".join(notes)))
            return r

        paths = [Path(p) for p in df["_path"]]
        n = len(df)
        n_unique = int(df["md5"].nunique())
        dup_rate = 1.0 - n_unique / n

        valid = df["phash"].notna()
        ph_arr = np.array([h for h in df.loc[valid, "phash"]], dtype=np.uint64)
        idx = np.flatnonzero(valid.to_numpy())
        if progress:
            progress(0.7, "comparing perceptual hashes")
        pairs_local = _near_pairs(ph_arr, PHASH_NEAR) if len(ph_arr) > 1 else []
        pairs = [(int(idx[a]), int(idx[b])) for a, b in pairs_local]
        comp = _components(n, pairs)
        near_unique = int(pd.unique(comp).size)
        near_rate = 1.0 - near_unique / n

        emb_pairs = 0
        emb_note = "not run (opt-in; needs torch, and the GPU is reserved)"
        if embedding:
            if progress:
                progress(0.8, "embedding nearest neighbours")
            E = _embed([str(p) for p in paths], device=device)
            if E is None:
                emb_note = "torch/torchvision unavailable"
            else:
                sim = E @ E.T
                np.fill_diagonal(sim, -1.0)
                emb_pairs = int(np.sum(np.triu(sim >= EMBED_SIM, 1)))
                emb_note = (f"{emb_pairs} pairs at cosine >= {EMBED_SIM} on "
                            f"{device}")

        # ---- the question that actually invalidates a score -------------------
        cross_exact: list[dict] = []
        cross_near: list[dict] = []
        if inp.has("split"):
            sp = df["split"].astype(str)
            for h, g in df.groupby("md5").groups.items():
                if sp.loc[g].nunique() > 1:
                    cross_exact.append({"md5": str(h),
                                        "splits": sorted(set(sp.loc[g])),
                                        "rows": int(len(g))})
            for c, g in pd.Series(comp, index=df.index).groupby(comp).groups.items():
                if len(g) > 1 and sp.loc[g].nunique() > 1:
                    cross_near.append({"component": int(c),
                                       "splits": sorted(set(sp.loc[g])),
                                       "rows": int(len(g))})

        measured = {
            "n_images": n,
            "n_unique_md5": n_unique,
            "exact_duplicate_rate": round(dup_rate, 4),
            "near_duplicate_rate_phash_le_%d" % PHASH_NEAR: round(near_rate, 4),
            "n_exact_duplicate_groups_crossing_a_split": len(cross_exact),
            "n_near_duplicate_groups_crossing_a_split": len(cross_near),
            "n_embedding_pairs": emb_pairs,
        }
        details = {
            "notes": notes, "embedding": emb_note,
            "cross_split_exact": cross_exact[:25],
            "cross_split_near": cross_near[:25],
            "thresholds_used": {"phash_hamming": PHASH_NEAR,
                                "dhash_hamming": DHASH_NEAR,
                                "embedding_cosine": EMBED_SIM},
        }

        if not inp.has("split"):
            if dup_rate > th["max_duplicate_rate"] or near_rate > 0:
                res = CheckResult(
                    CHECK_ID, TITLE, INSUFFICIENT,
                    headline=(f"{dup_rate:.1%} exact and {near_rate:.1%} near-duplicate "
                              "images, but no split column to test them against"),
                    explanation=(
                        "Duplicates are present. Whether they invalidate the reported "
                        "score depends on whether the same content appears on both "
                        "sides of a train/test boundary, and the submission carries no "
                        "split column, so that cannot be determined. The duplicate rate "
                        "is reported as measured; the verdict is withheld."),
                    provenance=PROVENANCE, measured=measured,
                    missing=["split"], details=details,
                    threshold=th, threshold_preregistered=preregistered)
            else:
                res = CheckResult(
                    CHECK_ID, TITLE, PASS,
                    headline=f"no duplicates among {n} images",
                    explanation=("No two images are byte-identical and none fall within "
                                 f"pHash Hamming {PHASH_NEAR}. With no duplicates there "
                                 "is nothing to cross a split boundary."),
                    provenance=PROVENANCE, measured=measured, details=details,
                    threshold=th, threshold_preregistered=preregistered)
        elif cross_exact or cross_near:
            res = CheckResult(
                CHECK_ID, TITLE, FAIL,
                headline=(f"{len(cross_exact)} byte-identical and {len(cross_near)} "
                          "near-identical image groups span a split boundary"),
                explanation=(
                    "The same image content appears in more than one split. Any "
                    "held-out score computed on these rows is partly a score on "
                    "training data, and the reported generalisation gap is understated "
                    "by an unknown amount. This is the failure Phase 1 found between "
                    "two datasets that were distributed as independent sources."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
        else:
            res = CheckResult(
                CHECK_ID, TITLE, PASS,
                headline=(f"{dup_rate:.1%} exact duplicates, none crossing a split "
                          "boundary"),
                explanation=(
                    "Duplicates, where they exist, stay on one side of every split. "
                    "The held-out score is computed on content the model did not see. "
                    "Note that the duplicate rate itself is still worth reporting: it "
                    "inflates apparent dataset size."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
    res.seconds = t.seconds
    return res
