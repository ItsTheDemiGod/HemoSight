"""Conventional image CNN baseline for haemoglobin from conjunctiva photographs.

This is the comparison arm that section 3 of CLAUDE.md requires for every claim and
that was never built for the imaging arm (audit 2026-09-12). It is deliberately the
standard recipe the literature uses: an ImageNet-pretrained ResNet-18, a conjunctiva
crop as input, a regression head, fine-tuned end to end.

Data: Eyes-Defy-Anemia. **217 subjects with Hb, one image each, one Samsung Galaxy
S6 in two regional variants, two sites (India 95, Italy 123), no severe cases.** A
pilot comparison arm, not a validation.

Construction mirrors `hemosight.ppg.cv` so the two arms are scrutinised alike:
  - subject-disjoint folds, asserted in code (one image per subject, so subject-level
    K-fold IS leave-subject-out);
  - the regression target standardised with TRAIN-fold statistics (Phase 4.5 lesson:
    an unstandardised head spends its budget finding the intercept);
  - geometric augmentation only. Colour jitter is deliberately NOT used: the signal
    under test is colour, and jittering it would train the model to ignore the one
    thing it is supposed to find;
  - one prediction per subject; train MAE recorded for the train-test gap.
"""
from __future__ import annotations

import gc

import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import KFold
from torchvision.models import ResNet18_Weights, resnet18

SEED = 20260911
N_SPLITS = 10
EPOCHS = 30
BATCH = 32
IMG = 224
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def free(dev: str) -> None:
    gc.collect()
    if dev.startswith("cuda"):
        torch.cuda.empty_cache()


def build_model(pretrained: bool = True) -> nn.Module:
    m = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1 if pretrained else None)
    m.fc = nn.Linear(m.fc.in_features, 1)
    return m


def _augment(x: torch.Tensor, gen: torch.Generator) -> torch.Tensor:
    """Horizontal flip and a random crop-and-resize (scale 0.8-1.0). Geometric only."""
    n = x.shape[0]
    flip = torch.rand(n, generator=gen, device="cpu") < 0.5
    x = torch.where(flip.to(x.device)[:, None, None, None], x.flip(-1), x)
    out = torch.empty_like(x)
    for i in range(n):
        s = 0.8 + 0.2 * torch.rand(1, generator=gen).item()
        h = w = int(IMG * s)
        top = int(torch.randint(0, IMG - h + 1, (1,), generator=gen).item())
        left = int(torch.randint(0, IMG - w + 1, (1,), generator=gen).item())
        crop = x[i:i + 1, :, top:top + h, left:left + w]
        out[i:i + 1] = nn.functional.interpolate(crop, size=(IMG, IMG), mode="bilinear",
                                                 align_corners=False)
    return out


def _to_tensor(X: np.ndarray) -> torch.Tensor:
    """uint8 NHWC -> float NCHW, ImageNet-normalised."""
    x = X.astype(np.float32) / 255.0
    x = (x - MEAN) / STD
    return torch.from_numpy(np.ascontiguousarray(x.transpose(0, 3, 1, 2)))


@torch.no_grad()
def _predict(model: nn.Module, X: np.ndarray, dev: str, batch: int = 64) -> np.ndarray:
    model.eval()
    out = np.empty(len(X), dtype=np.float32)
    for s in range(0, len(X), batch):
        xb = _to_tensor(X[s:s + batch]).to(dev)
        out[s:s + batch] = model(xb).squeeze(1).float().cpu().numpy()
        del xb
    return out


def fit_one(Xtr: np.ndarray, ytr: np.ndarray, dev: str, seed: int,
            epochs: int = EPOCHS, pretrained: bool = True) -> tuple[nn.Module, float, float]:
    """Train on one split. Returns (model, target mean, target sd)."""
    torch.manual_seed(seed)
    gen = torch.Generator().manual_seed(seed)
    mu, sd = float(ytr.mean()), float(ytr.std() + 1e-8)
    model = build_model(pretrained).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
    steps = epochs * max(1, (len(Xtr) + BATCH - 1) // BATCH)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-4, total_steps=steps)
    lossf = nn.SmoothL1Loss()
    scaler = torch.amp.GradScaler("cuda", enabled=dev.startswith("cuda"))
    Xt = _to_tensor(Xtr)
    yt = torch.from_numpy((ytr - mu) / sd).float()
    for _ in range(epochs):
        model.train()
        perm = torch.randperm(len(Xt), generator=gen)
        for s in range(0, len(perm), BATCH):
            idx = perm[s:s + BATCH]
            xb = _augment(Xt[idx], gen).to(dev)
            yb = yt[idx].to(dev)
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", enabled=dev.startswith("cuda")):
                loss = lossf(model(xb).squeeze(1).float(), yb)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
    del opt, sched, scaler, Xt, yt
    return model, mu, sd


def features(model: nn.Module, X: np.ndarray, dev: str) -> np.ndarray:
    """Penultimate-layer (512-d) representation, for the sex probe."""
    fc = model.fc
    model.fc = nn.Identity()
    out = _predict_feats(model, X, dev)
    model.fc = fc
    return out


@torch.no_grad()
def _predict_feats(model, X, dev, batch: int = 64) -> np.ndarray:
    model.eval()
    outs = []
    for s in range(0, len(X), batch):
        xb = _to_tensor(X[s:s + batch]).to(dev)
        outs.append(model(xb).float().cpu().numpy())
    return np.concatenate(outs)


def cv_predict(X: np.ndarray, y: np.ndarray, subjects: np.ndarray, dev: str,
               seed: int = SEED, epochs: int = EPOCHS, pretrained: bool = True,
               want_features: bool = False) -> dict:
    """10-fold subject-disjoint CV. One image per subject. Returns held-out predictions,
    train MAE (for the gap), and optionally the held-out penultimate features."""
    kf = KFold(N_SPLITS, shuffle=True, random_state=SEED)
    preds = np.full(len(y), np.nan)
    feats = np.full((len(y), 512), np.nan, dtype=np.float32) if want_features else None
    train_maes = []
    for tr, te in kf.split(subjects):
        assert not (set(subjects[tr]) & set(subjects[te])), "subject leaked across folds"
        model, mu, sd = fit_one(X[tr], y[tr], dev, seed, epochs, pretrained)
        preds[te] = _predict(model, X[te], dev) * sd + mu
        train_maes.append(float(np.mean(np.abs(_predict(model, X[tr], dev) * sd + mu - y[tr]))))
        if want_features:
            feats[te] = features(model, X[te], dev)
        del model
        free(dev)
    return {"preds": preds, "train_mae": float(np.mean(train_maes)), "features": feats}


def cross_site(X: np.ndarray, y: np.ndarray, site: np.ndarray, train_site: str,
               test_site: str, dev: str, seed: int = SEED, epochs: int = EPOCHS) -> dict:
    tr, te = np.where(site == train_site)[0], np.where(site == test_site)[0]
    model, mu, sd = fit_one(X[tr], y[tr], dev, seed, epochs)
    p = _predict(model, X[te], dev) * sd + mu
    ptr = _predict(model, X[tr], dev) * sd + mu
    del model
    free(dev)
    return {"preds": p, "test_idx": te, "train_mae": float(np.mean(np.abs(ptr - y[tr]))),
            "train_mean_hb": mu,
            # Added for Phase 9A: a screening operating point must be chosen on the
            # TRAINING site and applied to the test site, which needs the train-site
            # predictions. Additive only - no existing key changes.
            "train_preds": ptr, "train_idx": tr}
