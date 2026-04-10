"""
data/ingest/bse_fetcher.py — BSE bhavcopy and announcements fetcher.
"""
from __future__ import annotations

import io
import time
import zipfile
from datetime import date, timedelta

import pandas as pd
import requests

BSE_ARCHIVE_BASE = "https://www.bseindia.com"

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (research@argus.ai)",
    "Referer": "https://www.bseindia.com/",
    "Accept": "*/*",
})


def _get_with_retry(url: str, max_retries: int = 3) -> requests.Response:
    delay = 2.0
    for attempt in range(max_retries):
        try:
            resp = _SESSION.get(url, timeout=30)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            if attempt == max_retries - 1:
                raise RuntimeError(f"BSE fetch failed after retries: {exc}") from exc
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("Exhausted retries")


def fetch_bhavcopy(dt: date) -> pd.DataFrame:
    """
    Downloads BSE equity bhavcopy CSV for the given date.
    Returns DataFrame with standardized columns.
    """
    yyyy = dt.strftime("%Y")
    mm = dt.strftime("%m")
    dd = dt.strftime("%d")
    # BSE equity bhavcopy URL pattern
    url = f"{BSE_ARCHIVE_BASE}/download/BhavCopy/Equity/EQ{dd}{mm}{yyyy}_CSV.ZIP"
    try:
        resp = _get_with_retry(url)
    except RuntimeError:
        # Try alternate URL pattern
        url_alt = f"{BSE_ARCHIVE_BASE}/bseplus/StockReach/AdvanceDeclineData/BSEData/{dt.strftime('%Y%m%d')}.csv"
        try:
            resp = _get_with_retry(url_alt)
            df = pd.read_csv(io.StringIO(resp.text))
            df["timestamp"] = pd.Timestamp(dt)
            return df.reset_index(drop=True)
        except RuntimeError:
            return pd.DataFrame()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        csv_names = [n for n in z.namelist() if n.upper().endswith(".CSV")]
        if not csv_names:
            return pd.DataFrame()
        with z.open(csv_names[0]) as f:
            df = pd.read_csv(f)

    df.columns = df.columns.str.strip().str.lower()
    rename_map = {
        "sc_code": "symbol",
        "sc_name": "name",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "no_of_shrs": "volume",
        "net_turnov": "turnover",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    df["timestamp"] = pd.Timestamp(dt)
    df["exchange"] = "BSE"
    return df.reset_index(drop=True)


def fetch_historical_range(from_date: date, to_date: date) -> pd.DataFrame:
    """
    Fetches BSE bhavcopy data for each trading day in range.
    """
    frames: list[pd.DataFrame] = []
    current = from_date
    while current <= to_date:
        if current.weekday() < 5:
            try:
                df = fetch_bhavcopy(current)
                if not df.empty:
                    frames.append(df)
            except Exception:
                pass
        current += timedelta(days=1)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def fetch_corporate_announcements(scrip: str, days_back: int = 30) -> pd.DataFrame:
    """
    Fetches BSE corporate announcements for a given scrip.
    Returns DataFrame with: scrip, date, headline, category.
    """
    url = (
        f"{BSE_ARCHIVE_BASE}/corporates/ann.aspx?scrip={scrip}"
        f"&type=8&subcategory=-1"
    )
    try:
        resp = _get_with_retry(url)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = []
        for tr in soup.select("table tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) >= 3:
                rows.append({
                    "scrip": scrip,
                    "date": tds[0].get_text(strip=True),
                    "headline": tds[1].get_text(strip=True),
                    "category": tds[2].get_text(strip=True) if len(tds) > 2 else "",
                })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["scrip", "date", "headline", "category"])
