"""
api/routers/ps402.py — Unified PS-402 API router for digital threat signal ingestion.
Exposes endpoints for URL ingestion, social post ingestion, batch ingestion,
signal listing, and a 7-day summary dashboard feed.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.auth import get_current_user
from data.db.session import get_db
from data.db.models import MarketSignal
from data.ingest.url_social_ingestor import ingest_url, ingest_social_post, ingest_batch

router = APIRouter()


# ── Pydantic request models ───────────────────────────────────────────────────

class URLRequest(BaseModel):
    url: str
    platform: str = "web"
    entity_id: Optional[str] = None
    source_meta: Optional[dict] = None


class SocialPostRequest(BaseModel):
    text: str
    platform: str
    source_url: Optional[str] = None
    entity_id: Optional[str] = None
    source_meta: Optional[dict] = None


class BatchRecord(BaseModel):
    type: str  # "url" | "social"
    url: Optional[str] = None
    text: Optional[str] = None
    platform: str = "web"
    source_url: Optional[str] = None
    entity_id: Optional[str] = None
    source_meta: Optional[dict] = None


class BatchRequest(BaseModel):
    records: list[BatchRecord]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/ingest/url", summary="Ingest a URL for phishing/threat scoring")
def ingest_url_endpoint(
    body: URLRequest,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    return ingest_url(
        url=body.url,
        platform=body.platform,
        entity_id=body.entity_id,
        source_meta=body.source_meta,
        db=db,
    )


@router.post("/ingest/social", summary="Ingest a social media post for manipulation scoring")
def ingest_social_endpoint(
    body: SocialPostRequest,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    return ingest_social_post(
        text=body.text,
        platform=body.platform,
        source_url=body.source_url,
        entity_id=body.entity_id,
        source_meta=body.source_meta,
        db=db,
    )


@router.post("/ingest/batch", summary="Batch ingest URLs and social posts")
def ingest_batch_endpoint(
    body: BatchRequest,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    return {
        "results": ingest_batch([r.model_dump() for r in body.records], db=db),
        "count": len(body.records),
    }


@router.get("/signals", summary="List market signals with optional filters")
def list_signals(
    scrip: Optional[str] = Query(None, description="Filter by NSE scrip symbol"),
    platform: Optional[str] = Query(None, description="Filter by platform (twitter, reddit, …)"),
    is_market_moving: Optional[bool] = Query(None, description="Filter market-moving signals only"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    from data.db.crud import get_market_signals
    signals = get_market_signals(
        db,
        scrip=scrip,
        platform=platform,
        is_market_moving=is_market_moving,
        limit=limit,
        offset=offset,
    )
    return {
        "signals": [
            {
                "id": s.id,
                "signal_type": s.signal_type,
                "platform": s.platform,
                "source_url": s.source_url,
                "raw_text_preview": (s.raw_text or "")[:120],
                "scrips_mentioned": s.scrips_mentioned,
                "threat_score": s.threat_score,
                "misinfo_score": s.misinfo_score,
                "social_signal_score": s.social_signal_score,
                "is_market_moving": s.is_market_moving,
                "alert_id": s.alert_id,
                "ingested_at": str(s.ingested_at),
            }
            for s in signals
        ],
        "count": len(signals),
    }


@router.get("/summary", summary="PS-402 7-day threat signal summary")
def ps402_summary(
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    cutoff = datetime.utcnow() - timedelta(days=7)
    signals = db.query(MarketSignal).filter(MarketSignal.ingested_at >= cutoff).all()

    by_type: dict[str, int] = {}
    for s in signals:
        by_type[s.signal_type] = by_type.get(s.signal_type, 0) + 1

    entity_counts: dict[str, int] = {}
    for s in signals:
        if s.entity_id:
            entity_counts[s.entity_id] = entity_counts.get(s.entity_id, 0) + 1
    top_entities = sorted(entity_counts.items(), key=lambda x: -x[1])[:5]

    return {
        "period_days": 7,
        "total_signals": len(signals),
        "market_moving": sum(1 for s in signals if s.is_market_moving),
        "by_type": by_type,
        "top_entities": [{"entity_id": e, "count": c} for e, c in top_entities],
        "avg_threat_score": round(
            sum(s.threat_score for s in signals) / len(signals), 4
        ) if signals else 0.0,
    }
