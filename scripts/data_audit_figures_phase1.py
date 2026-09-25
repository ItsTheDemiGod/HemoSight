"""Phase 1 figures for reports/figures/.

1. Cross-set duplicate pairs (CP-AnemiC vs Ghana conjunctiva) at pHash distance 0.
2. One CP-AnemiC exact-duplicate group whose rows carry conflicting Hb values.
3. Haemoglobin distributions per dataset, with the severe-anemia region marked.

    .\\.venv\\Scripts\\python.exe scripts\\data_audit_figures_phase1.py
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

from hemosight.io import paths  # noqa: E402


def fig_cross_set_pairs(n=5):
    A = pd.read_csv(paths.OVERLAP / "hashes_cp_anemic.csv")
    B = pd.read_csv(paths.OVERLAP / "hashes_ghana_conj.csv")
    shared = set(A.md5) & set(B.md5)
    rows = []
    for m in list(shared)[:400]:
        a = A[A.md5 == m].iloc[0]
        b = B[B.md5 == m].iloc[0]
        rows.append((a, b))
        if len(rows) >= n:
            break
    fig, axes = plt.subplots(n, 2, figsize=(8, 2.2 * n))
    for r, (a, b) in enumerate(rows):
        for c, rec in enumerate((a, b)):
            ax = axes[r, c]
            with Image.open(rec.file_path) as im:
                ax.imshow(im.convert("RGB"))
            ax.set_title(paths.Path(rec.file_path).name, fontsize=8)
            ax.set_xticks([]); ax.set_yticks([])
        axes[r, 0].set_ylabel("MD5 identical", fontsize=8, color="crimson")
    axes[0, 0].text(0.5, 1.35, "CP-AnemiC", transform=axes[0, 0].transAxes,
                    ha="center", fontsize=12, fontweight="bold")
    axes[0, 1].text(0.5, 1.35, "Ghana conjunctiva", transform=axes[0, 1].transAxes,
                    ha="center", fontsize=12, fontweight="bold")
    fig.suptitle("Byte-identical images present in BOTH datasets\n"
                 f"{len(shared)} distinct MD5 hashes shared", fontsize=11, y=1.0)
    fig.tight_layout()
    out = paths.FIGURES / "phase1_overlap_cp_anemic__ghana_conj.png"
    fig.savefig(out, dpi=120, bbox_inches="tight"); plt.close(fig)
    print("wrote", out.name)


def fig_label_conflict():
    H = pd.read_csv(paths.OVERLAP / "hashes_cp_anemic.csv")
    cp = pd.read_csv(paths.MANIFESTS / "cp_anemic.csv")
    m = H.merge(cp[["image_id", "hb_g_dl", "hospital", "severity"]], on="image_id")
    g = m.groupby("md5").agg(n=("image_id", "size"), nhb=("hb_g_dl", "nunique"))
    worst = g[(g.n > 1)].sort_values(["nhb", "n"], ascending=False).index[0]
    rows = m[m.md5 == worst].sort_values("hb_g_dl")
    k = min(len(rows), 10)
    fig, axes = plt.subplots(1, k, figsize=(2.0 * k, 3.0))
    axes = np.atleast_1d(axes)
    for i in range(k):
        r = rows.iloc[i]
        with Image.open(r.file_path) as im:
            axes[i].imshow(im.convert("RGB"))
        axes[i].set_title(f"{r.image_id.split(':')[-1]}\nHb = {r.hb_g_dl} g/dL",
                          fontsize=8, color="crimson")
        axes[i].axis("off")
    fig.suptitle(
        "CP-AnemiC: one byte-identical image, "
        f"{rows.hb_g_dl.nunique()} different haemoglobin values, "
        f"{rows.hospital.nunique()} different hospitals",
        fontsize=12, fontweight="bold")
    fig.tight_layout()
    out = paths.FIGURES / "phase1_cp_anemic_label_conflict.png"
    fig.savefig(out, dpi=120, bbox_inches="tight"); plt.close(fig)
    print("wrote", out.name, f"(md5={worst[:8]}, n={len(rows)})")


def fig_hb_distributions():
    m = pd.read_csv(paths.MANIFESTS / "master.csv").dropna(subset=["hb_g_dl"])
    ds = ["cp_anemic", "eyes_defy", "hb_ppg"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), sharey=False)
    for ax, d in zip(axes, ds):
        v = m[m.dataset == d].hb_g_dl
        ax.hist(v, bins=28, color="#4C72B0", edgecolor="white")
        ax.axvspan(0, 7, color="crimson", alpha=0.12)
        ax.axvline(7, color="crimson", ls="--", lw=1.2)
        ax.set_title(f"{d}\nn={len(v)}, min={v.min():.1f}, severe(<7)={int((v<7).sum())}",
                     fontsize=10)
        ax.set_xlabel("Hb (g/dL)")
        ax.set_xlim(2, 19)
    axes[0].set_ylabel("images")
    fig.suptitle("Haemoglobin distributions. Red region = severe anemia (<7 g/dL); "
                 "present only in CP-AnemiC", fontsize=11)
    fig.tight_layout()
    out = paths.FIGURES / "phase1_hb_distributions.png"
    fig.savefig(out, dpi=120, bbox_inches="tight"); plt.close(fig)
    print("wrote", out.name)


def main() -> int:
    paths.ensure_dirs()
    fig_cross_set_pairs()
    fig_label_conflict()
    fig_hb_distributions()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
