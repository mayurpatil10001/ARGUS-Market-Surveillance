"""
demo/ps402_demo.py — Standalone PS-402 ingestion layer demo harness.
No HTTP server required — calls modules directly.

Run with:
    python demo/ps402_demo.py
"""
from __future__ import annotations

import os
import sys

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Bootstrap SQLite DB tables before importing ingestors
from data.db.session import engine  # noqa: E402
from data.db.models import Base     # noqa: E402
Base.metadata.create_all(engine)


from data.ingest.url_social_ingestor import ingest_url, ingest_social_post, ingest_batch  # noqa: E402

PASS = 0
FAIL = 0
TOTAL = 5


def _check(scenario: int, label: str, result: dict, *assertions):
    global PASS, FAIL
    try:
        for assertion_fn, msg in assertions:
            assert assertion_fn(result), f"{msg}  →  got: {result}"
        status = "PASS"
        PASS += 1
    except AssertionError as exc:
        status = "FAIL"
        FAIL += 1
        print(f"    ASSERTION ERROR: {exc}")
    print(f"  Scenario {scenario}: [{status}]  {label}")
    return result


print("=" * 60)
print("PS-402 INGESTION DEMO HARNESS")
print("=" * 60)
print()

# ── Scenario 1: Phishing URL targeting NSE ────────────────────────────────────
print("Scenario 1 — Phishing URL targeting NSE")
url_s1 = "http://nseindia-secure-login.xyz/verify?token=abc123&pan=ABCDE1234F"
r1 = ingest_url(url=url_s1, platform="web")
print(f"  Result: {r1}")
_check(
    1, "Phishing URL → threat_score >= 0.5", r1,
    (lambda r: "signal_id" in r,          "signal_id key missing"),
    (lambda r: r.get("threat_score", 0) >= 0.5, "threat_score < 0.5"),
)

print()

# ── Scenario 2: Reddit pump post (RELIANCE) ───────────────────────────────────
print("Scenario 2 — Reddit pump post (RELIANCE mentioned)")
text_s2 = "RELIANCE is going to 10x guaranteed!! Operator loading, buy now before circuit!!"
r2 = ingest_social_post(
    text=text_s2,
    platform="reddit",
    source_meta={"velocity_per_hour": 340, "likes": 8200},
)
print(f"  Result: {r2}")
_check(
    2, "Reddit pump → combined_score >= 0.5, RELIANCE in scrips", r2,
    (lambda r: r.get("combined_score", 0) >= 0.5,     "combined_score < 0.5"),
    (lambda r: "RELIANCE" in r.get("scrips_mentioned", []), "RELIANCE not in scrips_mentioned"),
)

print()

# ── Scenario 3: WhatsApp fake SEBI circular ───────────────────────────────────
print("Scenario 3 — WhatsApp fake SEBI circular (TATAMOTORS)")
text_s3 = (
    "SEBI has approved a special buyback for TATAMOTORS at Rs 1200. "
    "Invest before 5pm today. Forward to all groups."
)
r3 = ingest_social_post(text=text_s3, platform="whatsapp")
print(f"  Result: {r3}")
_check(
    3, "WhatsApp SEBI fake → misinfo_score >= 0.4", r3,
    (lambda r: r.get("misinfo_score", 0) >= 0.4, "misinfo_score < 0.4"),
)

print()

# ── Scenario 4: Telegram phishing link about HDFC ────────────────────────────
print("Scenario 4 — Telegram phishing link (HDFC KYC)")
url_s4 = "https://hdfcbank-kyc-update.top/login?ref=sebi_notice"
r4 = ingest_url(url=url_s4, platform="telegram")
print(f"  Result: {r4}")
_check(
    4, "Telegram phish URL → threat_score >= 0.5", r4,
    (lambda r: r.get("threat_score", 0) >= 0.5,  "threat_score < 0.5"),
    (lambda r: "signal_id" in r,                  "signal_id key missing"),
)
print(f"  is_market_moving: {r4.get('is_market_moving')}")

print()

# ── Scenario 5: Batch ingest — 3 mixed records ───────────────────────────────
print("Scenario 5 — Batch ingest (1 URL + 2 social posts, different scrips)")
batch_records = [
    {
        "type": "url",
        "url": "http://zerodha-login-secure.xyz/verify",
        "platform": "web",
    },
    {
        "type": "social",
        "text": "HDFCBANK going to 3000! Insider call confirmed. Load up now!! buy circuit",
        "platform": "twitter",
        "source_meta": {"velocity_per_hour": 120, "likes": 3400},
    },
    {
        "type": "social",
        "text": "SBIN promoter buying heavily. SEBI approved special dividend. Get in now!",
        "platform": "reddit",
        "source_meta": {"velocity_per_hour": 55, "likes": 900},
    },
]
r5 = ingest_batch(batch_records)
print(f"  Results ({len(r5)} items):")
for i, item in enumerate(r5):
    print(f"    [{i}] signal_id={item.get('signal_id','ERR')}  "
          f"score={item.get('threat_score', item.get('combined_score','?'))}")
_check(
    5, "Batch → 3 results, each has signal_id", {"results": r5},
    (lambda r: len(r["results"]) == 3,                        "len(results) != 3"),
    (lambda r: all("signal_id" in x for x in r["results"]),  "some result missing signal_id"),
)

print()
print("=" * 60)
print(f"Demo results: {PASS}/{TOTAL} PASS  |  {TOTAL - PASS}/{TOTAL} FAIL")
print("=" * 60)

if FAIL > 0:
    sys.exit(1)
