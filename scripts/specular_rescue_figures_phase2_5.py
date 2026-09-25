"""Phase 2.5 figures.

1. Method comparison on the held-out iris, with Phase 2 and Phase 2.5 methods together.
2. The Task 4 crop curve - the result that went opposite to the hypothesis.

    .\\.venv\\Scripts\\python.exe scripts\\specular_rescue_figures_phase2_5.py
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from hemosight.io import paths  # noqa: E402

IN = paths.INTERIM / "phase2_5"


def fig_methods():
    ev = json.loads((IN / "evaluation.json").read_text(encoding="utf-8"))
    sp = ev["spread"]
    methods = sorted(sp, key=lambda m: sp[m]["mean_pairwise_dE"])
    series = [list(sp[m]["per_subject_mean_pairwise"].values()) for m in methods]

    colours = []
    for m in methods:
        if m.startswith("specular"):
            colours.append("#C44E52")       # Phase 2.5 specular
        elif m.startswith("sclera"):
            colours.append("#DD8452")       # Phase 2 sclera
        elif m == "none":
            colours.append("#8C8C8C")
        else:
            colours.append("#4C72B0")       # classical

    fig, ax = plt.subplots(figsize=(12, 5.5))
    bp = ax.boxplot(series, tick_labels=methods, showfliers=False, patch_artist=True)
    for patch, c in zip(bp["boxes"], colours):
        patch.set_facecolor(c)
        patch.set_alpha(0.8)
    rng = np.random.default_rng(0)
    for i, s in enumerate(series, start=1):
        ax.plot(rng.normal(i, 0.05, len(s)), s, ".", color="black", ms=3, alpha=0.35)
    gw = sp["grey_world"]["mean_pairwise_dE"]
    ax.axhline(gw, color="#4C72B0", ls="--", lw=1.2,
               label=f"grey-world mean = {gw:.2f}")
    ax.set_ylabel("within-subject $\\Delta E_{2000}$ spread\n(3 phones x 3 lighting)")
    ax.set_title("Phase 2.5: every illuminant reference tested, on the held-out iris\n"
                 "red = corneal specular (Phase 2.5), orange = sclera (Phase 2), "
                 "blue = classical, grey = no correction", fontsize=11)
    ax.tick_params(axis="x", rotation=28)
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = paths.FIGURES / "phase2_5_method_comparison.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out.name)


def fig_crop():
    ev = json.loads((IN / "evaluation.json").read_text(encoding="utf-8"))
    crops = {float(k): v["mean_pairwise_dE"] for k, v in ev["crop"].items()
             if k.replace(".", "").isdigit()}
    if not crops:
        return
    xs = sorted(crops)
    ys = [crops[x] for x in xs]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot([x * 100 for x in xs], ys, "o-", color="#4C72B0", lw=2, ms=8,
            label="grey-world (needs scene context)")
    for m, c, ls in (("specular", "#C44E52", "--"),
                     ("sclera_fitted_prior", "#DD8452", "--"),
                     ("none", "#8C8C8C", ":")):
        if m in ev["crop"]:
            ax.axhline(ev["crop"][m]["mean_pairwise_dE"], color=c, ls=ls, lw=1.6,
                       label=f"{m} (crop-invariant)")
    best = min(crops, key=crops.get)
    ax.annotate(f"best: {crops[best]:.2f} at {best*100:.0f}% FOV",
                xy=(best * 100, crops[best]), xytext=(best * 100 + 14, crops[best] - 1.1),
                arrowprops=dict(arrowstyle="->", color="crimson"), color="crimson",
                fontsize=10)
    ax.set_xlabel("field of view retained (%) - tighter crop to the left")
    ax.set_ylabel("within-subject $\\Delta E_{2000}$ spread")
    ax.set_title("Task 4: grey-world was expected to DEGRADE as scene context vanished.\n"
                 "It improves - a wide frame is skin-dominated, a periocular crop is "
                 "better balanced.", fontsize=11)
    ax.invert_xaxis()
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    out = paths.FIGURES / "phase2_5_crop_sensitivity.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out.name)


def main() -> int:
    paths.ensure_dirs()
    fig_methods()
    fig_crop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
