"""
data/ingest/url_social_ingestor.py — Market-signal ingestor for URLs and social media posts.

Ingestion sources supported:
  - Web URLs (news articles, phishing broker sites, fake SEBI pages)
  - Social media posts (Twitter/X, Reddit, Telegram, WhatsApp forwards)
  - News headlines (scraped or API-fed)

Each signal is:
  1. Cleaned and normalised
  2. Scored by misinfo detector + social signal scorer + phishing heuristics
  3. Scrips mentioned are extracted via keyword matching
  4. Persisted as a MarketSignal DB record
  5. If threat_score >= MARKET_MOVING_THRESHOLD (0.6), an ARGUS Alert is created
"""
from __future__ import annotations

import re
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Scrip extraction ──────────────────────────────────────────────────────────
# A curated seed list; extend from DB or config in production.
KNOWN_SCRIPS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL",
    "HINDUNILVR", "ITC", "LT", "KOTAKBANK", "AXISBANK", "BAJFINANCE", "WIPRO",
    "ADANIENT", "ADANIPORTS", "MARUTI", "NESTLEIND", "ULTRACEMCO", "SUNPHARMA",
    "TATAMOTORS", "TATASTEEL", "ONGC", "NTPC", "POWERGRID", "COALINDIA", "JSWSTEEL",
    "HCLTECH", "TECHM", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP", "BAJAJFINSV",
    "GRASIM", "HEROMOTOCO", "INDUSINDBK", "BRITANNIA", "EICHERMOT", "HINDALCO",
]


def extract_scrips(text: str) -> list[str]:
    """Return NSE symbols mentioned in text (case-insensitive whole-word match)."""
    if not text:
        return []
    found = []
    upper = text.upper()
    for scrip in KNOWN_SCRIPS:
        pattern = r'\b' + re.escape(scrip) + r'\b'
        if re.search(pattern, upper):
            found.append(scrip)
    return list(dict.fromkeys(found))  # preserve order, dedupe


# ── URL feature scorer ────────────────────────────────────────────────────────
HIGH_RISK_TLDS = {
    ".xyz", ".tk", ".ml", ".ga", ".cf", ".gq", ".top", ".click",
    ".download", ".loan", ".win", ".bid", ".stream",
}
BRAND_TARGETS = [
    "nseindia", "bseindia", "sebi", "zerodha", "groww", "upstox",
    "angelone", "iifl", "hdfc", "icici", "kotakneo", "motilaloswal",
]
PHISH_KEYWORDS = [
    "login", "verify", "secure", "update", "confirm", "wallet",
    "kyc", "aadhar", "pan", "otp", "account", "signin", "auth",
]


def _score_url(url: str) -> float:
    """Heuristic phishing/threat score for a URL. Returns [0, 1]."""
    score = 0.0
    url_lower = url.lower()
    # TLD risk
    for tld in HIGH_RISK_TLDS:
        if tld in url_lower:
            score += 0.25
            break
    # Brand impersonation
    for brand in BRAND_TARGETS:
        if brand in url_lower and brand + ".com" not in url_lower:
            score += 0.35
            break
    # Phishing keywords in path/query
    hits = sum(1 for kw in PHISH_KEYWORDS if kw in url_lower)
    score += min(hits * 0.08, 0.25)
    # IP-as-hostname
    if re.search(r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url):
        score += 0.3
    # Excessive subdomains (>= 4 dots before TLD)
    try:
        host = url.split("/")[2]
        if host.count(".") >= 4:
            score += 0.1
    except IndexError:
        pass
    return round(min(score, 1.0), 4)


# ── Text cleaner ──────────────────────────────────────────────────────────────
def _clean_text(text: str) -> str:
    """Strip URLs, excess whitespace, and common noise from social posts."""
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#(\w+)', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── Main ingestion functions ──────────────────────────────────────────────────
MARKET_MOVING_THRESHOLD = 0.6


def ingest_url(
    url: str,
    platform: str = "web",
    entity_id: Optional[str] = None,
    source_meta: Optional[dict] = None,
    db=None,
) -> dict:
    """
    Ingest a single URL, score it, persist it, and optionally fire an alert.

    Args:
        url:         The raw URL string.
        platform:    Source platform (web, telegram, whatsapp, twitter).
        entity_id:   Known account/user ID if available.
        source_meta: Extra metadata (likes, shares, timestamp of original post).
        db:          SQLAlchemy session. If None, a new session is opened and closed.

    Returns:
        dict with keys: signal_id, threat_score, is_market_moving, scrips_mentioned,
                        alert_id (str or None), platform, source_url.
    """
    from data.db.crud import create_market_signal
    from data.db.session import get_session
    from models.misinfo.detector import detect as misinfo_detect
    from data.ingest.social_signal_fetcher import _score_manipulation

    close_db = db is None
    if close_db:
        db = get_session()

    try:
        url_score    = _score_url(url)
        misinfo_sc   = misinfo_detect(url)           # URL text as weak signal
        social_sc    = _score_manipulation(url)
        threat_score = round(url_score * 0.6 + misinfo_sc * 0.25 + social_sc * 0.15, 4)
        scrips       = extract_scrips(url)

        sig = create_market_signal(
            db,
            signal_type="url_threat",
            platform=platform,
            source_url=url,
            raw_text=None,
            scrips_mentioned=scrips,
            entity_id=entity_id,
            misinfo_score=misinfo_sc,
            social_signal_score=social_sc,
            threat_score=threat_score,
            source_meta=source_meta or {},
        )

        alert_id = None
        if sig.is_market_moving:
            alert_id = _maybe_create_alert(db, sig, scrips)

        return {
            "signal_id": sig.id,
            "threat_score": threat_score,
            "is_market_moving": sig.is_market_moving,
            "scrips_mentioned": scrips,
            "alert_id": alert_id,
            "platform": platform,
            "source_url": url,
        }
    except Exception as e:
        logger.error("ingest_url failed: %s", e)
        return {"error": str(e), "source_url": url, "threat_score": 0.0}
    finally:
        if close_db:
            db.close()


def ingest_social_post(
    text: str,
    platform: str,
    source_url: Optional[str] = None,
    entity_id: Optional[str] = None,
    source_meta: Optional[dict] = None,
    db=None,
) -> dict:
    """
    Ingest a social media post or news headline, score it, persist it,
    and optionally fire an alert.

    Args:
        text:        Raw post/headline text.
        platform:    twitter, reddit, telegram, whatsapp, news.
        source_url:  Permalink to original post (optional).
        entity_id:   Username or account ID if known.
        source_meta: Dict with engagement data: likes, shares, comments,
                     velocity_per_hour, verified_account (bool).
        db:          SQLAlchemy session. If None, opened and closed here.

    Returns:
        dict with keys: signal_id, misinfo_score, social_signal_score,
                        combined_score, is_market_moving, scrips_mentioned,
                        alert_id (str or None), platform.
    """
    from data.db.crud import create_market_signal
    from data.db.session import get_session
    from models.misinfo.detector import detect as misinfo_detect
    from data.ingest.social_signal_fetcher import _score_manipulation

    close_db = db is None
    if close_db:
        db = get_session()

    try:
        cleaned    = _clean_text(text)
        misinfo_sc = misinfo_detect(cleaned)
        social_sc  = _score_manipulation(cleaned)

        # Engagement velocity boosts score (capped at +0.2)
        velocity_boost = 0.0
        if source_meta and "velocity_per_hour" in source_meta:
            vph = float(source_meta["velocity_per_hour"])
            if vph > 500:
                velocity_boost = 0.20
            elif vph > 100:
                velocity_boost = 0.10
            elif vph > 20:
                velocity_boost = 0.05

        combined = round(min(misinfo_sc * 0.55 + social_sc * 0.45 + velocity_boost, 1.0), 4)
        scrips   = extract_scrips(cleaned)

        # Determine signal_type from platform
        type_map = {
            "twitter": "social_post", "x": "social_post",
            "reddit": "social_post", "telegram": "social_post",
            "whatsapp": "whatsapp_forward", "news": "news_headline",
        }
        sig_type = type_map.get(platform.lower(), "social_post")

        sig = create_market_signal(
            db,
            signal_type=sig_type,
            platform=platform,
            source_url=source_url,
            raw_text=text[:4000],   # truncate for DB storage
            scrips_mentioned=scrips,
            entity_id=entity_id,
            misinfo_score=misinfo_sc,
            social_signal_score=social_sc,
            threat_score=combined,
            source_meta=source_meta or {},
        )

        alert_id = None
        if sig.is_market_moving:
            alert_id = _maybe_create_alert(db, sig, scrips)

        return {
            "signal_id": sig.id,
            "misinfo_score": misinfo_sc,
            "social_signal_score": social_sc,
            "combined_score": combined,
            "is_market_moving": sig.is_market_moving,
            "scrips_mentioned": scrips,
            "alert_id": alert_id,
            "platform": platform,
        }
    except Exception as e:
        logger.error("ingest_social_post failed: %s", e)
        return {"error": str(e), "platform": platform, "combined_score": 0.0}
    finally:
        if close_db:
            db.close()


def ingest_batch(records: list[dict], db=None) -> list[dict]:
    """
    Batch ingest a list of URL or social post records.

    Each record must have:
      - type: "url" | "social"
      - For url:    url (str), platform (str, optional)
      - For social: text (str), platform (str), source_url (str, optional)
      Optional for both: entity_id, source_meta

    Returns list of result dicts in same order as input.
    """
    from data.db.session import get_session

    close_db = db is None
    if close_db:
        db = get_session()

    results = []
    try:
        for rec in records:
            rtype = rec.get("type", "social")
            if rtype == "url":
                results.append(ingest_url(
                    url=rec["url"],
                    platform=rec.get("platform", "web"),
                    entity_id=rec.get("entity_id"),
                    source_meta=rec.get("source_meta"),
                    db=db,
                ))
            else:
                results.append(ingest_social_post(
                    text=rec["text"],
                    platform=rec.get("platform", "unknown"),
                    source_url=rec.get("source_url"),
                    entity_id=rec.get("entity_id"),
                    source_meta=rec.get("source_meta"),
                    db=db,
                ))
    finally:
        if close_db:
            db.close()
    return results


# ── Internal: alert creation for market-moving signals ────────────────────────
def _maybe_create_alert(db, signal, scrips: list[str]) -> Optional[str]:
    """
    Create an ARGUS Alert for a market-moving signal.
    Returns the new alert_id or None on failure.
    """
    try:
        import uuid as _uuid
        from data.db.models import Alert
        from data.db.crud import link_signal_to_alert

        scrip = scrips[0] if scrips else "UNKNOWN"
        alert = Alert(
            id=str(_uuid.uuid4()),
            scrip=scrip,
            exchange="NSE",
            scheme_type=(
                "social_media_threat" if signal.signal_type == "social_post"
                else "phishing" if signal.signal_type == "url_threat"
                else "misinformation"
            ),
            accounts_involved=[signal.entity_id] if signal.entity_id else [],
            gnn_score=0.0,
            dna_score=0.0,
            cross_market_score=0.0,
            zero_day_score=0.0,
            social_signal_score=signal.social_signal_score,
            misinfo_score=signal.misinfo_score,
            threat_type=signal.signal_type,
            impossibility_score=0.0,
            status="open",
            severity="high" if signal.threat_score >= 0.8 else "medium",
            mitigation_status="pending",
            auto_mitigated=False,
            escalated_to_sebi=False,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        link_signal_to_alert(db, signal.id, alert.id)
        logger.info("Alert created for market-moving signal: %s", alert.id)
        return alert.id
    except Exception as e:
        logger.error("_maybe_create_alert failed: %s", e)
        return None
