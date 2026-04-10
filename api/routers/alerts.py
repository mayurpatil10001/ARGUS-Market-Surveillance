"""
api/routers/alerts.py — Alert CRUD endpoints with SSE live stream.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.schemas import AlertOut, AlertStatusUpdate, AlertAssign
from data.db.crud import (
    get_alert, get_alerts, update_alert_status, assign_alert, count_alerts_today
)
from data.db.session import get_db

router = APIRouter()


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status"),
    min_score: Optional[float] = Query(None, ge=0.0, le=10.0),
    scrip: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Paginated, filterable list of alerts. Requires authentication."""
    alerts = get_alerts(
        db,
        status=status,
        min_score=min_score,
        scrip=scrip,
        from_dt=from_date,
        to_dt=to_date,
        limit=limit,
        offset=offset,
    )
    return [AlertOut.model_validate(a) for a in alerts]


@router.get("/live")
async def live_alerts(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    SSE stream of new alerts. Polls DB every 5 seconds for alerts created after connection.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        seen_ids: set[str] = set()
        start_time = datetime.utcnow()

        # Send initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': start_time.isoformat()})}\n\n"

        while True:
            await asyncio.sleep(5)
            alerts = get_alerts(db, from_dt=start_time, limit=20)
            for alert in alerts:
                alert_id = str(alert.id)
                if alert_id not in seen_ids:
                    seen_ids.add(alert_id)
                    payload = AlertOut.model_validate(alert).model_dump()
                    payload["id"] = str(payload["id"])
                    payload["detected_at"] = str(payload["detected_at"])
                    payload["created_at"] = str(payload.get("created_at", ""))
                    yield f"data: {json.dumps({'type': 'alert', 'data': payload})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{alert_id}", response_model=AlertOut)
async def get_single_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Retrieves a single alert with full evidence."""
    alert = get_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut.model_validate(alert)


@router.post("/{alert_id}/status", response_model=AlertOut)
async def update_status(
    alert_id: uuid.UUID,
    body: AlertStatusUpdate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Updates alert status: open / investigating / closed / false_positive."""
    alert = update_alert_status(db, alert_id, body.status)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut.model_validate(alert)


@router.post("/{alert_id}/assign", response_model=AlertOut)
async def assign_to_analyst(
    alert_id: uuid.UUID,
    body: AlertAssign,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Assigns alert to an analyst by name."""
    alert = assign_alert(db, alert_id, body.analyst)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut.model_validate(alert)
