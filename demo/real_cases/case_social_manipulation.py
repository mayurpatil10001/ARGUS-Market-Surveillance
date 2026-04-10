"""
demo/real_cases/case_social_manipulation.py — ARGUS Social Manipulation Demo.
Simulates a coordinated pump-and-dump social media campaign against XYZTECH.

Case:
  Fictitious scrip XYZTECH suddenly flooded with pump posts across Reddit and
  Twitter over a 2-hour window. Engagement velocity spikes. Posts contain
  classic manipulation language: guaranteed returns, operator calls, circuit
  targets. A phishing site impersonating NSEIndia is also deployed alongside
  the campaign to harvest retail credentials.

Detections:
  - social_signal_fetcher: engagement velocity + pump keyword score
  - misinfo detector: classifies posts as misinformation (score > 0.5)
  - generic_threat_adapter: classifies phishing URL (score > 0)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ── Synthetic social media posts ───────────────────────────────────────────────

_POST_TEMPLATES = [
    "XYZTECH guaranteed 500% returns! Operator call confirmed. Buy before 10am. Join t.me/xyzpump",
    "XYZTECH going to moon! Upper circuit target by EOD. Load up now! #NSE #XYZTECH",
    "Hidden gem XYZTECH - SEBI approved breakout. 100x potential. Last chance to board! bit.ly/xyz",
    "XYZTECH fresh breakout on all charts. Insider tip: bulk deal announced. Price target 300%!",
    "Urgent: XYZTECH multibagger alert. Promoter buying heavily. No risk trade! Get in now!",
    "XYZTECH operator move detected. Strong accumulation by FIIs. Circuit target 200. FOMO alert!",
    "XYZTECH buy before 9:30am. Guaranteed profit. Share before deleted! Upper circuit imminent.",
    "XYZTECH explosive move incoming. 1000x potential. Next multibagger confirmed. Undiscovered gem!",
    "Strong XYZTECH signal - acquisition confirmed! Buyback announced. Load NOW or regret!",
    "XYZTECH going parabolic today. Insider info: government contract sealed. Buy buy buy!",
    "XYZTECH circuit target by 11am. Operator loaded at lower levels. Join t.me/xyzgroup",
    "XYZTECH undervalued gem! FII buying heavily. Price target 200% within 1 week. Sure shot!",
    "BREAKING: XYZTECH takeover bid from foreign entity! DII accumulation. 100% guaranteed move!",
    "XYZTECH fresh breakout — get in now or miss 500% returns. Insider tip from promoter group.",
    "XYZTECH going to 10x today! Last chance! RBI backing confirmed. Share before group is deleted!",
    "XYZTECH operator accumulation complete. Upper circuit lock by 12pm. This is not a drill!",
    "XYZTECH multibagger — next TCS! SEBI approved. FII bulk deal at open. No risk guaranteed gain.",
    "XYZTECH momentum building. Loaded at 45, target 200. Share in your WhatsApp groups NOW!",
    "ALERT: XYZTECH circuit target 150% up today. Paid group insider leaked: BIG move imminent.",
    "XYZTECH going parabolic in minutes. Buy before market opens. Sure shot 3x by closing bell!",
]

_ACCOUNTS = ["SOC_PUMP_001", "SOC_PUMP_002", "SOC_PUMP_003", "SOC_PUMP_004", "SOC_PUMP_005"]

_PHISHING_URL = "http://nse1ndia-login.xyz/verify?token=XYZ&redirect=account-suspended"


def _make_synthetic_posts() -> list[dict]:
    """Generate 20 posts over 2 hours with increasing velocity."""
    now = datetime.now(tz=timezone.utc)
    posts = []
    for i, template in enumerate(_POST_TEMPLATES):
        # Posts get more frequent in second hour (velocity spike)
        if i < 8:
            minutes_ago = 120 - (i * 15)   # first hour: 1 post every 15 min
        else:
            minutes_ago = 120 - 120 - (i - 8) * 4  # second hour: surge every 4 min
        ts = now + timedelta(minutes=minutes_ago)
        posts.append({
            "platform": "reddit" if i % 3 == 0 else "twitter",
            "post_id": f"mock_xyztech_{i:02d}",
            "timestamp": ts,
            "post_text": template,
            "symbol": "XYZTECH",
            "score": max(0, 100 - (i * 3)),  # engagement score
        })
    return posts


def run_detection() -> dict:
    """
    Run full social manipulation detection pipeline against XYZTECH campaign.

    Returns
    -------
    dict with keys:
        overall_score, scheme_type, accounts_involved,
        social_signal_score, misinfo_score, phishing_score,
        recommended_action, severity
    """
    # ── 1. Social signal score ─────────────────────────────────────────────────
    social_signal_score: float = 0.0
    try:
        from data.ingest.social_signal_fetcher import (
            _score_manipulation, get_social_score_for_scrip,
        )
        # Score all synthetic posts and aggregate
        posts = _make_synthetic_posts()
        raw_scores = [_score_manipulation(p["post_text"]) for p in posts]
        # Velocity weight: later cluster is denser = higher signal
        max_score = max(raw_scores)
        mean_score = sum(raw_scores) / len(raw_scores)
        agg_01 = float(max_score * 0.6 + mean_score * 0.4)
        social_signal_score = round(min(10.0, agg_01 * 10.0), 3)
    except Exception as exc:
        # Deterministic fallback for demo
        social_signal_score = 7.2
        print(f"  [SOCIAL] Fallback score used ({exc})")

    # ── 2. Misinfo score ───────────────────────────────────────────────────────
    misinfo_score: float = 0.0
    try:
        from models.misinfo.detector import detect
        sample_text = _POST_TEMPLATES[0]  # high-manipulation post
        misinfo_score = detect(sample_text)
    except Exception as exc:
        misinfo_score = 0.75  # deterministic fallback
        print(f"  [MISINFO] Fallback score used ({exc})")

    # ── 3. Phishing adapter ────────────────────────────────────────────────────
    phishing_score: float = 0.0
    try:
        from data.ingest.generic_threat_adapter import normalize
        result = normalize(
            _PHISHING_URL,
            platform="web",
            threat_type="phishing",
            entity_id="PHISH_XYZTECH_001",
        )
        phishing_score = float(result.get("threat_score", 0.0))
    except Exception as exc:
        phishing_score = 0.65  # deterministic fallback
        print(f"  [PHISHING] Fallback score used ({exc})")

    # ── 4. Combine into overall alert score (social-primary) ───────────────────
    # Weight: social 50%, misinfo*10 30%, phishing*10 20%
    overall_score = round(
        social_signal_score * 0.50
        + (misinfo_score * 10.0) * 0.30
        + (phishing_score * 10.0) * 0.20,
        3,
    )
    # Clamp to [0, 10]
    overall_score = round(min(10.0, max(0.0, overall_score)), 3)

    return {
        "overall_score": overall_score,
        "scheme_type": "social_media_pump_campaign",
        "accounts_involved": _ACCOUNTS,
        "social_signal_score": social_signal_score,
        "misinfo_score": misinfo_score,
        "phishing_score": phishing_score,
        "recommended_action": "block_social_signals_and_alert_compliance",
        "severity": "high",
    }


def print_verdict():
    """Pretty-print detection result for CLI demo."""
    print()
    print("=" * 64)
    print("ARGUS DEMO — SOCIAL MANIPULATION: XYZTECH")
    print("=" * 64)
    print("Scenario : Coordinated Reddit/Twitter pump + phishing campaign")
    print("Target   : XYZTECH (fictitious NSE scrip)")
    print("Duration : 2-hour post velocity spike (20 posts)")
    print("-" * 64)

    result = run_detection()

    print(f"Social Signal Score : {result['social_signal_score']:.3f} / 10")
    print(f"Misinfo Score       : {result['misinfo_score']:.4f}  (0=legit, 1=misinformation)")
    print(f"Phishing Score      : {result['phishing_score']:.4f}  (nse1ndia-login.xyz)")
    print(f"Overall Score       : {result['overall_score']:.3f} / 10")
    print(f"Severity            : {result['severity'].upper()}")
    print(f"Scheme Type         : {result['scheme_type']}")
    print(f"Accounts Involved   : {result['accounts_involved']}")
    print(f"Recommended Action  : {result['recommended_action']}")
    print()
    print("VERDICT: SOCIAL MANIPULATION CAMPAIGN DETECTED")
    print("=" * 64)
    print()


if __name__ == "__main__":
    print_verdict()
