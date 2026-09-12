"""Database session handling. SQLite for development, PostgreSQL-ready.

`HEMOSIGHT_AUDIT_DB` overrides the URL, so moving to PostgreSQL is a connection string
and nothing else: no SQLite-specific column types, no raw SQL, and JSON payloads use
SQLAlchemy's dialect-neutral JSON type.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.types import TypeDecorator

from hemosight.audit.jsonsafe import to_jsonable

DATA_DIR = Path(os.environ.get(
    "HEMOSIGHT_AUDIT_DATA",
    Path(__file__).resolve().parents[2] / "data" / "interim" / "phase6" / "service"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("HEMOSIGHT_AUDIT_DB",
                              f"sqlite:///{(DATA_DIR / 'audit.db').as_posix()}")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False,
                            future=True)


class SafeJSON(TypeDecorator):
    """A JSON column that coerces NumPy scalars, arrays, NaN and Inf on the way in.

    This is the boundary, and it is a COLUMN TYPE rather than a helper somebody has to
    remember to call. Every JSON column in models.py uses it, so a field added later is
    covered without anyone thinking about it - which is the failure mode that produced
    the original 500: `AuditInput.summary()` grew two numpy.bool_ fields and nothing
    between there and the database noticed.
    """

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return to_jsonable(value)


class Base(DeclarativeBase):
    pass


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401 - registers the tables
    Base.metadata.create_all(engine)
