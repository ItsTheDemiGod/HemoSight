"""Deep models over raw PPG waveforms.

Phase 4 tested hand-engineered AC/DC features and found nothing. This closes the one
remaining representation: let a network see the waveform itself, in case pulse
morphology carries haemoglobin information that a scalar ratio discards.

PREPROCESSING - deliberately minimal
    Raw 200 Hz -> anti-alias filtered and decimated to 50 Hz (PPG content is < 10 Hz,
    so this is lossless for the signal and 4x cheaper). Split into fixed windows.
    Each channel is z-scored WITHIN its window, which removes the DC pedestal and the
    per-recording gain - the same nuisances AC/DC targets, but without committing to a
    scalar summary. Pulse SHAPE survives; absolute intensity does not.

    A second variant keeps the per-channel log-DC as an auxiliary scalar input, so the
    network can use absolute level if that is where the information lives.

LEAKAGE
    Windows from one subject must never straddle a fold. `make_windows` returns a
    subject id per window and the training script asserts disjointness. With 252
    subjects and a model of this capacity, subject leakage would produce an
    impressive-looking and completely false result.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from scipy import signal as sps

FS_RAW = 200.0
FS = 50.0                 # after decimation
WINDOW_S = 10.0
WINDOW = int(WINDOW_S * FS)     # 500 samples
STRIDE_S = 5.0                  # 50% overlap


def preprocess(sig: np.ndarray) -> np.ndarray | None:
    """(n, 4) raw at 200 Hz -> (m, 4) at 50 Hz, band-limited."""
    x = np.asarray(sig, dtype=float)
    if x.ndim != 2 or x.shape[1] != 4 or len(x) < int(15 * FS_RAW):
        return None
    # Band-pass 0.5-8 Hz before decimating: keeps the pulse and its harmonics, drops
    # baseline wander and anything above the new Nyquist.
    b, a = sps.butter(4, [0.5 / (FS_RAW / 2), 8.0 / (FS_RAW / 2)], btype="band")
    filt = sps.filtfilt(b, a, x, axis=0)
    return sps.decimate(filt, int(FS_RAW / FS), axis=0, zero_phase=True)


def make_windows(sig: np.ndarray, subject_id: int) -> tuple[np.ndarray, np.ndarray]:
    """Fixed windows, each channel z-scored within the window."""
    p = preprocess(sig)
    if p is None or len(p) < WINDOW:
        return np.empty((0, 4, WINDOW), dtype=np.float32), np.empty(0, dtype=np.int64)
    step = int(STRIDE_S * FS)
    out = []
    for s in range(0, len(p) - WINDOW + 1, step):
        w = p[s:s + WINDOW]
        mu = w.mean(axis=0, keepdims=True)
        sd = w.std(axis=0, keepdims=True)
        if np.any(sd < 1e-9):
            continue
        out.append(((w - mu) / sd).T.astype(np.float32))   # (4, WINDOW)
    if not out:
        return np.empty((0, 4, WINDOW), dtype=np.float32), np.empty(0, dtype=np.int64)
    return np.stack(out), np.full(len(out), subject_id, dtype=np.int64)


class CNN1D(nn.Module):
    """Small dilated 1D CNN. Kept small on purpose: 252 subjects cannot support more."""

    def __init__(self, in_ch: int = 4, width: int = 32):
        super().__init__()
        def blk(i, o, d):
            return nn.Sequential(
                nn.Conv1d(i, o, 7, padding=3 * d, dilation=d), nn.BatchNorm1d(o),
                nn.ReLU(inplace=True), nn.MaxPool1d(2))
        self.body = nn.Sequential(
            blk(in_ch, width, 1), blk(width, width * 2, 2),
            blk(width * 2, width * 2, 4), nn.AdaptiveAvgPool1d(1))
        self.head = nn.Sequential(nn.Flatten(), nn.Dropout(0.3),
                                  nn.Linear(width * 2, 1))

    def embed(self, x):
        return self.body(x).flatten(1)

    def forward(self, x):
        return self.head(self.body(x)).squeeze(-1)


class GRUNet(nn.Module):
    """Bidirectional GRU over a lightly strided waveform."""

    def __init__(self, in_ch: int = 4, hidden: int = 48):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(in_ch, 32, 7, stride=2, padding=3), nn.BatchNorm1d(32),
            nn.ReLU(inplace=True))
        self.rnn = nn.GRU(32, hidden, num_layers=1, batch_first=True,
                          bidirectional=True)
        self.head = nn.Sequential(nn.Dropout(0.3), nn.Linear(hidden * 2, 1))

    def embed(self, x):
        h = self.stem(x).transpose(1, 2)
        o, _ = self.rnn(h)
        return o.mean(dim=1)

    def forward(self, x):
        return self.head(self.embed(x)).squeeze(-1)


class SpecCNN(nn.Module):
    """2D CNN over a per-channel spectrogram."""

    def __init__(self, in_ch: int = 4, width: int = 16):
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv2d(in_ch, width, 3, padding=1), nn.BatchNorm2d(width),
            nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(width, width * 2, 3, padding=1), nn.BatchNorm2d(width * 2),
            nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d(1))
        self.head = nn.Sequential(nn.Flatten(), nn.Dropout(0.3),
                                  nn.Linear(width * 2, 1))

    @staticmethod
    def to_spec(x: torch.Tensor) -> torch.Tensor:
        # (B, C, T) -> (B, C, F, T'); small window so the 500-sample input survives.
        B, C, T = x.shape
        z = torch.stft(x.reshape(B * C, T), n_fft=64, hop_length=16,
                       window=torch.hann_window(64, device=x.device),
                       return_complex=True)
        m = torch.log1p(z.abs())
        return m.reshape(B, C, m.shape[-2], m.shape[-1])

    def embed(self, x):
        return self.body(self.to_spec(x)).flatten(1)

    def forward(self, x):
        return self.head(self.body(self.to_spec(x))).squeeze(-1)


ARCHITECTURES = {"cnn1d": CNN1D, "gru": GRUNet, "speccnn": SpecCNN}
