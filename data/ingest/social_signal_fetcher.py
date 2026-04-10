"""
data/ingest/social_signal_fetcher.py — Social media threat signal ingestion.
Fetches posts from Reddit/Twitter, scores for manipulation intent, and
outputs a DataFrame compatible with the Zero-Day anomaly engine.
"""
from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ── NSE/BSE symbol pattern ────────────────────────────────────────────────────
# Matches symbols like RELIANCE, TCS, INFY, XYZTECH, etc.
_SYMBOL_RE = re.compile(r"\b([A-Z]{2,10})\b")

# Known NSE/BSE scrips subset for symbol extraction (fallback list)
_KNOWN_SCRIPS: set[str] = {
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BAJFINANCE",
    "BHARTIARTL", "ITC", "HINDUNILVR", "LT", "KOTAKBANK", "AXISBANK", "WIPRO",
    "MARUTI", "ULTRACEMCO", "TITAN", "SUNPHARMA", "NESTLEIND", "TECHM",
    "POWERGRID", "NTPC", "ONGC", "COALINDIA", "BPCL", "HCLTECH", "ADANIENT",
    "ADANIPORTS", "JSWSTEEL", "TATASTEEL", "TATAMOTORS", "HEROMOTOCO",
    "BAJAJ_AUTO", "DRREDDY", "DIVISLAB", "CIPLA", "EICHERMOT", "BRITANNIA",
    "GRASIM", "INDUSINDBK", "ASIANPAINT", "HDFCLIFE", "SBILIFE", "SHREECEM",
    "XYZTECH",  # fictitious scrip used in demos
}

# ── Pump/manipulation keyword lexicon ────────────────────────────────────────
_PUMP_KEYWORDS: list[str] = [
    "to the moon", "moon shot", "100x", "1000x", "buy now", "buy before",
    "last chance", "guaranteed profit", "sure shot", "next multibagger",
    "multibagger alert", "hidden gem", "undiscovered", "share before deleted",
    "circuit", "upper circuit", "breakout", "insider tip", "insider info",
    "bulk deal", "operator move", "strong accumulation", "fomo",
    "get in now", "loaded", "accumulate", "targets", "fresh breakout",
    "going parabolic", "undervalued gem", "explosive move",
]

_SUSPICIOUS_DOMAINS: list[str] = [
    "t.me/", "telegram.me", "bit.ly", "tinyurl", "cutt.ly",
    "wa.me/", "whatsapp.com/", "discord.gg/",
]

_FAKE_NEWS_KEYWORDS: list[str] = [
    "sebi approved", "rbi backing", "government contract",
    "acquisition confirmed", "buyback announced", "takeover bid",
    "fii buying heavily", "dii accumulation", "promoter buying",
    "price target 200%", "price target 300%", "guaranteed return",
    "no risk", "risk free", "pump group", "paid group",
]


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _extract_symbols(text: str, known_only: bool = True) -> list[str]:
    """Extract stock symbols mentioned in text."""
    candidates = _SYMBOL_RE.findall(text.upper())
    if known_only:
        return [s for s in candidates if s in _KNOWN_SCRIPS]
    # Heuristic: 2-10 uppercase letters that look like tickers
    return list(set(c for c in candidates if 2 <= len(c) <= 10))


def _score_manipulation(text: str) -> float:
    """
    Returns manipulation_score in [0, 1] based on:
    - pump keyword matches (weighted 0.55)
    - suspicious URL presence (weighted 0.25)
    - fake news keyword matches (weighted 0.20)
    """
    text_lower = text.lower()

    # Pump keyword score
    pump_hits = sum(1 for kw in _PUMP_KEYWORDS if kw in text_lower)
    pump_score = min(1.0, pump_hits / 3.0)

    # Suspicious URL score
    url_hits = sum(1 for d in _SUSPICIOUS_DOMAINS if d in text_lower)
    url_score = min(1.0, url_hits)

    # Fake news score
    fake_hits = sum(1 for kw in _FAKE_NEWS_KEYWORDS if kw in text_lower)
    fake_score = min(1.0, fake_hits / 2.0)

    return round(0.55 * pump_score + 0.25 * url_score + 0.20 * fake_score, 4)


def _infer_signal_type(text: str, score: float) -> str:
    text_lower = text.lower()
    if any(kw in text_lower for kw in _FAKE_NEWS_KEYWORDS):
        return "misinformation"
    if any(kw in text_lower for kw in _PUMP_KEYWORDS):
        return "pump_signal"
    if any(d in text_lower for d in _SUSPICIOUS_DOMAINS):
        return "suspicious_link"
    if score > 0.3:
        return "coordinated_post"
    return "neutral"


# ── Reddit fetcher (public JSON API, no auth required) ────────────────────────

def _fetch_reddit_posts(
    subreddit: str,
    limit: int = 25,
    after: Optional[str] = None,
) -> list[dict]:
    """Fetch posts from a subreddit using Reddit's public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/new.json"
    params: dict = {"limit": limit, "raw_json": 1}
    if after:
        params["after"] = after

    headers = {"User-Agent": "SENTINEL-SocialSignal/2.0 (digital threat detection research)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        posts = []
        for child in data.get("data", {}).get("children", []):
            p = child.get("data", {})
            posts.append({
                "platform": "reddit",
                "subreddit": subreddit,
                "post_id": p.get("id", ""),
                "timestamp": datetime.fromtimestamp(
                    p.get("created_utc", time.time()), tz=timezone.utc
                ),
                "post_text": f"{p.get('title', '')} {p.get('selftext', '')}".strip(),
                "url": p.get("url", ""),
                "score": p.get("score", 0),
            })
        return posts
    except Exception as exc:
        logger.warning(f"Reddit fetch failed for r/{subreddit}: {exc}")
        return []


# ── Twitter/X fetcher (public search, no auth, scraping fallback) ─────────────

def _fetch_twitter_mock(query: str, limit: int = 10) -> list[dict]:
    """
    Twitter public API requires OAuth2 bearer token.
    When TWITTER_BEARER_TOKEN is set, uses v2 API; otherwise returns
    synthetic mock posts for offline/demo mode.
    """
    bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
    if bearer:
        return _fetch_twitter_api(query, bearer, limit)
    # Offline mock — returns synthetic pump posts for demo
    return _mock_twitter_posts(query, limit)


def _fetch_twitter_api(query: str, bearer: str, limit: int = 10) -> list[dict]:
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {bearer}"}
    params = {
        "query": f"{query} -is:retweet lang:en",
        "max_results": min(limit, 100),
        "tweet.fields": "created_at,text,public_metrics",
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        tweets = []
        for tw in resp.json().get("data", []):
            tweets.append({
                "platform": "twitter",
                "subreddit": None,
                "post_id": tw.get("id", ""),
                "timestamp": datetime.fromisoformat(
                    tw.get("created_at", datetime.utcnow().isoformat()).replace("Z", "+00:00")
                ),
                "post_text": tw.get("text", ""),
                "url": "",
                "score": tw.get("public_metrics", {}).get("like_count", 0),
            })
        return tweets
    except Exception as exc:
        logger.warning(f"Twitter API fetch failed: {exc}")
        return []


def _mock_twitter_posts(query: str, limit: int = 10) -> list[dict]:
    """Synthetic Twitter posts for offline demo / unit testing."""
    templates = [
        f"🚀 {query} going to moon! Buy before 10am - guaranteed 3x returns. Join t.me/stockpump",
        f"ALERT: {query} operator move detected. Upper circuit target. Load up now! #NSE",
        f"Hidden gem {query} - SEBI approved breakout. 100x potential. Last chance!",
        f"Strong {query} accumulation by FIIs. Insider tip: buyback announced soon.",
        f"{query} fresh breakout on charts. Price target 200%. No risk trade!",
    ]
    now = datetime.now(tz=timezone.utc)
    posts = []
    for i, tmpl in enumerate(templates[:limit]):
        posts.append({
            "platform": "twitter",
            "subreddit": None,
            "post_id": f"mock_tw_{i}",
            "timestamp": now - timedelta(minutes=i * 5),
            "post_text": tmpl,
            "url": "",
            "score": 0,
        })
    return posts


# ── Main public API ───────────────────────────────────────────────────────────

def fetch_social_signals(
    scrips: Optional[list[str]] = None,
    subreddits: Optional[list[str]] = None,
    twitter_queries: Optional[list[str]] = None,
    limit_per_source: int = 25,
    since: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    Fetch + score social media posts for stock manipulation signals.

    Parameters
    ----------
    scrips : list[str]
        NSE/BSE scrip symbols to filter for (None = all detected).
    subreddits : list[str]
        Reddit communities to monitor. Defaults to IndianStockMarket + stocks.
    twitter_queries : list[str]
        Twitter search queries. Defaults to scrip-based queries.
    limit_per_source : int
        Max posts per subreddit/query.
    since : datetime
        Only include posts after this timestamp.

    Returns
    -------
    pd.DataFrame with columns:
        timestamp, platform, symbol, post_text,
        manipulation_score (0-1), signal_type
    """
    if subreddits is None:
        subreddits = ["IndianStockMarket", "stocks", "IndiaInvestments", "StockMarketIndia"]

    if twitter_queries is None:
        base_scrips = scrips or list(_KNOWN_SCRIPS)[:5]
        twitter_queries = [f"#{s} NSE stock" for s in base_scrips[:3]]

    raw_posts: list[dict] = []

    # Fetch Reddit
    for sr in subreddits:
        posts = _fetch_reddit_posts(sr, limit=limit_per_source)
        raw_posts.extend(posts)

    # Fetch Twitter
    for q in twitter_queries:
        posts = _fetch_twitter_mock(q, limit=min(limit_per_source, 10))
        raw_posts.extend(posts)

    if not raw_posts:
        logger.warning("No social posts fetched. Returning empty DataFrame.")
        return _empty_df()

    rows = []
    for post in raw_posts:
        text = post.get("post_text", "")
        if not text:
            continue

        ts = post.get("timestamp", datetime.now(tz=timezone.utc))
        if since and ts < since:
            continue

        symbols = _extract_symbols(text)
        if scrips:
            symbols = [s for s in symbols if s in scrips]
        if not symbols:
            symbols = ["UNKNOWN"]

        score = _score_manipulation(text)
        sig_type = _infer_signal_type(text, score)

        for sym in symbols:
            rows.append({
                "timestamp": ts,
                "platform": post.get("platform", "unknown"),
                "symbol": sym,
                "post_text": text[:500],  # truncate for storage
                "manipulation_score": score,
                "signal_type": sig_type,
            })

    if not rows:
        return _empty_df()

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
    return df


def get_social_score_for_scrip(scrip: str, lookback_hours: int = 24) -> float:
    """
    Returns a single aggregated social manipulation score [0, 10]
    for a given scrip over the last `lookback_hours`.
    Used as a feature input to Zero-Day anomaly engine.
    """
    since = datetime.now(tz=timezone.utc) - timedelta(hours=lookback_hours)
    try:
        df = fetch_social_signals(scrips=[scrip], since=since)
        if df.empty or (df["symbol"] == "UNKNOWN").all():
            return 0.0
        scrip_df = df[df["symbol"] == scrip]
        if scrip_df.empty:
            return 0.0
        # Weight by recency: more recent posts have higher weight
        scores = scrip_df["manipulation_score"].values
        agg = float(scores.max() * 0.6 + scores.mean() * 0.4)
        return round(min(10.0, agg * 10.0), 3)
    except Exception as exc:
        logger.warning(f"Social score failed for {scrip}: {exc}")
        return 0.0


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "timestamp", "platform", "symbol", "post_text",
        "manipulation_score", "signal_type",
    ])
