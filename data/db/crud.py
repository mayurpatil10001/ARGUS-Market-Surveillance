"""
data/db/crud.py — CRUD operations for all SENTINEL models.
SENTINEL: Scalable ENTity Intelligence for NEtwork-Level threat detection
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from data.db.models import (
    Trade, Account, Entity, Alert, SEBICase, KnownFraudster,
    AlertStatusEnum, ThreatTypeEnum, MarketSignal,
)


# ─── Trade ────────────────────────────────────────────────────────────────────

def create_trade(session: Session, **kwargs) -> Trade:
    trade = Trade(**kwargs)
    session.add(trade)
    session.commit()
    session.refresh(trade)
    return trade


def bulk_create_trades(session: Session, trades: list[dict]) -> int:
    rows = [Trade(**t) for t in trades]
    session.add_all(rows)
    session.commit()
    return len(rows)


def get_trades(
    session: Session,
    scrip: Optional[str] = None,
    account_id: Optional[str] = None,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
    exchange: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0,
) -> list[Trade]:
    q = session.query(Trade)
    if scrip:
        q = q.filter(Trade.scrip == scrip)
    if account_id:
        q = q.filter(Trade.account_id == account_id)
    if from_dt:
        q = q.filter(Trade.timestamp >= from_dt)
    if to_dt:
        q = q.filter(Trade.timestamp <= to_dt)
    if exchange:
        q = q.filter(Trade.exchange == exchange)
    return q.order_by(Trade.timestamp).offset(offset).limit(limit).all()


def get_distinct_scrips(session: Session, from_dt: datetime, to_dt: datetime) -> list[str]:
    rows = (
        session.query(Trade.scrip)
        .filter(Trade.timestamp >= from_dt, Trade.timestamp <= to_dt)
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


# ─── Account ──────────────────────────────────────────────────────────────────

def get_or_create_account(session: Session, account_id: str, broker: str = "") -> Account:
    acc = session.query(Account).filter(Account.id == account_id).first()
    if acc is None:
        acc = Account(id=account_id, broker=broker)
        session.add(acc)
        session.commit()
        session.refresh(acc)
    return acc


def update_account_dna(
    session: Session, account_id: str, dna: list[float]
) -> Account:
    acc = get_or_create_account(session, account_id)
    acc.behavioral_dna = dna
    acc.dna_updated_at = datetime.utcnow()
    session.commit()
    session.refresh(acc)
    return acc


def flag_account(session: Session, account_id: str, reason: str) -> Account:
    acc = get_or_create_account(session, account_id)
    acc.is_flagged = True
    acc.flag_reason = reason
    session.commit()
    session.refresh(acc)
    return acc


def get_account(session: Session, account_id: str) -> Optional[Account]:
    return session.query(Account).filter(Account.id == account_id).first()


def search_accounts(
    session: Session,
    broker: Optional[str] = None,
    is_flagged: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Account]:
    q = session.query(Account)
    if broker:
        q = q.filter(Account.broker == broker)
    if is_flagged is not None:
        q = q.filter(Account.is_flagged == is_flagged)
    return q.offset(offset).limit(limit).all()


# ─── Alert ────────────────────────────────────────────────────────────────────

def create_alert(session: Session, **kwargs) -> Alert:
    # Sync PS-402 fields with legacy aliases
    if "threat_category" in kwargs and "scheme_type" not in kwargs:
        kwargs["scheme_type"] = kwargs["threat_category"]
    if "scheme_type" in kwargs and "threat_category" not in kwargs:
        kwargs["threat_category"] = kwargs["scheme_type"]
    if "platform" in kwargs and "exchange" not in kwargs:
        kwargs["exchange"] = kwargs["platform"]
    if "entities_involved" in kwargs and "accounts_involved" not in kwargs:
        kwargs["accounts_involved"] = kwargs["entities_involved"]
    if "accounts_involved" in kwargs and "entities_involved" not in kwargs:
        kwargs["entities_involved"] = kwargs["accounts_involved"]
    alert = Alert(**kwargs)
    if "id" not in kwargs or kwargs["id"] is None:
        alert.id = uuid.uuid4()
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


def get_alert(session: Session, alert_id: uuid.UUID) -> Optional[Alert]:
    return session.query(Alert).filter(Alert.id == alert_id).first()


def get_alerts(
    session: Session,
    status: Optional[str] = None,
    min_score: Optional[float] = None,
    scrip: Optional[str] = None,
    platform: Optional[str] = None,
    threat_category: Optional[str] = None,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
    threat_type: Optional[str] = None,
    severity: Optional[str] = None,
    mitigation_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Alert]:
    q = session.query(Alert)
    if status:
        q = q.filter(Alert.status == status)
    if min_score is not None:
        q = q.filter(Alert.impossibility_score >= min_score)
    if scrip:
        q = q.filter(Alert.scrip == scrip)
    if platform:
        q = q.filter(Alert.platform == platform)
    if threat_category:
        q = q.filter(Alert.threat_category == threat_category)
    if from_dt:
        q = q.filter(Alert.detected_at >= from_dt)
    if to_dt:
        q = q.filter(Alert.detected_at <= to_dt)
    if threat_type:
        q = q.filter(Alert.threat_type == threat_type)
    if severity:
        q = q.filter(Alert.severity == severity)
    if mitigation_status:
        q = q.filter(Alert.mitigation_status == mitigation_status)
    return q.order_by(desc(Alert.impossibility_score)).offset(offset).limit(limit).all()


def update_alert_status(
    session: Session, alert_id: uuid.UUID, status: str
) -> Optional[Alert]:
    alert = get_alert(session, alert_id)
    if alert:
        alert.status = status
        session.commit()
        session.refresh(alert)
    return alert


def assign_alert(
    session: Session, alert_id: uuid.UUID, analyst: str
) -> Optional[Alert]:
    alert = get_alert(session, alert_id)
    if alert:
        alert.assigned_to = analyst
        session.commit()
        session.refresh(alert)
    return alert


def count_alerts_today(session: Session) -> int:
    today = datetime.utcnow().date()
    start = datetime(today.year, today.month, today.day)
    return session.query(func.count(Alert.id)).filter(Alert.created_at >= start).scalar() or 0


# ─── Mitigation CRUD ──────────────────────────────────────────────────────────────────

def apply_mitigation(
    session: Session,
    alert_id,
    action: str,
    applied_by: str,
    notes: Optional[str] = None,
) -> Optional[Alert]:
    from scoring.mitigation_engine import get_mitigation_engine
    try:
        return get_mitigation_engine().apply(session, alert_id, action, applied_by, notes)
    except ValueError:
        return None


def dismiss_mitigation(
    session: Session,
    alert_id,
    dismissed_by: str,
    reason: str,
) -> Optional[Alert]:
    from scoring.mitigation_engine import get_mitigation_engine
    try:
        return get_mitigation_engine().dismiss(session, alert_id, dismissed_by, reason)
    except ValueError:
        return None


def escalate_alert(
    session: Session,
    alert_id,
    escalated_by: str,
) -> Optional[Alert]:
    from scoring.mitigation_engine import get_mitigation_engine
    try:
        return get_mitigation_engine().escalate(session, alert_id, escalated_by)
    except ValueError:
        return None


def get_alerts_pending_mitigation(
    session: Session,
    severity: Optional[str] = None,
    limit: int = 50,
) -> list[Alert]:
    q = session.query(Alert).filter(Alert.mitigation_status == "pending")
    if severity:
        q = q.filter(Alert.severity == severity)
    return q.order_by(desc(Alert.impossibility_score)).limit(limit).all()


def get_mitigation_stats(session: Session) -> dict:
    from scoring.mitigation_engine import get_mitigation_engine
    return get_mitigation_engine().get_mitigation_summary(session)


def get_weekly_stats(session: Session) -> dict:
    """
    Returns PS-402 weekly threat statistics:
    total_threats, by_category breakdown, top_platforms, mitigation_rate.
    """
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    total = session.query(func.count(Alert.id)).filter(Alert.created_at >= week_ago).scalar() or 0
    resolved = (
        session.query(func.count(Alert.id))
        .filter(Alert.created_at >= week_ago, Alert.status == "closed")
        .scalar()
        or 0
    )
    fp = (
        session.query(func.count(Alert.id))
        .filter(Alert.created_at >= week_ago, Alert.status == "false_positive")
        .scalar()
        or 0
    )
    fp_rate = round(fp / max(total, 1) * 100, 2)

    # PS-402: by_category breakdown
    category_rows = (
        session.query(Alert.threat_category, func.count(Alert.id).label("cnt"))
        .filter(Alert.created_at >= week_ago)
        .group_by(Alert.threat_category)
        .all()
    )
    # Fallback to scheme_type if threat_category column not yet populated
    if not category_rows:
        category_rows = (
            session.query(Alert.scheme_type, func.count(Alert.id).label("cnt"))
            .filter(Alert.created_at >= week_ago)
            .group_by(Alert.scheme_type)
            .all()
        )
    by_category = {row[0]: row[1] for row in category_rows if row[0]}

    # PS-402: top_platforms
    platform_rows = (
        session.query(Alert.platform, func.count(Alert.id).label("cnt"))
        .filter(Alert.created_at >= week_ago)
        .group_by(Alert.platform)
        .order_by(desc("cnt"))
        .limit(5)
        .all()
    )
    # Fallback to exchange if platform column not yet populated
    if not platform_rows:
        platform_rows = (
            session.query(Alert.exchange, func.count(Alert.id).label("cnt"))
            .filter(Alert.created_at >= week_ago)
            .group_by(Alert.exchange)
            .order_by(desc("cnt"))
            .limit(5)
            .all()
        )
    top_platforms = [{"platform": row[0], "count": row[1]} for row in platform_rows if row[0]]

    # PS-402: mitigation_rate
    mitigated = (
        session.query(func.count(Alert.id))
        .filter(Alert.created_at >= week_ago, Alert.mitigation_status == "applied")
        .scalar()
        or 0
    )
    mitigation_rate = round(mitigated / max(total, 1) * 100, 2)

    # Legacy top_scrips for backward compatibility
    top_scrips_rows = (
        session.query(Alert.scrip, func.count(Alert.id).label("cnt"))
        .filter(Alert.created_at >= week_ago)
        .group_by(Alert.scrip)
        .order_by(desc("cnt"))
        .limit(5)
        .all()
    )

    return {
        "total_alerts": total,
        "total_threats": total,
        "resolved": resolved,
        "false_positives": fp,
        "false_positive_rate_pct": fp_rate,
        "by_category": by_category,
        "top_platforms": top_platforms,
        "mitigation_rate": mitigation_rate,
        "top_flagged_scrips": [{"scrip": r[0], "count": r[1]} for r in top_scrips_rows],
    }


# ─── SEBICase ─────────────────────────────────────────────────────────────────

def create_sebi_case(session: Session, **kwargs) -> SEBICase:
    case = SEBICase(**kwargs)
    if "id" not in kwargs or kwargs["id"] is None:
        case.id = uuid.uuid4()
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def get_sebi_case_by_alert(session: Session, alert_id: uuid.UUID) -> Optional[SEBICase]:
    return session.query(SEBICase).filter(SEBICase.alert_id == alert_id).first()


def update_sebi_case_pdf(session: Session, case_id: uuid.UUID, pdf_path: str) -> Optional[SEBICase]:
    case = session.query(SEBICase).filter(SEBICase.id == case_id).first()
    if case:
        case.pdf_path = pdf_path
        session.commit()
        session.refresh(case)
    return case


# ─── KnownFraudster ───────────────────────────────────────────────────────────

def upsert_known_fraudster(session: Session, **kwargs) -> KnownFraudster:
    existing = (
        session.query(KnownFraudster)
        .filter(KnownFraudster.sebi_order_ref == kwargs["sebi_order_ref"])
        .first()
    )
    if existing:
        return existing
    kf = KnownFraudster(**kwargs)
    if "id" not in kwargs or kwargs["id"] is None:
        kf.id = uuid.uuid4()
    session.add(kf)
    session.commit()
    session.refresh(kf)
    return kf


def get_all_known_fraudsters(session: Session) -> list[KnownFraudster]:
    return session.query(KnownFraudster).all()


# ─── MarketSignal (PS-402) ────────────────────────────────────────────────────

def create_market_signal(
    db,
    *,
    signal_type: str,
    platform: str,
    scrips_mentioned: list,
    source_url: Optional[str] = None,
    raw_text: Optional[str] = None,
    entity_id: Optional[str] = None,
    misinfo_score: float = 0.0,
    social_signal_score: float = 0.0,
    threat_score: float = 0.0,
    source_meta: Optional[dict] = None,
) -> MarketSignal:
    is_market_moving = threat_score >= 0.6
    obj = MarketSignal(
        id=str(uuid.uuid4()),
        signal_type=signal_type,
        platform=platform,
        source_url=source_url,
        raw_text=raw_text,
        scrips_mentioned=scrips_mentioned or [],
        entity_id=entity_id,
        misinfo_score=misinfo_score,
        social_signal_score=social_signal_score,
        threat_score=threat_score,
        is_market_moving=is_market_moving,
        source_meta=source_meta or {},
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_market_signals(
    db,
    *,
    scrip: Optional[str] = None,
    platform: Optional[str] = None,
    is_market_moving: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[MarketSignal]:
    q = db.query(MarketSignal)
    if scrip:
        q = q.filter(MarketSignal.scrips_mentioned.contains([scrip]))
    if platform:
        q = q.filter(MarketSignal.platform == platform)
    if is_market_moving is not None:
        q = q.filter(MarketSignal.is_market_moving == is_market_moving)
    return q.order_by(MarketSignal.ingested_at.desc()).offset(offset).limit(limit).all()


def link_signal_to_alert(db, signal_id: str, alert_id: str) -> None:
    obj = db.query(MarketSignal).filter(MarketSignal.id == signal_id).first()
    if obj:
        obj.alert_id = alert_id
        db.commit()

