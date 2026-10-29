"""Database engine and session handling."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    # SQLite's default thread check fights FastAPI's threadpool.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
    echo=False,
)

if _is_sqlite:

    @event.listens_for(Engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - setup
        """Enforce foreign keys and use WAL so reads don't block writes.

        SQLite ignores `ondelete` rules unless foreign keys are switched on
        per connection, which would silently leave orphaned rows behind.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def create_all() -> None:
    """Create any missing tables.

    Fine for local development. Production uses Alembic — see the deployment
    notes in BUILD_PLAN.md.
    """
    Base.metadata.create_all(bind=engine)
    # Additive local-development upgrade for databases created before custom
    # website source files were introduced. Production deployments should run
    # the equivalent Alembic migration before releasing the new API.
    if _is_sqlite:
        columns = {column["name"] for column in inspect(engine).get_columns("projects")}
        with engine.begin() as connection:
            for name in ("draft_files", "published_files"):
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE projects ADD COLUMN {name} JSON"))


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """A session with commit-on-success, rollback-on-error. For workers and tests."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
