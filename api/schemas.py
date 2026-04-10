"""
api/schemas.py — Pydantic v2 request/response schemas for ARGUS API.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Auth ─────────────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Trade ────────────────────────────────────────────────────────────────────

class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: str
    scrip: str
    exchange: str
    timestamp: datetime
    price: float
    volume: float
    side: str
    order_type: Optional[str] = None
    is_manipulated: bool = False
    created_at: Optional[datetime] = None


# ─── Account ──────────────────────────────────────────────────────────────────

class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    broker: Optional[str] = None
    pan_hash: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    behavioral_dna: Optional[List[float]] = None
    dna_updated_at: Optional[datetime] = None
    is_flagged: bool = False
    flag_reason: Optional[str] = None


class AccountDNAOut(BaseModel):
    account_id: str
    dna_vector: List[float]
    fraudster_matches: List[dict] = Field(default_factory=list)
    reconstruction_error: float = 0.0
    is_anomalous: bool = False


class AccountNetworkOut(BaseModel):
    account_id: str
    nodes: List[dict]
    edges: List[dict]


class AccountSearchParams(BaseModel):
    broker: Optional[str] = None
    scrip: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    is_flagged: Optional[bool] = None


# ─── Alert ────────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scrip: str
    exchange: str
    detected_at: datetime
    impossibility_score: float
    scheme_type: str
    accounts_involved: List[str] = Field(default_factory=list)
    gnn_score: float
    dna_score: float
    cross_market_score: float
    zero_day_score: float
    social_signal_score: float = 0.0
    misinfo_score: float = 0.0
    threat_type: str = "market_manipulation"
    status: str
    case_file_path: Optional[str] = None
    assigned_to: Optional[str] = None
    created_at: Optional[datetime] = None
    # ── Mitigation fields ────────────────────────────────
    recommended_action: Optional[str] = None
    mitigation_status: Optional[str] = "pending"
    mitigation_applied_at: Optional[datetime] = None
    mitigation_applied_by: Optional[str] = None
    auto_mitigated: Optional[bool] = False
    mitigation_notes: Optional[str] = None
    severity: Optional[str] = "medium"
    escalated_to_sebi: Optional[bool] = False
    escalation_timestamp: Optional[datetime] = None


class AlertStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern="^(open|investigating|closed|false_positive)$",
        description="New alert status",
    )


class AlertAssign(BaseModel):
    analyst: str = Field(..., min_length=1, max_length=100)


class AlertListParams(BaseModel):
    status: Optional[str] = None
    min_score: Optional[float] = None
    scrip: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    severity: Optional[str] = None
    mitigation_status: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ── Mitigation schemas ────────────────────────────────────────────────────

class MitigationApplyRequest(BaseModel):
    action: str = Field(..., min_length=1)
    applied_by: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = None


class MitigationDismissRequest(BaseModel):
    dismissed_by: str = Field(..., min_length=1, max_length=100)
    reason: str = Field(..., min_length=1)


class MitigationEscalateRequest(BaseModel):
    escalated_by: str = Field(..., min_length=1, max_length=100)


class MitigationSummaryOut(BaseModel):
    total_alerts: int
    pending_mitigation: int
    applied: int
    dismissed: int
    escalated: int
    auto_mitigated: int
    escalated_to_sebi: int
    by_severity: dict
    by_action: dict


# ─── SEBI Case / Reports ──────────────────────────────────────────────────────

class SEBICaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    case_number: str
    entity_names: List[str] = Field(default_factory=list)
    scrip: str
    from_date: date
    to_date: date
    estimated_gain: Optional[float] = None
    evidence_json: dict = Field(default_factory=dict)
    status: str
    pdf_path: Optional[str] = None
    created_at: Optional[datetime] = None


class CaseGenerateRequest(BaseModel):
    estimated_gain: Optional[float] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    entity_names: Optional[List[str]] = None
    notes: Optional[str] = None


class CaseGenerateResponse(BaseModel):
    case_id: uuid.UUID
    case_number: str
    pdf_path: Optional[str] = None
    download_url: str


class WeeklySummaryOut(BaseModel):
    total_alerts: int
    resolved: int
    false_positives: int
    false_positive_rate_pct: float
    top_flagged_scrips: List[dict]


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthOut(BaseModel):
    status: str = "ok"
    services: dict = Field(default_factory=dict)
    model_versions: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
