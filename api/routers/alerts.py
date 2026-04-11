"""
api/routers/alerts.py — Alert CRUD + Mitigation endpoints with SSE live stream.
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

from api.auth import get_current_user, get_current_user_sse
from api.schemas import (
    AlertOut, AlertStatusUpdate, AlertAssign,
    MitigationApplyRequest, MitigationDismissRequest,
    MitigationEscalateRequest, MitigationSummaryOut,
    SimulationRequest, SimulationResultOut,
)
from data.db.crud import (
    get_alert, get_alerts, update_alert_status, assign_alert, count_alerts_today,
    apply_mitigation, dismiss_mitigation, escalate_alert,
    get_alerts_pending_mitigation, get_mitigation_stats,
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
    severity: Optional[str] = Query(None, description="low/medium/high/critical"),
    mitigation_status: Optional[str] = Query(None, description="pending/applied/dismissed/escalated"),
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
        severity=severity,
        mitigation_status=mitigation_status,
        limit=limit,
        offset=offset,
    )
    return [AlertOut.model_validate(a) for a in alerts]


@router.get("/live")
async def live_alerts(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_sse),
):
    """SSE stream of new alerts. Polls DB every 5 seconds."""
    async def event_generator() -> AsyncGenerator[str, None]:
        seen_ids: set[str] = set()
        start_time = datetime.utcnow()
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
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Mitigation summary must be declared BEFORE /{alert_id} to avoid routing conflict ──

@router.get("/mitigation/summary", response_model=MitigationSummaryOut)
async def mitigation_summary(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Aggregated mitigation statistics for the dashboard."""
    stats = get_mitigation_stats(db)
    return MitigationSummaryOut(**stats)


@router.get("/mitigation/pending", response_model=list[AlertOut])
async def mitigation_pending(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """List all alerts with mitigation_status=pending."""
    alerts = get_alerts_pending_mitigation(db, severity=severity, limit=limit)
    return [AlertOut.model_validate(a) for a in alerts]


@router.get("/{alert_id}", response_model=AlertOut)
async def get_single_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Retrieves a single alert with full evidence and mitigation state."""
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


@router.post("/{alert_id}/mitigate", response_model=AlertOut)
async def mitigate_alert(
    alert_id: uuid.UUID,
    body: MitigationApplyRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Apply a mitigation action to the alert."""
    alert = apply_mitigation(db, alert_id, body.action, body.applied_by, body.notes)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut.model_validate(alert)


@router.post("/{alert_id}/dismiss-mitigation", response_model=AlertOut)
async def dismiss_alert_mitigation(
    alert_id: uuid.UUID,
    body: MitigationDismissRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Dismiss the recommended mitigation for an alert."""
    alert = dismiss_mitigation(db, alert_id, body.dismissed_by, body.reason)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut.model_validate(alert)


@router.post("/{alert_id}/escalate", response_model=AlertOut)
async def escalate_to_sebi(
    alert_id: uuid.UUID,
    body: MitigationEscalateRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Escalate alert to SEBI enforcement."""
    alert = escalate_alert(db, alert_id, body.escalated_by)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut.model_validate(alert)


# ── Simulation endpoints ──────────────────────────────────────────────────────

@router.get("/simulate/scenarios")
async def list_simulation_scenarios():
    """
    Returns list of available simulation scenarios with descriptions.
    No authentication required.
    """
    from scoring.simulation_engine import SIMULATION_SCENARIOS
    return {
        "scenarios": [
            {"id": k, **v}
            for k, v in SIMULATION_SCENARIOS.items()
        ] + [
            {
                "id": "all",
                "name": "All Scenarios",
                "description": "Run all 5 scenarios in sequence.",
            }
        ],
    }


@router.post("/simulate")
async def run_simulation(
    body: SimulationRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Run a full ARGUS system simulation for the given scenario.
    Generates synthetic threats and passes them through the full detection pipeline.
    All generated data is labeled synthetic_data_used=True.
    """
    from scoring.simulation_engine import SimulationEngine
    try:
        result = SimulationEngine().run_full_simulation(db, scenario=body.scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}")
    return result
