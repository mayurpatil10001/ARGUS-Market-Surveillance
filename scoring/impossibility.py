"""
scoring/impossibility.py — Statistical impossibility scoring for market manipulation detection.
Uses a Poisson null model to quantify the probability that observed coincidences
occurred by chance.
"""
from __future__ import annotations

import math

from scipy.stats import poisson


def compute_poisson_impossibility(
    observed_coincidences: int,
    n_accounts: int,
    n_trades: int,
    window_ms: float,
    trading_day_ms: float = 23_400_000.0,  # 6.5 hours in milliseconds
) -> float:
    """
    P(observing >= observed_coincidences by chance) under Poisson null model.
    Returns impossibility score 0–10 where 10 = p < 1e-10.

    Parameters
    ----------
    observed_coincidences : int
        Number of trade pairs occurring within window_ms of each other.
    n_accounts : int
        Total number of trading accounts in the scrip window.
    n_trades : int
        Total number of trades in the window.
    window_ms : float
        Coincidence window in milliseconds.
    trading_day_ms : float
        Length of trading day in milliseconds (default: 9:15–15:45 = 23,400 seconds).
    """
    rate_per_ms = n_trades / trading_day_ms
    # Expected number of coincidental pairs under random trading assumption
    expected_pairs = (n_accounts * (n_accounts - 1) / 2) * (
        1 - math.exp(-2 * rate_per_ms * window_ms)
    )
    lambda_expected = max(expected_pairs, 1e-10)

    # P(X >= observed) = 1 - P(X <= observed - 1) under Poisson(lambda)
    p_value = 1.0 - poisson.cdf(observed_coincidences - 1, lambda_expected)
    p_value = max(p_value, 1e-300)

    # Map to 0–10 scale: score = -log10(p), capped at 10
    score = min(10.0, -math.log10(p_value))
    return round(score, 3)


def compute_synchrony_chi2(timing_deltas_ms: list[float]) -> float:
    """
    Tests whether the inter-trade timing distribution deviates from exponential (natural).
    Under random trading, inter-trade intervals follow an exponential distribution.
    Coordinated trading produces non-exponential (e.g., uniform or multi-modal) patterns.

    Returns KS-test p-value. Low p-value = non-exponential = likely coordinated.

    Parameters
    ----------
    timing_deltas_ms : list[float]
        List of inter-trade time deltas in milliseconds.
    """
    if len(timing_deltas_ms) < 10:
        return 1.0

    import numpy as np
    from scipy.stats import kstest

    data = np.array(timing_deltas_ms, dtype=float)
    data = data[data > 0]

    if len(data) < 5:
        return 1.0

    mean_interval = data.mean()
    if mean_interval <= 0:
        return 1.0

    # KS-test against exponential with MLE rate parameter
    _, p_value = kstest(data, "expon", args=(0, mean_interval))
    return float(p_value)


def compute_composite_score(
    gnn_score: float,
    zero_day_score: float,
    dna_score: float,
    cross_market_score: float,
) -> float:
    """
    Computes the weighted composite ARGUS impossibility score.
    Weights: GNN 35%, Zero-Day 25%, DNA 25%, Cross-Market 15%.
    Output is 0–10, rounded to 3 decimal places.
    """
    score = (
        0.35 * gnn_score
        + 0.25 * zero_day_score
        + 0.25 * dna_score
        + 0.15 * cross_market_score
    )
    return round(min(max(score, 0.0), 10.0), 3)
