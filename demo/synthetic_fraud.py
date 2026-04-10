"""
demo/synthetic_fraud.py — Synthetic fraud data generator for testing and training.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generate_random_trades(
    n_accounts: int = 50,
    n_trades: int = 500,
    scrip: str = "RANDTEST",
    seed: int = 0,
) -> pd.DataFrame:
    """Generates random, non-manipulated trade data under Poisson timing model."""
    rng = np.random.default_rng(seed)
    base_time = datetime(2024, 1, 2, 9, 15, 0)
    accounts = [f"rand_{i:04d}" for i in range(n_accounts)]
    records = []
    price = 100.0
    for _ in range(n_trades):
        price += rng.normal(0, 0.2)
        inter_s = rng.exponential(scale=23000.0 / n_trades)
        base_time += timedelta(seconds=inter_s)
        records.append({
            "account_id": rng.choice(accounts),
            "scrip": scrip,
            "timestamp": base_time,
            "price": round(max(price, 1.0), 2),
            "volume": float(abs(rng.exponential(scale=500))),
            "side": rng.choice(["BUY", "SELL"]),
            "is_manipulated": False,
        })
    return pd.DataFrame(records)


def generate_coordinated_trades(
    n_colluding: int = 10,
    n_innocent: int = 40,
    n_bursts: int = 30,
    window_ms: int = 50,
    scrip: str = "COORDTEST",
    seed: int = 1,
) -> pd.DataFrame:
    """Generates coordinated trades with multi-account bursts within window_ms."""
    rng = np.random.default_rng(seed)
    base_time = datetime(2024, 1, 3, 9, 15, 0)
    colluding = [f"coord_{i:03d}" for i in range(n_colluding)]
    innocent = [f"innocent_{i:03d}" for i in range(n_innocent)]
    records = []

    for burst in range(n_bursts):
        burst_time = base_time + timedelta(seconds=int(rng.integers(300, 22000)))
        for acc in rng.choice(colluding, size=rng.integers(4, n_colluding), replace=False):
            ms = rng.integers(0, window_ms)
            ts = burst_time + timedelta(milliseconds=int(ms))
            records.append({
                "account_id": acc,
                "scrip": scrip,
                "timestamp": ts,
                "price": round(100 + rng.normal(0, 0.5), 2),
                "volume": float(rng.integers(500, 5000)),
                "side": "BUY",
                "is_manipulated": True,
            })

    for _ in range(300):
        ts = base_time + timedelta(seconds=int(rng.integers(0, 23000)))
        records.append({
            "account_id": rng.choice(innocent),
            "scrip": scrip,
            "timestamp": ts,
            "price": round(100 + rng.normal(0, 1), 2),
            "volume": float(rng.integers(100, 2000)),
            "side": rng.choice(["BUY", "SELL"]),
            "is_manipulated": False,
        })

    return pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)
