"""
data/ingest/generic_threat_adapter.py — Generic Digital Threat Input Adapter.
Accepts threat data beyond financial markets (phishing URLs, suspicious
transaction logs, generic platform activity logs) and normalizes them into
a standard threat schema compatible with ARGUS Alert model.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── Standard threat schema ────────────────────────────────────────────────────
THREAT_SCHEMA_FIELDS = [
    "entity_id",
    "timestamp",
    "threat_type",
    "platform",
    "raw_signal",
    "threat_score",
]

# Valid threat_type values (mirrors ThreatTypeEnum in DB models)
VALID_THREAT_TYPES = {
    "market_manipulation",
    "social_media_threat",
    "misinformation",
    "phishing",
    "generic_digital_threat",
}

# ── Phishing URL heuristics ───────────────────────────────────────────────────
_PHISHING_TLD_RISK: dict[str, float] = {
    ".xyz": 0.7, ".tk": 0.8, ".ml": 0.7, ".ga": 0.7, ".cf": 0.7,
    ".gq": 0.7, ".buzz": 0.6, ".click": 0.6, ".link": 0.5,
    ".top": 0.5, ".online": 0.4, ".site": 0.4, ".store": 0.3,
}

_PHISHING_KEYWORDS: list[str] = [
    "login", "signin", "update-account", "verify", "secure",
    "bank", "paypal", "amazon", "netflix", "nse", "sebi",
    "account-suspended", "confirm", "wallet", "crypto", "reward",
]

_HOMOGLYPH_BRANDS: list[str] = [
    "nseindia", "bseindia", "sebi", "rbi", "hdfcbank", "sbi",
    "icicibank", "axisbank", "paytm", "zerodha", "groww",
]


def _score_phishing_url(url: str) -> float:
    """Return phishing risk score [0, 1] for a URL."""
    try:
        parsed = urlparse(url if url.startswith("http") else f"http://{url}")
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        full = domain + path
    except Exception:
        return 0.5

    score = 0.0

    # TLD risk
    for tld, risk in _PHISHING_TLD_RISK.items():
        if domain.endswith(tld):
            score += risk * 0.3
            break

    # Keyword in path/domain
    kw_hits = sum(1 for kw in _PHISHING_KEYWORDS if kw in full)
    score += min(0.35, kw_hits * 0.12)

    # IP address instead of domain name
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}", domain):
        score += 0.4

    # Excessive subdomains (e.g. login.secure.bank.evil.xyz)
    parts = domain.split(".")
    if len(parts) > 4:
        score += 0.2

    # Homoglyph brand impersonation
    for brand in _HOMOGLYPH_BRANDS:
        if brand in domain and not domain.startswith(f"{brand}."):
            score += 0.35
            break

    # Long URL with many query params = form phishing
    if len(url) > 150:
        score += 0.1

    return round(min(1.0, score), 4)


# ── Transaction log heuristics ────────────────────────────────────────────────

def _score_transaction_log(record: dict) -> float:
    """Score suspicious transaction record [0, 1]."""
    score = 0.0
    amount = float(record.get("amount", 0))
    freq = int(record.get("frequency_per_hour", 0))
    failed = bool(record.get("failed", False))
    foreign = bool(record.get("foreign_ip", False))
    unusual_hour = int(record.get("hour", 12)) not in range(6, 23)

    if amount > 1_000_000:
        score += 0.3
    elif amount > 100_000:
        score += 0.15

    if freq > 50:
        score += 0.3
    elif freq > 20:
        score += 0.15

    if failed:
        score += 0.2
    if foreign:
        score += 0.2
    if unusual_hour:
        score += 0.1

    return round(min(1.0, score), 4)


# ── Generic activity log heuristics ──────────────────────────────────────────

def _score_activity_log(record: dict) -> float:
    """Score generic platform activity log [0, 1]."""
    score = 0.0
    action = str(record.get("action", "")).lower()
    bulk = bool(record.get("bulk_action", False))
    automated = bool(record.get("is_automated", False))
    error_rate = float(record.get("error_rate", 0.0))
    repeat_count = int(record.get("repeat_count", 0))

    high_risk_actions = {
        "mass_message", "bulk_post", "account_create", "api_abuse",
        "scrape", "credential_stuff", "brute_force", "data_exfil",
    }
    if action in high_risk_actions:
        score += 0.45

    if bulk:
        score += 0.2
    if automated:
        score += 0.15
    if error_rate > 0.5:
        score += 0.15
    if repeat_count > 100:
        score += 0.2

    return round(min(1.0, score), 4)


# ── Auto-detect threat type ───────────────────────────────────────────────────

def _infer_threat_type(raw: dict | str) -> str:
    """Infer threat_type from raw signal structure."""
    if isinstance(raw, str):
        text = raw.lower()
        if text.startswith("http") or "://" in text or "www." in text:
            return "phishing"
        if any(w in text for w in ["pump", "circuit", "operator", "multibagger", "moon"]):
            return "social_media_threat"
        if any(w in text for w in ["fake", "sebi approved", "insider", "guaranteed profit"]):
            return "misinformation"
        return "generic_digital_threat"

    if isinstance(raw, dict):
        keys = set(raw.keys())
        if {"url", "domain"} & keys:
            return "phishing"
        if {"amount", "account", "transaction_id"} & keys:
            return "market_manipulation"
        if {"post_text", "platform", "subreddit"} & keys:
            return "social_media_threat"
        if {"headline", "source", "article"} & keys:
            return "misinformation"

    return "generic_digital_threat"


def _derive_entity_id(raw: dict | str, platform: str) -> str:
    """Create a stable entity_id from the raw signal fingerprint."""
    key_str = f"{platform}::{str(raw)[:200]}"
    return "ENT_" + hashlib.sha1(key_str.encode()).hexdigest()[:12].upper()


# ── Public API ────────────────────────────────────────────────────────────────

def normalize(
    raw_signal: Any,
    platform: Optional[str] = None,
    threat_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> dict:
    """
    Normalize any threat input into standard ARGUS threat schema.

    Parameters
    ----------
    raw_signal : Any
        The raw threat data: URL string, dict (transaction log, activity log,
        social post), or freeform text.
    platform : str, optional
        Source platform (e.g. 'twitter', 'email', 'broker_api', 'web').
    threat_type : str, optional
        Override threat type. Must be one of VALID_THREAT_TYPES.
        If None, auto-detected from raw_signal.
    entity_id : str, optional
        Override entity identifier. If None, derived from raw_signal hash.
    timestamp : datetime, optional
        Event timestamp. Defaults to utcnow.

    Returns
    -------
    dict with keys: entity_id, timestamp, threat_type, platform,
                    raw_signal, threat_score
    """
    ts = timestamp or datetime.now(tz=timezone.utc)
    plat = platform or "unknown"

    # Auto-detect threat type
    detected_type = threat_type or _infer_threat_type(raw_signal)
    if detected_type not in VALID_THREAT_TYPES:
        logger.warning(
            f"Unknown threat_type '{detected_type}', defaulting to generic_digital_threat"
        )
        detected_type = "generic_digital_threat"

    # Score based on threat type
    if detected_type == "phishing":
        url_str = raw_signal if isinstance(raw_signal, str) else raw_signal.get("url", "")
        threat_score = _score_phishing_url(url_str)
    elif detected_type == "market_manipulation":
        rec = raw_signal if isinstance(raw_signal, dict) else {}
        threat_score = _score_transaction_log(rec)
    elif detected_type == "social_media_threat":
        rec = raw_signal if isinstance(raw_signal, dict) else {}
        if isinstance(raw_signal, str):
            # Use text-based scoring
            from data.ingest.social_signal_fetcher import _score_manipulation
            threat_score = _score_manipulation(raw_signal)
        else:
            threat_score = _score_activity_log(rec)
    elif detected_type == "misinformation":
        text = raw_signal if isinstance(raw_signal, str) else raw_signal.get("text", raw_signal.get("headline", ""))
        try:
            from models.misinfo.detector import detect
            threat_score = detect(str(text))
        except Exception:
            threat_score = 0.5
    else:
        rec = raw_signal if isinstance(raw_signal, dict) else {}
        threat_score = _score_activity_log(rec) if rec else 0.1

    ent_id = entity_id or _derive_entity_id(raw_signal, plat)

    # Serialize raw_signal for storage
    if isinstance(raw_signal, dict):
        raw_str = str(raw_signal)[:1000]
    else:
        raw_str = str(raw_signal)[:1000]

    return {
        "entity_id": ent_id,
        "timestamp": ts,
        "threat_type": detected_type,
        "platform": plat,
        "raw_signal": raw_str,
        "threat_score": round(float(threat_score), 4),
    }


def normalize_batch(
    records: list[Any],
    platform: Optional[str] = None,
    threat_type: Optional[str] = None,
) -> list[dict]:
    """
    Normalize a batch of raw threat signals.

    Parameters
    ----------
    records : list
        List of raw signals (strings, dicts, URLs, etc.).
    platform : str, optional
        Common platform for all records.
    threat_type : str, optional
        Common threat_type override for all records.

    Returns
    -------
    list of normalized threat dicts.
    """
    results = []
    for rec in records:
        try:
            normalized = normalize(rec, platform=platform, threat_type=threat_type)
            results.append(normalized)
        except Exception as exc:
            logger.warning(f"normalize_batch: skipping record due to error: {exc}")
    return results
