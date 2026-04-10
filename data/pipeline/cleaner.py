"""
data/pipeline/cleaner.py — Trade data cleaning and normalization utilities.
"""
from __future__ import annotations

import hashlib
from datetime import timezone

import numpy as np
import pandas as pd


def clean_nse_trades(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize NSE trade data:
    - Normalize column names
    - Parse timestamps to UTC-aware datetimes
    - Remove auction trades (typically flagged by 'series' != 'EQ')
    - Remove duplicates
    - Validate price > 0, volume > 0
    - Fill missing exchange with 'NSE'
    """
    df = raw_df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Column normalization
    rename_candidates = {
        "tottrdqty": "volume",
        "totaltrdqty": "volume",
        "qty": "volume",
        "quantity": "volume",
        "trd_dt": "timestamp",
        "tradedate": "timestamp",
        "dt": "timestamp",
        "clsprc": "close",
        "closeprice": "close",
        "last": "close",
        "sym": "symbol",
        "scripname": "symbol",
        "tradesymbol": "symbol",
        "account": "account_id",
        "client": "account_id",
        "clientcode": "account_id",
        "tradeprice": "price",
        "tradeval": "price",
    }
    df = df.rename(columns={k: v for k, v in rename_candidates.items() if k in df.columns})

    # Parse timestamps to UTC
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], dayfirst=True, errors="coerce", utc=True)
    else:
        df["timestamp"] = pd.Timestamp.utcnow()

    # Remove auction trades: series != 'EQ'
    if "series" in df.columns:
        df = df[df["series"].str.strip().str.upper() == "EQ"]

    # Remove duplicates
    dup_cols = [c for c in ["account_id", "symbol", "timestamp", "price", "volume"] if c in df.columns]
    if dup_cols:
        df = df.drop_duplicates(subset=dup_cols)

    # Validate price and volume
    if "price" in df.columns:
        df = df[pd.to_numeric(df["price"], errors="coerce").fillna(0) > 0]
    if "volume" in df.columns:
        df = df[pd.to_numeric(df["volume"], errors="coerce").fillna(0) > 0]

    # Fill missing exchange
    if "exchange" not in df.columns:
        df["exchange"] = "NSE"
    else:
        df["exchange"] = df["exchange"].fillna("NSE")

    # Ensure price/volume are float
    for col in ["price", "volume", "open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.reset_index(drop=True)


def normalize_account_id(broker_code: str, client_id: str) -> str:
    """
    Returns a 16-char anonymized but consistent account ID.
    Uses SHA-256 of 'broker_code:client_id'.
    """
    raw = f"{broker_code}:{client_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def label_trades_with_sebi_cases(
    trades_df: pd.DataFrame,
    cases: list[dict],
) -> pd.DataFrame:
    """
    Adds boolean column 'is_manipulated' to trades_df by matching scrip + date range
    against known SEBI enforcement cases.

    cases: list of dicts with keys: scrips_involved (list), from_date (str|date), to_date (str|date)
    """
    df = trades_df.copy()
    if "is_manipulated" not in df.columns:
        df["is_manipulated"] = False

    if "timestamp" not in df.columns or "symbol" not in df.columns:
        return df

    # Normalize timestamps to date for comparison
    df["_trade_date"] = pd.to_datetime(df["timestamp"]).dt.date

    for case in cases:
        scrips = case.get("scrips_mentioned", case.get("scrips_involved", []))
        from_date_raw = case.get("from_date")
        to_date_raw = case.get("to_date")

        if not scrips:
            continue

        try:
            from_date = pd.to_datetime(from_date_raw).date() if from_date_raw else None
            to_date = pd.to_datetime(to_date_raw).date() if to_date_raw else None
        except Exception:
            continue

        mask = df["symbol"].isin(scrips)
        if from_date:
            mask &= df["_trade_date"] >= from_date
        if to_date:
            mask &= df["_trade_date"] <= to_date

        df.loc[mask, "is_manipulated"] = True

    df = df.drop(columns=["_trade_date"])
    return df
