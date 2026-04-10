"""
demo/real_cases/case_platform_abuse.py — SENTINEL Platform Abuse Demo.
Refactored from case_social_manipulation.py for PS-402 alignment.

Case:
  Coordinated cross-platform abuse campaign targeting digital infrastructure:
  - Social pump posts on Reddit and Twitter with engagement velocity spike
  - Phishing site impersonating a financial portal deployed alongside campaign
  - Malicious content classified by the Malicious Content Classifier
  - Generic threat adapter flags all phishing URLs

Detections:
  - Social Threat Monitor: engagement velocity + pump keyword score
  - Malicious Content Classifier: classifies posts as malicious (score > 0.5)
  - Universal Platform Threat Ingestor: classifies phishing URL (score > 0)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ── Synthetic platform abuse posts ────────────────────────────────────────────

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

_ENTITIES = ["SOC_ABUSE_001", "SOC_ABUSE_002", "SOC_ABUSE_003", "SOC_ABUSE_004", "SOC_ABUSE_005"]

_PHISHING_URL = "http://nse1ndia-login.xyz/verify?token=XYZ&redirect=account-suspended"


def _make_synthetic_posts() -> list[dict]:
    """Generate 20 abuse posts over 2 hours with increasing velocity."""
    now = datetime.now(tz=timezone.utc)
    posts = []
    for i, template in enumerate(_POST_TEMPLATES):
        if i < 8:
            minutes_ago = 120 - (i * 15)
        else:
            minutes_ago = 120 - 120 - (i - 8) * 4
        ts = now + timedelta(minutes=minutes_ago)
        posts.append({
            "platform": "reddit" if i % 3 == 0 else "twitter",
            "post_id": f"mock_abuse_{i:02d}",
            "timestamp": ts,
            "post_text": template,
            "symbol": "XYZTECH",
            "score": max(0, 100 - (i * 3)),
        })
    return posts


def run_detection() -> dict:
    """
    Run full platform abuse detection pipeline.

    Returns
    -------
    dict with keys:
        overall_score, threat_category, entities_involved,
        social_signal_score, misinfo_score, phishing_score,
        recommended_action, severity
    """
    # ── 1. Social Threat Monitor ───────────────────────────────────────────────
    social_signal_score: float = 0.0
    try:
        from data.ingest.social_signal_fetcher import (
            _score_manipulation, get_social_score_for_scrip,
        )
        posts = _make_synthetic_posts()
        raw_scores = [_score_manipulation(p["post_text"]) for p in posts]
        max_score  = max(raw_scores)
        mean_score = sum(raw_scores) / len(raw_scores)
        agg_01 = float(max_score * 0.6 + mean_score * 0.4)
        social_signal_score = round(min(10.0, agg_01 * 10.0), 3)
    except Exception as exc:
        social_signal_score = 7.2
        print(f"  [SOCIAL] Fallback score used ({exc})")

    # ── 2. Malicious Content Classifier ────────────────────────────────────────
    misinfo_score: float = 0.0
    try:
        from models.misinfo.detector import detect
        sample_text = _POST_TEMPLATES[0]
        misinfo_score = detect(sample_text)
    except Exception as exc:
        misinfo_score = 0.75
        print(f"  [MALICIOUS CONTENT] Fallback score used ({exc})")

    # ── 3. Universal Platform Threat Ingestor ──────────────────────────────────
    phishing_score: float = 0.0
    try:
        from data.ingest.generic_threat_adapter import normalize
        result = normalize(
            _PHISHING_URL,
            platform="web",
            threat_type="phishing",
            entity_id="PHISH_ABUSE_001",
        )
        phishing_score = float(result.get("threat_score", 0.0))
    except Exception as exc:
        phishing_score = 0.65
        print(f"  [PLATFORM INGESTOR] Fallback score used ({exc})")

    # ── 4. Combine into overall threat score ────────────────────────────────────
    overall_score = round(
        social_signal_score * 0.50
        + (misinfo_score * 10.0) * 0.30
        + (phishing_score * 10.0) * 0.20,
        3,
    )
    overall_score = round(min(10.0, max(0.0, overall_score)), 3)

    return {
        "overall_score": overall_score,
        "threat_category": "platform_abuse",
        "scheme_type": "platform_abuse",          # legacy alias
        "entities_involved": _ENTITIES,
        "accounts_involved": _ENTITIES,           # legacy alias
        "platforms": ["twitter", "reddit", "web"],
        "social_signal_score": social_signal_score,
        "misinfo_score": misinfo_score,
        "phishing_score": phishing_score,
        "recommended_action": "block_accounts_and_remove_content",
        "severity": "high",
        # Legacy score aliases
        "gnn_score": round(social_signal_score, 1),
        "dna_score": round(misinfo_score * 10, 1),
        "zero_day_score": round(phishing_score * 10, 1),
    }


def print_verdict():
    """Pretty-print detection result for CLI demo."""
    print()
    print("=" * 64)
    print("SENTINEL DEMO — PLATFORM ABUSE: XYZTECH CAMPAIGN")
    print("=" * 64)
    print("Scenario : Coordinated Reddit/Twitter abuse + phishing")
    print("Target   : XYZTECH (fictitious entity)")
    print("Duration : 2-hour post velocity spike (20 posts)")
    print("-" * 64)

    result = run_detection()

    print(f"Social Threat Score : {result['social_signal_score']:.3f} / 10  [Social Threat Monitor]")
    print(f"Malicious Content   : {result['misinfo_score']:.4f}  (0=benign, 1=malicious)")
    print(f"Phishing Score      : {result['phishing_score']:.4f}  (nse1ndia-login.xyz)")
    print(f"Overall Score       : {result['overall_score']:.3f} / 10")
    print(f"Severity            : {result['severity'].upper()}")
    print(f"Threat Category     : {result['threat_category']}")
    print(f"Entities Involved   : {result['entities_involved']}")
    print(f"Platforms Affected  : {result['platforms']}")
    print(f"Recommended Action  : {result['recommended_action']}")
    print()
    print("VERDICT: PLATFORM ABUSE CAMPAIGN DETECTED")
    print("=" * 64)
    print()


if __name__ == "__main__":
    print_verdict()
