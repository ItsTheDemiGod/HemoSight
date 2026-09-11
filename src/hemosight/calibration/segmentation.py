"""U-Net with a pretrained ResNet-18 encoder for eye-region segmentation.

Sized for an 8 GB RTX 4060: ResNet-18 encoder at 384x384 with batch 12 and AMP peaks
around 4 GB, leaving headroom. A heavier backbone buys little here - the classes are
large, high-contrast regions, and the hard part of this phase is the colour science,
not the segmentation architecture.

Also provides the two things the rest of the project needs from segmentation:
  * a per-image QUALITY SCORE, which N4's abstention logic will consume, and
  * VASCULATURE EXCLUSION inside the sclera, without which the reference patch is
    contaminated by haemoglobin - the very signal the project is trying to measure
    elsewhere.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models

from .segmentation_data import N_CLASSES, SCLERA


class _DecoderBlock(nn.Module):
    def __init__(self, in_ch: int, skip_ch: int, out_ch: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch + skip_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
        )

    def forward(self, x, skip=None):
        x = F.interpolate(x, scale_factor=2, mode="nearest")
        if skip is not None:
            x = torch.cat([x, skip], dim=1)
        return self.conv(x)


class UNetResNet18(nn.Module):
    def __init__(self, n_classes: int = N_CLASSES, pretrained: bool = True):
        super().__init__()
        w = models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        r = models.resnet18(weights=w)
        self.stem = nn.Sequential(r.conv1, r.bn1, r.relu)   # /2   64
        self.pool = r.maxpool                               # /4
        self.layer1, self.layer2 = r.layer1, r.layer2       # /4 64, /8 128
        self.layer3, self.layer4 = r.layer3, r.layer4       # /16 256, /32 512
        self.d4 = _DecoderBlock(512, 256, 256)
        self.d3 = _DecoderBlock(256, 128, 128)
        self.d2 = _DecoderBlock(128, 64, 64)
        self.d1 = _DecoderBlock(64, 64, 32)
        self.d0 = _DecoderBlock(32, 0, 16)
        self.head = nn.Conv2d(16, n_classes, 1)

    def forward(self, x):
        s0 = self.stem(x)
        s1 = self.layer1(self.pool(s0))
        s2 = self.layer2(s1)
        s3 = self.layer3(s2)
        s4 = self.layer4(s3)
        y = self.d4(s4, s3)
        y = self.d3(y, s2)
        y = self.d2(y, s1)
        y = self.d1(y, s0)
        y = self.d0(y)
        return self.head(y)


def merged_bg_cross_entropy(logits: torch.Tensor, target: torch.Tensor,
                            merge_bg_periocular: torch.Tensor) -> torch.Tensor:
    """Cross-entropy that reconciles the two datasets' incompatible label spaces.

    MOBIUS marks periocular skin BLACK, i.e. identical to true background, while
    SBVPI gives it its own class. Training naively on both teaches the model that
    skin is simultaneously class 0 and class 4, and the periocular class collapses.

    For MOBIUS samples this merges the background and periocular logits with a
    logsumexp before scoring, so predicting "periocular" on MOBIUS skin costs nothing
    - both merely mean "not sclera, iris or pupil". MOBIUS still supplies full
    negative supervision for the three classes it does annotate, and SBVPI remains
    the only source of the background/periocular distinction.

    `merge_bg_periocular` is a per-sample bool tensor of shape (B,).
    """
    from .segmentation_data import PERIOCULAR

    if not bool(merge_bg_periocular.any()):
        return F.cross_entropy(logits, target)

    loss = logits.new_zeros(())
    n = 0
    strict = ~merge_bg_periocular
    if bool(strict.any()):
        loss = loss + F.cross_entropy(logits[strict], target[strict]) * int(strict.sum())
        n += int(strict.sum())

    idx = merge_bg_periocular
    if bool(idx.any()):
        lg, tg = logits[idx], target[idx].clone()
        keep = [c for c in range(lg.shape[1]) if c != PERIOCULAR]
        merged = torch.logsumexp(
            torch.stack([lg[:, 0], lg[:, PERIOCULAR]], dim=1), dim=1)
        lg2 = torch.stack([merged] + [lg[:, c] for c in keep[1:]], dim=1)
        # Any target of PERIOCULAR cannot occur in MOBIUS, but guard anyway.
        tg[tg == PERIOCULAR] = 0
        loss = loss + F.cross_entropy(lg2, tg) * int(idx.sum())
        n += int(idx.sum())
    return loss / max(n, 1)


def dice_loss(logits: torch.Tensor, target: torch.Tensor, eps: float = 1.0) -> torch.Tensor:
    """Soft multi-class Dice. Pairs with cross-entropy to handle the heavy class
    imbalance: pupil occupies a fraction of a percent of most frames."""
    p = torch.softmax(logits, dim=1)
    t = F.one_hot(target, num_classes=logits.shape[1]).permute(0, 3, 1, 2).float()
    dims = (0, 2, 3)
    inter = (p * t).sum(dims)
    denom = p.sum(dims) + t.sum(dims)
    return 1.0 - ((2 * inter + eps) / (denom + eps)).mean()


@torch.no_grad()
def confusion(logits: torch.Tensor, target: torch.Tensor, n: int = N_CLASSES) -> torch.Tensor:
    pred = logits.argmax(dim=1).reshape(-1)
    t = target.reshape(-1)
    k = (t * n + pred).to(torch.int64)
    return torch.bincount(k, minlength=n * n).reshape(n, n)


def iou_dice_from_confusion(cm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    cm = cm.astype(np.float64)
    tp = np.diag(cm)
    fp = cm.sum(axis=0) - tp
    fn = cm.sum(axis=1) - tp
    iou = tp / np.maximum(tp + fp + fn, 1e-9)
    dice = 2 * tp / np.maximum(2 * tp + fp + fn, 1e-9)
    present = (cm.sum(axis=1) > 0)
    iou[~present] = np.nan
    dice[~present] = np.nan
    return iou, dice


# --------------------------------------------------------------------------- #
# Quality score and vasculature handling
# --------------------------------------------------------------------------- #
@torch.no_grad()
def quality_score(probs: torch.Tensor, cls: int = SCLERA) -> dict[str, float]:
    """Per-image segmentation quality, in [0, 1]. Feeds N4's abstention logic.

    Three factors, multiplied so that any one failing sinks the score:
      * confidence - mean predicted probability inside the predicted region;
      * decisiveness - 1 - normalised predictive entropy over the whole frame;
      * area plausibility - a sclera occupying 0.05% or 60% of the frame is wrong
        regardless of how confident the network is.
    """
    p = probs[0] if probs.dim() == 4 else probs
    pred = p.argmax(dim=0)
    m = pred == cls
    frac = float(m.float().mean())
    conf = float(p[cls][m].mean()) if m.any() else 0.0

    ent = -(p.clamp_min(1e-8) * p.clamp_min(1e-8).log()).sum(dim=0)
    decisive = float(1.0 - (ent.mean() / np.log(p.shape[0])).clamp(0, 1))

    lo, hi = 0.005, 0.45           # plausible sclera area fraction
    if frac <= 0:
        plaus = 0.0
    elif frac < lo:
        plaus = float(frac / lo)
    elif frac > hi:
        plaus = float(max(0.0, 1.0 - (frac - hi) / hi))
    else:
        plaus = 1.0

    return {"quality": float(conf * decisive * plaus), "confidence": conf,
            "decisiveness": decisive, "area_fraction": frac, "area_plausibility": plaus}


def vessel_exclusion_mask(rgb: np.ndarray, sclera: np.ndarray,
                          redness_percentile: float = 75.0) -> tuple[np.ndarray, float]:
    """Drop visibly vascularised sclera pixels from the reference region.

    Vessels are red and spatially non-uniform, and haemoglobin absorption is exactly
    what corrupts a white reference. Redness is measured as R / (G + B), which is
    largely invariant to overall illumination intensity, and pixels above a percentile
    OF THE SCLERA ITSELF are dropped - an absolute threshold would behave differently
    under each of MOBIUS's three lighting conditions.

    Returns (kept_mask, fraction_removed).
    """
    if sclera.sum() == 0:
        return sclera, 0.0
    img = rgb.astype(np.float64)
    redness = img[..., 0] / np.clip(img[..., 1] + img[..., 2], 1e-6, None)
    vals = redness[sclera]
    thr = np.percentile(vals, redness_percentile)
    kept = sclera & (redness <= thr)
    removed = 1.0 - kept.sum() / max(sclera.sum(), 1)
    return kept, float(removed)


@torch.no_grad()
def predict_mask(model: nn.Module, img_rgb: np.ndarray, size: int = 384,
                 device: str = "cuda") -> tuple[np.ndarray, torch.Tensor]:
    """Run the model on a full-resolution RGB image; return labels at native size."""
    import cv2

    h, w = img_rgb.shape[:2]
    x = cv2.resize(img_rgb, (size, size), interpolation=cv2.INTER_AREA)
    t = torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1))).float() / 255.0
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    t = ((t - mean) / std).unsqueeze(0).to(device)
    with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device == "cuda"):
        logits = model(t)
    probs = torch.softmax(logits.float(), dim=1)
    lab = probs.argmax(dim=1)[0].cpu().numpy().astype(np.uint8)
    lab_full = cv2.resize(lab, (w, h), interpolation=cv2.INTER_NEAREST)
    return lab_full, probs.cpu()
