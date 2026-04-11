"""
api/routers/mrfe.py — Market Reaction Fingerprint Engine API endpoints.
Prefix: /mrfe  — all endpoints require JWT authentication.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from api.auth import get_current_user
from api.schemas import MRFEAnalysisOut, MRFETextRequest

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".docx"}


def _get_engine():
    from models.mrfe.engine import MRFEEngine
    return MRFEEngine()


# ── Text analysis ──────────────────────────────────────────────────────────────

@router.post("/analyze/text")
async def analyze_text(
    body: MRFETextRequest,
    _user: dict = Depends(get_current_user),
):
    """
    Analyze free-form text for financial threats.
    Returns event_type, threat_score, affected_scrips, and recommended action.
    Optionally fetches 30-day historical price context for affected scrips.
    """
    engine = _get_engine()
    result = engine.analyze_text(body.text)

    if body.fetch_historical and result.get("affected_scrips"):
        try:
            historical = engine.fetch_historical_context(result["affected_scrips"])
            result["historical_context"] = historical
        except Exception as exc:
            logger.warning(f"MRFE historical fetch failed: {exc}")
            result["historical_context"] = {}
    else:
        result["historical_context"] = {}

    return result


# ── File analysis ──────────────────────────────────────────────────────────────

@router.post("/analyze/file")
async def analyze_file(
    file: UploadFile = File(...),
    fetch_historical: bool = Query(False),
    _user: dict = Depends(get_current_user),
):
    """
    Analyze an uploaded document (PDF, TXT, CSV, DOCX) for financial threats.
    Max file size: 10 MB. Returns the same analysis dict as /analyze/text.
    """
    # Validate extension
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {ext!r}. "
                f"Allowed: {sorted(_ALLOWED_EXTENSIONS)}"
            ),
        )

    # Read and validate size
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(file_bytes) // 1024} KB). Max: 10 MB.",
        )

    engine = _get_engine()
    result = engine.analyze_document(file_bytes, filename)

    if fetch_historical and result.get("affected_scrips"):
        try:
            historical = engine.fetch_historical_context(result["affected_scrips"])
            result["historical_context"] = historical
        except Exception as exc:
            logger.warning(f"MRFE historical fetch (file) failed: {exc}")
            result["historical_context"] = {}
    else:
        result["historical_context"] = {}

    return result


# ── Status ─────────────────────────────────────────────────────────────────────

@router.get("/status")
async def mrfe_status():
    """
    Returns MRFE engine status and model availability.
    No authentication required.
    """
    # Check which sub-models are importable
    misinfo_ok = False
    social_ok = False
    threat_ok = False

    try:
        from models.misinfo.detector import _get_pipeline
        _get_pipeline()
        misinfo_ok = True
    except Exception:
        pass

    try:
        from data.ingest.social_signal_fetcher import _score_manipulation
        social_ok = True
    except Exception:
        pass

    try:
        from data.ingest.generic_threat_adapter import normalize
        threat_ok = True
    except Exception:
        pass

    return {
        "engine": "MRFE",
        "version": "1.0",
        "description": (
            "Market Reaction Fingerprint Engine — analyzes text, PDF, and document "
            "inputs for financial threat classification and market impact scoring."
        ),
        "models_loaded": {
            "misinfo": misinfo_ok,
            "social_signal": social_ok,
            "threat_adapter": threat_ok,
        },
        "supported_formats": ["pdf", "txt", "csv", "docx"],
        "score_note": (
            "All scores are heuristic estimates from ARGUS detection modules. "
            "Not validated accuracy percentages."
        ),
    }
