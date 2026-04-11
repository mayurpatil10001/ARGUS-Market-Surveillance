"""
api/routers/ps402.py — Unified PS-402 API router for digital threat signal ingestion.
Exposes endpoints for URL ingestion, social post ingestion, batch ingestion,
signal listing, and a 7-day summary dashboard feed.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from api.auth import get_current_user
from data.db.session import get_db
from data.db.models import MarketSignal
from data.ingest.url_social_ingestor import ingest_url, ingest_social_post, ingest_batch

logger = logging.getLogger(__name__)

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


# ── Document Threat Analyzer ──────────────────────────────────────────────────

def _extract_text_from_upload(filename: str, raw: bytes) -> str:
    """
    Extract plain text from an uploaded file.
    Supports: .pdf (via pdfplumber), .docx (via python-docx), .txt (direct).
    Returns empty string on failure — caller should handle gracefully.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

    if ext == "pdf":
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(pages).strip()
        except Exception as e:
            logger.warning("PDF extraction failed: %s", e)
            return ""

    if ext == "docx":
        try:
            import docx  # python-docx
            doc = docx.Document(io.BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            logger.warning("DOCX extraction failed: %s", e)
            return ""

    # Plain text / fallback
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return raw.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return ""


def _build_reasons(
    *,
    threat_score: float,
    misinfo_score: float,
    social_score: float,
    finbert_label: str,
    finbert_score: float,
    finbert_neg: float,
    scrips: list[str],
    phish_keywords_found: list[str],
    threat_type: str,
    is_malicious: bool,
) -> list[str]:
    """
    Generate a list of plain-English reasons explaining the verdict.
    Each item is one specific, factual reason — safe or unsafe.
    """
    reasons: list[str] = []

    # ── FinBERT sentiment ──────────────────────────────────────────────────────
    if finbert_label == "negative" and finbert_neg >= 0.55:
        reasons.append(
            f"FinBERT sentiment is NEGATIVE ({finbert_neg*100:.0f}% confidence) — "
            "language typically associated with financial distress, fear-mongering or manipulation."
        )
    elif finbert_label == "positive" and finbert_score >= 0.70:
        reasons.append(
            f"FinBERT sentiment is POSITIVE ({finbert_score*100:.0f}% confidence) — "
            "language consistent with legitimate earnings/growth reporting."
        )
    elif finbert_label == "neutral":
        reasons.append(
            f"FinBERT sentiment is NEUTRAL ({finbert_score*100:.0f}% confidence) — "
            "factual, balanced financial language detected."
        )

    # ── Misinformation score ───────────────────────────────────────────────────
    if misinfo_score >= 0.75:
        reasons.append(
            f"High misinformation score ({misinfo_score*100:.0f}%) — document contains language "
            "strongly associated with fake financial news, unverified insider claims, or pump narratives."
        )
    elif misinfo_score >= 0.50:
        reasons.append(
            f"Moderate misinformation score ({misinfo_score*100:.0f}%) — some pump/hype language "
            "detected (e.g. guaranteed returns, unverified targets)."
        )
    elif misinfo_score < 0.30:
        reasons.append(
            f"Low misinformation score ({misinfo_score*100:.0f}%) — no significant manipulation "
            "language patterns found."
        )

    # ── Social manipulation score ──────────────────────────────────────────────
    if social_score >= 0.60:
        reasons.append(
            f"Social manipulation indicators active ({social_score*100:.0f}%) — coordinated "
            "push language, urgency triggers, or viral spread patterns detected."
        )
    elif social_score < 0.25:
        reasons.append(
            f"Low social manipulation score ({social_score*100:.0f}%) — no persuasion or "
            "coordinated spread patterns detected."
        )

    # ── Phishing keywords ─────────────────────────────────────────────────────
    if phish_keywords_found:
        kw_str = ", ".join(f"'{k}'" for k in phish_keywords_found[:6])
        reasons.append(
            f"Credential-harvesting keywords found: {kw_str} — typical of phishing documents "
            "designed to collect PAN, Aadhaar, OTP, or login credentials."
        )

    # ── Urgency / legal threat language ───────────────────────────────────────
    URGENCY_TOKENS = [
        "within 24 hours", "immediate", "legal action", "fir", "ipc",
        "account frozen", "suspend", "penalty", "prosecution", "arrest",
        "do not delay", "act now",
    ]
    found_urgency = [t for t in URGENCY_TOKENS if t in threat_score and isinstance(threat_score, str)]
    # (we pass text presence check below instead)

    # ── Scrips ────────────────────────────────────────────────────────────────
    if scrips:
        reasons.append(
            f"NSE scrips detected: {', '.join(scrips)} — document references specific listed securities."
        )
    else:
        reasons.append("No NSE scrip symbols detected in the document text.")

    # ── Threat type specific ───────────────────────────────────────────────────
    if threat_type == "phishing":
        reasons.append(
            "Document classified as PHISHING — impersonates a regulatory body (SEBI/NSE/BSE) "
            "or broker to harvest credentials or funds."
        )
    elif threat_type == "misinformation":
        reasons.append(
            "Document classified as MISINFORMATION — likely contains fabricated financial data, "
            "fake price targets, or manipulative narratives."
        )
    elif threat_type == "low_risk_document":
        reasons.append(
            "Document classified as LOW RISK — overall scores are below threat thresholds. "
            "Content appears consistent with legitimate financial reporting."
        )
    elif threat_type == "generic_digital_threat":
        reasons.append(
            "Document classified as DIGITAL THREAT — elevated threat score from a combination "
            "of heuristic signals even without a dominant single category."
        )

    # ── Overall verdict context ────────────────────────────────────────────────
    if is_malicious:
        reasons.append(
            f"Combined threat score: {threat_score*100:.0f}% — exceeds the 60% threshold for "
            "MALICIOUS classification. Do not act on instructions in this document."
        )
    else:
        reasons.append(
            f"Combined threat score: {threat_score*100:.0f}% — below the 60% malicious threshold. "
            "Document can be treated as low-risk but monitor for unusual scrip movements."
        )

    return reasons


@router.post("/analyze-document", summary="Analyze an uploaded financial document for threats")
async def analyze_document(
    file: UploadFile = File(...),
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Accept a PDF, DOCX, or TXT file. Runs:
      1. Text extraction
      2. FinBERT financial sentiment analysis
      3. Misinformation detector (TF-IDF + LR)
      4. Social manipulation scorer
      5. Phishing keyword heuristics
      6. Mitigation engine recommendation
    Returns full threat analysis with human-readable reasons.
    """
    ALLOWED_TYPES = {"pdf", "docx", "txt", "text"}
    filename = file.filename or "upload.txt"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: pdf, docx, txt",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ── 1. Text extraction ────────────────────────────────────────────────────
    text = _extract_text_from_upload(filename, raw)
    if not text:
        text = "<no readable text extracted>"

    # ── 2. FinBERT financial sentiment ────────────────────────────────────────
    from models.finbert.sentiment import analyse as finbert_analyse
    fb = finbert_analyse(text)
    finbert_label: str  = fb["label"]
    finbert_score: float = fb["score"]
    finbert_neg: float  = fb["negative_prob"]

    # FinBERT contributes to threat score: strongly negative → high risk
    # scale: negative_prob → [0, 0.35] boost
    finbert_threat_boost = round(min(finbert_neg * 0.7, 0.35), 4)

    # ── 3. Misinformation + social scoring (existing pipeline) ────────────────
    from models.misinfo.detector import detect as misinfo_detect
    from data.ingest.social_signal_fetcher import _score_manipulation
    from data.ingest.url_social_ingestor import extract_scrips

    cleaned     = text[:8000]          # enough for misinfo model, way under RAM limit
    misinfo_sc  = misinfo_detect(cleaned)
    social_sc   = _score_manipulation(cleaned)
    scrips      = extract_scrips(cleaned)

    # ── 4. Phishing keyword check ─────────────────────────────────────────────
    PHISH_KW = [
        "pan number", "aadhaar", "aadhar", "otp", "password", "username",
        "login credentials", "account number", "ifsc", "upi id",
        "crypto wallet", "bitcoin", "wire transfer", "verification fee",
        "kyc update", "demat frozen", "account suspended",
    ]
    text_lower = text.lower()
    phish_found = [kw for kw in PHISH_KW if kw in text_lower]
    phish_score = round(min(len(phish_found) * 0.12, 0.40), 4)

    # ── 5. Urgency / legal threat heuristics ──────────────────────────────────
    URGENCY_KW = [
        "within 24 hours", "immediate action", "legal action", "fir filed",
        "account frozen", "penalty", "prosecution", "do not delay",
        "act now", "arrest warrant",
    ]
    urgency_hits = sum(1 for kw in URGENCY_KW if kw in text_lower)
    urgency_boost = round(min(urgency_hits * 0.08, 0.24), 4)

    # ── 6. Combined threat score ──────────────────────────────────────────────
    # Weights: misinfo(35%), social(20%), finbert_neg(25%), phish(12%), urgency(8%)
    threat_score = round(
        min(
            misinfo_sc * 0.35
            + social_sc * 0.20
            + finbert_threat_boost * 0.25 / 0.35   # normalise boost to weight
            + phish_score * 0.12
            + urgency_boost * 0.08,
            1.0,
        ),
        4,
    )
    # Re-apply simpler formula for clarity
    threat_score = round(
        min(
            misinfo_sc * 0.35
            + social_sc * 0.20
            + finbert_neg * 0.25
            + phish_score * 0.12
            + urgency_boost * 0.08,
            1.0
        ),
        4,
    )

    # ── 7. Threat type classification ─────────────────────────────────────────
    if phish_found and phish_score >= 0.24:
        threat_type = "phishing"
    elif misinfo_sc >= 0.60:
        threat_type = "misinformation"
    elif threat_score >= 0.60:
        threat_type = "generic_digital_threat"
    else:
        threat_type = "low_risk_document"

    is_malicious = threat_score >= 0.60

    # ── 8. Mitigation recommendation ─────────────────────────────────────────
    try:
        from scoring.mitigation_engine import get_mitigation_engine
        engine = get_mitigation_engine()
        mitigation = engine.recommend(
            alert_score=threat_score * 10,
            threat_type=threat_type,
            scheme_type="document_analysis",
            misinfo_score=misinfo_sc,
        )
        severity           = mitigation["severity"]
        recommended_action = mitigation["recommended_action"]
    except Exception as e:
        logger.warning("Mitigation engine unavailable: %s", e)
        severity           = "high" if threat_score >= 0.8 else "medium" if threat_score >= 0.6 else "low"
        recommended_action = "escalate_to_sebi" if threat_score >= 0.8 else "monitor_and_log"

    # ── 9. Build human-readable reasons ──────────────────────────────────────
    reasons = _build_reasons(
        threat_score=threat_score,
        misinfo_score=misinfo_sc,
        social_score=social_sc,
        finbert_label=finbert_label,
        finbert_score=finbert_score,
        finbert_neg=finbert_neg,
        scrips=scrips,
        phish_keywords_found=phish_found,
        threat_type=threat_type,
        is_malicious=is_malicious,
    )

    return {
        "filename":           filename,
        "threat_score":       threat_score,
        "misinfo_score":      round(misinfo_sc, 4),
        "social_score":       round(social_sc, 4),
        "phishing_score":     phish_score,
        "finbert_label":      finbert_label,
        "finbert_score":      finbert_score,
        "finbert_negative":   finbert_neg,
        "threat_type":        threat_type,
        "scrips_detected":    scrips,
        "is_malicious":       is_malicious,
        "severity":           severity,
        "recommended_action": recommended_action,
        "reasons":            reasons,
    }
