"""
Alembic environment configuration for ARGUS database migrations.
Reads POSTGRES_URL from environment; falls back to SQLite for local dev.
"""
from logging.config import fileConfig
import logging
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

target_metadata = Base.metadata

# Resolve active URL: prefer POSTGRES_URL from environment, else SQLite fallback
_pg_url = os.environ.get("POSTGRES_URL", "")
if _pg_url:
    ACTIVE_URL = _pg_url
    _IS_POSTGRES = True
else:
    _db_path = os.path.join(os.path.dirname(__file__), "..", "argus_dev.db")
    ACTIVE_URL = f"sqlite:///{os.path.abspath(_db_path)}"
    _IS_POSTGRES = False

# Log active URL with masked password (show only up to @)
_masked = ACTIVE_URL
if "@" in ACTIVE_URL:
    _scheme_user_pass, _rest = ACTIVE_URL.split("@", 1)
    _masked = f"{_scheme_user_pass.rsplit(':', 1)[0]}:***@{_rest}"
logger.info("Alembic migration URL: %s", _masked)


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    context.configure(
        url=ACTIVE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,          # SQLite-safe ALTER TABLE via batch
        include_schemas=_IS_POSTGRES,  # PostgreSQL multi-schema support
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        {"sqlalchemy.url": ACTIVE_URL},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            include_schemas=_IS_POSTGRES,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
