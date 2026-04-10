"""
data/db/models.py — SQLAlchemy ORM models for ARGUS.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, Text, func,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import JSON
import enum
import os

# ── Dialect-agnostic type helpers ────────────────────────────────────────────
# SQLite (local dev) doesn't support ARRAY or UUID natively.
_is_sqlite = os.getenv("POSTGRES_URL", "").startswith("postgresql") is False or True

def _array_type(item_type):
    """Returns ARRAY for Postgres, JSON for SQLite."""
    try:
        from data.db.session import DATABASE_URL
        if DATABASE_URL.startswith("sqlite"):
            return JSON
        return PG_ARRAY(item_type)
    except Exception:
        return JSON

def _uuid_type():
    """Returns PostgreSQL UUID(as_uuid=True) or String(36) for SQLite."""
    try:
        from data.db.session import DATABASE_URL
        if DATABASE_URL.startswith("sqlite"):
            return String(36)
        return PG_UUID(as_uuid=True)
    except Exception:
        return String(36)



class Base(DeclarativeBase):
    pass


class ExchangeEnum(str, enum.Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    MCX = "MCX"


class SideEnum(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class EntityTypeEnum(str, enum.Enum):
    individual = "individual"
    company = "company"
    huf = "huf"


class AlertStatusEnum(str, enum.Enum):
    open = "open"
    investigating = "investigating"
    closed = "closed"
    false_positive = "false_positive"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(_uuid_type(), primary_key=True, default=uuid.uuid4)
    account_id = Column(String, nullable=False, index=True)
    scrip = Column(String, nullable=False, index=True)
    exchange = Column(Enum(ExchangeEnum), nullable=False, default=ExchangeEnum.NSE)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    side = Column(Enum(SideEnum), nullable=False)
    order_type = Column(String, nullable=True)
    is_manipulated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Entity(Base):
    __tablename__ = "entities"

    id = Column(_uuid_type(), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(Enum(EntityTypeEnum), nullable=False, default=EntityTypeEnum.individual)
    mca_cin = Column(String, nullable=True)
    related_entity_ids = Column(_array_type(String), nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    accounts = relationship("Account", back_populates="entity")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String, primary_key=True)
    broker = Column(String, nullable=True)
    pan_hash = Column(String, unique=True, nullable=True)
    entity_id = Column(_uuid_type(), ForeignKey("entities.id"), nullable=True)
    behavioral_dna = Column(_array_type(Float), nullable=True)
    dna_updated_at = Column(DateTime(timezone=True), nullable=True)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String, nullable=True)
    entity = relationship("Entity", back_populates="accounts")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(_uuid_type(), primary_key=True, default=uuid.uuid4)
    scrip = Column(String, nullable=False)
    exchange = Column(String, nullable=False, default="NSE")
    detected_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    impossibility_score = Column(Float, nullable=False)
    scheme_type = Column(String, nullable=False)
    accounts_involved = Column(_array_type(String), nullable=False, default=list)
    gnn_score = Column(Float, nullable=False, default=0.0)
    dna_score = Column(Float, nullable=False, default=0.0)
    cross_market_score = Column(Float, nullable=False, default=0.0)
    zero_day_score = Column(Float, nullable=False, default=0.0)
    status = Column(Enum(AlertStatusEnum), nullable=False, default=AlertStatusEnum.open)
    case_file_path = Column(String, nullable=True)
    assigned_to = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sebi_cases = relationship("SEBICase", back_populates="alert")


class SEBICase(Base):
    __tablename__ = "sebi_cases"

    id = Column(_uuid_type(), primary_key=True, default=uuid.uuid4)
    alert_id = Column(_uuid_type(), ForeignKey("alerts.id"), nullable=False)
    case_number = Column(String, unique=True, nullable=False)
    entity_names = Column(_array_type(String), nullable=False, default=list)
    scrip = Column(String, nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    estimated_gain = Column(Float, nullable=True)
    evidence_json = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="draft")
    pdf_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    alert = relationship("Alert", back_populates="sebi_cases")


class KnownFraudster(Base):
    __tablename__ = "known_fraudsters"

    id = Column(_uuid_type(), primary_key=True, default=uuid.uuid4)
    entity_name = Column(String, nullable=False)
    sebi_order_ref = Column(String, nullable=False)
    scheme_type = Column(String, nullable=False)
    behavioral_dna = Column(_array_type(Float), nullable=True)
    scrips_involved = Column(_array_type(String), nullable=False, default=list)
    conviction_date = Column(Date, nullable=False)
    source_url = Column(String, nullable=True)
