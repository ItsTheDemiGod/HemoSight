"""Check 2 - split integrity.

PROVENANCE. Phase 1, splits (src/hemosight/io/splits.py, DECISION LOG 2026-09-11
"Splits grouped by (subject_id, content hash), not subject_id alone"). Grouping by
subject id looks sufficient and is not: identical images appeared under different
subject ids, so 1,708 nominal subject ids collapsed to 1,067 leak-proof groups. That
gap of 641 is precisely the leakage a subject-level split would have permitted, and a
reader of the resulting paper could not have seen it.

The grouping construction is not reimplemented - leakproof_groups() and
verify_no_leak() are imported from the Phase 1 module unchanged. What is generalised
is the target: the submitter's own split column, judged against the grouping their
data actually requires.

Three questions, in descending order of how badly a failure invalidates a score:
  1. Does a subject_id appear in more than one split?
  2. Does a content-identical image appear in more than one split?
  3. Is the submitter's declared `group` column coarse enough - does it ever cut a
     leak-proof component in half?
Question 2 needs pixels. Without them the check reports what it could establish and
returns INSUFFICIENT_DATA for the rest rather than passing the submission on the
strength of the axis it could see.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from hemosight.io.splits import leakproof_groups, verify_no_leak

from .contract import AuditInput
from .images import hash_frame
from .verdict import FAIL, INSUFFICIENT, PASS, CheckResult, Timer, insufficient

CHECK_ID = "split_integrity"
TITLE = "Split integrity"
PROVENANCE = ("Phase 1 splits - connected components of (subject_id, content hash) "
              "(src/hemosight/io/splits.py, DECISION LOG 2026-09-11)")


def run(inp: AuditInput, thresholds: dict | None = None,
        preregistered: bool = False, progress=None,
        cache: dict | None = None) -> CheckResult:
    th = {"allow_subject_across_splits": False, "allow_group_undersplit": False}
    th.update(thresholds or {})

    with Timer() as t:
        if not inp.has("split"):
            return insufficient(
                CHECK_ID, TITLE, PROVENANCE, missing=["split"],
                explanation=(
                    "There is no split column, so there is no declared train/test "
                    "boundary to test. The grouping statistics below are still "
                    "computable, but whether the split respects them is not, and is "
                    "not inferred."))

        df = inp.df
        sp = df["split"].astype(str)
        subjects = pd.unique(inp.subject_id)
        n_sub = int(subjects.size)

        # ---- question 1: the subject axis, always available -------------------
        per_sub = pd.Series(sp.to_numpy()).groupby(inp.subject_id).nunique()
        sub_cross = per_sub[per_sub > 1]

        # ---- question 2: the content axis, needs pixels -----------------------
        hashed, notes = hash_frame(inp, cache=cache, progress=progress)
        have_hashes = len(hashed) > 0 and hashed["md5"].notna().any()
        collapse = None
        hash_cross: list[str] = []
        if have_hashes:
            g = leakproof_groups(hashed.rename(columns={"subject_id": "subject_id"}),
                                 hash_col="md5")
            frame = hashed.assign(_group=g.to_numpy())
            n_groups = int(pd.unique(frame["_group"]).size)
            n_nominal = int(pd.unique(frame["subject_id"].astype(str)).size)
            collapse = {
                "nominal_subject_ids": n_nominal,
                "leakproof_groups": n_groups,
                "collapsed_by": n_nominal - n_groups,
            }
            problems = verify_no_leak(
                frame.assign(subject_id=frame["subject_id"].astype(str),
                             split=frame["split"].astype(str)),
                group_col="_group", split_col="split", hash_col="md5")
            hash_cross = problems

        # ---- question 3: is the submitter's own grouping coarse enough? -------
        group_undersplit = None
        if inp.has("group") and have_hashes:
            frame = hashed.assign(
                _group=leakproof_groups(hashed, hash_col="md5").to_numpy(),
                _claimed=hashed["group"].astype(str).to_numpy())
            per_comp = frame.groupby("_group")["_claimed"].nunique()
            group_undersplit = int((per_comp > 1).sum())

        measured = {
            "n_rows": int(len(df)),
            "n_subjects": n_sub,
            "splits": sorted(sp.unique().tolist()),
            "n_subjects_in_more_than_one_split": int(len(sub_cross)),
            "content_hashes_available": bool(have_hashes),
        }
        if collapse:
            measured.update({
                "nominal_subject_ids": collapse["nominal_subject_ids"],
                "leakproof_groups": collapse["leakproof_groups"],
                "subject_ids_collapsed_by": collapse["collapsed_by"],
            })
        if group_undersplit is not None:
            measured["declared_groups_cutting_a_leakproof_component"] = group_undersplit

        details = {
            "image_notes": notes,
            "subjects_crossing_splits": [str(s) for s in sub_cross.index[:25]],
            "verify_no_leak_problems": hash_cross,
            "rows_per_split": sp.value_counts().to_dict(),
        }

        failures = []
        if len(sub_cross):
            failures.append(f"{len(sub_cross)} subject_ids appear in more than one "
                            "split")
        if hash_cross:
            failures.extend(hash_cross)
        if group_undersplit:
            failures.append(f"{group_undersplit} leak-proof components are cut by the "
                            "declared group column")

        if failures:
            res = CheckResult(
                CHECK_ID, TITLE, FAIL,
                headline="; ".join(failures),
                explanation=(
                    "The declared split does not isolate the unit of independence. "
                    "Rows on the held-out side share a subject, or share pixels, with "
                    "rows the model trained on, so the held-out score measures recall "
                    "as well as generalisation. Phase 1 of this project found 1,708 "
                    "nominal subject ids collapsing to 1,067 leak-proof groups on data "
                    "that looked correctly split."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
        elif not have_hashes:
            res = CheckResult(
                CHECK_ID, TITLE, INSUFFICIENT,
                headline=(f"no subject_id spans a split across {n_sub} subjects, but "
                          "the content axis could not be checked"),
                explanation=(
                    "The subject axis is clean. The content axis is not testable: "
                    "without images there are no content hashes, so whether two rows "
                    "carry identical pixels under different subject ids cannot be "
                    "determined. That is exactly the case Phase 1 found, and it is not "
                    "visible from a predictions table. Supply an image directory or an "
                    "image_path column to complete this check."),
                provenance=PROVENANCE, measured=measured,
                missing=["content hashes (image_path column or image directory)"],
                details=details, threshold=th,
                threshold_preregistered=preregistered)
        else:
            res = CheckResult(
                CHECK_ID, TITLE, PASS,
                headline=(f"{measured.get('leakproof_groups', n_sub)} leak-proof "
                          "groups, none spanning a split"),
                explanation=(
                    "Every connected component of (subject_id, content hash) lies "
                    "wholly inside one split, so neither a subject nor a byte-identical "
                    "image crosses the train/test boundary."),
                provenance=PROVENANCE, measured=measured, details=details,
                threshold=th, threshold_preregistered=preregistered)
    res.seconds = t.seconds
    return res
