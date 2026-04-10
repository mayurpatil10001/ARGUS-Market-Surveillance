"""
data/ingest/sebi_scraper.py — SEBI enforcement orders scraper and PDF parser.
"""
from __future__ import annotations

import io
import re
import time
from datetime import date
from typing import Optional

import requests
from bs4 import BeautifulSoup

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore

SEBI_BASE = "https://www.sebi.gov.in"
ORDERS_URL = f"{SEBI_BASE}/enforcement/orders.html"

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (research@argus.ai)",
    "Accept": "text/html,application/xhtml+xml",
})

SCHEME_KEYWORDS: dict[str, list[str]] = {
    "pump_and_dump": ["pump", "dump", "price rigging", "artificial inflation"],
    "spoofing": ["spoofing", "layering", "phantom orders", "cancel"],
    "circular_trading": ["circular", "synchronized", "wash trade", "reversal"],
    "insider_trading": ["insider", "unpublished price sensitive", "upsi"],
}


def _classify_scheme(text: str) -> str:
    text_lower = text.lower()
    for scheme, keywords in SCHEME_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return scheme
    return "other"


def _extract_dates_from_text(text: str) -> tuple[Optional[str], Optional[str]]:
    pattern = r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b"
    matches = re.findall(pattern, text)
    if len(matches) >= 2:
        return matches[0], matches[-1]
    elif len(matches) == 1:
        return matches[0], matches[0]
    return None, None


def scrape_enforcement_orders(max_pages: int = 50) -> list[dict]:
    """
    Scrapes SEBI enforcement orders page. Parses: date, entity_name, order_type, pdf_url.
    Handles pagination via query params or page links.
    """
    orders: list[dict] = []
    page_url = ORDERS_URL

    for page_num in range(max_pages):
        try:
            resp = _SESSION.get(page_url, timeout=30)
            resp.raise_for_status()
        except Exception:
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try common table structures on SEBI enforcement pages
        tables = soup.find_all("table")
        found_any = False
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) < 3:
                    continue
                date_txt = cols[0].get_text(strip=True)
                entity_txt = cols[1].get_text(strip=True)
                order_type_txt = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                link_tag = row.find("a", href=True)
                pdf_url = ""
                if link_tag:
                    href = link_tag["href"]
                    pdf_url = href if href.startswith("http") else f"{SEBI_BASE}{href}"
                if entity_txt:
                    orders.append({
                        "date": date_txt,
                        "entity_name": entity_txt,
                        "order_type": order_type_txt,
                        "pdf_url": pdf_url,
                    })
                    found_any = True

        # Try to find "next page" link
        next_link = soup.find("a", string=re.compile(r"next|›|»", re.I))
        if next_link and next_link.get("href"):
            href = next_link["href"]
            page_url = href if href.startswith("http") else f"{SEBI_BASE}{href}"
        else:
            # Try page number parameters
            next_page_url = f"{ORDERS_URL}?page={page_num + 2}"
            page_url = next_page_url

        if not found_any and page_num > 0:
            break

        time.sleep(1.0)  # polite crawl delay

    return orders


def parse_order_pdf(pdf_url: str) -> dict:
    """
    Downloads a SEBI order PDF and extracts structured information.
    Returns: accused_entities, scrips_mentioned, from_date, to_date,
             order_type, scheme_type.
    """
    if pdfplumber is None:
        return {"error": "pdfplumber not installed"}

    try:
        resp = _SESSION.get(pdf_url, timeout=60)
        resp.raise_for_status()
    except Exception as exc:
        return {"error": str(exc), "pdf_url": pdf_url}

    try:
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            full_text = "\n".join(
                page.extract_text() or "" for page in pdf.pages[:20]
            )
    except Exception as exc:
        return {"error": f"PDF parse error: {exc}", "pdf_url": pdf_url}

    # Extract accused entities (names in ALL CAPS or after "M/s" / "Shri")
    entity_patterns = [
        r"M/s\s+([A-Z][A-Za-z\s&\.]+?)(?:\s*,|\s*\n)",
        r"Shri\s+([A-Z][A-Za-z\s]+?)(?:\s*,|\s*\n)",
        r"\bnoticee[s]?\s+([A-Z][A-Z\s&\.]+?)(?:\s*,|\s*\.)",
    ]
    accused: list[str] = []
    for pat in entity_patterns:
        accused.extend(re.findall(pat, full_text))
    accused = list(dict.fromkeys([a.strip() for a in accused if len(a.strip()) > 3])[:10])

    # Extract scrips (typically in format SCRIP / equity or stock names)
    scrip_pattern = r"\b([A-Z]{2,12}(?:LTD|LIMITED|IND|INDUSTRIES)?)\b"
    scrips = list(
        dict.fromkeys([
            s for s in re.findall(scrip_pattern, full_text)
            if len(s) >= 3 and s not in {"SEBI", "NSE", "BSE", "THE", "AND", "FOR", "OF"}
        ])[:10]
    )

    from_date_str, to_date_str = _extract_dates_from_text(full_text)
    scheme = _classify_scheme(full_text)
    order_type_match = re.search(r"(adjudication|consent|settlement|show cause|interim)", full_text, re.I)
    order_type = order_type_match.group(1).lower() if order_type_match else "enforcement"

    return {
        "accused_entities": accused,
        "scrips_mentioned": scrips,
        "from_date": from_date_str,
        "to_date": to_date_str,
        "order_type": order_type,
        "scheme_type": scheme,
        "pdf_url": pdf_url,
    }


def load_known_fraudsters_to_db(session) -> int:
    """
    Scrapes SEBI orders, parses PDFs, inserts KnownFraudster records.
    Skips duplicates by sebi_order_ref. Returns count of new records inserted.
    """
    from data.db.crud import upsert_known_fraudster
    from datetime import datetime

    orders = scrape_enforcement_orders(max_pages=5)
    inserted = 0
    for order in orders:
        if not order.get("pdf_url"):
            continue
        parsed = parse_order_pdf(order["pdf_url"])
        if "error" in parsed:
            continue
        try:
            conviction_date = datetime.strptime(order["date"], "%d %b %Y").date()
        except Exception:
            conviction_date = date.today()

        for entity in parsed.get("accused_entities", [order["entity_name"]]):
            upsert_known_fraudster(
                session,
                entity_name=entity,
                sebi_order_ref=order["pdf_url"],
                scheme_type=parsed.get("scheme_type", "other"),
                scrips_involved=parsed.get("scrips_mentioned", []),
                conviction_date=conviction_date,
                source_url=order["pdf_url"],
            )
            inserted += 1
    return inserted
