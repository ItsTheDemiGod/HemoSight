"""Reflectance priors for reference surfaces.

THE SCIENTIFIC PREMISE OF PHASE 2
---------------------------------
The sclera is NOT a neutral white reference. It is slightly yellowish, varies with
age, and carries visible vasculature that is red and spatially non-uniform. A method
that assumes the reference is white will fail, and when it fails we must be able to
say WHY.

So illuminant estimation here is posed as: *estimate the illuminant given a surface
with a KNOWN NON-NEUTRAL REFLECTANCE PRIOR*, never as *given an assumed-white
surface*. The prior is an explicit, swappable object so that the central empirical
question of this phase can be answered rather than assumed:

    Does a fixed population-average prior suffice, or does per-subject variation
    dominate?

The measurement model is deliberately simple and stated openly:

    measured_rgb  =  illuminant_rgb  *  reflectance_rgb        (element-wise)

so an estimate is `illuminant = measured / reflectance`. `reflectance_rgb` is a
*relative* camera-space reflectance, defined up to scale, because illuminants are
themselves only defined up to scale. Assuming neutrality means reflectance = (1,1,1),
which recovers the naive white-reference method as one prior among several - so the
naive method is evaluated on exactly the same footing as the informed ones.

The same abstraction serves the ColorChecker neutral patches (N1a) and the sclera
(N1b), which is what makes the N1a ablation genuinely predictive of the N1b result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


class ReflectancePrior:
    """Base class. `reflectance(key)` returns a relative RGB reflectance, up to scale."""

    name: str = "base"

    def reflectance(self, key: object | None = None) -> np.ndarray:
        raise NotImplementedError

    def is_fitted(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r}>"


class NeutralPrior(ReflectancePrior):
    """The naive assumption: the reference surface is spectrally flat.

    This is the hypothesis Phase 2 exists to test, not a fallback. Keeping it as a
    first-class prior means every result reports what assuming neutrality costs.
    """

    name = "neutral"

    def reflectance(self, key: object | None = None) -> np.ndarray:
        return np.ones(3, dtype=float)


@dataclass
class FixedPopulationPrior(ReflectancePrior):
    """One reflectance for the whole population, fitted on training data only.

    If this suffices, calibration-free operation is practical: a single constant
    shipped with the model. That is the strong practical result N1b is testing for.
    """

    value: np.ndarray = field(default_factory=lambda: np.ones(3))
    name: str = "fixed_population"
    n_fitted_on: int = 0

    def reflectance(self, key: object | None = None) -> np.ndarray:
        return np.asarray(self.value, dtype=float)

    def is_fitted(self) -> bool:
        return self.n_fitted_on > 0

    @classmethod
    def fit(cls, measured: np.ndarray, illuminants: np.ndarray,
            name: str = "fixed_population") -> FixedPopulationPrior:
        """Recover the reference surface's reflectance from paired observations.

        Given measured RGB and the KNOWN illuminant for the same samples, the
        element-wise ratio is the surface reflectance. Aggregation is by median in log
        space: the model is multiplicative, so the geometric mean is the natural
        centre, and the median resists the outliers that segmentation errors produce.
        """
        m = np.atleast_2d(np.asarray(measured, dtype=float))
        i = np.atleast_2d(np.asarray(illuminants, dtype=float))
        m = m / np.linalg.norm(m, axis=1, keepdims=True)
        i = i / np.linalg.norm(i, axis=1, keepdims=True)
        ratio = m / np.clip(i, 1e-8, None)
        ok = np.isfinite(ratio).all(axis=1) & (ratio > 0).all(axis=1)
        ratio = ratio[ok]
        if len(ratio) == 0:
            return cls(np.ones(3), name=name, n_fitted_on=0)
        val = np.exp(np.median(np.log(ratio), axis=0))
        return cls(val / val.sum() * 3.0, name=name, n_fitted_on=int(len(ratio)))


@dataclass
class PerKeyPrior(ReflectancePrior):
    """A separate reflectance per key (per camera, or per subject).

    For N1b the key is the subject. If this materially beats the fixed prior, then
    per-subject variation dominates and calibration-free deployment is NOT supported
    by a shipped constant - an important negative finding.
    """

    table: dict = field(default_factory=dict)
    fallback: np.ndarray = field(default_factory=lambda: np.ones(3))
    name: str = "per_key"

    def reflectance(self, key: object | None = None) -> np.ndarray:
        v = self.table.get(key)
        return np.asarray(v if v is not None else self.fallback, dtype=float)

    def is_fitted(self) -> bool:
        return len(self.table) > 0

    @classmethod
    def fit(cls, keys, measured: np.ndarray, illuminants: np.ndarray,
            min_samples: int = 2, name: str = "per_key") -> PerKeyPrior:
        m = np.atleast_2d(np.asarray(measured, dtype=float))
        i = np.atleast_2d(np.asarray(illuminants, dtype=float))
        table: dict = {}
        keys = list(keys)
        for k in set(keys):
            sel = [n for n, kk in enumerate(keys) if kk == k]
            if len(sel) < min_samples:
                continue
            p = FixedPopulationPrior.fit(m[sel], i[sel])
            if p.is_fitted():
                table[k] = p.value
        glob = FixedPopulationPrior.fit(m, i)
        return cls(table=table, fallback=glob.value, name=name)


@dataclass
class OraclePrior(ReflectancePrior):
    """Per-sample true reflectance. Not deployable - it is the performance ceiling.

    Reporting it turns "our method has error X" into "of the achievable error, our
    prior captures this fraction", which is the honest framing.
    """

    table: dict = field(default_factory=dict)
    name: str = "oracle_per_sample"

    def reflectance(self, key: object | None = None) -> np.ndarray:
        v = self.table.get(key)
        return np.asarray(v if v is not None else np.ones(3), dtype=float)


def estimate_illuminant(measured_rgb: np.ndarray, prior: ReflectancePrior,
                        key: object | None = None) -> np.ndarray:
    """Invert the measurement model: illuminant = measured / reflectance.

    Returns a unit vector; illuminants are defined only up to scale.
    """
    m = np.asarray(measured_rgb, dtype=float)
    r = np.clip(prior.reflectance(key), 1e-8, None)
    est = m / r
    n = np.linalg.norm(est)
    return est / n if n > 0 else np.array([1.0, 1.0, 1.0]) / np.sqrt(3)
