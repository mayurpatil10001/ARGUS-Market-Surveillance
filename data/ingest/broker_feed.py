"""
data/ingest/broker_feed.py — Broker feed ingestion via Zerodha Kite Connect.
"""
from __future__ import annotations

import os
import time
import functools
import threading
from datetime import datetime, date
from typing import Callable, Optional, Any

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

try:
    from kiteconnect import KiteConnect, KiteTicker
    KITE_AVAILABLE = True
except ImportError:
    KITE_AVAILABLE = False


class BrokerFeedError(Exception):
    pass


class ZerodhaFeed:
    """
    Real-time and historical trade feed from Zerodha Kite Connect.
    Falls back to simulated feed when API keys are not configured.
    """

    def __init__(self):
        self.api_key = os.getenv("ZERODHA_API_KEY", "")
        self.access_token = os.getenv("ZERODHA_ACCESS_TOKEN", "")
        self._kite: Optional[Any] = None
        self._ticker: Optional[Any] = None
        self._subscribed_tokens: list[int] = []
        self._tick_handlers: list[Callable] = []

    def _get_kite(self):
        if not KITE_AVAILABLE:
            raise BrokerFeedError("kiteconnect not installed")
        if not self.api_key or not self.access_token:
            raise BrokerFeedError("Zerodha API credentials not configured")
        if self._kite is None:
            self._kite = KiteConnect(api_key=self.api_key)
            self._kite.set_access_token(self.access_token)
        return self._kite

    def fetch_historical_trades(
        self,
        instrument_token: int,
        from_date: date,
        to_date: date,
        interval: str = "minute",
    ) -> pd.DataFrame:
        """
        Fetches OHLCV candles from Kite. Falls back to empty DataFrame on error.
        interval: 'minute', '5minute', '15minute', '30minute', '60minute', 'day'
        """
        try:
            kite = self._get_kite()
            data = kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
            )
            df = pd.DataFrame(data)
            if "date" in df.columns:
                df["timestamp"] = pd.to_datetime(df["date"])
                df = df.drop(columns=["date"])
            return df
        except Exception as exc:
            return pd.DataFrame()

    def get_instruments(self, exchange: str = "NSE") -> pd.DataFrame:
        """Fetches master list of instruments for the given exchange."""
        try:
            kite = self._get_kite()
            instruments = kite.instruments(exchange)
            return pd.DataFrame(instruments)
        except Exception:
            return pd.DataFrame()

    def get_quote(self, instruments: list[str]) -> dict:
        """Fetches live quotes for given instruments (e.g., ['NSE:RELIANCE'])."""
        try:
            kite = self._get_kite()
            return kite.quote(instruments)
        except Exception:
            return {}

    def on_tick(self, handler: Callable) -> None:
        """Register a handler to be called on each tick."""
        self._tick_handlers.append(handler)

    def subscribe(self, tokens: list[int]) -> None:
        """Subscribe to live tick stream for given instrument tokens."""
        if not KITE_AVAILABLE:
            return
        self._subscribed_tokens = tokens
        try:
            kite = self._get_kite()
            self._ticker = KiteTicker(self.api_key, self.access_token)

            def _on_ticks(ws, ticks):
                for handler in self._tick_handlers:
                    for tick in ticks:
                        handler(tick)

            def _on_connect(ws, response):
                ws.subscribe(tokens)
                ws.set_mode(ws.MODE_FULL, tokens)

            self._ticker.on_ticks = _on_ticks
            self._ticker.on_connect = _on_connect
            t = threading.Thread(target=self._ticker.connect, daemon=True)
            t.start()
        except Exception:
            pass

    def stop(self) -> None:
        if self._ticker:
            try:
                self._ticker.close()
            except Exception:
                pass


def simulate_live_feed(
    scrip: str,
    n_ticks: int = 100,
    tick_interval_ms: int = 100,
    on_tick: Optional[Callable] = None,
) -> list[dict]:
    """
    Generates a simulated live tick feed for demo/testing when broker is unavailable.
    Returns list of tick dicts with: scrip, price, volume, timestamp, side.
    """
    import numpy as np
    base_price = 500.0
    ticks: list[dict] = []
    now = datetime.utcnow()

    for i in range(n_ticks):
        price = base_price + np.random.normal(0, 0.5)
        base_price = price
        tick = {
            "scrip": scrip,
            "price": round(max(price, 1.0), 2),
            "volume": int(abs(np.random.exponential(scale=500))),
            "timestamp": now,
            "side": "BUY" if np.random.random() > 0.5 else "SELL",
        }
        ticks.append(tick)
        if on_tick:
            on_tick(tick)
        time.sleep(tick_interval_ms / 1000.0)
        now = datetime.fromtimestamp(now.timestamp() + tick_interval_ms / 1000.0)

    return ticks
