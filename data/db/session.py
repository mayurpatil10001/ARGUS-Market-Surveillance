"""
data/db/session.py — SQLAlchemy session management.
Falls back to SQLite for local development when PostgreSQL is unavailable.
"""
from __future__ import annotations

import logging
import os
import socket
import sys

# Windows: ensure stdout can handle non-ASCII without crashing
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from sqlalchemy import create_engine, text as sa_text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _pg_unavailable() -> bool:
    """Quick check: is the configured Postgres actually reachable?"""
    try:
        with socket.create_connection(("localhost", 5432), timeout=1):
            return False
    except OSError:
        return True


_raw_url: str = os.getenv("POSTGRES_URL", "")
_USE_SQLITE = not _raw_url or _pg_unavailable()

if _USE_SQLITE:
    _db_path = os.path.join(os.path.dirname(__file__), "..", "..", "argus_dev.db")
    DATABASE_URL = f"sqlite:///{os.path.abspath(_db_path)}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    print(f"[ARGUS] [DEV] Using SQLite dev DB: {DATABASE_URL}")
else:
    DATABASE_URL = _raw_url
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        connect_args={"connect_timeout": 10},
        echo=False,
    )
    print(f"[ARGUS] [OK] Using PostgreSQL: {DATABASE_URL}")

# Log active backend at startup
logger.info("ARGUS DB backend: %s", "postgresql" if not _USE_SQLITE else "sqlite")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def is_postgres() -> bool:
    """Returns True when the active engine is PostgreSQL."""
    return not _USE_SQLITE


def get_pg_engine():
    """
    Returns the PostgreSQL engine.
    Raises RuntimeError if POSTGRES_URL is not set or PostgreSQL is unreachable.
    Used by production health checks and migration scripts.
    """
    if not _raw_url:
        raise RuntimeError("POSTGRES_URL environment variable is not set.")
    if _USE_SQLITE:
        raise RuntimeError(
            f"PostgreSQL is unreachable at the configured URL: {_raw_url}"
        )
    return engine


def get_db() -> Session:
    """FastAPI dependency: yields a DB session and closes it after use."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """Direct session factory for non-FastAPI use."""
    return SessionLocal()
