"""Add market_signals table (PS-402 digital threat ingestion layer).

Revision ID: 002_market_signals
Revises: 001_initial
Create Date: 2024-06-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

revision = "002_market_signals"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def upgrade() -> None:
    if _is_sqlite():
        # SQLite: use String(36) for PK and JSON for arrays
        op.create_table(
            "market_signals",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("signal_type", sa.String(32), nullable=False),
            sa.Column("platform", sa.String(64), nullable=False),
            sa.Column("source_url", sa.String(2048), nullable=True),
            sa.Column("raw_text", sa.Text(), nullable=True),
            sa.Column("scrips_mentioned", sa.JSON(), nullable=False),
            sa.Column("entity_id", sa.String(128), nullable=True),
            sa.Column("misinfo_score", sa.Float(), nullable=True, default=0.0),
            sa.Column("social_signal_score", sa.Float(), nullable=True, default=0.0),
            sa.Column("threat_score", sa.Float(), nullable=True, default=0.0),
            sa.Column("is_market_moving", sa.Boolean(), nullable=True, default=False),
            sa.Column(
                "alert_id",
                sa.String(36),
                sa.ForeignKey("alerts.id"),
                nullable=True,
            ),
            sa.Column(
                "ingested_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column("source_meta", sa.JSON(), nullable=True),
        )
    else:
        # PostgreSQL: use UUID and JSON (JSONB not required for portability)
        from sqlalchemy.dialects import postgresql

        op.create_table(
            "market_signals",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=False),
                primary_key=True,
            ),
            sa.Column("signal_type", sa.String(32), nullable=False),
            sa.Column("platform", sa.String(64), nullable=False),
            sa.Column("source_url", sa.String(2048), nullable=True),
            sa.Column("raw_text", sa.Text(), nullable=True),
            sa.Column("scrips_mentioned", sa.JSON(), nullable=False),
            sa.Column("entity_id", sa.String(128), nullable=True),
            sa.Column("misinfo_score", sa.Float(), nullable=True, default=0.0),
            sa.Column("social_signal_score", sa.Float(), nullable=True, default=0.0),
            sa.Column("threat_score", sa.Float(), nullable=True, default=0.0),
            sa.Column("is_market_moving", sa.Boolean(), nullable=True, default=False),
            sa.Column(
                "alert_id",
                postgresql.UUID(as_uuid=False),
                sa.ForeignKey("alerts.id"),
                nullable=True,
            ),
            sa.Column(
                "ingested_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column("source_meta", sa.JSON(), nullable=True),
        )

    # Indexes useful for the /ps402/signals query patterns
    op.create_index(
        "ix_market_signals_platform",
        "market_signals",
        ["platform"],
    )
    op.create_index(
        "ix_market_signals_is_market_moving",
        "market_signals",
        ["is_market_moving"],
    )
    op.create_index(
        "ix_market_signals_ingested_at",
        "market_signals",
        ["ingested_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_market_signals_ingested_at", table_name="market_signals")
    op.drop_index("ix_market_signals_is_market_moving", table_name="market_signals")
    op.drop_index("ix_market_signals_platform", table_name="market_signals")
    op.drop_table("market_signals")
