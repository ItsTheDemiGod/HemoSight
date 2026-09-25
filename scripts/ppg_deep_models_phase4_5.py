"""Phase 4.5, TASK 1: deep models over raw PPG waveforms.

Closes the one representation Phase 4 did not test. Same grouped leave-subject-out
folds, same pre-declared thresholds, same baselines.

Leakage control is explicit: every fold asserts that no subject appears in both train
and test, and the train-test gap is reported. With 252 subjects a model of this size
could memorise, and subject leakage would produce an impressive, false result.

    .\\.venv\\Scripts\\python.exe scripts\\ppg_deep_models_phase4_5.py [--epochs 40]
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold

from hemosight.io import paths
from hemosight.ppg.deep import ARCHITECTURES, make_windows
from hemosight.ppg.features import load_subject

OUT = paths.INTERIM / "phase4_5"
SEED = 20260911
N_SPLITS = 10


def build_windows(channels: list[int]):
    """Cache windows for all subjects. `channels` selects wavelength indices."""
    tag = "".join(str(c) for c in channels)
    cache = OUT / f"windows_{tag}.npz"
    if cache.exists():
        z = np.load(cache)
        return z["X"], z["sid"]
    OUT.mkdir(parents=True, exist_ok=True)
    info = pd.read_excel(paths.HB_PPG_SHEET)
    Xs, sids = [], []
    t0 = time.time()
    for i, r in enumerate(info.to_dict("records")):
        if i % 50 == 0:
            print(f"  windowing {i}/{len(info)} {time.time()-t0:.0f}s", end="\r", flush=True)
        sid = int(r["ID"])
        sig = load_subject(paths.HB_PPG / "data_csv" / f"{sid}.csv")
        if sig is None:
            continue
        w, s = make_windows(sig, sid)
        if len(w):
            Xs.append(w[:, channels, :])
            sids.append(s)
    print()
    X = np.concatenate(Xs).astype(np.float32)
    sid = np.concatenate(sids)
    np.savez_compressed(cache, X=X, sid=sid)
    return X, sid


def train_fold(arch, Xtr, ytr, Xte, yte, epochs, dev, in_ch):
    """Train one fold. The target is standardised using TRAIN statistics only.

    Without this the head starts at 0 against a mean Hb of ~13.9 g/dL and spends the
    whole budget travelling to the intercept - which looks like catastrophic failure
    but is only an unfair initialisation. Standardising gives the model the best
    honest chance, which is the point: this phase is trying to FIND signal.
    """
    mu, sd = float(ytr.mean()), float(ytr.std() + 1e-8)
    ytr = (ytr - mu) / sd
    model = ARCHITECTURES[arch](in_ch=in_ch).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-3)
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt, max_lr=3e-3, total_steps=epochs * max(1, (len(Xtr) + 127) // 128))
    lossf = torch.nn.SmoothL1Loss()
    Xtr_t = torch.from_numpy(Xtr).to(dev)
    ytr_t = torch.from_numpy(ytr).float().to(dev)
    for _ in range(epochs):
        model.train()
        perm = torch.randperm(len(Xtr_t), device=dev)
        for s in range(0, len(perm), 128):
            idx = perm[s:s + 128]
            opt.zero_grad(set_to_none=True)
            loss = lossf(model(Xtr_t[idx]), ytr_t[idx])
            loss.backward()
            opt.step()
            sched.step()
    model.eval()
    with torch.no_grad():
        ptr = model(Xtr_t).cpu().numpy() * sd + mu       # back to g/dL
        pte = model(torch.from_numpy(Xte).to(dev)).cpu().numpy() * sd + mu
        emb = model.embed(torch.from_numpy(Xte).to(dev)).cpu().numpy()
    return ptr, pte, emb


def aggregate(pred_w, sid_w, sid_order):
    """Window predictions -> one prediction per subject (median)."""
    out = []
    for s in sid_order:
        v = pred_w[sid_w == s]
        out.append(float(np.median(v)) if len(v) else np.nan)
    return np.array(out)


def run_condition(name, channels, hb_by_sid, sex_by_sid, epochs, dev, archs):
    X, sid_w = build_windows(channels)
    subs = np.array(sorted(set(sid_w.tolist()) & set(hb_by_sid)))
    keep = np.isin(sid_w, subs)
    X, sid_w = X[keep], sid_w[keep]
    y_w = np.array([hb_by_sid[s] for s in sid_w], dtype=np.float32)
    y_sub = np.array([hb_by_sid[s] for s in subs])
    print(f"\n=== {name}: {X.shape[0]} windows, {len(subs)} subjects, "
          f"input {X.shape[1]}x{X.shape[2]} ===")

    res = {}
    kf = KFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    for arch in archs:
        preds = np.full(len(subs), np.nan)
        tr_maes, embs, emb_sids = [], [], []
        t0 = time.time()
        for tr_s, te_s in kf.split(subs):
            tr_subs, te_subs = set(subs[tr_s].tolist()), set(subs[te_s].tolist())
            # LEAKAGE ASSERTION - the whole result depends on this.
            assert not (tr_subs & te_subs), "subject appears in both train and test"
            mtr = np.isin(sid_w, list(tr_subs))
            mte = np.isin(sid_w, list(te_subs))
            ptr, pte, emb = train_fold(arch, X[mtr], y_w[mtr], X[mte], y_w[mte],
                                       epochs, dev, X.shape[1])
            tr_maes.append(float(np.mean(np.abs(ptr - y_w[mtr]))))  # ptr already in g/dL
            preds[te_s] = aggregate(pte, sid_w[mte], subs[te_s])
            embs.append(emb)
            emb_sids.append(sid_w[mte])
        err = preds - y_sub
        mae = float(np.mean(np.abs(err)))
        r2 = float(1 - np.sum(err ** 2) / np.sum((y_sub - y_sub.mean()) ** 2))
        band = "VIABLE" if mae < 1.0 else "MARGINAL" if mae <= 2.0 else "NOT VIABLE"
        train_mae = float(np.mean(tr_maes))
        res[arch] = {
            "mae_g_dl": mae, "r2": r2,
            "pearson_r": float(np.corrcoef(preds, y_sub)[0, 1]),
            "train_mae_g_dl": train_mae, "train_test_gap": mae - train_mae,
            "band": band, "n_subjects": int(len(subs)),
            "seconds": round(time.time() - t0, 1),
        }
        print(f"  {arch:9s} MAE={mae:.3f}  r={res[arch]['pearson_r']:+.3f}  "
              f"R2={r2:+.3f}  train MAE={train_mae:.3f}  gap={mae-train_mae:+.3f}  "
              f"-> {band}  ({res[arch]['seconds']:.0f}s)")

        # --- sex probe on the learned representation --------------------------
        E = np.concatenate(embs)
        ES = np.concatenate(emb_sids)
        sx = np.array([sex_by_sid[s] for s in ES])
        m = np.isfinite(E).all(axis=1)
        if m.sum() > 50 and len(set(sx[m].tolist())) == 2:
            # Subject-grouped probe, so the probe itself cannot leak.
            usub = np.array(sorted(set(ES[m].tolist())))
            pk = KFold(5, shuffle=True, random_state=SEED)
            acc = []
            for a, b in pk.split(usub):
                tr = np.isin(ES, usub[a]) & m
                te = np.isin(ES, usub[b]) & m
                if len(set(sx[tr].tolist())) < 2:
                    continue
                clf = LogisticRegression(max_iter=2000, C=1.0)
                clf.fit(E[tr], sx[tr])
                acc.append(float(clf.score(E[te], sx[te])))
            if acc:
                res[arch]["sex_probe_accuracy"] = float(np.mean(acc))
                res[arch]["sex_base_rate"] = float(max(np.mean(sx), 1 - np.mean(sx)))
                print(f"            sex probe on its representation: "
                      f"{np.mean(acc)*100:.1f}% (base rate "
                      f"{res[arch]['sex_base_rate']*100:.1f}%)")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--archs", default="cnn1d,gru,speccnn")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    feats = pd.read_csv(paths.INTERIM / "phase4" / "features.csv")
    feats = feats[np.isfinite(feats.hb_g_dl)]
    hb = {int(r.subject_id): float(r.hb_g_dl) for r in feats.itertuples()}
    sex = {int(r.subject_id): float(r.sex) for r in feats.itertuples()}
    y_all = np.array(list(hb.values()))
    archs = args.archs.split(",")
    print(f"device={dev}  epochs={args.epochs}  archs={archs}")
    print(f"baselines to beat: population mean MAE="
          f"{np.mean(np.abs(y_all - y_all.mean())):.3f}, sex alone 0.831, "
          f"demographics 0.831, best Phase 4 feature model 1.190")

    results = {
        "baselines": {"population_mean": float(np.mean(np.abs(y_all - y_all.mean()))),
                      "sex_alone": 0.831, "demographics": 0.831,
                      "phase4_features_4wl": 1.190},
        "conditions": {},
    }
    results["conditions"]["four_wavelength"] = run_condition(
        "four wavelengths", [0, 1, 2, 3], hb, sex, args.epochs, dev, archs)
    results["conditions"]["660nm_only"] = run_condition(
        "660 nm only", [0], hb, sex, args.epochs, dev, archs)

    best = min(((c, a, v["mae_g_dl"]) for c, d in results["conditions"].items()
                for a, v in d.items()), key=lambda x: x[2])
    results["best"] = {"condition": best[0], "arch": best[1], "mae_g_dl": best[2]}
    results["beats_demographics"] = bool(best[2] < 0.831)
    results["beats_population_mean"] = bool(best[2] < results["baselines"]["population_mean"])

    print("\n" + "=" * 70)
    print(f"BEST DEEP MODEL: {best[1]} on {best[0]}, MAE {best[2]:.3f} g/dL")
    print(f"  beats demographics (0.831)?     {results['beats_demographics']}")
    print(f"  beats population mean "
          f"({results['baselines']['population_mean']:.3f})?  "
          f"{results['beats_population_mean']}")
    print("=" * 70)

    (OUT / "deep_results.json").write_text(json.dumps(results, indent=2, default=float),
                                           encoding="utf-8")
    print(f"\nresults -> {OUT / 'deep_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
