"""
models/cross_market/fusion.py — Cross-Market Phantom Detector.
Fuses NSE/BSE/NFO/MCX signals to detect derivative-spot manipulation and circular trading.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import networkx as nx
import numpy as np
import pandas as pd


class CrossMarketFusion:
    """
    Detects manipulation patterns that span multiple market segments.
    """

    def load_segment_data(
        self,
        session,
        scrip: str,
        from_dt: datetime,
        to_dt: datetime,
    ) -> dict[str, pd.DataFrame]:
        """
        Loads trade data per exchange (NSE/BSE/NFO/MCX) for given scrip+window.
        Returns dict keyed by exchange abbreviation.
        """
        from data.db.crud import get_trades

        result: dict[str, pd.DataFrame] = {}
        for exchange in ["NSE", "BSE", "NFO", "MCX"]:
            trades = get_trades(
                session,
                scrip=scrip,
                from_dt=from_dt,
                to_dt=to_dt,
                exchange=exchange,
                limit=10000,
            )
            if trades:
                rows = [
                    {
                        "account_id": t.account_id,
                        "scrip": t.scrip,
                        "exchange": t.exchange.value if hasattr(t.exchange, "value") else str(t.exchange),
                        "timestamp": t.timestamp,
                        "price": t.price,
                        "volume": t.volume,
                        "side": t.side.value if hasattr(t.side, "value") else str(t.side),
                    }
                    for t in trades
                ]
                result[exchange] = pd.DataFrame(rows)
            else:
                result[exchange] = pd.DataFrame()

        return result

    def detect_derivative_spot_manipulation(
        self,
        spot_df: pd.DataFrame,
        fno_df: pd.DataFrame,
    ) -> list[dict]:
        """
        Flags accounts that:
         (a) took large FNO position (>95th percentile volume)
         (b) spot price moved >1.5% within 30 min
         (c) account exited FNO position within 30 min of price move

        Returns list of suspicious events with: account_id, fno_volume, price_impact, profit_estimate.
        """
        if spot_df.empty or fno_df.empty:
            return []

        suspicious: list[dict] = []

        # Ensure datetime
        for df in [spot_df, fno_df]:
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

        fno_vol_95 = fno_df["volume"].quantile(0.95)

        # Accounts with large FNO positions
        large_fno = fno_df[fno_df["volume"] > fno_vol_95].copy()

        if large_fno.empty:
            return []

        # Calculate spot OHLC in 5-min windows
        spot_df = spot_df.sort_values("timestamp")
        spot_df["window"] = spot_df["timestamp"].dt.floor("5min")
        spot_ohlc = (
            spot_df.groupby("window")["price"]
            .agg(["first", "last", "max", "min"])
            .reset_index()
        )
        spot_ohlc["price_change_pct"] = (
            (spot_ohlc["last"] - spot_ohlc["first"]).abs()
            / (spot_ohlc["first"] + 1e-9)
            * 100
        )

        # Find windows with >1.5% move
        big_moves = spot_ohlc[spot_ohlc["price_change_pct"] > 1.5]

        for _, move in big_moves.iterrows():
            move_window = move["window"]
            window_end = move_window + timedelta(minutes=5)
            window_30 = move_window + timedelta(minutes=30)

            # Get large FNO trades around this window
            pre_fno = large_fno[
                (large_fno["timestamp"] >= move_window - timedelta(minutes=30))
                & (large_fno["timestamp"] < move_window)
            ]

            for _, fno_trade in pre_fno.iterrows():
                acc = fno_trade["account_id"]
                # Check if this account exits FNO within 30 min
                exits = fno_df[
                    (fno_df["account_id"] == acc)
                    & (fno_df["timestamp"] >= window_end)
                    & (fno_df["timestamp"] <= window_30)
                    & (fno_df["side"] != fno_trade["side"])  # opposite side = exit
                ]

                if not exits.empty:
                    entry_price = float(spot_df[
                        spot_df["timestamp"] <= fno_trade["timestamp"]
                    ]["price"].iloc[-1]) if not spot_df.empty else 100.0
                    exit_price = float(move["last"])
                    direction = 1 if fno_trade["side"] == "BUY" else -1
                    profit_estimate = direction * (exit_price - entry_price) * float(fno_trade["volume"])

                    suspicious.append({
                        "account_id": acc,
                        "fno_volume": float(fno_trade["volume"]),
                        "price_impact": float(move["price_change_pct"]),
                        "profit_estimate": round(profit_estimate, 2),
                        "window": str(move_window),
                        "manipulation_type": "derivative_spot",
                    })

        return suspicious

    def detect_circular_trading(
        self,
        trades_df: pd.DataFrame,
    ) -> list[tuple]:
        """
        Builds directed graph of trade flows (A sells → B buys same scrip within 30s).
        Uses NetworkX simple_cycles to find rings of length 2–6.
        Returns list of (cycle_accounts, combined_volume, price_impact).
        """
        if trades_df.empty or len(trades_df) < 4:
            return []

        if not pd.api.types.is_datetime64_any_dtype(trades_df["timestamp"]):
            trades_df = trades_df.copy()
            trades_df["timestamp"] = pd.to_datetime(trades_df["timestamp"], utc=True, errors="coerce")

        G = nx.DiGraph()
        sells = trades_df[trades_df["side"] == "SELL"].sort_values("timestamp")
        buys = trades_df[trades_df["side"] == "BUY"].sort_values("timestamp")

        window_s = 30  # 30-second window for A→B connection

        for _, sell in sells.iterrows():
            sell_ts = sell["timestamp"]
            # Find buys within 30s after this sell
            window_buys = buys[
                (buys["timestamp"] >= sell_ts)
                & (buys["timestamp"] <= sell_ts + timedelta(seconds=window_s))
                & (buys["account_id"] != sell["account_id"])
            ]
            for _, buy in window_buys.iterrows():
                if not G.has_edge(sell["account_id"], buy["account_id"]):
                    G.add_edge(
                        sell["account_id"],
                        buy["account_id"],
                        volume=float(sell["volume"]),
                        price=float(sell["price"]),
                    )

        circles = []
        try:
            for cycle in nx.simple_cycles(G):
                if 2 <= len(cycle) <= 6:
                    combined_vol = sum(
                        G[cycle[i]][cycle[(i + 1) % len(cycle)]].get("volume", 0)
                        for i in range(len(cycle))
                    )
                    prices = [
                        G[cycle[i]][cycle[(i + 1) % len(cycle)]].get("price", 0)
                        for i in range(len(cycle))
                    ]
                    price_impact = (max(prices) - min(prices)) / (min(prices) + 1e-9) * 100 if prices else 0.0
                    circles.append((cycle, round(combined_vol, 2), round(price_impact, 2)))
        except Exception:
            pass

        return circles

    def cross_market_score(
        self,
        scrip: str,
        from_dt: datetime,
        to_dt: datetime,
        session,
    ) -> float:
        """
        Runs derivative-spot and circular trading detectors.
        Returns normalized 0–10 score.
        """
        segment_data = self.load_segment_data(session, scrip, from_dt, to_dt)
        spot_df = segment_data.get("NSE", pd.DataFrame())
        fno_df = segment_data.get("NFO", pd.DataFrame())

        deriv_events = self.detect_derivative_spot_manipulation(spot_df, fno_df)
        all_trades = pd.concat([df for df in segment_data.values() if not df.empty], ignore_index=True)
        circular_events = self.detect_circular_trading(all_trades)

        # Compute score: weighted count of manipulation signals
        deriv_score = min(len(deriv_events) * 1.5, 5.0)
        circular_score = min(len(circular_events) * 2.0, 5.0)
        raw_score = deriv_score + circular_score

        return round(min(raw_score, 10.0), 3)
