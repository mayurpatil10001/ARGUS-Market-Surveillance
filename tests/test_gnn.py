"""
tests/test_gnn.py — Unit tests for the Temporal Coincidence Network.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest
import torch

from demo.synthetic_fraud import generate_random_trades, generate_coordinated_trades
from models.gnn.tcn import TemporalCoincidenceNetwork, build_trade_graph
from scoring.impossibility import compute_poisson_impossibility


def _make_natural_trades(n: int = 300) -> pd.DataFrame:
    """Creates random trades under Poisson timing (natural market)."""
    return generate_random_trades(n_accounts=30, n_trades=n, scrip="NATURAL", seed=42)


def _make_manipulated_trades(n_bursts: int = 20) -> pd.DataFrame:
    """Creates coordinated trades with tight temporal windows."""
    return generate_coordinated_trades(
        n_colluding=10,
        n_innocent=20,
        n_bursts=n_bursts,
        window_ms=50,
        scrip="MANIPULATED",
        seed=1,
    )


# ─── Graph Construction Tests ─────────────────────────────────────────────────

def test_build_trade_graph_natural():
    """Natural trades should produce a sparse coincidence graph."""
    df = _make_natural_trades(300)
    graph = build_trade_graph(df, window_ms=50, min_coincidences=3)

    assert graph.num_nodes > 0
    assert graph.x.shape[1] == 16
    # Under random (Poisson) trading, coincidences within 50ms should be rare
    n_edges = graph.edge_index.shape[1] // 2 if graph.edge_index.shape[1] > 0 else 0
    total_pairs = graph.num_nodes * (graph.num_nodes - 1) / 2
    edge_density = n_edges / max(total_pairs, 1)
    # Natural trades should have low edge density
    assert edge_density < 0.5, f"Natural graph too dense: {edge_density:.2%}"


def test_build_trade_graph_manipulated():
    """Coordinated trades within 50ms should produce a dense cluster."""
    df = _make_manipulated_trades(30)
    graph = build_trade_graph(df, window_ms=50, min_coincidences=3)

    assert graph.num_nodes > 0
    n_edges = graph.edge_index.shape[1] // 2 if graph.edge_index.shape[1] > 0 else 0
    # Manipulated data with many coordinated bursts should produce significant edges
    assert n_edges > 0, "Manipulated graph should have coincidence edges"


def test_build_trade_graph_empty():
    """Empty DataFrame should return valid empty graph."""
    graph = build_trade_graph(pd.DataFrame(), window_ms=50, min_coincidences=3)
    assert graph.num_nodes >= 1


def test_build_trade_graph_node_features():
    """Node features should be finite and normalized."""
    df = _make_natural_trades(100)
    graph = build_trade_graph(df, window_ms=50, min_coincidences=1)
    assert not torch.isnan(graph.x).any(), "Node features contain NaN"
    assert not torch.isinf(graph.x).any(), "Node features contain Inf"


# ─── TCN Forward Pass Tests ───────────────────────────────────────────────────

def test_tcn_forward_pass():
    """TCN forward pass should return correct output shapes."""
    model = TemporalCoincidenceNetwork(node_features=16, hidden=64, heads=2)
    model.eval()

    df = _make_natural_trades(100)
    graph = build_trade_graph(df, window_ms=50, min_coincidences=1)

    with torch.no_grad():
        node_embeddings, manipulation_prob = model(graph)

    assert node_embeddings.shape == (graph.num_nodes, 64), \
        f"Expected ({graph.num_nodes}, 64), got {node_embeddings.shape}"
    assert manipulation_prob.shape == (1, 1), \
        f"Expected (1, 1), got {manipulation_prob.shape}"
    assert 0.0 <= float(manipulation_prob.item()) <= 1.0, \
        "Manipulation probability must be in [0, 1]"


def test_tcn_deterministic():
    """TCN should be deterministic in eval mode."""
    model = TemporalCoincidenceNetwork()
    model.eval()
    df = _make_natural_trades(80)
    graph = build_trade_graph(df, window_ms=50, min_coincidences=1)

    torch.manual_seed(0)
    with torch.no_grad():
        _, prob1 = model(graph)
    torch.manual_seed(0)
    with torch.no_grad():
        _, prob2 = model(graph)

    assert abs(float(prob1) - float(prob2)) < 1e-6, "TCN not deterministic in eval mode"


# ─── Impossibility Score Tests ────────────────────────────────────────────────

def test_impossibility_score_natural():
    """Natural (low) coincidences should produce score < 3."""
    # Under random trading: very few coincidences expected
    score = compute_poisson_impossibility(
        observed_coincidences=2,
        n_accounts=50,
        n_trades=300,
        window_ms=50.0,
    )
    assert score < 3.0, f"Natural score too high: {score}"


def test_impossibility_score_manipulated():
    """Heavy coordination (many coincidences) should produce score > 8."""
    score = compute_poisson_impossibility(
        observed_coincidences=500,
        n_accounts=20,
        n_trades=200,
        window_ms=50.0,
    )
    assert score > 8.0, f"Manipulated score too low: {score}"


def test_impossibility_score_boundary():
    """Score must always be in [0, 10] range."""
    for coincidences in [0, 1, 10, 100, 10000]:
        score = compute_poisson_impossibility(
            observed_coincidences=coincidences,
            n_accounts=30,
            n_trades=300,
            window_ms=50.0,
        )
        assert 0.0 <= score <= 10.0, f"Score {score} out of [0, 10] for {coincidences} coincidences"


def test_impossibility_zero_coincidences():
    """Zero observed coincidences should give a score near 0."""
    score = compute_poisson_impossibility(
        observed_coincidences=0,
        n_accounts=10,
        n_trades=100,
        window_ms=50.0,
    )
    assert score < 1.0


def test_tcn_handles_no_edges():
    """TCN should gracefully handle graphs with no edges."""
    model = TemporalCoincidenceNetwork()
    model.eval()
    # Create a graph with far-apart trades (no coincidences)
    df = pd.DataFrame([{
        "account_id": f"acc_{i}",
        "scrip": "TEST",
        "timestamp": datetime(2024, 1, 1, 9, 15, 0) + timedelta(minutes=i * 10),
        "price": 100.0,
        "volume": 500.0,
        "side": "BUY",
    } for i in range(5)])
    graph = build_trade_graph(df, window_ms=50, min_coincidences=3)

    with torch.no_grad():
        node_embeds, prob = model(graph)
    assert 0.0 <= float(prob.item()) <= 1.0
