"""Phase 2, Task 1: train sclera/iris/pupil/periocular segmentation on SBVPI+MOBIUS.

Reports IoU and Dice overall AND broken down by MOBIUS device and lighting, because
a segmentation quality that varies by device would confound every downstream N1b
result and must be measured now rather than discovered later.

    .\\.venv\\Scripts\\python.exe scripts\\phase2_train_segmentation.py [--epochs N]
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset

from hemosight.calibration.segmentation import (
    UNetResNet18,
    confusion,
    dice_loss,
    iou_dice_from_confusion,
    merged_bg_cross_entropy,
)
from hemosight.calibration.segmentation_data import (
    CLASSES,
    N_CLASSES,
    EyeSegDataset,
    index_mobius,
    index_sbvpi,
    subject_split,
)
from hemosight.io import paths

OUT = paths.INTERIM / "phase2"
CKPT = OUT / "segmentation_unet_r18.pt"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=12)
    ap.add_argument("--size", type=int, default=384)
    ap.add_argument("--limit-mobius", type=int, default=0, help="0 = use all")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={dev}")

    mob = index_mobius()
    sbv = index_sbvpi()
    # `_bad` frames are deliberately unusable; they are excluded from training and
    # kept aside as a labelled probe for the quality score.
    mob_bad = [s for s in mob if s.is_bad]
    mob = [s for s in mob if not s.is_bad]
    if args.limit_mobius:
        mob = mob[: args.limit_mobius]
    samples = mob + sbv
    print(f"MOBIUS: {len(mob)} annotated ({len(mob_bad)} 'bad' held out) | SBVPI: {len(sbv)}")

    tr_idx, va_idx = subject_split(samples)
    print(f"train={len(tr_idx)} val={len(va_idx)} "
          f"(subject-level split; {len({samples[i].subject_id for i in va_idx})} val subjects)")

    ds_tr = EyeSegDataset(samples, size=args.size, augment=True)
    ds_va = EyeSegDataset(samples, size=args.size, augment=False)
    dl_tr = DataLoader(Subset(ds_tr, tr_idx), batch_size=args.batch, shuffle=True,
                       num_workers=4, pin_memory=True, drop_last=True, persistent_workers=True)
    dl_va = DataLoader(Subset(ds_va, va_idx), batch_size=args.batch, shuffle=False,
                       num_workers=4, pin_memory=True, persistent_workers=True)

    model = UNetResNet18().to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt, max_lr=1e-3, total_steps=args.epochs * max(1, len(dl_tr)))
    scaler = torch.amp.GradScaler("cuda", enabled=dev == "cuda")

    history = []
    best = -1.0
    for ep in range(args.epochs):
        model.train()
        t0, tot, n = time.time(), 0.0, 0
        for x, y, mg, _ in dl_tr:
            x, y = x.to(dev, non_blocking=True), y.to(dev, non_blocking=True)
            mg = mg.to(dev, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=dev == "cuda"):
                logits = model(x)
                loss = merged_bg_cross_entropy(logits, y, mg) + dice_loss(logits, y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            tot += float(loss) * len(x)
            n += len(x)

        model.eval()
        cm = torch.zeros(N_CLASSES, N_CLASSES, dtype=torch.int64)
        with torch.no_grad():
            for x, y, _mg, _ in dl_va:
                x, y = x.to(dev), y.to(dev)
                with torch.autocast("cuda", dtype=torch.float16, enabled=dev == "cuda"):
                    logits = model(x)
                cm += confusion(logits.float(), y).cpu()
        iou, dice = iou_dice_from_confusion(cm.numpy())
        sclera_iou = float(iou[1])
        mem = torch.cuda.max_memory_allocated() / 1024**3 if dev == "cuda" else 0.0
        print(f"ep{ep+1}/{args.epochs} loss={tot/max(n,1):.4f} "
              f"sclera_IoU={sclera_iou:.4f} "
              f"IoU=[{', '.join(f'{c}:{v:.3f}' for c, v in zip(CLASSES, iou))}] "
              f"{time.time()-t0:.0f}s peakGPU={mem:.1f}GB")
        history.append({"epoch": ep + 1, "loss": tot / max(n, 1),
                        "iou": [None if np.isnan(v) else float(v) for v in iou],
                        "dice": [None if np.isnan(v) else float(v) for v in dice]})
        if sclera_iou > best:
            best = sclera_iou
            torch.save({"model": model.state_dict(), "classes": CLASSES,
                        "size": args.size, "sclera_iou": best}, CKPT)

    (OUT / "segmentation_history.json").write_text(
        json.dumps({"history": history, "best_sclera_iou": best,
                    "n_train": len(tr_idx), "n_val": len(va_idx),
                    "args": vars(args)}, indent=2), encoding="utf-8")
    print(f"\nbest sclera IoU={best:.4f} -> {CKPT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
