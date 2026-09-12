"""The input contract: one CSV of predictions, plus optional images.

The audit checks in Phases 1-5 were each written against this project's own data.
Generalising them means agreeing one table that any submitted model can be described
by, and refusing to guess when a column is absent.

REQUIRED
    subject_id   the unit of independence. Never a row/image id: the whole point of
                 this project's Phase 1 finding is that image-level thinking is what
                 leaks.
    y_true       reference measurement
    y_pred       the submitted model's held-out prediction

OPTIONAL, each unlocking specific checks
    split        train/calibration/test membership          -> leakage, split integrity
    age sex device site                                     -> demographic baseline,
                                                               proxy probe, subgroups
    group        the submitter's own claimed grouping unit  -> split integrity
    image_path   path to the image a row came from          -> duplicate detection
    y_pred__<name>       a candidate the submitted model was SELECTED from. Supplying
                         these is what allows the selection-aware permutation null;
                         without them only the selected-model-only null is available.
    y_pred_seed__<k>     the same model retrained under a different seed -> seed
                         stability. Fewer than three and the check declines to answer.
    any other numeric column is treated as a feature for the ceiling analysis.

Nothing here is inferred. A missing column produces INSUFFICIENT_DATA from the checks
that need it, never a substituted default.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = ("subject_id", "y_true", "y_pred")
OPTIONAL = ("split", "age", "sex", "device", "site", "group", "image_path")
DEMOGRAPHIC_CANDIDATES = ("age", "sex", "device", "site")
CATEGORICAL = ("sex", "device", "site", "split")

CAND_RE = re.compile(r"^y_pred__(.+)$")
SEED_RE = re.compile(r"^y_pred_seed__(.+)$")


@dataclass
class AuditInput:
    """A validated submission. Construct with load_predictions()."""

    df: pd.DataFrame
    source: str = "<in-memory>"
    image_dir: Path | None = None
    warnings: list[str] = field(default_factory=list)

    # ---------------------------------------------------------------- accessors
    @property
    def n(self) -> int:
        return len(self.df)

    @property
    def y_true(self) -> np.ndarray:
        return self.df["y_true"].to_numpy(dtype=float)

    @property
    def y_pred(self) -> np.ndarray:
        return self.df["y_pred"].to_numpy(dtype=float)

    @property
    def subject_id(self) -> np.ndarray:
        return self.df["subject_id"].astype(str).to_numpy()

    def has(self, col: str) -> bool:
        # bool() is load-bearing: `notna().any()` returns numpy.bool_, which is NOT a
        # subclass of bool and is not JSON-serialisable. Returning it from a public
        # accessor put np.True_ into summary() and 500ed the upload endpoint.
        if col not in self.df.columns:
            return False
        return bool(self.df[col].notna().any())

    @property
    def demographics(self) -> list[str]:
        """Demographic-like columns actually present and populated."""
        return [c for c in DEMOGRAPHIC_CANDIDATES if self.has(c)]

    @property
    def candidates(self) -> dict[str, np.ndarray]:
        """Selection candidates, including the submitted model itself.

        The submitted prediction is always a candidate: a best-of-one selection is
        still a selection, and naming it keeps the two permutation constructions
        directly comparable.
        """
        out = {"submitted": self.y_pred}
        for c in self.df.columns:
            m = CAND_RE.match(c)
            if m:
                out[m.group(1)] = self.df[c].to_numpy(dtype=float)
        return out

    @property
    def seed_predictions(self) -> dict[str, np.ndarray]:
        out = {}
        for c in self.df.columns:
            m = SEED_RE.match(c)
            if m:
                out[m.group(1)] = self.df[c].to_numpy(dtype=float)
        return out

    @property
    def feature_columns(self) -> list[str]:
        """Numeric columns that are neither the contract's own nor a prediction."""
        reserved = set(REQUIRED) | set(OPTIONAL)
        cols = []
        for c in self.df.columns:
            if c in reserved or CAND_RE.match(c) or SEED_RE.match(c):
                continue
            if pd.api.types.is_numeric_dtype(self.df[c]):
                cols.append(c)
        return cols

    @property
    def grouping(self) -> np.ndarray:
        """The unit whole-fold splits must respect: the submitter's group if given."""
        if self.has("group"):
            return self.df["group"].astype(str).to_numpy()
        return self.subject_id

    def summary(self) -> dict:
        return {
            "source": self.source,
            "rows": int(self.n),
            "subjects": int(pd.unique(self.subject_id).size),
            "columns": list(self.df.columns),
            "demographics_present": self.demographics,
            "n_selection_candidates": len(self.candidates),
            "n_seed_replicates": len(self.seed_predictions),
            "n_feature_columns": len(self.feature_columns),
            "has_split": self.has("split"),
            "has_image_path": self.has("image_path"),
            "image_dir": str(self.image_dir) if self.image_dir else None,
            "y_true_mean": float(np.mean(self.y_true)),
            "y_true_sd": float(np.std(self.y_true)),
            "warnings": self.warnings,
        }


class ContractError(ValueError):
    """The submission cannot be audited at all, as opposed to a check declining."""


def validate_frame(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors block the audit; warnings do not."""
    errors: list[str] = []
    warnings: list[str] = []
    for c in REQUIRED:
        if c not in df.columns:
            errors.append("missing required column " + repr(c))
    if errors:
        return errors, warnings

    for c in ("y_true", "y_pred"):
        v = pd.to_numeric(df[c], errors="coerce")
        if v.isna().all():
            errors.append("column " + repr(c) + " holds no numeric values")
        elif v.isna().any():
            warnings.append(f"{int(v.isna().sum())} non-numeric {c} values -> dropped")

    if df["subject_id"].isna().any():
        warnings.append(
            f"{int(df['subject_id'].isna().sum())} rows have no subject_id -> dropped; "
            "a row with no unit of independence cannot be grouped, and guessing one is "
            "exactly the failure this tool exists to catch")

    n_sub = df["subject_id"].nunique()
    if n_sub == len(df):
        warnings.append("one row per subject_id: within-subject grouping is trivially "
                        "satisfied, and the split-integrity check can only inspect the "
                        "content-hash axis")
    if n_sub < 20:
        warnings.append(f"only {n_sub} subjects: every statistical check here will be "
                        "wide, and several will return INSUFFICIENT_DATA")
    return errors, warnings


def load_predictions(path_or_df, image_dir: str | Path | None = None) -> AuditInput:
    """Load and validate a submission. Raises ContractError on a blocking problem."""
    if isinstance(path_or_df, pd.DataFrame):
        df, source = path_or_df.copy(), "<in-memory>"
    else:
        source = str(path_or_df)
        df = pd.read_csv(path_or_df)

    df.columns = [str(c).strip() for c in df.columns]
    errors, warnings = validate_frame(df)
    if errors:
        raise ContractError("; ".join(errors))

    for c in list(df.columns):
        if c in ("y_true", "y_pred") or CAND_RE.match(c) or SEED_RE.match(c):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "age" in df.columns:
        df["age"] = pd.to_numeric(df["age"], errors="coerce")

    before = len(df)
    df = df[df["subject_id"].notna() & df["y_true"].notna() & df["y_pred"].notna()]
    df = df.reset_index(drop=True)
    if len(df) < before:
        warnings.append(f"dropped {before - len(df)} incomplete rows of {before}")
    if len(df) == 0:
        raise ContractError("no complete rows after dropping missing values")

    d = None if image_dir is None else Path(image_dir)
    if d is not None and not d.is_dir():
        warnings.append(f"image directory {d} does not exist -> image checks will "
                        "report INSUFFICIENT_DATA")
        d = None
    return AuditInput(df=df, source=source, image_dir=d, warnings=warnings)


def encode_design(df: pd.DataFrame, cols: list[str]) -> tuple[np.ndarray, list[str]]:
    """Numeric design matrix over cols: numerics as-is, categoricals one-hot.

    Categorical levels are taken over the whole table rather than per fold, which
    affects only column identity, never which rows a fold may see.
    """
    parts: list[np.ndarray] = []
    names: list[str] = []
    for c in cols:
        s = df[c]
        if c in CATEGORICAL or not pd.api.types.is_numeric_dtype(s):
            s = s.astype(str).fillna("NA")
            levels = sorted(s.unique())
            keep = levels[:-1] if len(levels) > 1 else levels
            for lev in keep:
                parts.append((s == lev).to_numpy(dtype=float)[:, None])
                names.append(f"{c}={lev}")
        else:
            v = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
            parts.append(v[:, None])
            names.append(c)
    if not parts:
        return np.zeros((len(df), 0)), []
    return np.hstack(parts), names
