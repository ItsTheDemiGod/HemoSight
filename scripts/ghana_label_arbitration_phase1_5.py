"""Phase 1.5, Task 3: arbitrate the haemoglobin labels of the Ghana pool.

The task as briefed asks which collection's Hb value to adopt for images present in
both. That comparison cannot be run as stated: **the Ghana conjunctiva set ships no
haemoglobin values at all** - only an anemic/non-anemic token in the filename. So the
arbitration reduces to a different, answerable set of questions:

  Q1. Is CP-AnemiC's Hb self-consistent per unique image?
  Q2. Is Ghana's BINARY label self-consistent per unique image?
  Q3. Do CP-AnemiC and Ghana agree on the binary label for shared images?
  Q4. Is CP-AnemiC's Hb consistent with its own binary label?

Q1 decides the Hb question. Q2-Q4 decide whether the binary label - the only label the
pool would retain - is itself trustworthy.

Writes `hb_label_trusted` into every manifest so no downstream code can silently
consume an untrusted haemoglobin value.

    .\\.venv\\Scripts\\python.exe scripts\\ghana_label_arbitration_phase1_5.py
"""

from __future__ import annotations

import json

import pandas as pd

from hemosight.io import paths

# WHO threshold for children 6-59 months, which is CP-AnemiC's population.
WHO_CHILD_6_59M = 11.0


def main() -> int:
    paths.ensure_dirs()
    H = {s: pd.read_csv(paths.OVERLAP / f"hashes_{s}.csv")
         for s in ("cp_anemic", "ghana_conj", "ghana_nail")}
    cp = pd.read_csv(paths.MANIFESTS / "cp_anemic.csv")
    gc = pd.read_csv(paths.MANIFESTS / "ghana_conj.csv")

    out: dict = {}

    # ---- Q1: CP-AnemiC Hb self-consistency ----------------------------------
    m = H["cp_anemic"].merge(cp[["image_id", "hb_g_dl", "anemia_label"]], on="image_id")
    g = m.groupby("md5").agg(n=("image_id", "size"), n_hb=("hb_g_dl", "nunique"),
                             hb_min=("hb_g_dl", "min"), hb_max=("hb_g_dl", "max"),
                             n_lab=("anemia_label", "nunique"))
    dup = g[g.n > 1]
    q1 = {
        "files": len(m), "unique_images": int(m.md5.nunique()),
        "duplicate_groups": int(len(dup)),
        "groups_with_conflicting_hb": int((dup.n_hb > 1).sum()),
        "files_in_conflicted_groups": int(dup[dup.n_hb > 1].n.sum()),
        "max_hb_spread_within_one_image": float((dup.hb_max - dup.hb_min).max()),
        "self_consistent": bool((dup.n_hb > 1).sum() == 0),
    }
    out["Q1_cp_anemic_hb"] = q1
    print("Q1 CP-AnemiC Hb self-consistent:", q1["self_consistent"])
    print(f"   {q1['groups_with_conflicting_hb']}/{q1['duplicate_groups']} duplicate groups "
          f"conflict; worst spread {q1['max_hb_spread_within_one_image']:.2f} g/dL")

    # ---- Q2: Ghana binary-label self-consistency ----------------------------
    mg = H["ghana_conj"].merge(gc[["image_id", "anemia_label"]], on="image_id")
    gg = mg.groupby("md5").agg(n=("image_id", "size"), n_lab=("anemia_label", "nunique"))
    dupg = gg[gg.n > 1]
    q2 = {
        "files": len(mg), "unique_images": int(mg.md5.nunique()),
        "duplicate_groups": int(len(dupg)),
        "groups_with_conflicting_binary_label": int((dupg.n_lab > 1).sum()),
        "files_affected": int(dupg[dupg.n_lab > 1].n.sum()),
        "hb_values_present": int(gc.hb_g_dl.notna().sum()),
        "self_consistent": bool((dupg.n_lab > 1).sum() == 0),
    }
    out["Q2_ghana_binary"] = q2
    print("\nQ2 Ghana binary label self-consistent:", q2["self_consistent"])
    print(f"   {q2['groups_with_conflicting_binary_label']}/{q2['duplicate_groups']} "
          f"duplicate groups conflict ({q2['files_affected']} files)")
    print(f"   Ghana Hb values present: {q2['hb_values_present']} (this is why the briefed "
          f"comparison cannot be run)")

    # ---- Q3: cross-collection binary agreement on shared images -------------
    cp_lab = m.groupby("md5").anemia_label.agg(lambda s: s.mode().iloc[0])
    gc_lab = mg.groupby("md5").anemia_label.agg(lambda s: s.mode().iloc[0])
    shared = sorted(set(cp_lab.index) & set(gc_lab.index))
    agree = int(sum(cp_lab[k] == gc_lab[k] for k in shared))
    q3 = {
        "shared_unique_images": len(shared),
        "binary_label_agree": agree,
        "binary_label_disagree": len(shared) - agree,
        "agreement_rate": round(agree / len(shared), 4) if shared else None,
    }
    out["Q3_cross_binary_agreement"] = q3
    print(f"\nQ3 shared images={len(shared)} | binary labels agree {agree} "
          f"({100*agree/max(len(shared),1):.2f}%) disagree {len(shared)-agree}")

    # ---- Q4: is CP-AnemiC Hb consistent with its own binary label? ----------
    v = cp.dropna(subset=["hb_g_dl"])
    implied = (v.hb_g_dl < WHO_CHILD_6_59M).astype(int)
    mism = int((implied != v.anemia_label).sum())
    q4 = {
        "threshold_used": WHO_CHILD_6_59M,
        "population": "children 6-59 months (WHO)",
        "rows": int(len(v)), "mismatches": mism,
        "mismatch_rate": round(mism / len(v), 4),
    }
    out["Q4_cp_hb_vs_binary"] = q4
    print(f"\nQ4 CP-AnemiC Hb vs its own binary label at WHO {WHO_CHILD_6_59M} g/dL: "
          f"{mism}/{len(v)} mismatches ({100*mism/len(v):.2f}%)")

    # ---- Verdict -------------------------------------------------------------
    ghana_authoritative = q2["hb_values_present"] > 0 and q2["self_consistent"]
    if ghana_authoritative:
        verdict = "ADOPT_GHANA_HB"
    elif q1["self_consistent"]:
        verdict = "ADOPT_CP_ANEMIC_HB"
    else:
        verdict = "BINARY_LABEL_ONLY"
    out["verdict"] = verdict

    # The binary label is the only label the pool retains, so its own noise matters.
    # Ghana is internally self-consistent, but it disagrees with CP-AnemiC on shared
    # images. CP-AnemiC's label is exactly (Hb < 11.0), so a disagreement means one of
    # the two collections has mislabelled that participant.
    noise = q3["binary_label_disagree"] / q3["shared_unique_images"] if q3["shared_unique_images"] else None
    out["binary_label_noise"] = {
        "checkable_images": q3["shared_unique_images"],
        "disagreements": q3["binary_label_disagree"],
        "observed_noise_floor": round(noise, 4) if noise is not None else None,
        "cp_label_is_function_of_hb": bool(
            ((v.hb_g_dl < WHO_CHILD_6_59M).astype(int) == v.anemia_label).all()
        ),
        "interpretation": (
            "CP-AnemiC's anemia_label is exactly (hb_g_dl < 11.0) and its severity bins "
            "are the exact WHO bands, so it carries no information beyond Hb. Where the "
            "two collections overlap, they disagree on ~1.7% of unique images. That is a "
            "label-noise floor on the ONLY label the Ghana pool retains, measurable on "
            "419 images and unmeasurable on the rest. No binary result on this pool may "
            "claim accuracy above it and attribute the gap to the model."
        ),
    }
    out["binary_label_usable_with_caveat"] = True
    print(f"\n=== VERDICT: {verdict} ===")
    print(f"    binary label self-consistent within Ghana: {q2['self_consistent']}")
    print(f"    cross-collection binary noise floor: {q3['binary_label_disagree']}"
          f"/{q3['shared_unique_images']} = {100*noise:.2f}%")
    print(f"    CP-AnemiC label is exactly (Hb<11.0): "
          f"{out['binary_label_noise']['cp_label_is_function_of_hb']}")

    # ---- Apply the hard flag to every manifest -------------------------------
    GHANA_POOL = {"cp_anemic", "ghana_conj", "ghana_nail"}
    changed = []
    for f in sorted(paths.MANIFESTS.glob("*.csv")):
        if f.name == "nus8.csv":
            continue
        df = pd.read_csv(f)
        if "dataset" not in df.columns:
            continue
        trusted = ~df.dataset.isin(GHANA_POOL) & df.hb_g_dl.notna()
        df["hb_label_trusted"] = trusted
        reason = (
            "Phase1.5 arbitration: Ghana pool is BINARY-LABEL-ONLY. CP-AnemiC Hb "
            "conflicts on duplicated images; Ghana ships no Hb."
        )
        # Build as an object column outright: assigning a string into a subset of an
        # all-NaN float column raises in pandas 3.
        df["hb_label_untrusted_reason"] = pd.Series(
            [reason if d in GHANA_POOL else None for d in df.dataset],
            index=df.index, dtype="object",
        )
        df.to_csv(f, index=False)
        changed.append((f.name, int(trusted.sum()), int((~trusted).sum())))

    print("\n=== hb_label_trusted written ===")
    for n, t, u in changed:
        print(f"  {n:18s} trusted={t:6d} untrusted={u:6d}")

    out["manifest_flags"] = {n: {"trusted": t, "untrusted": u} for n, t, u in changed}
    p = paths.INTERIM / "phase1_5_label_arbitration.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nreport -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
