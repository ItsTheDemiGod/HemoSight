"""Request and response shapes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class PreRegIn(BaseModel):
    # A pre-registration is a record someone will cite later; a one-character title
    # was accepted during Phase 6 and left junk rows in the database (audit
    # 2026-09-12). Whitespace is stripped before the length check.
    title: str = Field(min_length=8, max_length=300)
    notes: str = ""

    @field_validator("title", mode="before")
    @classmethod
    def _strip_title(cls, v):
        return v.strip() if isinstance(v, str) else v
    thresholds: dict[str, dict[str, Any]] = Field(default_factory=dict)
    checks_planned: list[str] = Field(default_factory=list)


class PreRegOut(BaseModel):
    id: str
    title: str
    notes: str
    thresholds: dict[str, Any]
    checks_planned: list[str]
    fingerprint: str
    declared_at: str


class SubmissionOut(BaseModel):
    id: str
    filename: str
    n_rows: int
    n_subjects: int
    summary: dict[str, Any]
    uploaded_at: str
    warnings: list[str] = Field(default_factory=list)
    available_checks: list[str] = Field(default_factory=list)
    unavailable_checks: dict[str, str] = Field(default_factory=dict)


class RunIn(BaseModel):
    submission_id: str
    checks: list[str] = Field(default_factory=list)
    prereg_id: str | None = None
    options: dict[str, dict[str, Any]] = Field(default_factory=dict)


class RunOut(BaseModel):
    id: str
    submission_id: str
    prereg_id: str | None
    checks: list[str]
    status: str
    progress: float
    message: str
    report: dict[str, Any] | None
    error: str | None
    thresholds_declared_in_advance: bool | None
    started_at: str
    finished_at: str | None
