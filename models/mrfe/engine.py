"""
models/mrfe/engine.py — Market Reaction Fingerprint Engine (MRFE).

Accepts text, PDF, and document inputs. Detects financial event type,
extracts affected NSE/BSE scrips, scores misinfo + social manipulation +
threat risk (heuristic scores, not validated accuracy percentages).
Returns structured analysis dict with recommended enforcement action.
"""
from __future__ import annotations

import io
import logging
import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── NSE/BSE scrip list (top 50 NIFTY/BSE500 symbols) ────────────────────────
_KNOWN_SCRIPS: list[str] = [
    "RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK", "SBIN", "TATAMOTORS",
    "WIPRO", "AXISBANK", "KOTAKBANK", "BAJFINANCE", "HCLTECH", "ASIANPAINT",
    "MARUTI", "SUNPHARMA", "ULTRACEMCO", "TITAN", "NESTLEIND", "POWERGRID",
    "NTPC", "ONGC", "COALINDIA", "GRASIM", "JSWSTEEL", "TATASTEEL",
    "HINDALCO", "ADANIENT", "ADANIPORTS", "DMART", "LT", "TECHM",
    "HDFCBANK", "BAJAJFINSV", "INDUSINDBK", "DIVISLAB", "CIPLA", "DRREDDY",
    "EICHERMOT", "HEROMOTOCO", "BRITANNIA", "SHREECEM", "UPL", "SBILIFE",
    "BPCL", "IOC", "HINDUNILVR", "M_M", "TATACONSUM", "APOLLOHOSP",
    # Fictitious scrips used in ARGUS/SENTINEL demos
    "XYZLTD", "ABCIND", "DEFCORP", "GHITECH", "XYZTECH",
]

# ── Event classification keyword map ─────────────────────────────────────────
_EVENT_KEYWORDS: list[tuple[list[str], str]] = [
    (["rate", "rbi", "repo", "monetary", "interest rate", "policy rate"],
     "central_bank_policy"),
    (["earnings", "profit", "loss", "revenue", "quarterly", "results", "eps", "q1", "q2", "q3", "q4"],
     "earnings_announcement"),
    (["merger", "acquisition", "takeover", "buyout", "amalgamation", "m&a"],
     "merger_acquisition"),
    (["sebi", "penalty", "fraud", "manipulation", "investigation", "enforcement", "order", "violation"],
     "regulatory_action"),
    (["ipo", "listing", "offer", "issue price", "open offer", "subscription"],
     "ipo_listing"),
    (["dividend", "bonus", "split", "buyback", "rights issue"],
     "corporate_action"),
    (["phishing", "hack", "breach", "credential", "malware", "ransomware", "data theft"],
     "cyber_threat"),
    (["fake", "false", "rumour", "unverified", "hoax", "misinformation", "fabricated"],
     "misinformation"),
]

# ── High-risk keywords for evidence extraction ────────────────────────────────
_HIGH_RISK_KEYWORDS: list[str] = [
    "pump", "circuit", "operator", "guaranteed", "moon", "multibagger",
    "insider", "sebi", "penalty", "fraud", "manipulation", "phishing",
    "fake", "rumour", "breach", "hack", "guaranteed profit", "100x",
]

# ── Impact → action mapping ───────────────────────────────────────────────────
_IMPACT_ACTION: dict[str, str] = {
    "critical": "freeze_accounts_and_escalate_sebi",
    "high":     "flag_content_and_notify_exchange",
    "medium":   "monitor_and_log",
    "low":      "log_only",
}


class MRFEEngine:
    """
    Market Reaction Fingerprint Engine.
    All scores are heuristic estimates — not validated accuracy percentages.
    """

    # ── Text analysis ─────────────────────────────────────────────────────────

    def analyze_text(self, text: str) -> dict:
        """
        Analyze text for financial threats, event classification, and
        affected scrips. Returns full analysis dict.

        Scores are heuristic estimates derived from keyword matching and
        existing ARGUS detection modules.
        """
        t0 = time.monotonic()

        if not text or not text.strip():
            return self._empty_result("empty input", t0)

        text_clean = text.strip()

        # ── Sub-scores ────────────────────────────────────────────────────────

        # 1. Misinfo heuristic score from existing TF-IDF+LR classifier
        misinfo_score = self._get_misinfo_score(text_clean)

        # 2. Social manipulation heuristic score
        social_score = self._get_social_score(text_clean)

        # 3. Threat adapter heuristic score
        threat_adapter_score = self._get_threat_adapter_score(text_clean)

        # ── Composite threat score ────────────────────────────────────────────
        threat_score = round(
            misinfo_score * 0.40 + social_score * 0.30 + threat_adapter_score * 0.30,
            4,
        )
        threat_score = max(0.0, min(1.0, threat_score))

        # ── Derived fields ────────────────────────────────────────────────────
        market_impact = self._assign_impact(threat_score)
        event_type = self._classify_event(text_clean)
        affected_scrips = self._extract_scrips(text_clean)
        evidence_snippets = self._extract_evidence(text_clean, affected_scrips)
        recommended_action = _IMPACT_ACTION[market_impact]
        confidence = self._estimate_confidence(misinfo_score, social_score, threat_adapter_score)

        processing_time_ms = round((time.monotonic() - t0) * 1000, 2)

        return {
            "event_type": event_type,
            "threat_score": threat_score,
            "misinfo_score": misinfo_score,
            "social_score": social_score,
            "threat_adapter_score": threat_adapter_score,
            "market_impact": market_impact,
            "affected_scrips": affected_scrips,
            "recommended_action": recommended_action,
            "confidence": confidence,
            "evidence_snippets": evidence_snippets,
            "processing_time_ms": processing_time_ms,
            "synthetic_data": False,
            "analyzed_at": datetime.now(tz=timezone.utc).isoformat(),
            "note": "All scores are heuristic estimates from ARGUS detection modules.",
        }

    # ── PDF analysis ──────────────────────────────────────────────────────────

    def analyze_pdf(self, file_bytes: bytes) -> dict:
        """Extract text from PDF and run analyze_text. Requires pdfplumber."""
        try:
            import pdfplumber
        except ImportError:
            return {
                "error": "pdfplumber not installed",
                "threat_score": 0.0,
                "misinfo_score": 0.0,
                "market_impact": "low",
                "affected_scrips": [],
                "recommended_action": "log_only",
                "confidence": 0.0,
                "evidence_snippets": [],
                "event_type": "unknown",
                "processing_time_ms": 0.0,
                "pdf_pages": 0,
                "pdf_word_count": 0,
                "synthetic_data": False,
            }

        t0 = time.monotonic()
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = pdf.pages
                page_count = len(pages)
                full_text = " ".join(page.extract_text() or "" for page in pages)
        except Exception as exc:
            logger.warning(f"MRFEEngine.analyze_pdf: PDF parse failed: {exc}")
            full_text = file_bytes.decode("utf-8", errors="ignore")
            page_count = 1

        word_count = len(full_text.split())
        result = self.analyze_text(full_text)
        result["pdf_pages"] = page_count
        result["pdf_word_count"] = word_count
        result["processing_time_ms"] = round((time.monotonic() - t0) * 1000, 2)
        return result

    # ── Document dispatch ─────────────────────────────────────────────────────

    def analyze_document(self, file_bytes: bytes, filename: str) -> dict:
        """
        Dispatch by file extension to appropriate analyzer.
        Supports: .pdf, .txt, .csv, .docx (docx requires python-docx, optional).
        """
        fname = filename.lower()

        if fname.endswith(".pdf"):
            result = self.analyze_pdf(file_bytes)
            file_type = "pdf"

        elif fname.endswith((".txt", ".csv")):
            text = file_bytes.decode("utf-8", errors="ignore")
            result = self.analyze_text(text)
            file_type = "txt" if fname.endswith(".txt") else "csv"

        elif fname.endswith(".docx"):
            text = self._extract_docx_text(file_bytes)
            result = self.analyze_text(text)
            file_type = "docx"

        else:
            # Fallback: attempt utf-8 decode
            text = file_bytes.decode("utf-8", errors="ignore")
            result = self.analyze_text(text)
            file_type = "unknown"

        result["filename"] = filename
        result["file_type"] = file_type
        return result

    # ── Historical context (synthetic fallback) ───────────────────────────────

    def fetch_historical_context(self, scrips: list[str]) -> dict:
        """
        Attempt to fetch last-30-day NSE data for each scrip (max 5).
        Falls back to synthetic random-walk OHLCV data if NSE fetch fails.
        Synthetic data is clearly labeled synthetic_data=True.
        """
        results: dict = {}
        for scrip in scrips[:5]:
            try:
                ctx = self._fetch_nse_data(scrip)
            except Exception:
                ctx = self._synthetic_ohlcv(scrip)
            results[scrip] = ctx
        return results

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_misinfo_score(self, text: str) -> float:
        try:
            from models.misinfo.detector import detect
            return float(detect(text))
        except Exception as exc:
            logger.debug(f"MRFE misinfo fallback: {exc}")
            return self._heuristic_misinfo_score(text)

    def _heuristic_misinfo_score(self, text: str) -> float:
        """Keyword-based misinfo estimate when model unavailable."""
        bad = ["fake", "false", "unverified", "hoax", "rumour", "fabricated",
               "guaranteed profit", "operator", "insider tip", "no risk", "risk free"]
        text_lower = text.lower()
        hits = sum(1 for kw in bad if kw in text_lower)
        return round(min(1.0, hits / 4.0), 4)

    def _get_social_score(self, text: str) -> float:
        try:
            from data.ingest.social_signal_fetcher import _score_manipulation
            return float(_score_manipulation(text))
        except Exception as exc:
            logger.debug(f"MRFE social_score fallback: {exc}")
            return 0.0

    def _get_threat_adapter_score(self, text: str) -> float:
        try:
            from data.ingest.generic_threat_adapter import normalize
            result = normalize(text, platform="mrfe_input")
            return float(result.get("threat_score", 0.0))
        except Exception as exc:
            logger.debug(f"MRFE threat_adapter fallback: {exc}")
            return 0.0

    def _classify_event(self, text: str) -> str:
        text_lower = text.lower()
        for keywords, event_type in _EVENT_KEYWORDS:
            if any(kw in text_lower for kw in keywords):
                return event_type
        return "market_news"

    def _extract_scrips(self, text: str) -> list[str]:
        text_upper = text.upper()
        found = []
        for scrip in _KNOWN_SCRIPS:
            pattern = r"\b" + re.escape(scrip) + r"\b"
            if re.search(pattern, text_upper):
                found.append(scrip)
        return list(dict.fromkeys(found))  # deduplicate preserving order

    def _extract_evidence(self, text: str, scrips: list[str]) -> list[str]:
        """Extract up to 5 sentences containing scrip names or high-risk keywords."""
        sentences = re.split(r"[.!?\n]+", text)
        evidence = []
        all_triggers = [s.upper() for s in scrips] + [k.lower() for k in _HIGH_RISK_KEYWORDS]

        for sent in sentences:
            sent_stripped = sent.strip()
            if not sent_stripped or len(sent_stripped) < 10:
                continue
            sent_up = sent_stripped.upper()
            sent_lo = sent_stripped.lower()
            if any(t in sent_up or t in sent_lo for t in all_triggers):
                evidence.append(sent_stripped[:300])
            if len(evidence) >= 5:
                break
        return evidence

    def _assign_impact(self, threat_score: float) -> str:
        if threat_score >= 0.75:
            return "critical"
        if threat_score >= 0.50:
            return "high"
        if threat_score >= 0.25:
            return "medium"
        return "low"

    def _estimate_confidence(
        self, misinfo: float, social: float, threat: float
    ) -> float:
        """
        Estimate engine confidence based on score agreement.
        Higher when all three sub-scores agree (all high or all low).
        This is a heuristic estimate, not a validated accuracy metric.
        """
        scores = [misinfo, social, threat]
        mean = sum(scores) / 3
        variance = sum((s - mean) ** 2 for s in scores) / 3
        # Low variance = high agreement = higher confidence
        confidence = 1.0 - min(1.0, variance * 4)
        return round(max(0.1, min(1.0, confidence)), 4)

    def _extract_docx_text(self, file_bytes: bytes) -> str:
        """Extract text from .docx using python-docx (optional). Falls back to raw bytes."""
        try:
            import docx  # python-docx
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join(para.text for para in doc.paragraphs)
        except ImportError:
            logger.debug("python-docx not installed, falling back to raw decode for .docx")
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.warning(f"MRFE docx extract failed: {exc}")
            return file_bytes.decode("utf-8", errors="ignore")

    def _fetch_nse_data(self, scrip: str) -> dict:
        """Try NSE fetcher for last-30-day bhavcopy data."""
        from data.ingest.nse_fetcher import NSEFetcher
        fetcher = NSEFetcher()
        today = datetime.now()
        dfs = []
        for days_ago in range(30, 0, -5):
            dt = today - timedelta(days=days_ago)
            try:
                df = fetcher.fetch_bhavcopy(dt.date())
                if df is not None and not df.empty:
                    scrip_row = df[df["SYMBOL"] == scrip]
                    if not scrip_row.empty:
                        dfs.append(float(scrip_row.iloc[0].get("CLOSE", 0)))
            except Exception:
                pass

        if len(dfs) < 3:
            raise ValueError("insufficient NSE data")

        dates = [(today - timedelta(days=30 - i * 5)).strftime("%Y-%m-%d")
                 for i in range(len(dfs))]
        pct_chg = round((dfs[-1] - dfs[0]) / dfs[0] * 100, 2) if dfs[0] else 0.0
        return {
            "prices": dfs,
            "dates": dates,
            "avg_volume": 0.0,
            "price_change_30d_pct": pct_chg,
            "synthetic_data": False,
        }

    def _synthetic_ohlcv(self, scrip: str) -> dict:
        """Generate synthetic 30-day random-walk price series as fallback."""
        rng = random.Random(hash(scrip) % (2**31))
        base = rng.uniform(100, 5000)
        prices = [round(base, 2)]
        for _ in range(29):
            delta = prices[-1] * rng.gauss(0, 0.02)
            prices.append(round(max(1.0, prices[-1] + delta), 2))
        today = datetime.now()
        dates = [(today - timedelta(days=29 - i)).strftime("%Y-%m-%d") for i in range(30)]
        avg_vol = round(rng.uniform(500_000, 5_000_000), 0)
        pct_chg = round((prices[-1] - prices[0]) / prices[0] * 100, 2)
        return {
            "prices": prices,
            "dates": dates,
            "avg_volume": avg_vol,
            "price_change_30d_pct": pct_chg,
            "synthetic_data": True,
        }

    def _empty_result(self, reason: str, t0: float) -> dict:
        return {
            "event_type": "unknown",
            "threat_score": 0.0,
            "misinfo_score": 0.0,
            "social_score": 0.0,
            "threat_adapter_score": 0.0,
            "market_impact": "low",
            "affected_scrips": [],
            "recommended_action": "log_only",
            "confidence": 0.0,
            "evidence_snippets": [],
            "processing_time_ms": round((time.monotonic() - t0) * 1000, 2),
            "synthetic_data": False,
            "analyzed_at": datetime.now(tz=timezone.utc).isoformat(),
            "note": f"Empty result: {reason}",
        }
