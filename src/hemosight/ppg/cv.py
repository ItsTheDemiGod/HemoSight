"""Shared subject-disjoint CV driver for the raw-waveform PPG models.

Extracted from `scripts/phase5_harden.py` unchanged in NUMERICS so that the extended
permutation runner and the original hardening script cannot drift apart. Two things
were added, neither of which alters a single output value:

MEMORY HYGIENE. The first extended run was killed by an out-of-memory condition after
41 permutations. One permutation builds 6 architectures x 10 folds = 60 models, and
nothing was released between them: the model, its optimiser, its LR schedule and the
resident training tensors all stayed reachable until Python happened to collect them,
while CUDA's caching allocator held every block it had ever handed out. Every fold now
drops its tensors explicitly and returns the cache to the driver.

CHUNKED INFERENCE. Evaluation ran the whole held-out fold through the network in one
forward pass. For `SpecCNN` that materialises a complex STFT over the entire fold at
once, which is the largest single allocation in the run. Chunking is numerically exact
here - the models carry no cross-sample operation, and BatchNorm in eval mode uses
running statistics - so this changes peak memory and nothing else.
"""

from __future__ import annotations

import gc

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import KFold

from hemosight.io import paths
from hemosight.ppg.deep import ARCHITECTURES, make_windows
from hemosight.ppg.features import load_subject

SEED = 20260911
N_SPLITS = 10
EPOCHS = 40
TRAIN_BATCH = 128
EVAL_BATCH = 256

# The six configurations the Phase 4.5 selection actually ranged over.
CONFIGS = [(a, c) for c in ("four", "660") for a in ("cnn1d", "gru", "speccnn")]
CHANNELS = {"four": [0, 1, 2, 3], "660": [0]}
SELECTED = ("speccnn", "660")


def build_windows(channels: list[int]) -> tuple[np.ndarray, np.ndarray]:
    """Windowed waveforms and their subject ids, cached on disk by channel set."""
    tag = "".join(str(c) for c in channels)
    cache = paths.INTERIM / "phase4_5" / f"windows_{tag}.npz"
    if cache.exists():
        z = np.load(cache)
        return z["X"], z["sid"]
    info = pd.read_excel(paths.HB_PPG_SHEET)
    Xs, sids = [], []
    for r in info.to_dict("records"):
        sid = int(r["ID"])
        sig = load_subject(paths.HB_PPG / "data_csv" / f"{sid}.csv")
        if sig is None:
            continue
        w, s = make_windows(sig, sid)
        if len(w):
            Xs.append(w[:, channels, :])
            sids.append(s)
    X = np.concatenate(Xs).astype(np.float32)
    sid = np.concatenate(sids)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, X=X, sid=sid)
    return X, sid


def load_hb() -> dict[int, float]:
    feats = pd.read_csv(paths.INTERIM / "phase4" / "features.csv")
    feats = feats[np.isfinite(feats.hb_g_dl)]
    return {int(r.subject_id): float(r.hb_g_dl) for r in feats.itertuples()}


def load_data() -> dict[str, tuple]:
    """{tag: (X, sid_per_window, subjects, hb_per_subject)} for both channel sets."""
    hb = load_hb()
    out = {}
    for tag, ch in CHANNELS.items():
        X, sid = build_windows(ch)
        subs = np.array(sorted(set(sid.tolist()) & set(hb)))
        keep = np.isin(sid, subs)
        out[tag] = (X[keep], sid[keep], subs, np.array([hb[s] for s in subs]))
    return out


def free(dev: str) -> None:
    gc.collect()
    if dev == "cuda":
        torch.cuda.empty_cache()


def peak_mb() -> float:
    return torch.cuda.max_memory_allocated() / 1e6 if torch.cuda.is_available() else 0.0


def reserved_mb() -> float:
    return torch.cuda.max_memory_reserved() / 1e6 if torch.cuda.is_available() else 0.0


@torch.no_grad()
def _predict(model, X: np.ndarray, dev: str, batch: int) -> np.ndarray:
    """Forward the held-out fold in chunks. Exact; only the peak allocation changes."""
    out = np.empty(len(X), dtype=np.float32)
    for s in range(0, len(X), batch):
        xb = torch.from_numpy(X[s:s + batch]).to(dev)
        out[s:s + batch] = model(xb).float().cpu().numpy()
        del xb
    return out


def fit_predict(arch: str, X, sid_w, subs, y_sub, dev: str, seed: int,
                train_batch: int = TRAIN_BATCH,
                eval_batch: int = EVAL_BATCH) -> np.ndarray:
    """Full 10-fold subject-disjoint CV. Returns one prediction per subject."""
    torch.manual_seed(seed)
    m = {s: v for s, v in zip(subs, y_sub)}
    y_w = np.array([m[s] for s in sid_w], dtype=np.float32)
    kf = KFold(N_SPLITS, shuffle=True, random_state=SEED)
    preds = np.full(len(subs), np.nan)
    for tr, te in kf.split(subs):
        trs, tes = set(subs[tr].tolist()), set(subs[te].tolist())
        assert not (trs & tes), "subject leaked across a fold boundary"
        mtr, mte = np.isin(sid_w, list(trs)), np.isin(sid_w, list(tes))
        Xtr, ytr, Xte = X[mtr], y_w[mtr], X[mte]
        mu, sd = float(ytr.mean()), float(ytr.std() + 1e-8)
        model = ARCHITECTURES[arch](in_ch=X.shape[1]).to(dev)
        opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-3)
        sched = torch.optim.lr_scheduler.OneCycleLR(
            opt, max_lr=3e-3,
            total_steps=EPOCHS * max(1, (len(Xtr) + train_batch - 1) // train_batch))
        lossf = torch.nn.SmoothL1Loss()
        Xt = torch.from_numpy(Xtr).to(dev)
        yt = torch.from_numpy((ytr - mu) / sd).float().to(dev)
        model.train()
        for _ in range(EPOCHS):
            perm = torch.randperm(len(Xt), device=dev)
            for s in range(0, len(perm), train_batch):
                idx = perm[s:s + train_batch]
                opt.zero_grad(set_to_none=True)
                lossf(model(Xt[idx]), yt[idx]).backward()
                opt.step()
                sched.step()
            del perm
        model.eval()
        pw = _predict(model, Xte, dev, eval_batch) * sd + mu
        sw = sid_w[mte]
        for i, s in enumerate(subs[te]):
            v = pw[sw == s]
            preds[te[i]] = float(np.median(v)) if len(v) else np.nan
        # Release everything this fold allocated before the next one is built.
        del model, opt, sched, lossf, Xt, yt, Xtr, ytr, Xte, pw
        free(dev)
    return preds
