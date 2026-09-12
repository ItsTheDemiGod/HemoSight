"""ORM tables.

Four objects, and the relationship between two of them carries the discipline the tool
exists to encode: a PreRegistration has a declared_at, a Submission has an uploaded_at,
and a Run records whether the first preceded the second. That ordering is the only
thing distinguishing a threshold from an interpretation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, SafeJSON


def new_id() -> str:
    """Ids are generated eagerly, not at flush: the upload route needs the id to
    name a directory before the row is committed."""
    return uuid.uuid4().hex[:16]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PreRegistrationRow(Base):
    __tablename__ = "preregistrations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(300), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    thresholds: Mapped[dict] = mapped_column(SafeJSON, default=dict)
    checks_planned: Mapped[list] = mapped_column(SafeJSON, default=list)
    fingerprint: Mapped[str] = mapped_column(String(64), default="")
    declared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=utcnow)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    filename: Mapped[str] = mapped_column(String(300), default="")
    csv_path: Mapped[str] = mapped_column(Text, default="")
    image_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    n_rows: Mapped[int] = mapped_column(Integer, default=0)
    n_subjects: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict] = mapped_column(SafeJSON, default=dict)
    column_map: Mapped[dict] = mapped_column(SafeJSON, default=dict)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=utcnow)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"))
    prereg_id: Mapped[str | None] = mapped_column(
        ForeignKey("preregistrations.id"), nullable=True)
    checks: Mapped[list] = mapped_column(SafeJSON, default=list)
    options: Mapped[dict] = mapped_column(SafeJSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[str] = mapped_column(Text, default="queued")
    report: Mapped[dict | None] = mapped_column(SafeJSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Recorded at run time, not derived later: whether the thresholds this run was
    # judged against were declared before the results were uploaded.
    thresholds_declared_in_advance: Mapped[bool | None] = mapped_column(
        Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                         nullable=True)
