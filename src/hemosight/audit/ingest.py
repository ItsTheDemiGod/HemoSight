"""Ingestion of EXTERNAL submissions into the audit contract.

A third party's released predictions almost never arrive in the contract's shape
(`subject_id, y_true, y_pred, ...`). This module converts the common shapes and, more
importantly, RECORDS every assumption the conversion had to make, so that the checks
which depend on an assumed column return INSUFFICIENT DATA rather than a verdict the
data cannot support.

The cases it handles, and what each costs:

  per-image predictions, subject id present
      -> one row per subject: predictions aggregated (median); image paths kept as a
         list for the duplicate check. No assumption.
  per-image predictions, NO subject id, a filename pattern that encodes one
      -> subject_id derived by regex. Recorded as DERIVED; the pattern is stored so a
         reader can judge it.
  per-image predictions, NO subject id, no pattern
      -> subject_id := image id. This is the Phase 1 leak in disguise: every check that
         relies on subject independence (split integrity, the subject-level leak test,
         subject robustness) is FORCED to INSUFFICIENT DATA, because a split that shows
         no subject in two folds proves nothing when each image is its own "subject".
         The duplicate check still runs if images are supplied: byte-identical images in
         different splits are evidence whatever the ids say.
  missing splits            -> split integrity INSUFFICIENT (the contract already does this)
  missing demographics      -> demographic baseline / proxy probe INSUFFICIENT (likewise)
  classification-only outputs (a class label or probability, no numeric reference)
      -> NOT INGESTIBLE for the regression checks. `NotAuditable` is raised with the
         list of what is absent, and the register records the attempt.
  haemoglobin in g/L        -> refused unless `hb_units` is stated explicitly; values
         that look like g/L (median > 30) with no declared unit raise, never convert.
  sex encodings             -> normalised to M / F from the usual spellings; anything
         else is left as-is and reported.

Nothing is inferred silently. The `IngestRecord` travels with the CSV and into the
external report, where "what could not be checked" gets the same prominence as "what
was checked".
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .contract import REQUIRED

SEX_MAP = {"m": "M", "male": "M", "man": "M", "1": "M", "true": "M",
           "f": "F", "female": "F", "woman": "F", "0": "F", "false": "F"}
SUBJECT_DEPENDENT_CHECKS = ("split_integrity", "subgroup_robustness")


class NotAuditable(Exception):
    """The submission cannot be brought into the contract. `missing` says why."""

    def __init__(self, missing: list[str], note: str = ""):
        self.missing, self.note = missing, note
        super().__init__("not auditable: missing " + ", ".join(missing) + (f" ({note})" if note else ""))


@dataclass
class IngestSpec:
    """How to read a third party's table. Every field is a statement by the auditor
    about the source, recorded verbatim in the IngestRecord."""
    y_true: str                              # column holding the reference Hb
    y_pred: str                              # column holding the model's held-out prediction
    hb_units: str = "g/dL"                   # "g/dL" or "g/L"; must be stated
    subject_id: str | None = None            # column with the subject id, if any
    subject_from_image: str | None = None    # regex with one group applied to the image column
    image_path: str | None = None            # column with an image id / path
    split: str | None = None
    split_map: dict[str, str] = field(default_factory=dict)   # e.g. {"0": "train", "1": "test"}
    age: str | None = None
    sex: str | None = None
    device: str | None = None
    site: str | None = None
    group: str | None = None
    candidates: dict[str, str] = field(default_factory=dict)  # name -> column (selection candidates)
    seeds: dict[str, str] = field(default_factory=dict)       # k -> column (seed replicates)
    source_description: str = ""             # where the table came from, in the auditor's words


@dataclass
class IngestRecord:
    source_description: str
    n_rows_in: int
    n_rows_out: int
    n_subjects: int
    columns_supplied: list[str]
    columns_derived: list[str]
    assumptions: list[str]
    unsupported_checks: dict[str, str]       # check_id -> reason it must return INSUFFICIENT
    warnings: list[str]
    spec: dict

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def _norm_sex(v):
    if pd.isna(v):
        return np.nan
    return SEX_MAP.get(str(v).strip().lower(), str(v).strip())


def ingest(df: pd.DataFrame, spec: IngestSpec) -> tuple[pd.DataFrame, IngestRecord]:
    """Convert `df` to the contract. Returns (contract_frame, record)."""
    assumptions: list[str] = []
    derived: list[str] = []
    warnings: list[str] = []
    unsupported: dict[str, str] = {}
    n_in = len(df)

    # ---------------------------------------------------------------- reference
    missing = [c for c in (spec.y_true, spec.y_pred) if c not in df.columns]
    if missing:
        raise NotAuditable([f"column {c!r}" for c in missing],
                           "a numeric reference and a numeric prediction are the minimum")
    y_true = pd.to_numeric(df[spec.y_true], errors="coerce")
    y_pred = pd.to_numeric(df[spec.y_pred], errors="coerce")
    if y_true.notna().sum() == 0 or y_pred.notna().sum() == 0:
        raise NotAuditable(["numeric y_true and y_pred"],
                           "classification labels or probabilities cannot feed regression checks")
    if set(y_true.dropna().unique()) <= {0, 1} or set(y_pred.dropna().unique()) <= {0, 1}:
        raise NotAuditable(["a numeric haemoglobin reference and prediction"],
                           "the released outputs are binary; only the duplicate and split "
                           "checks could apply and they need images or ids, not these columns")
    if spec.hb_units not in ("g/dL", "g/L"):
        raise NotAuditable(["hb_units stated as 'g/dL' or 'g/L'"])
    if spec.hb_units == "g/L":
        y_true, y_pred = y_true / 10.0, y_pred / 10.0
        assumptions.append("haemoglobin converted from g/L to g/dL as declared in the spec")
    elif float(np.nanmedian(y_true)) > 30:
        raise NotAuditable(["hb_units"], f"median y_true is {float(np.nanmedian(y_true)):.0f}, "
                           "which looks like g/L; declare hb_units='g/L' explicitly rather than "
                           "letting the tool guess")

    out = pd.DataFrame({"y_true": y_true.to_numpy(), "y_pred": y_pred.to_numpy()})

    # ---------------------------------------------------------------- subject id
    if spec.subject_id and spec.subject_id in df.columns:
        out["subject_id"] = df[spec.subject_id].astype(str).to_numpy()
    elif spec.subject_from_image and spec.image_path and spec.image_path in df.columns:
        rx = re.compile(spec.subject_from_image)
        ids = df[spec.image_path].astype(str).map(lambda s: (rx.search(s).group(1) if rx.search(s) else None))
        if ids.isna().any():
            raise NotAuditable(["a subject id for every row"],
                               f"{int(ids.isna().sum())} image names did not match {spec.subject_from_image!r}")
        out["subject_id"] = ids.to_numpy()
        derived.append("subject_id")
        assumptions.append(f"subject_id DERIVED from the image name with pattern "
                           f"{spec.subject_from_image!r}; if the pattern is wrong, independence "
                           "is wrong")
    else:
        key = df[spec.image_path].astype(str) if spec.image_path and spec.image_path in df.columns \
            else pd.Series([f"row{i}" for i in range(len(df))])
        out["subject_id"] = key.to_numpy()
        derived.append("subject_id")
        assumptions.append("subject_id ASSUMED = one subject per image/row. Independence is "
                           "NOT established. Any split that shows no subject in two folds "
                           "proves nothing under this assumption.")
        for c in SUBJECT_DEPENDENT_CHECKS:
            unsupported[c] = ("subject_id was assumed unique per row; a subject-level "
                              "verdict cannot be supported")

    # ---------------------------------------------------------------- optional columns
    if spec.image_path and spec.image_path in df.columns:
        out["image_path"] = df[spec.image_path].astype(str).to_numpy()
    if spec.split and spec.split in df.columns:
        s = df[spec.split].astype(str)
        if spec.split_map:
            s = s.map(lambda v: spec.split_map.get(v, v))
            assumptions.append(f"split labels mapped via {spec.split_map}")
        out["split"] = s.to_numpy()
    for name in ("age", "device", "site", "group"):
        col = getattr(spec, name)
        if col and col in df.columns:
            out[name] = df[col].to_numpy()
    if spec.sex and spec.sex in df.columns:
        sx = df[spec.sex].map(_norm_sex)
        odd = sorted(set(sx.dropna()) - {"M", "F"})
        if odd:
            warnings.append(f"sex values not normalised to M/F: {odd[:5]}")
        out["sex"] = sx.to_numpy()
    for name, col in spec.candidates.items():
        if col in df.columns:
            out[f"y_pred__{name}"] = pd.to_numeric(df[col], errors="coerce").to_numpy()
    for k, col in spec.seeds.items():
        if col in df.columns:
            out[f"y_pred_seed__{k}"] = pd.to_numeric(df[col], errors="coerce").to_numpy()

    # ---------------------------------------------------------------- per-image -> per-subject
    if out["subject_id"].duplicated().any():
        n_img = len(out)
        agg = {"y_true": "median", "y_pred": "median"}
        for c in out.columns:
            if c.startswith("y_pred__") or c.startswith("y_pred_seed__"):
                agg[c] = "median"
        for c in ("age", "sex", "device", "site", "group", "split"):
            if c in out.columns:
                agg[c] = "first"
        if "image_path" in out.columns:
            agg["image_path"] = lambda v: "|".join(map(str, v))
        # Subjects whose images sit in more than one split are a leak; keep the fact.
        if "split" in out.columns:
            multi = out.groupby("subject_id")["split"].nunique()
            n_multi = int((multi > 1).sum())
            if n_multi:
                warnings.append(f"{n_multi} subjects have images in more than one split "
                                "(kept as 'first' after aggregation; the split-integrity "
                                "check should be run on the PER-IMAGE table too)")
        out = out.groupby("subject_id", as_index=False).agg(agg)
        assumptions.append(f"{n_img} per-image rows aggregated to {len(out)} subjects "
                           "(median of predictions and references)")

    # ---------------------------------------------------------------- what is absent
    absent = []
    if "split" not in out.columns:
        absent.append("split -> split_integrity will be INSUFFICIENT")
    if not any(c in out.columns for c in ("age", "sex", "device", "site")):
        absent.append("age/sex/device/site -> demographic_baseline and proxy_probe will be INSUFFICIENT")
    if "image_path" not in out.columns:
        absent.append("image_path -> duplicates will be INSUFFICIENT")
    if not any(c.startswith("y_pred_seed__") for c in out.columns):
        absent.append("seed replicates -> seed_stability will be INSUFFICIENT")
    warnings.extend(absent)

    for c in REQUIRED:
        assert c in out.columns, c
    rec = IngestRecord(
        source_description=spec.source_description, n_rows_in=n_in, n_rows_out=len(out),
        n_subjects=int(out["subject_id"].nunique()),
        columns_supplied=[c for c in out.columns if c not in derived],
        columns_derived=derived, assumptions=assumptions, unsupported_checks=unsupported,
        warnings=warnings, spec=asdict(spec))
    return out, rec


def ingest_file(path: str | Path, spec: IngestSpec) -> tuple[pd.DataFrame, IngestRecord]:
    p = Path(path)
    df = pd.read_csv(p) if p.suffix.lower() == ".csv" else pd.read_excel(p)
    return ingest(df, spec)
