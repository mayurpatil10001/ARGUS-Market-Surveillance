"""
data/db/models.py — SQLAlchemy ORM models for SENTINEL.
SENTINEL: Scalable ENTity Intelligence for NEtwork-Level threat detection
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


# ── Platform enum replaces ExchangeEnum for digital threat context ────────────
class PlatformEnum(str, enum.Enum):
    twitter = "twitter"
    reddit = "reddit"
    telegram = "telegram"
    web = "web"
    email = "email"
    other = "other"


# Keep ExchangeEnum as alias for backward compatibility with Trade model
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


class ThreatTypeEnum(str, enum.Enum):
    market_manipulation = "market_manipulation"
    social_media_threat = "social_media_threat"
    misinformation = "misinformation"
    phishing = "phishing"
    generic_digital_threat = "generic_digital_threat"


# ── Threat category enum for PS-402 classification ───────────────────────────
class ThreatCategoryEnum(str, enum.Enum):
    coordinated_attack = "coordinated_attack"
    malicious_content = "malicious_content"
    phishing = "phishing"
    misinformation = "misinformation"
    platform_abuse = "platform_abuse"
    novel_threat = "novel_threat"


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
    # PS-402: platform replaces exchange; entities_involved replaces accounts_involved
    # threat_category replaces scheme_type for digital threat classification
    scrip = Column(String, nullable=False)           # entity/target identifier
    platform = Column(String, nullable=False, default="web")  # twitter/reddit/web/telegram/email
    # Keep exchange as legacy alias for backward compatibility
    exchange = Column(String, nullable=False, default="web")
    detected_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    impossibility_score = Column(Float, nullable=False)
    # threat_category is the new primary classification field (PS-402)
    threat_category = Column(String, nullable=False, default="novel_threat")
    # scheme_type kept as legacy alias — same column semantics
    scheme_type = Column(String, nullable=False, default="novel_threat")
    # entities_involved replaces accounts_involved (broader digital context)
    entities_involved = Column(_array_type(String), nullable=False, default=list)
    # Keep accounts_involved as legacy alias
    accounts_involved = Column(_array_type(String), nullable=False, default=list)
    # Renamed scoring fields to PS-402 terminology
    gnn_score = Column(Float, nullable=False, default=0.0)         # coordination_score
    dna_score = Column(Float, nullable=False, default=0.0)         # behavior_score
    cross_market_score = Column(Float, nullable=False, default=0.0)  # cross_platform_score
    zero_day_score = Column(Float, nullable=False, default=0.0)    # novelty_score
    social_signal_score = Column(Float, nullable=False, default=0.0)
    misinfo_score = Column(Float, nullable=False, default=0.0)
    threat_type = Column(String, nullable=False, default="generic_digital_threat")
    status = Column(Enum(AlertStatusEnum), nullable=False, default=AlertStatusEnum.open)
    case_file_path = Column(String, nullable=True)
    assigned_to = Column(String, nullable=True)
    # content_sample stores flagged post/URL/message snippet (PS-402 requirement)
    content_sample = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # ── Mitigation fields ────────────────────────────────────────────────────
    recommended_action = Column(String, nullable=True)
    mitigation_status = Column(String, nullable=False, default="pending")
    mitigation_applied_at = Column(DateTime(timezone=True), nullable=True)
    mitigation_applied_by = Column(String, nullable=True)
    auto_mitigated = Column(Boolean, default=False, nullable=False)
    mitigation_notes = Column(String, nullable=True)
    severity = Column(String, nullable=False, default="medium")
    escalated_to_sebi = Column(Boolean, default=False, nullable=False)
    escalation_timestamp = Column(DateTime(timezone=True), nullable=True)
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


# ── PS-402: Market Signal ORM ─────────────────────────────────────────────────

class MarketSignalTypeEnum(str, enum.Enum):
    url_threat       = "url_threat"
    social_post      = "social_post"
    news_headline    = "news_headline"
    whatsapp_forward = "whatsapp_forward"


class MarketSignal(Base):
    __tablename__ = "market_signals"

    id                  = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_type         = Column(String(32), nullable=False)         # MarketSignalTypeEnum value
    platform            = Column(String(64), nullable=False)         # twitter, reddit, telegram, web, whatsapp
    source_url          = Column(String(2048), nullable=True)        # original URL if available
    raw_text            = Column(Text, nullable=True)                # post body / headline
    scrips_mentioned    = Column(JSON, nullable=False, default=list) # ["XYZLTD", "ABCBANK"]
    entity_id           = Column(String(128), nullable=True)         # account/user if known
    misinfo_score       = Column(Float, default=0.0)
    social_signal_score = Column(Float, default=0.0)
    threat_score        = Column(Float, default=0.0)
    is_market_moving    = Column(Boolean, default=False)             # True if threat_score >= 0.6
    alert_id            = Column(String(36), ForeignKey("alerts.id"), nullable=True)
    ingested_at         = Column(DateTime(timezone=True), server_default=func.now())
    source_meta         = Column(JSON, nullable=True)                # likes, shares, velocity, etc.
