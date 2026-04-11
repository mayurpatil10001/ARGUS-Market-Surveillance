"""
api/schemas.py — Pydantic v2 request/response schemas for SENTINEL API.
SENTINEL: Scalable ENTity Intelligence for NEtwork-Level threat detection
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
    """
    PS-402 threat alert response schema.
    Renamed fields: scheme_type→threat_category, accounts_involved→entities_involved,
    gnn_score→coordination_score, dna_score→behavior_score,
    cross_market_score→cross_platform_score, zero_day_score→novelty_score.
    Legacy aliases retained for backward compatibility.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # PS-402 platform field (twitter/reddit/web/telegram/email)
    platform: str = "web"
    scrip: str
    exchange: str = "web"  # legacy alias
    detected_at: datetime
    impossibility_score: float
    # PS-402 threat classification
    threat_category: str = "novel_threat"
    scheme_type: str = "novel_threat"  # legacy alias
    # PS-402 entity tracking
    entities_involved: List[str] = Field(default_factory=list)
    accounts_involved: List[str] = Field(default_factory=list)  # legacy alias
    # PS-402 scoring fields
    coordination_score: Optional[float] = Field(default=None, description="Network Coordination Detector score (35%)")
    behavior_score: Optional[float] = Field(default=None, description="Behavioral Anomaly Profiler score (25%)")
    novelty_score: Optional[float] = Field(default=None, description="Novel Threat Detector score (25%)")
    cross_platform_score: Optional[float] = Field(default=None, description="Cross-Platform Threat Correlator score (15%)")
    # Raw legacy score fields (mapped from DB)
    gnn_score: float = 0.0
    dna_score: float = 0.0
    cross_market_score: float = 0.0
    zero_day_score: float = 0.0
    social_signal_score: float = 0.0
    misinfo_score: float = 0.0
    threat_type: str = "generic_digital_threat"
    # content_sample stores a flagged post/URL/message snippet
    content_sample: Optional[str] = None
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

    def model_post_init(self, __context):
        # Populate PS-402 named score aliases from raw DB fields
        if self.coordination_score is None:
            object.__setattr__(self, 'coordination_score', self.gnn_score)
        if self.behavior_score is None:
            object.__setattr__(self, 'behavior_score', self.dna_score)
        if self.cross_platform_score is None:
            object.__setattr__(self, 'cross_platform_score', self.cross_market_score)
        if self.novelty_score is None:
            object.__setattr__(self, 'novelty_score', self.zero_day_score)
        # Sync legacy aliases
        if not self.threat_category or self.threat_category == "novel_threat":
            if self.scheme_type and self.scheme_type != "novel_threat":
                object.__setattr__(self, 'threat_category', self.scheme_type)
        if not self.entities_involved:
            object.__setattr__(self, 'entities_involved', self.accounts_involved)
        if not self.platform or self.platform == "web":
            if self.exchange and self.exchange != "web":
                object.__setattr__(self, 'platform', self.exchange.lower())


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
    platform: Optional[str] = None
    threat_category: Optional[str] = None
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


# ─── Threat Report / Case ─────────────────────────────────────────────────────

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


# ─── Weekly / Platform Summary (PS-402) ───────────────────────────────────────

class WeeklySummaryOut(BaseModel):
    """
    PS-402 weekly threat summary.
    Fields: total_threats, by_category breakdown, top_platforms, mitigation_rate.
    Legacy fields retained for backward compatibility.
    """
    total_alerts: int
    total_threats: int = 0          # PS-402 primary field (equals total_alerts)
    resolved: int
    false_positives: int
    false_positive_rate_pct: float
    # PS-402 breakdown fields
    by_category: dict = Field(default_factory=dict,
                              description="Threat counts by category (coordinated_attack, phishing, etc.)")
    top_platforms: List[dict] = Field(default_factory=list,
                                      description="Top platforms by threat volume")
    mitigation_rate: float = 0.0    # percentage of threats mitigated
    # Legacy field
    top_flagged_scrips: List[dict] = Field(default_factory=list)


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthOut(BaseModel):
    """
    Production health response — DB/Redis/Kafka connectivity, model load states,
    overall status, backend type, and uptime.
    """
    status: str = "healthy"          # healthy | degraded | unhealthy
    version: str = "2.0.0"
    backend: str = "sqlite"          # postgresql | sqlite
    services: dict = Field(default_factory=dict)  # database, redis, kafka
    models: dict = Field(default_factory=dict)    # gnn, dna, misinfo, zero_day, cross_market
    uptime_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # Legacy fields kept for backward compatibility
    system: str = "SENTINEL"
    model_versions: dict = Field(default_factory=dict)


# ─── MRFE ─────────────────────────────────────────────────────────────────────

class MRFETextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000,
                      description="Text to analyze (news headline, social post, document text, etc.)")
    fetch_historical: bool = Field(
        default=False,
        description="If True, fetch 30-day price context for affected scrips (may use synthetic fallback data).",
    )


class MRFEAnalysisOut(BaseModel):
    event_type: str
    threat_score: float
    misinfo_score: float
    social_score: float = 0.0
    threat_adapter_score: float = 0.0
    market_impact: str       # low / medium / high / critical
    affected_scrips: List[str] = Field(default_factory=list)
    recommended_action: str
    confidence: float
    evidence_snippets: List[str] = Field(default_factory=list)
    processing_time_ms: float
    synthetic_data: bool = False
    analyzed_at: Optional[str] = None
    historical_context: dict = Field(default_factory=dict)
    note: Optional[str] = None
    # File-specific (optional)
    filename: Optional[str] = None
    file_type: Optional[str] = None
    pdf_pages: Optional[int] = None
    pdf_word_count: Optional[int] = None


# ─── Simulation ────────────────────────────────────────────────────────────────

class SimulationRequest(BaseModel):
    scenario: str = Field(
        default="all",
        description=(
            "Scenario to run: pump_dump, spoofing, circular_trading, "
            "social_manipulation, phishing_campaign, or all"
        ),
    )


class SimulationScenarioResult(BaseModel):
    status: str                               # pass / fail
    alert_created: bool = False
    alert_id: Optional[str] = None
    signal_id: Optional[str] = None
    threat_score: float = 0.0
    severity: str = "unknown"
    recommended_action: str = "log_only"
    detection_time_ms: float = 0.0
    synthetic_data_used: bool = True
    error: Optional[str] = None


class SimulationSummary(BaseModel):
    total_scenarios: int
    passed: int
    failed: int
    alerts_created: int
    signals_created: int
    avg_detection_time_ms: float


class SimulationResultOut(BaseModel):
    simulation_id: str
    started_at: str
    completed_at: str
    total_duration_ms: float
    scenarios_run: List[str]
    results: dict     # scenario_name -> SimulationScenarioResult dict
    summary: SimulationSummary
