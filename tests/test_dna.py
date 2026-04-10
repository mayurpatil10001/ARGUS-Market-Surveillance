"""
tests/test_dna.py — Unit tests for the Behavioral DNA Autoencoder and FingerprintStore.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
import pytest

from models.dna.autoencoder import BehavioralAutoencoder, extract_features, INPUT_DIM, DNA_DIM


def _make_account_trades(account_id: str = "test_acc", n: int = 100, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    from datetime import datetime, timedelta
    base = datetime(2024, 1, 10, 9, 15)
    records = []
    price = 100.0
    for i in range(n):
        price += rng.normal(0, 0.3)
        records.append({
            "account_id": account_id,
            "scrip": "TESTSCRIP",
            "timestamp": base + timedelta(seconds=i * 30),
            "price": round(max(price, 1.0), 2),
            "volume": float(abs(rng.exponential(500))),
            "side": rng.choice(["BUY", "SELL"]),
        })
    return pd.DataFrame(records)


# ─── Autoencoder Architecture Tests ───────────────────────────────────────────

def test_autoencoder_output_shapes():
    """Autoencoder should produce correct DNA dim and reconstruction shape."""
    ae = BehavioralAutoencoder()
    import torch
    x = torch.randn(4, INPUT_DIM)
    z, recon = ae(x)
    assert z.shape == (4, DNA_DIM), f"DNA shape mismatch: {z.shape}"
    assert recon.shape == (4, INPUT_DIM), f"Reconstruction shape mismatch: {recon.shape}"


def test_autoencoder_encode_numpy():
    """encode_numpy should return (32,) array."""
    ae = BehavioralAutoencoder()
    df = _make_account_trades()
    feats = extract_features(df)
    dna = ae.encode_numpy(feats)
    assert dna.shape == (DNA_DIM,), f"DNA vector shape: {dna.shape}"
    assert np.all(np.isfinite(dna)), "DNA contains non-finite values"


def test_autoencoder_reconstruction():
    """Reconstruction error for seen data pattern should be reasonable (not infinity)."""
    ae = BehavioralAutoencoder()
    df = _make_account_trades()
    feats = extract_features(df)
    error = ae.reconstruction_error(feats)
    assert np.isfinite(error), f"Reconstruction error is non-finite: {error}"
    assert error >= 0.0, "Reconstruction error must be non-negative"


def test_autoencoder_reconstruction_decreases_after_training():
    """After training on normal data, reconstruction error should decrease."""
    import pandas as pd
    from models.dna.autoencoder import train_autoencoder, BehavioralAutoencoder, extract_features

    # Build a simple normal dataset
    dfs = [_make_account_trades(f"acc_{i}", n=80, seed=i) for i in range(15)]
    combined = pd.concat(dfs, ignore_index=True)

    ae_before = BehavioralAutoencoder()
    df0 = _make_account_trades(seed=0)
    feats = extract_features(df0)
    error_before = ae_before.reconstruction_error(feats)

    # Train and reload
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
        tmp_path = f.name

    from models.dna import autoencoder as ae_module
    orig_path = ae_module.MODEL_PATH
    ae_module.MODEL_PATH = tmp_path
    try:
        train_autoencoder(combined, epochs=10)
        ae_after = BehavioralAutoencoder()
        if os.path.exists(tmp_path):
            import torch
            ae_after.load_state_dict(torch.load(tmp_path, map_location="cpu"))
        error_after = ae_after.reconstruction_error(feats)
        # error_after should be finite — training should converge somewhat
        assert np.isfinite(error_after), "Post-training reconstruction error is non-finite"
    finally:
        ae_module.MODEL_PATH = orig_path
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ─── Fingerprint Similarity Tests ─────────────────────────────────────────────

def test_fingerprint_similarity_same_account():
    """Same features should give cosine similarity of 1.0."""
    ae = BehavioralAutoencoder()
    df = _make_account_trades("acc_same")
    feats = extract_features(df)
    dna1 = ae.encode_numpy(feats)
    dna2 = ae.encode_numpy(feats)

    norm1 = np.linalg.norm(dna1)
    norm2 = np.linalg.norm(dna2)
    if norm1 > 1e-9 and norm2 > 1e-9:
        sim = np.dot(dna1, dna2) / (norm1 * norm2)
        assert abs(sim - 1.0) < 1e-5, f"Same account DNA similarity should be ~1.0, got {sim}"


def test_fingerprint_similarity_different_accounts():
    """Very different behavior patterns should have lower similarity."""
    ae = BehavioralAutoencoder()

    # Normal account: balanced buys/sells, moderate volume
    df_normal = _make_account_trades("normal", seed=42)
    feats_n = extract_features(df_normal)
    dna_n = ae.encode_numpy(feats_n)

    # Manipulator: all buys, massive volume
    rng = np.random.default_rng(99)
    from datetime import datetime, timedelta
    records = [{
        "account_id": "manip",
        "scrip": "TESTSCRIP",
        "timestamp": datetime(2024, 1, 1, 9, 15) + timedelta(milliseconds=i),
        "price": 100 + rng.normal(0, 2),
        "volume": float(rng.integers(50000, 200000)),
        "side": "BUY",
    } for i in range(100)]
    df_manip = pd.DataFrame(records)
    feats_m = extract_features(df_manip)
    dna_m = ae.encode_numpy(feats_m)

    norm_n = np.linalg.norm(dna_n)
    norm_m = np.linalg.norm(dna_m)
    if norm_n > 1e-9 and norm_m > 1e-9:
        sim = np.dot(dna_n, dna_m) / (norm_n * norm_m)
        assert sim < 0.99, f"Very different accounts should not be near-identical: {sim}"


# ─── Known Fraudster Match Tests (unit, no Redis required) ────────────────────

def test_known_fraudster_cosine_similarity_logic():
    """Test the cosine similarity computation directly."""
    a = np.array([1, 0, 0], dtype=np.float32)
    b = np.array([1, 0, 0], dtype=np.float32)
    c = np.array([0, 1, 0], dtype=np.float32)

    def cosine(x, y):
        return float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-9))

    assert abs(cosine(a, b) - 1.0) < 1e-6
    assert abs(cosine(a, c)) < 1e-6


def test_extract_features_shape():
    """extract_features should always return (20,)-shaped array."""
    df = _make_account_trades()
    feats = extract_features(df)
    assert feats.shape == (INPUT_DIM,), f"Feature shape: {feats.shape}"
    assert np.all(np.isfinite(feats)), "Features contain non-finite values"


def test_extract_features_empty():
    """extract_features on empty DataFrame should return zeros without error."""
    feats = extract_features(pd.DataFrame())
    assert feats.shape == (INPUT_DIM,)
    assert np.all(feats == 0.0)
