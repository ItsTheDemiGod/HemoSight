"""Phase 1, Task 2: the participant-overlap check. HIGHEST PRIORITY.

Question: do CP-AnemiC and the Ghana conjunctiva dataset (Mendeley nt7r8hv2pz)
share participants? The same authors and hospitals collected both, so treating them
as independent sites would invalidate every cross-site claim built on them. The
Ghana fingernail set is checked against both, since the same participants may have
been photographed at more than one body site.

Two outcomes are meaningfully different:

* Same participant, SAME body site  -> contamination. Sites must be merged.
* Same participant, DIFFERENT body sites -> an N6 opportunity: genuine per-subject
  multimodal pairs (conjunctiva + nail) that allow real fusion rather than an
  ensemble over unrelated subjects.

Signals: MD5 (exact), dHash and pHash (near-duplicate), and ImageNet embedding
nearest neighbours (semantic). Metadata correspondence is attempted but the Ghana
sets ship no per-subject metadata, which is reported rather than worked around.

    .\\.venv\\Scripts\\python.exe scripts\\participant_overlap_check_phase1.py
"""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from hemosight.io import paths
from hemosight.io.hashing import dhash, hamming_matrix, md5_file, phash

# pHash Hamming threshold for "near-duplicate". 64-bit hash; <=10 is the common
# working value. The empirical distance distribution is reported so the choice can
# be checked rather than taken on faith.
PHASH_NEAR = 10
DHASH_NEAR = 10
EMBED_SIM = 0.92  # cosine similarity for the embedding signal

SETS = ["cp_anemic", "ghana_conj", "ghana_nail"]


def load_manifests() -> dict[str, pd.DataFrame]:
    return {s: pd.read_csv(paths.MANIFESTS / f"{s}.csv") for s in SETS}


def compute_hashes(df: pd.DataFrame, name: str) -> pd.DataFrame:
    cache = paths.OVERLAP / f"hashes_{name}.csv"
    if cache.exists():
        print(f"  [{name}] hashes cached")
        return pd.read_csv(cache)
    t0 = time.time()
    recs = []
    for i, r in enumerate(df.itertuples()):
        if i % 500 == 0:
            print(f"  [{name}] {i}/{len(df)}", end="\r", flush=True)
        p = paths.Path(r.file_path)
        recs.append(
            {
                "image_id": r.image_id,
                "subject_id": r.subject_id,
                "file_path": r.file_path,
                "md5": md5_file(p),
                "dhash": dhash(p),
                "phash": phash(p),
            }
        )
    out = pd.DataFrame(recs)
    out.to_csv(cache, index=False)
    print(f"  [{name}] hashed {len(out)} in {time.time()-t0:.0f}s")
    return out


def embed(df: pd.DataFrame, name: str) -> np.ndarray:
    """ResNet18 penultimate features, L2-normalised. Runs on the GPU."""
    cache = paths.OVERLAP / f"embed_{name}.npy"
    if cache.exists():
        print(f"  [{name}] embeddings cached")
        return np.load(cache)

    import torch
    from PIL import Image
    from torch.utils.data import DataLoader, Dataset
    from torchvision import models, transforms

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    net.fc = torch.nn.Identity()
    net = net.eval().to(dev)

    tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    class DS(Dataset):
        def __init__(self, paths_): self.p = paths_
        def __len__(self): return len(self.p)
        def __getitem__(self, i):
            try:
                with Image.open(self.p[i]) as im:
                    return tf(im.convert("RGB"))
            except Exception:
                return torch.zeros(3, 224, 224)

    dl = DataLoader(DS(df.file_path.tolist()), batch_size=64, num_workers=0)
    feats = []
    t0 = time.time()
    with torch.no_grad():
        for j, b in enumerate(dl):
            f = net(b.to(dev))
            feats.append(torch.nn.functional.normalize(f, dim=1).cpu().numpy())
            print(f"  [{name}] embed batch {j+1}/{len(dl)}", end="\r", flush=True)
    out = np.concatenate(feats).astype(np.float32)
    np.save(cache, out)
    print(f"  [{name}] embedded {len(out)} on {dev} in {time.time()-t0:.0f}s")
    return out


def pair_report(a_name, b_name, A, B, Ea, Eb) -> dict:
    """Compare two sets on all available signals."""
    print(f"\n--- {a_name} vs {b_name} ---")
    res = {"pair": f"{a_name}|{b_name}", "n_a": len(A), "n_b": len(B)}

    # 1. exact MD5
    common = set(A.md5) & set(B.md5)
    res["md5_exact_pairs"] = int(sum((A.md5 == m).sum() * (B.md5 == m).sum() for m in common))
    res["md5_distinct_hashes_shared"] = len(common)
    print(f"MD5 identical files: {len(common)} distinct hashes shared")

    # 2/3. perceptual hashes
    for tag, thresh in (("phash", PHASH_NEAR), ("dhash", DHASH_NEAR)):
        ha = A[tag].to_numpy(dtype=np.uint64)
        hb = B[tag].to_numpy(dtype=np.uint64)
        best = np.full(len(A), 64, dtype=np.uint8)
        best_j = np.zeros(len(A), dtype=np.int64)
        step = 2000
        for s in range(0, len(B), step):
            d = hamming_matrix(ha, hb[s:s + step])
            j = d.argmin(axis=1)
            v = d[np.arange(len(A)), j]
            upd = v < best
            best[upd] = v[upd]
            best_j[upd] = j[upd] + s
        res[f"{tag}_min"] = int(best.min())
        res[f"{tag}_n_below_thresh"] = int((best <= thresh).sum())
        res[f"{tag}_frac_below_thresh"] = float((best <= thresh).mean())
        res[f"{tag}_pct_le"] = {str(t): int((best <= t).sum()) for t in (0, 2, 5, 10, 15, 20)}
        print(f"{tag}: min={best.min()} | <= {thresh}: {(best<=thresh).sum()}/{len(A)} "
              f"({(best<=thresh).mean()*100:.2f}%) | counts by threshold {res[f'{tag}_pct_le']}")
        if tag == "phash":
            res["_phash_best"] = best
            res["_phash_best_j"] = best_j

    # 4. embeddings
    sims = np.zeros(len(A), dtype=np.float32)
    idx = np.zeros(len(A), dtype=np.int64)
    step = 4096
    for s in range(0, len(A), step):
        S = Ea[s:s + step] @ Eb.T
        idx[s:s + step] = S.argmax(axis=1)
        sims[s:s + step] = S.max(axis=1)
    res["embed_max"] = float(sims.max())
    res["embed_mean"] = float(sims.mean())
    res["embed_n_above"] = int((sims >= EMBED_SIM).sum())
    res["embed_frac_above"] = float((sims >= EMBED_SIM).mean())
    res["_embed_sims"] = sims
    res["_embed_idx"] = idx
    print(f"embed: max={sims.max():.4f} mean={sims.mean():.4f} | "
          f">= {EMBED_SIM}: {(sims>=EMBED_SIM).sum()}/{len(A)} ({(sims>=EMBED_SIM).mean()*100:.2f}%)")
    return res


def save_examples(a_name, b_name, A, B, res, n=6):
    """Side-by-side figures for the closest pairs found."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    best = res["_phash_best"]
    best_j = res["_phash_best_j"]
    order = np.argsort(best)[:n]
    if len(order) == 0:
        return None
    fig, axes = plt.subplots(len(order), 2, figsize=(7, 3.1 * len(order)))
    axes = np.atleast_2d(axes)
    for row, i in enumerate(order):
        j = best_j[i]
        for col, (df, k, tag) in enumerate(((A, i, a_name), (B, j, b_name))):
            ax = axes[row, col]
            try:
                with Image.open(df.file_path.iloc[k]) as im:
                    ax.imshow(im.convert("RGB"))
            except Exception:
                ax.text(0.5, 0.5, "unreadable", ha="center")
            ax.set_title(f"{tag}\n{paths.Path(df.file_path.iloc[k]).name}", fontsize=7)
            ax.axis("off")
        axes[row, 0].set_ylabel(f"pHash d={best[i]}")
        fig.text(0.5, axes[row, 0].get_position().y1, f"pHash Hamming = {best[i]}",
                 ha="center", fontsize=9, color="crimson")
    fig.suptitle(f"Closest cross-set pairs: {a_name} vs {b_name}", fontsize=11)
    fig.tight_layout()
    out = paths.FIGURES / f"phase1_overlap_{a_name}__{b_name}.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"  figure -> {out.name}")
    return out


def intra_duplicates(H: pd.DataFrame, name: str) -> dict:
    """Duplicate detection WITHIN one dataset. The Ghana conjunctiva filenames carry
    162 ' - Copy' markers, so internal duplication is expected and matters: it
    inflates apparent dataset size and leaks across folds if split naively."""
    md5_groups = H.groupby("md5").size()
    dup_md5 = md5_groups[md5_groups > 1]
    n_extra = int((dup_md5 - 1).sum())
    # how many exact-duplicate groups span more than one subject_id?
    cross = 0
    for m in dup_md5.index:
        if H.loc[H.md5 == m, "subject_id"].nunique() > 1:
            cross += 1
    print(f"[{name}] exact duplicate groups={len(dup_md5)} redundant files={n_extra} "
          f"groups spanning >1 subject_id={cross}")
    return {
        "dataset": name,
        "n_files": len(H),
        "dup_groups": int(len(dup_md5)),
        "redundant_files": n_extra,
        "dup_groups_spanning_multiple_subjects": cross,
        "unique_md5": int(H.md5.nunique()),
    }


def main() -> int:
    paths.ensure_dirs()
    paths.OVERLAP.mkdir(parents=True, exist_ok=True)
    mans = load_manifests()

    print("=== hashing ===")
    H = {k: compute_hashes(v, k) for k, v in mans.items()}
    print("\n=== embedding ===")
    E = {k: embed(H[k], k) for k in SETS}

    print("\n=== intra-dataset duplicates ===")
    intra = [intra_duplicates(H[k], k) for k in SETS]

    print("\n=== cross-dataset overlap ===")
    results, figs = [], []
    pairs = [("cp_anemic", "ghana_conj"), ("cp_anemic", "ghana_nail"), ("ghana_conj", "ghana_nail")]
    for a, b in pairs:
        r = pair_report(a, b, H[a], H[b], E[a], E[b])
        figs.append(save_examples(a, b, H[a], H[b], r))
        results.append({k: v for k, v in r.items() if not k.startswith("_")})

    # Metadata correspondence: only CP-AnemiC ships per-subject metadata.
    meta_note = (
        "Metadata correspondence on (Hb, age, sex) could NOT be computed. CP-AnemiC "
        "is the only one of the three that ships per-subject metadata; the Ghana "
        "conjunctiva and fingernail sets provide no Hb, age or sex, only an "
        "anemic/non-anemic class in the filename. This signal is unavailable, not "
        "negative."
    )
    print("\n=== metadata correspondence ===\n" + meta_note)

    out = paths.OVERLAP / "overlap_results.json"
    out.write_text(json.dumps(
        {"pairs": results, "intra": intra, "metadata_note": meta_note,
         "thresholds": {"phash": PHASH_NEAR, "dhash": DHASH_NEAR, "embed_cos": EMBED_SIM}},
        indent=2, default=str), encoding="utf-8")
    print(f"\nresults -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
