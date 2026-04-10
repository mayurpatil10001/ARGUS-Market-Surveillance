"""Initial migration — creates all ARGUS tables.

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    exchange_enum = sa.Enum("NSE", "BSE", "NFO", "MCX", name="exchangeenum")
    side_enum = sa.Enum("BUY", "SELL", name="sideenum")
    entity_type_enum = sa.Enum("individual", "company", "huf", name="entitytypeenum")
    alert_status_enum = sa.Enum("open", "investigating", "closed", "false_positive", name="alertstatusenum")

    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", entity_type_enum, nullable=False, default="individual"),
        sa.Column("mca_cin", sa.String(), nullable=True),
        sa.Column("related_entity_ids", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("broker", sa.String(), nullable=True),
        sa.Column("pan_hash", sa.String(), nullable=True, unique=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("behavioral_dna", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("dna_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_flagged", sa.Boolean(), default=False),
        sa.Column("flag_reason", sa.String(), nullable=True),
    )

    op.create_table(
        "trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False, index=True),
        sa.Column("scrip", sa.String(), nullable=False, index=True),
        sa.Column("exchange", exchange_enum, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("side", side_enum, nullable=False),
        sa.Column("order_type", sa.String(), nullable=True),
        sa.Column("is_manipulated", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scrip", sa.String(), nullable=False),
        sa.Column("exchange", sa.String(), nullable=False, default="NSE"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("impossibility_score", sa.Float(), nullable=False),
        sa.Column("scheme_type", sa.String(), nullable=False),
        sa.Column("accounts_involved", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("gnn_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("dna_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("cross_market_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("zero_day_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("status", alert_status_enum, nullable=False, default="open"),
        sa.Column("case_file_path", sa.String(), nullable=True),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sebi_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id"), nullable=False),
        sa.Column("case_number", sa.String(), unique=True, nullable=False),
        sa.Column("entity_names", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("scrip", sa.String(), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("estimated_gain", sa.Float(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, default="draft"),
        sa.Column("pdf_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "known_fraudsters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_name", sa.String(), nullable=False),
        sa.Column("sebi_order_ref", sa.String(), nullable=False),
        sa.Column("scheme_type", sa.String(), nullable=False),
        sa.Column("behavioral_dna", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("scrips_involved", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("conviction_date", sa.Date(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("known_fraudsters")
    op.drop_table("sebi_cases")
    op.drop_table("alerts")
    op.drop_table("trades")
    op.drop_table("accounts")
    op.drop_table("entities")
    for enum_name in ("exchangeenum", "sideenum", "entitytypeenum", "alertstatusenum"):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
