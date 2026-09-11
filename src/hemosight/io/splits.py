"""Reproducible, leakage-proof split construction.

The grouping unit is NOT the subject id on its own. The overlap check found that

* the same byte-identical image appears under different subject ids, and
* CP-AnemiC is largely contained inside the Ghana conjunctiva set,

so grouping by `subject_id` alone would still place identical pixels on both sides
of a split. Groups are therefore the connected components of a graph whose nodes are
subject ids and content hashes, joined by an edge whenever an image links the two.
Two images that are byte-identical always land in the same group, whatever their
nominal subject id, and whatever dataset they came from.

This is the single most important guard in Phase 1. Everything downstream inherits it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:  # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def leakproof_groups(df: pd.DataFrame, hash_col: str = "md5") -> pd.Series:
    """Connected components over (subject_id, content hash).

    Returns a group label per row. Rows with a missing hash fall back to their
    subject id alone.
    """
    uf = UnionFind()
    for sid, h in zip(df["subject_id"], df.get(hash_col, pd.Series([None] * len(df)))):
        s_node = f"S::{sid}"
        uf.find(s_node)
        if isinstance(h, str) and h:
            uf.union(s_node, f"H::{h}")
    return pd.Series(
        [uf.find(f"S::{s}") for s in df["subject_id"]], index=df.index, name="group"
    )


def grouped_split(
    df: pd.DataFrame,
    group_col: str,
    fractions: dict[str, float],
    seed: int,
    stratify_col: str | None = None,
) -> pd.Series:
    """Assign each row a split name, splitting whole groups.

    When `stratify_col` is given, groups are bucketed by their majority value of
    that column and each bucket is split separately, so class balance is roughly
    preserved without ever splitting a group.
    """
    rng = np.random.default_rng(seed)
    names = list(fractions)
    probs = np.array([fractions[n] for n in names], dtype=float)
    probs = probs / probs.sum()

    groups = df[group_col].to_numpy()
    uniq = pd.unique(groups)

    if stratify_col is not None and stratify_col in df.columns:
        maj = (
            df.groupby(group_col)[stratify_col]
            .agg(lambda s: s.dropna().mode().iloc[0] if s.notna().any() else "NA")
            .astype(str)
        )
        buckets: dict[str, list] = {}
        for g in uniq:
            buckets.setdefault(maj.get(g, "NA"), []).append(g)
    else:
        buckets = {"all": list(uniq)}

    assign: dict[str, str] = {}
    for _, gs in sorted(buckets.items()):
        gs = np.array(gs, dtype=object)
        rng.shuffle(gs)
        # Deterministic cut points; every group gets exactly one split.
        cuts = (np.cumsum(probs) * len(gs)).round().astype(int)
        start = 0
        for name, end in zip(names, cuts):
            for g in gs[start:end]:
                assign[g] = name
            start = end
        for g in gs[start:]:  # rounding remainder
            assign[g] = names[-1]

    return pd.Series([assign[g] for g in groups], index=df.index, name="split")


def verify_no_leak(df: pd.DataFrame, group_col: str, split_col: str,
                   hash_col: str | None = "md5") -> list[str]:
    """Return a list of violations. Empty means the split is clean."""
    problems = []
    per_group = df.groupby(group_col)[split_col].nunique()
    bad = per_group[per_group > 1]
    if len(bad):
        problems.append(f"{len(bad)} groups span multiple splits: {list(bad.index[:5])}")
    if hash_col and hash_col in df.columns:
        h = df[df[hash_col].notna()]
        per_hash = h.groupby(hash_col)[split_col].nunique()
        badh = per_hash[per_hash > 1]
        if len(badh):
            problems.append(
                f"{len(badh)} identical images (md5) span multiple splits: {list(badh.index[:3])}"
            )
    sub = df.groupby("subject_id")[split_col].nunique()
    bads = sub[sub > 1]
    if len(bads):
        problems.append(f"{len(bads)} subject_ids span multiple splits: {list(bads.index[:5])}")
    return problems


def kfold_by_group(df: pd.DataFrame, group_col: str, k: int, seed: int) -> pd.Series:
    """Assign a fold index 0..k-1, splitting whole groups."""
    rng = np.random.default_rng(seed)
    uniq = pd.unique(df[group_col].to_numpy())
    rng.shuffle(uniq)
    fold_of = {g: i % k for i, g in enumerate(uniq)}
    return pd.Series([fold_of[g] for g in df[group_col]], index=df.index, name="fold")
