"""
data/db/session.py — SQLAlchemy session management.
Falls back to SQLite for local development when PostgreSQL is unavailable.
"""
from __future__ import annotations

import os
import socket
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

load_dotenv()


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
    print(f"[ARGUS] ⚠️  Using SQLite dev DB: {DATABASE_URL}")
else:
    DATABASE_URL = _raw_url
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
    )
    print(f"[ARGUS] ✅ Using PostgreSQL: {DATABASE_URL}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
