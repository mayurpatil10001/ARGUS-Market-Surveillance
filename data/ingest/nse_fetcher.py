"""
data/ingest/nse_fetcher.py — NSE data fetcher with retry and rate limiting.
"""
from __future__ import annotations

import io
import time
import zipfile
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import requests


class DataUnavailableError(Exception):
    """Raised when NSE data is not available for the requested date."""
    pass


NSE_ARCHIVE_BASE = "https://archives.nseindia.com"

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (research@argus.ai)",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "*/*",
    "Connection": "keep-alive",
})


def _get_with_retry(url: str, max_retries: int = 3) -> requests.Response:
    """GET a URL with exponential backoff. Raises DataUnavailableError on 404."""
    delay = 2.0
    for attempt in range(max_retries):
        try:
            resp = _SESSION.get(url, timeout=30)
            if resp.status_code == 404:
                raise DataUnavailableError(f"Data not found at {url}")
            resp.raise_for_status()
            return resp
        except DataUnavailableError:
            raise
        except Exception as exc:
            if attempt == max_retries - 1:
                raise DataUnavailableError(f"Failed after {max_retries} attempts: {exc}") from exc
            time.sleep(delay)
            delay *= 2
    raise DataUnavailableError(f"Exhausted retries for {url}")


def fetch_bhavcopy(dt: date) -> pd.DataFrame:
    """
    Downloads and unzips NSE equity bhavcopy CSV for the given date.
    Returns DataFrame with columns: symbol, open, high, low, close, volume, timestamp.
    """
    mmm = dt.strftime("%b").upper()
    yyyy = dt.strftime("%Y")
    dd = dt.strftime("%d")
    filename = f"cm{dd}{mmm}{yyyy}bhav.csv.zip"
    url = f"{NSE_ARCHIVE_BASE}/content/historical/EQUITIES/{yyyy}/{mmm}/{filename}"

    resp = _get_with_retry(url)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        csv_names = [n for n in z.namelist() if n.endswith(".csv")]
        if not csv_names:
            raise DataUnavailableError(f"No CSV in zip from {url}")
        with z.open(csv_names[0]) as f:
            df = pd.read_csv(f)

    df.columns = df.columns.str.strip().str.lower()
    column_map = {
        "symbol": "symbol",
        "series": "series",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "tottrdqty": "volume",
        "timestamp": "timestamp",
    }
    available = {k: v for k, v in column_map.items() if k in df.columns}
    df = df.rename(columns=available)
    if "timestamp" not in df.columns:
        df["timestamp"] = pd.Timestamp(dt)
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["symbol", "close"])
    df = df[df["series"].str.strip() == "EQ"] if "series" in df.columns else df
    return df[["symbol", "open", "high", "low", "close", "volume", "timestamp"]].reset_index(drop=True)


def fetch_fno_bhavcopy(dt: date) -> pd.DataFrame:
    """
    Downloads NSE F&O bhavcopy CSV for the given date.
    """
    mmm = dt.strftime("%b").upper()
    yyyy = dt.strftime("%Y")
    dd = dt.strftime("%d")
    filename = f"fo{dd}{mmm}{yyyy}bhav.csv.zip"
    url = f"{NSE_ARCHIVE_BASE}/content/historical/DERIVATIVES/{yyyy}/{mmm}/{filename}"

    resp = _get_with_retry(url)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        csv_names = [n for n in z.namelist() if n.endswith(".csv")]
        with z.open(csv_names[0]) as f:
            df = pd.read_csv(f)

    df.columns = df.columns.str.strip().str.lower()
    if "timestamp" not in df.columns:
        df["timestamp"] = pd.Timestamp(dt)
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], dayfirst=True, errors="coerce")

    rename_map = {
        "symbol": "symbol",
        "expiry_dt": "expiry",
        "strike_pr": "strike",
        "option_typ": "option_type",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "contracts": "volume",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df.reset_index(drop=True)


def fetch_bulk_deals(dt: date) -> pd.DataFrame:
    """
    Download NSE bulk deals CSV for the given date.
    """
    url = f"{NSE_ARCHIVE_BASE}/archives/equities/bhavcopy/bulkdeals/bulkdeals_{dt.strftime('%d%m%Y')}.csv"
    try:
        resp = _get_with_retry(url)
        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = df.columns.str.strip().str.lower()
        if "date of acquisition" in df.columns:
            df["timestamp"] = pd.to_datetime(df["date of acquisition"], dayfirst=True, errors="coerce")
        else:
            df["timestamp"] = pd.Timestamp(dt)
        return df.reset_index(drop=True)
    except DataUnavailableError:
        return pd.DataFrame()


def fetch_historical_range(
    from_date: date,
    to_date: date,
    segment: str = "equity",
) -> pd.DataFrame:
    """
    Fetches bhavcopy data for every trading day in [from_date, to_date].
    Skips weekends (Sat/Sun) and dates with no data.
    segment: 'equity' or 'fno'
    """
    frames: list[pd.DataFrame] = []
    current = from_date
    fetcher = fetch_fno_bhavcopy if segment == "fno" else fetch_bhavcopy

    while current <= to_date:
        if current.weekday() < 5:  # Mon–Fri only
            try:
                df = fetcher(current)
                frames.append(df)
            except DataUnavailableError:
                pass
        current += timedelta(days=1)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    result = result.drop_duplicates()
    return result
