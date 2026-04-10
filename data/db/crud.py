"""
data/db/crud.py — CRUD operations for all ARGUS models.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from data.db.models import (
    Trade, Account, Entity, Alert, SEBICase, KnownFraudster,
    AlertStatusEnum,
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
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
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
    if from_dt:
        q = q.filter(Alert.detected_at >= from_dt)
    if to_dt:
        q = q.filter(Alert.detected_at <= to_dt)
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


def get_weekly_stats(session: Session) -> dict:
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
        "resolved": resolved,
        "false_positives": fp,
        "false_positive_rate_pct": fp_rate,
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
