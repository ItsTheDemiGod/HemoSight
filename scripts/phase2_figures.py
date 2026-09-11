"""Phase 2 figures.

1. N1a: angular error by method, per camera (the prior ablation made visible).
2. N1b KEY FIGURE: per-subject DeltaE2000 spread, before vs after, all methods.
3. Segmentation IoU by device and lighting (the confounder check).

    .\\.venv\\Scripts\\python.exe scripts\\phase2_figures.py
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from hemosight.io import paths  # noqa: E402

IN = paths.INTERIM / "phase2"


def fig_n1a():
    f = IN / "n1a_nus8_results.json"
    if not f.exists():
        return
    r = json.loads(f.read_text(encoding="utf-8"))
    pooled = r.get("pooled_all_methods", {})
    if not pooled:
        return
    items = sorted(pooled.items(), key=lambda kv: kv[1]["mean"])
    names = [k.replace("reference_patch/", "sclera-analogue: ").replace("classical/", "")
             for k, _ in items]
    means = [v["mean"] for _, v in items]
    med = [v["median"] for _, v in items]
    w25 = [v["worst25"] for _, v in items]
    colours = ["#C44E52" if k.startswith("reference_patch") else "#4C72B0"
               for k, _ in items]

    fig, ax = plt.subplots(figsize=(10, 5))
    y = np.arange(len(names))
    ax.barh(y, means, color=colours, alpha=0.9, label="mean")
    ax.plot(med, y, "o", color="black", ms=5, label="median")
    ax.plot(w25, y, "d", color="grey", ms=5, label="worst 25%")
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("angular error (degrees) - lower is better")
    ax.set_title("N1a: illuminant estimation on nus8, 6 cameras\n"
                 "red = reference-patch methods (sclera analogue), blue = classical baselines",
                 fontsize=11)
    ax.legend(loc="lower right"); ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out = paths.FIGURES / "phase2_n1a_angular_error.png"
    fig.savefig(out, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("wrote", out.name)


def fig_n1b():
    f = IN / "n1b_selfconsistency.json"
    if not f.exists():
        print("  (n1b results not present yet)")
        return
    r = json.loads(f.read_text(encoding="utf-8"))
    for region in r.get("spread", {}):
        data = r["spread"][region]
        methods = sorted(data, key=lambda m: data[m]["mean_pairwise_dE"])
        series = [list(data[m]["per_subject_mean_pairwise"].values()) for m in methods]

        fig, ax = plt.subplots(figsize=(11, 5.5))
        bp = ax.boxplot(series, tick_labels=[m.replace("sclera_prior_", "sclera:")
                                             for m in methods],
                        showfliers=False, patch_artist=True)
        for patch, m in zip(bp["boxes"], methods):
            patch.set_facecolor("#C44E52" if m.startswith("sclera") else "#4C72B0")
            patch.set_alpha(0.75)
        for i, s in enumerate(series, start=1):
            x = np.random.default_rng(0).normal(i, 0.05, len(s))
            ax.plot(x, s, ".", color="black", ms=3, alpha=0.35)
        ax.set_ylabel("within-subject $\\Delta E_{2000}$ spread across\n"
                      "3 phones x 3 lighting conditions")
        ax.set_xlabel("method")
        primary = " [PRIMARY, non-circular]" if region == "iris" else " [secondary]"
        ax.set_title(f"N1b: per-subject colour consistency after correction - "
                     f"region: {region}{primary}\nlower = the correction actually removed "
                     f"the capture-condition variation", fontsize=11)
        ax.tick_params(axis="x", rotation=25)
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        out = paths.FIGURES / f"phase2_n1b_spread_{region}.png"
        fig.savefig(out, dpi=130, bbox_inches="tight"); plt.close(fig)
        print("wrote", out.name)


def fig_segmentation():
    f = IN / "segmentation_eval.json"
    if not f.exists():
        print("  (segmentation eval not present yet)")
        return
    r = json.loads(f.read_text(encoding="utf-8"))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for ax, key, title in ((axes[0], "by_phone", "by device"),
                           (axes[1], "by_lighting", "by lighting condition")):
        d = r.get(key, {})
        if not d:
            continue
        names = list(d)
        vals = [d[n]["sclera_iou"] for n in names]
        ax.bar(range(len(names)), vals, color="#55A868", alpha=0.9)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
        ax.set_ylim(0, 1)
        ax.axhline(np.mean(vals), color="crimson", ls="--", lw=1,
                   label=f"mean {np.mean(vals):.3f}")
        ax.set_ylabel("sclera IoU")
        ax.set_title(f"Segmentation quality {title}\nspread = "
                     f"{max(vals)-min(vals):.3f}", fontsize=10)
        ax.legend(); ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Does segmentation quality depend on capture device? "
                 "(a device effect here would confound every N1b result)", fontsize=11)
    fig.tight_layout()
    out = paths.FIGURES / "phase2_segmentation_by_device.png"
    fig.savefig(out, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("wrote", out.name)


def main() -> int:
    paths.ensure_dirs()
    fig_n1a()
    fig_n1b()
    fig_segmentation()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
