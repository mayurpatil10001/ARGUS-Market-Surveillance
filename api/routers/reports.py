"""
api/routers/reports.py — PDF case generation, download, and weekly summary endpoints.
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.schemas import CaseGenerateRequest, CaseGenerateResponse, SEBICaseOut, WeeklySummaryOut
from data.db.crud import (
    create_sebi_case,
    get_alert,
    get_sebi_case_by_alert,
    get_weekly_stats,
    update_sebi_case_pdf,
)
from data.db.session import get_db

router = APIRouter()

REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "/tmp/argus_reports"))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/case/{alert_id}", response_model=CaseGenerateResponse)
async def generate_case(
    alert_id: uuid.UUID,
    body: CaseGenerateRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Generates a SEBI-style PDF case file for the given alert.
    Creates or updates SEBICase record. Returns download URL.
    """
    from reports.pdf_generator import generate_case_pdf

    alert = get_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check if case already exists
    existing_case = get_sebi_case_by_alert(db, alert_id)

    from_date = body.from_date or alert.detected_at.date() - timedelta(days=30)
    to_date = body.to_date or alert.detected_at.date()
    entity_names = body.entity_names or alert.accounts_involved[:5]

    if existing_case is None:
        case_number = f"ARGUS/{datetime.utcnow().year}/{str(alert_id)[:8].upper()}"
        case = create_sebi_case(
            db,
            alert_id=alert.id,
            case_number=case_number,
            entity_names=entity_names,
            scrip=alert.scrip,
            from_date=from_date,
            to_date=to_date,
            estimated_gain=body.estimated_gain,
            evidence_json={
                "gnn_score": alert.gnn_score,
                "dna_score": alert.dna_score,
                "cross_market_score": alert.cross_market_score,
                "zero_day_score": alert.zero_day_score,
                "scheme_type": alert.scheme_type,
                "accounts_involved": alert.accounts_involved,
                "notes": body.notes or "",
            },
            status="draft",
        )
    else:
        case = existing_case

    # Generate PDF
    pdf_filename = f"case_{str(case.id)}.pdf"
    pdf_path = str(REPORTS_DIR / pdf_filename)

    try:
        generate_case_pdf(alert, case, pdf_path)
        update_sebi_case_pdf(db, case.id, pdf_path)
        # Also update alert's case_file_path
        alert.case_file_path = pdf_path
        db.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    return CaseGenerateResponse(
        case_id=case.id,
        case_number=case.case_number,
        pdf_path=pdf_path,
        download_url=f"/reports/case/{alert_id}/download",
    )


@router.get("/case/{alert_id}/download")
async def download_case(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Streams the PDF case file for download."""
    case = get_sebi_case_by_alert(db, alert_id)
    if not case or not case.pdf_path:
        raise HTTPException(status_code=404, detail="Case PDF not found. Generate it first via POST /reports/case/{id}")

    if not os.path.exists(case.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        path=case.pdf_path,
        media_type="application/pdf",
        filename=f"ARGUS_Case_{case.case_number.replace('/', '-')}.pdf",
    )


@router.get("/summary/weekly", response_model=WeeklySummaryOut)
async def weekly_summary(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Returns weekly statistics: alerts, resolved, false positive rate, top scrips."""
    stats = get_weekly_stats(db)
    return WeeklySummaryOut(**stats)
