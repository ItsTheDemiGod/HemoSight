"""Phase 3 / Phase 6.5 Task 1 - the EMPIRICAL colour-per-haemoglobin signal, measured.

The figure "~0.70 dE2000 per g/dL on 216 Eyes-Defy subjects" was, until 2026-09-12, a
string constant in `tissue_simulator_gate_report_phase3.py` with no producing script and no stored output
(`reports/claude_md_audit.md`, section 3). It is the numerator of the noise/signal
ratio that closed the imaging arm. This script measures it from the data and writes
`data/interim/phase3/empirical_signal.json`; the report reads that file.

Method (matches the description on record, now made explicit):
  1. For every Eyes-Defy subject with a trusted Hb and a palpebral mask, take the
     dataset's own `_palpebral.png` (RGBA cutout, alpha > 0 marks the region). The
     JPEG is resampled to the mask's size and the colour is read from the JPEG, not
     from the cutout's own RGB channels.
  2. Per-subject colour = mean linear-sRGB over mask pixels whose luminance lies
     between the 5th and 95th percentile inside the mask (trims specular highlights
     and shadowed folds), converted to CIELAB under D65. NO colour correction is
     applied in the primary figure: the images are as captured. A secondary figure
     applies grey-world on a tight crop around the mask (the project's recommended
     normalisation) so the effect of that step on the apparent signal is visible.
  3. BINNED estimate (the one on record): subjects binned by Hb in 1 g/dL bins; mean
     Lab per bin; CIEDE2000 between adjacent bin means divided by the difference of
     their mean Hb; averaged over adjacent pairs, weighted by the smaller bin count.
     Reported with and without bins of n < 5, because the original quoted figure
     excluded an n=3 lowest bin as sampling noise.
  4. REGRESSION estimate (the HEADLINE, no binning): OLS of (L*, a*, b*) on Hb with
     site, sex and age as covariates; the signal is CIEDE2000 between the fitted
     colour at the median Hb and at median + 1 g/dL. Bootstrap over subjects for a
     95% CI. Sex matters: men carry higher Hb (r = 0.55 here) and the site-only slope
     counts sex-linked colour as haemoglobin signal. The site-only figure is kept as
     an explicit upper bound.
  4b. PERMUTATION NULL for every estimator (Hb shuffled across subjects, 500 draws).
     CIEDE2000 is a distance and is biased upward by noise; the binned estimator's
     null turned out to be ~2.1 dE2000/g/dL - it cannot measure the signal at all,
     which is why the figure on record is withdrawn rather than corrected.
  5. Everything is also reported per site, because India and Italy differ in device
     variant and illumination and the two must not be assumed alike.

Caveats carried into the output: bin-to-bin differences contain inter-subject,
capture and device variation as well as haemoglobin, so this is an UPPER bound on the
haemoglobin signal; and the JPEGs are camera-processed sRGB, not linear sensor data.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hemosight.io.manifests import trusted_hb  # noqa: E402

MANIFEST = ROOT / "data" / "interim" / "manifests" / "eyes_defy.csv"
OUT_DIR = ROOT / "data" / "interim" / "phase3"
OUT = OUT_DIR / "empirical_signal.json"
SEED = 20260911
BIN_WIDTH = 1.0
MIN_BIN_N = 5
LUM_TRIM = (5.0, 95.0)
CROP_MARGIN = 1.0      # grey-world crop: mask bbox expanded by this fraction each side

# sRGB (D65) -> XYZ, IEC 61966-2-1
_M = np.array([[0.4124564, 0.3575761, 0.1804375],
               [0.2126729, 0.7151522, 0.0721750],
               [0.0193339, 0.1191920, 0.9503041]])
_D65 = np.array([0.95047, 1.0, 1.08883])


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float64) / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_lab(rgb: np.ndarray) -> np.ndarray:
    xyz = rgb @ _M.T
    r = xyz / _D65
    eps, kappa = 216 / 24389, 24389 / 27
    f = np.where(r > eps, np.cbrt(r), (kappa * r + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def de2000(a: np.ndarray, b: np.ndarray) -> float:
    from colour.difference import delta_E_CIE2000
    return float(delta_E_CIE2000(np.asarray(a, float), np.asarray(b, float)))


def palpebral_mask_path(row) -> Path | None:
    """The palpebral-only mask. `_forniceal_palpebral.png` also ends in
    `_palpebral.png`, and a first version of this script picked it up - the bug is
    kept out by the explicit exclusion."""
    for p in str(row["mask_paths"]).split("|"):
        if p.endswith("_palpebral.png") and not p.endswith("_forniceal_palpebral.png"):
            return Path(p)
    return None


def mask_region(mask: np.ndarray) -> tuple[np.ndarray, str]:
    """Eyes-Defy ships THREE mask encodings, found by inspecting all 216 files:
      - RGBA cutout, alpha > 0 marks the region                (185 files)
      - RGB(A) cutout on a WHITE background, alpha all 255      (30 files, Italy 1-31)
      - 3-channel cutout on a white background, no alpha        (1 file, Italy 9)
    Every format's cutout pixels were checked against the resampled JPEG: mean
    |mask - JPEG| inside the region is <= 2.3/255, so the region is aligned."""
    rgb = mask[..., :3]
    if mask.ndim == 3 and mask.shape[2] == 4 and not (mask[..., 3] > 0).all():
        return mask[..., 3] > 0, "alpha_cutout"
    white = (rgb.min(axis=2) > 245).mean()
    if white > 0.3:
        return rgb.min(axis=2) <= 245, "white_background"
    return rgb.max(axis=2) > 10, "black_background"


def subject_colour(img_path: Path, mask_path: Path) -> dict | None:
    mask = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
    img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
    if mask is None or img is None or mask.ndim != 3 or mask.shape[2] not in (3, 4):
        return None
    h, w = mask.shape[:2]
    img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)[..., ::-1]  # BGR->RGB
    region, fmt = mask_region(mask)
    if region.sum() < 50 or region.mean() > 0.6:
        return None
    # Alignment check: the mask's own cutout pixels must match the resampled JPEG.
    align = float(np.abs(img[region].astype(float)
                         - mask[..., :3][..., ::-1][region].astype(float)).mean())
    lin = srgb_to_linear(img)
    px = lin[region]
    lum = px @ np.array([0.2126, 0.7152, 0.0722])
    lo, hi = np.percentile(lum, LUM_TRIM)
    keep = (lum >= lo) & (lum <= hi)
    raw_rgb = px[keep].mean(axis=0)

    # Grey-world on a tight crop around the mask (Phase 2.5 recommendation).
    ys, xs = np.where(region)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    dy, dx = int((y1 - y0) * CROP_MARGIN), int((x1 - x0) * CROP_MARGIN)
    crop = lin[max(0, y0 - dy):y1 + dy + 1, max(0, x0 - dx):x1 + dx + 1]
    gw = crop.reshape(-1, 3).mean(axis=0)
    gw = gw / gw.mean()
    gw_rgb = raw_rgb / np.clip(gw, 1e-6, None)
    return {"raw_rgb": raw_rgb, "gw_rgb": gw_rgb, "n_pixels": int(region.sum()),
            "n_used": int(keep.sum()), "mask_format": fmt,
            "region_fraction": float(region.mean()), "mask_jpeg_abs_diff": align}


def binned_signal(lab: np.ndarray, hb: np.ndarray, min_n: int) -> dict:
    edges = np.arange(np.floor(hb.min()), np.ceil(hb.max()) + BIN_WIDTH, BIN_WIDTH)
    idx = np.digitize(hb, edges) - 1
    bins = []
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() == 0:
            continue
        bins.append({"lo": float(edges[b]), "hi": float(edges[b + 1]), "n": int(m.sum()),
                     "hb_mean": float(hb[m].mean()), "lab_mean": lab[m].mean(axis=0)})
    pairs, kept = [], [x for x in bins if x["n"] >= min_n]
    for a, b in zip(kept[:-1], kept[1:]):
        d_hb = b["hb_mean"] - a["hb_mean"]
        if d_hb <= 0:
            continue
        pairs.append({"from": f"{a['lo']:.0f}-{a['hi']:.0f}", "to": f"{b['lo']:.0f}-{b['hi']:.0f}",
                      "n_from": a["n"], "n_to": b["n"], "d_hb": float(d_hb),
                      "de2000": de2000(a["lab_mean"], b["lab_mean"]),
                      "de_per_g_dl": de2000(a["lab_mean"], b["lab_mean"]) / d_hb})
    if not pairs:
        return {"bins": [], "pairs": [], "de_per_g_dl_weighted": None}
    w = np.array([min(p["n_from"], p["n_to"]) for p in pairs], float)
    v = np.array([p["de_per_g_dl"] for p in pairs])
    return {
        "bins": [{k: (v_.tolist() if isinstance(v_, np.ndarray) else v_) for k, v_ in x.items()}
                 for x in bins],
        "pairs": pairs,
        "de_per_g_dl_weighted": float((w * v).sum() / w.sum()),
        "de_per_g_dl_unweighted": float(v.mean()),
        "min_bin_n_applied": min_n,
    }


def regression_signal(lab: np.ndarray, hb: np.ndarray, site: np.ndarray,
                      rng: np.random.Generator, n_boot: int = 2000,
                      covariates: dict[str, np.ndarray] | None = None) -> dict:
    """CIEDE2000 between the fitted colour at median Hb and at median + 1 g/dL, from
    OLS of Lab on Hb + site (+ any extra covariates). The covariates cancel in the
    difference, so only the Hb slope survives; adjusting for sex and age removes the
    colour change that travels WITH Hb (men have higher Hb: r = 0.55 here) but is
    not caused by it. Bootstrap over subjects for the CI."""
    sites = sorted(set(site.tolist()))
    cov = covariates or {}

    def design(idx):
        cols = [np.ones(len(idx)), hb[idx]] + [(site[idx] == x).astype(float) for x in sites[1:]]
        cols += [v[idx] for v in cov.values()]
        return np.stack(cols, axis=1)

    all_idx = np.arange(len(hb))
    beta, *_ = np.linalg.lstsq(design(all_idx), lab, rcond=None)     # (k, 3)
    h0 = float(np.median(hb))

    def signal(b):
        return de2000(b[0] + b[1] * h0, b[0] + b[1] * (h0 + 1.0))

    point = signal(beta)
    boots = []
    n = len(hb)
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        bb, *_ = np.linalg.lstsq(design(i), lab[i], rcond=None)
        boots.append(signal(bb))
    boots = np.array(boots)
    from colour.difference import delta_E_CIE2000
    resid = delta_E_CIE2000(lab, design(all_idx) @ beta)
    return {"de_per_g_dl": point, "ci95": [float(np.percentile(boots, 2.5)),
                                            float(np.percentile(boots, 97.5))],
            "lab_slope_per_g_dl": beta[1].tolist(), "at_hb": h0, "n_boot": n_boot,
            "covariates": ["site"] + list(cov.keys()),
            "residual_de2000_mean": float(resid.mean()),
            "residual_de2000_median": float(np.median(resid))}


def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = trusted_hb(pd.read_csv(MANIFEST))
    rows, skipped = [], []
    for _, r in df.iterrows():
        mp = palpebral_mask_path(r)
        if mp is None or not mp.exists():
            skipped.append((r["image_id"], "no palpebral mask"))
            continue
        c = subject_colour(Path(r["file_path"]), mp)
        if c is None:
            skipped.append((r["image_id"], "unreadable or empty mask"))
            continue
        rows.append({"image_id": r["image_id"], "subject_id": r["subject_id"],
                     "site": r["site"], "hb": float(r["hb_g_dl"]),
                     "male": float(str(r["sex"]).strip().upper() == "M"),
                     "age": float(r["age"]), **c})
    print(f"subjects measured: {len(rows)}  skipped: {len(skipped)}  ({time.time()-t0:.0f}s)")
    for s in skipped:
        print("  skipped:", s)

    hb = np.array([r["hb"] for r in rows])
    site = np.array([r["site"] for r in rows])
    male = np.array([r["male"] for r in rows])
    age = np.array([r["age"] for r in rows])
    ADJ = {"male": male, "age": age}
    lab_raw = linear_to_lab(np.stack([r["raw_rgb"] for r in rows]))
    lab_gw = linear_to_lab(np.stack([r["gw_rgb"] for r in rows]))
    rng = np.random.default_rng(SEED)

    res = {"n_subjects": len(rows), "n_skipped": len(skipped), "skipped": skipped,
           "hb_range": [float(hb.min()), float(hb.max())], "bin_width_g_dl": BIN_WIDTH,
           "luminance_trim_percentiles": LUM_TRIM, "seed": SEED,
           "per_site_n": {s: int((site == s).sum()) for s in sorted(set(site))},
           "mask_formats": {f: sum(1 for r in rows if r["mask_format"] == f)
                            for f in sorted({r["mask_format"] for r in rows})},
           "mask_jpeg_abs_diff_max": float(max(r["mask_jpeg_abs_diff"] for r in rows)),
           "region_fraction_range": [float(min(r["region_fraction"] for r in rows)),
                                     float(max(r["region_fraction"] for r in rows))],
           "method": {"colour": "mean linear-sRGB over palpebral mask (alpha>0), "
                                "luminance-trimmed 5-95%, CIELAB D65; JPEG resampled to "
                                "mask size (INTER_AREA)",
                      "binned": "1 g/dL bins, CIEDE2000 between adjacent bin means / "
                                "d(mean Hb), weighted by min(n) of the pair",
                      "regression": "OLS Lab ~ Hb + site; CIEDE2000 between fitted colour "
                                    "at median Hb and median+1; 2000 bootstrap resamples"},
           "conditions": {}}

    for name, lab in (("raw_as_captured", lab_raw), ("grey_world_tight_crop", lab_gw)):
        cond = {"all_sites": {
            "binned_all_bins": binned_signal(lab, hb, 1),
            "binned_min_n": binned_signal(lab, hb, MIN_BIN_N),
            "regression_site": regression_signal(lab, hb, site, rng),
            "regression_site_sex": regression_signal(lab, hb, site, rng,
                                                     covariates={"male": male}),
            "regression_site_sex_age": regression_signal(lab, hb, site, rng,
                                                         covariates=ADJ)},
            "per_site": {}}
        for s in sorted(set(site)):
            m = site == s
            cond["per_site"][s] = {
                "n": int(m.sum()),
                "binned_min_n": binned_signal(lab[m], hb[m], MIN_BIN_N),
                "regression_site": regression_signal(lab[m], hb[m], site[m], rng, 1000),
                "regression_site_sex_age": regression_signal(
                    lab[m], hb[m], site[m], rng, 1000,
                    covariates={"male": male[m], "age": age[m]})}
        res["conditions"][name] = cond

    # ------------------------------------------------------------------ nulls
    # What does each estimator return when there is NO haemoglobin signal? Hb is
    # shuffled across subjects; everything else (colours, sites, sex, age, bin
    # counts) is kept. CIEDE2000 is a distance, so both estimators are biased upward
    # by noise; the null says by how much. A signal is credible only above its own
    # estimator's null.
    N_PERM = 500
    site_cols = [(site == x).astype(float) for x in sorted(set(site))[1:]]

    def site_design(h):
        return np.stack([np.ones_like(h), h] + site_cols, axis=1)

    def adj_design(h):
        return np.stack([np.ones_like(h), h] + site_cols + [male, age], axis=1)

    null_b, null_r, null_a = [], [], []
    for _ in range(N_PERM):
        hp = rng.permutation(hb)
        null_b.append(binned_signal(lab_raw, hp, MIN_BIN_N)["de_per_g_dl_weighted"])
        h0 = float(np.median(hp))
        bb, *_ = np.linalg.lstsq(site_design(hp), lab_raw, rcond=None)
        null_r.append(de2000(bb[0] + bb[1] * h0, bb[0] + bb[1] * (h0 + 1.0)))
        ba, *_ = np.linalg.lstsq(adj_design(hp), lab_raw, rcond=None)
        null_a.append(de2000(ba[0] + ba[1] * h0, ba[0] + ba[1] * (h0 + 1.0)))
    A = res["conditions"]["raw_as_captured"]["all_sites"]

    def null_block(null, real):
        null = np.array(null)
        return {"null_mean": float(null.mean()), "null_sd": float(null.std()),
                "null_p95": float(np.percentile(null, 95)), "real": real,
                "p_empirical": float((np.sum(null >= real) + 1) / (N_PERM + 1)),
                "real_minus_null_mean": float(real - null.mean())}

    res["permutation_null"] = {
        "n_perm": N_PERM,
        "binned_min_n": null_block(null_b, A["binned_min_n"]["de_per_g_dl_weighted"]),
        "regression_site": null_block(null_r, A["regression_site"]["de_per_g_dl"]),
        "regression_site_sex_age": null_block(null_a, A["regression_site_sex_age"]["de_per_g_dl"]),
        "note": "The binned estimator's null is what it returns with NO Hb signal; the "
                "excess over the null, not the raw figure, is what it detects.",
    }

    prim = res["conditions"]["raw_as_captured"]["all_sites"]
    adj = prim["regression_site_sex_age"]
    sig = adj["de_per_g_dl"]
    res["headline"] = {
        "de_per_g_dl": sig,
        "ci95": adj["ci95"],
        "estimator": "OLS Lab ~ Hb + site + sex + age; CIEDE2000 per +1 g/dL at median Hb",
        "null_mean": res["permutation_null"]["regression_site_sex_age"]["null_mean"],
        "upper_bound_site_only": prim["regression_site"]["de_per_g_dl"],
        "upper_bound_site_only_ci95": prim["regression_site"]["ci95"],
        "binned_method_on_record": prim["binned_min_n"]["de_per_g_dl_weighted"],
        "binned_method_null_mean": res["permutation_null"]["binned_min_n"]["null_mean"],
        "binned_method_p": res["permutation_null"]["binned_min_n"]["p_empirical"],
        "per_site": {s: d["regression_site_sex_age"]["de_per_g_dl"]
                     for s, d in res["conditions"]["raw_as_captured"]["per_site"].items()},
        "grey_world_tight_crop": res["conditions"]["grey_world_tight_crop"]["all_sites"]
                                    ["regression_site_sex_age"]["de_per_g_dl"],
        "residual_between_subject_de2000_at_fixed_hb_sex_age_site": adj["residual_de2000_mean"],
        "previously_reported_hardcoded": 0.70,
        "verdict_on_previous_figure": "WITHDRAWN as a measurement: the binned method it was "
            "attributed to returns ~2.1 dE2000/g/dL with Hb shuffled (its null), so it "
            "cannot resolve the signal. The regression figure adjusted for site, sex and "
            "age happens to bracket 0.70, which is coincidence, not confirmation.",
        "note": "Every figure here is an UPPER bound on the haemoglobin signal: colour "
                "correlates of Hb that are not in the covariates (skin tone, perfusion, "
                "tissue thickness) are still counted as signal.",
    }
    res["noise_over_signal"] = {
        "signal_used": sig, "signal_ci95": adj["ci95"],
        "grey_world_25pct_fov_3.935": 3.935 / sig,
        "grey_world_25pct_fov_3.935_ci95": [3.935 / adj["ci95"][1], 3.935 / adj["ci95"][0]],
        "grey_world_full_frame_6.076": 6.076 / sig,
        "equivalent_hb_error_g_dl_at_3.935": 3.935 / sig,
        "equivalent_hb_error_g_dl_at_3.935_using_upper_bound_signal":
            3.935 / prim["regression_site"]["de_per_g_dl"],
        "between_subject_residual_in_hb_equivalents": adj["residual_de2000_mean"] / sig,
        "simulated_signal_0.452_ratio_to_empirical": sig / 0.452,
    }
    OUT.write_text(json.dumps(res, indent=2, default=float), encoding="utf-8")

    print("\n=== EMPIRICAL SIGNAL (raw, as captured) ===")
    H = res["headline"]; pn = res["permutation_null"]
    print(f"  binned (method on record, bins n>={MIN_BIN_N}): {H['binned_method_on_record']:.3f}"
          f"   NULL {H['binned_method_null_mean']:.3f} +/- {pn['binned_min_n']['null_sd']:.3f}"
          f"  p={H['binned_method_p']:.3f}  -> CANNOT MEASURE THE SIGNAL")
    for p_ in prim["binned_all_bins"]["pairs"]:
        print(f"    {p_['from']:>6} -> {p_['to']:<6} n={p_['n_from']:>3}/{p_['n_to']:<3} "
              f"dE={p_['de2000']:.3f}  per g/dL={p_['de_per_g_dl']:.3f}")
    r1 = prim["regression_site"]; r3 = prim["regression_site_sex_age"]
    print(f"  regression Hb+site (upper bound):      {r1['de_per_g_dl']:.3f}  CI {r1['ci95'][0]:.2f}-{r1['ci95'][1]:.2f}"
          f"   NULL {pn['regression_site']['null_mean']:.3f} p={pn['regression_site']['p_empirical']:.3f}")
    print(f"  regression Hb+site+sex+age (HEADLINE): {r3['de_per_g_dl']:.3f}  CI {r3['ci95'][0]:.2f}-{r3['ci95'][1]:.2f}"
          f"   NULL {pn['regression_site_sex_age']['null_mean']:.3f} p={pn['regression_site_sex_age']['p_empirical']:.3f}")
    print(f"  per site (adjusted): {H['per_site']}")
    print(f"  grey-world tight crop (adjusted): {H['grey_world_tight_crop']:.3f}")
    print(f"  between-subject residual at fixed Hb/sex/age/site: {r3['residual_de2000_mean']:.2f} dE2000"
          f" = {res['noise_over_signal']['between_subject_residual_in_hb_equivalents']:.1f} g/dL equivalent")
    ns = res["noise_over_signal"]
    print(f"  noise/signal @3.935: {ns['grey_world_25pct_fov_3.935']:.2f}x "
          f"(CI {ns['grey_world_25pct_fov_3.935_ci95'][0]:.2f}-{ns['grey_world_25pct_fov_3.935_ci95'][1]:.2f}); "
          f"@6.076: {ns['grey_world_full_frame_6.076']:.2f}x; empirical/simulated = {ns['simulated_signal_0.452_ratio_to_empirical']:.2f}x")
    print(f"\nwrote {OUT}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
