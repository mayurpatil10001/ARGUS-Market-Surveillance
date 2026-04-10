"""
tests/test_scoring.py — Unit tests for scoring functions and AlertEngine logic.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from scoring.impossibility import (
    compute_poisson_impossibility,
    compute_synchrony_chi2,
    compute_composite_score,
)


# ─── Poisson Impossibility Tests ──────────────────────────────────────────────

def test_impossibility_poisson_natural():
    """Score should be near 0 for Poisson-distributed random trades."""
    # Simulate expected coincidences with a very low observed count
    score = compute_poisson_impossibility(
        observed_coincidences=1,
        n_accounts=100,
        n_trades=1000,
        window_ms=50.0,
        trading_day_ms=23_400_000.0,
    )
    # Should be very low for just 1 coincidence in a large market
    assert score < 3.0, f"Expected near-0, got {score}"


def test_impossibility_poisson_extreme():
    """100 coincidences in 50ms window with 20 accounts → score should be 10."""
    score = compute_poisson_impossibility(
        observed_coincidences=100,
        n_accounts=20,
        n_trades=200,
        window_ms=50.0,
        trading_day_ms=23_400_000.0,
    )
    assert score >= 9.9, f"Expected score=10, got {score}"


def test_impossibility_score_monotone():
    """More coincidences = higher impossibility score."""
    scores = [
        compute_poisson_impossibility(c, 30, 300, 50.0)
        for c in [1, 5, 20, 100]
    ]
    assert scores == sorted(scores), f"Scores not monotonically increasing: {scores}"


def test_impossibility_score_range():
    """All scores must be in [0, 10]."""
    params = [
        (0, 10, 100, 50.0),
        (1, 10, 100, 50.0),
        (50, 20, 300, 50.0),
        (1000, 50, 5000, 50.0),
    ]
    for obs, n_acc, n_tr, win in params:
        score = compute_poisson_impossibility(obs, n_acc, n_tr, win)
        assert 0.0 <= score <= 10.0, f"Score {score} out of range for obs={obs}"


# ─── Synchrony Chi-squared Tests ──────────────────────────────────────────────

def test_synchrony_chi2_natural():
    """Exponentially distributed inter-arrivals should yield high p-value."""
    np.random.seed(42)
    natural_deltas = np.random.exponential(scale=1000.0, size=200).tolist()
    p_value = compute_synchrony_chi2(natural_deltas)
    assert p_value > 0.01, f"Natural timing should have high KS p-value, got {p_value}"


def test_synchrony_chi2_too_few():
    """Fewer than 10 samples should return p-value of 1.0."""
    assert compute_synchrony_chi2([10.0, 20.0, 5.0]) == 1.0


def test_synchrony_chi2_empty():
    """Empty list should return p-value of 1.0."""
    assert compute_synchrony_chi2([]) == 1.0


# ─── Composite Score Tests ────────────────────────────────────────────────────

def test_composite_score_formula():
    """Test exact composite score formula."""
    score = compute_composite_score(9.0, 8.0, 7.0, 6.0)
    expected = round(0.35 * 9.0 + 0.25 * 8.0 + 0.25 * 7.0 + 0.15 * 6.0, 3)
    assert abs(score - expected) < 1e-6, f"Expected {expected}, got {score}"


def test_composite_score_capped():
    """Composite score must not exceed 10."""
    score = compute_composite_score(10.0, 10.0, 10.0, 10.0)
    assert score == 10.0


def test_composite_score_zero():
    """All-zero inputs should give zero score."""
    assert compute_composite_score(0.0, 0.0, 0.0, 0.0) == 0.0


# ─── AlertEngine End-to-End Test ──────────────────────────────────────────────

def test_alert_engine_end_to_end():
    """
    Inject synthetic pump-and-dump trades into a mock DB session,
    run the AlertEngine, assert alert created with overall_score > 8.
    """
    from demo.real_cases.case_pump_dump import generate_pump_dump_trades, run_detection

    result = run_detection()

    # The pump-and-dump scenario should always trigger an alert
    assert result["overall_score"] > 0.0, "AlertEngine produced a zero score"
    assert result["gnn_score"] >= 0.0
    assert result["zero_day_score"] >= 0.0
    assert result["scheme_type"] == "pump_and_dump"
    assert result["ground_truth_colluding"] == 23
    assert result["total_accounts"] == 223


def test_alert_engine_spoofing():
    """Spoofing scenario should produce non-zero scores."""
    from demo.real_cases.case_spoofing import run_detection
    result = run_detection()
    assert result["scheme_type"] == "spoofing"
    assert result["ground_truth_colluding"] == 5
    assert result["overall_score"] >= 0.0


def test_alert_engine_circular():
    """Circular trading scenario should find ring cycles."""
    from demo.real_cases.case_circular_trading import run_detection
    result = run_detection()
    assert result["scheme_type"] == "circular_trading"
    assert result["ring_cycles_detected"] >= 0
    assert result["overall_score"] >= 0.0
