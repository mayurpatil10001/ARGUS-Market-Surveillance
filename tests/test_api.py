"""
tests/test_api.py — Integration tests for ARGUS FastAPI endpoints.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.fixture
def client():
    """Creates FastAPI test client with mocked DB."""
    # Patch DB engine creation to avoid needing a real PostgreSQL
    with patch("data.db.session.create_engine") as mock_engine, \
         patch("data.db.models.Base.metadata.create_all"), \
         patch("models.gnn.train_tcn.load_model", return_value=_make_mock_tcn()), \
         patch("models.dna.autoencoder.get_autoencoder", return_value=_make_mock_ae()), \
         patch("models.zero_day.anomaly.get_detector", return_value=_make_mock_zd()), \
         patch("models.dna.fingerprint_store.FingerprintStore", return_value=_make_mock_fp()):

        from sqlalchemy import create_engine as real_create_engine
        mock_engine.return_value = real_create_engine("sqlite:///:memory:")

        from api.main import app

        with TestClient(app, raise_server_exceptions=False) as tc:
            yield tc


def _make_mock_tcn():
    mock = MagicMock()
    import torch
    mock.return_value = (torch.zeros(3, 64), torch.tensor([[0.3]]))
    mock.eval.return_value = mock
    return mock


def _make_mock_ae():
    mock = MagicMock()
    import numpy as np
    mock.encode_numpy.return_value = np.zeros(32, dtype=np.float32)
    mock.reconstruction_error.return_value = 0.05
    mock.eval.return_value = mock
    return mock


def _make_mock_zd():
    mock = MagicMock()
    import numpy as np
    mock.score.return_value = np.array([3.0])
    mock.build_session_features.return_value = np.zeros((1, 25))
    return mock


def _make_mock_fp():
    mock = MagicMock()
    mock.load_fraudster_dnas.return_value = 0
    mock.find_similar.return_value = []
    mock.get.return_value = None
    mock.store.return_value = None
    return mock


def _get_token(client) -> str:
    """Helper to get auth token."""
    resp = client.post("/auth/token", data={"username": "admin", "password": "argus2024"})
    if resp.status_code == 200:
        return resp.json().get("access_token", "")
    return ""


# ─── Health Tests ─────────────────────────────────────────────────────────────

def test_health(client):
    """Health endpoint should return 200 with status field."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "services" in data
    assert "model_versions" in data


# ─── Auth Tests ───────────────────────────────────────────────────────────────

def test_auth_success(client):
    """Valid credentials should return access token."""
    resp = client.post("/auth/token", data={"username": "admin", "password": "argus2024"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_auth_wrong_password(client):
    """Wrong password should return 401."""
    resp = client.post("/auth/token", data={"username": "admin", "password": "wrongpass"})
    assert resp.status_code == 401


def test_auth_wrong_user(client):
    """Wrong username should return 401."""
    resp = client.post("/auth/token", data={"username": "hacker", "password": "argus2024"})
    assert resp.status_code == 401


# ─── Alert Endpoint Tests ──────────────────────────────────────────────────────

def test_get_alerts_unauthed(client):
    """Alerts endpoint requires authentication — should return 401 without token."""
    resp = client.get("/alerts")
    assert resp.status_code == 401


def test_get_alerts_authed(client):
    """Authenticated request to /alerts should return 200 with a list."""
    token = _get_token(client)
    if not token:
        pytest.skip("Could not get auth token (likely no DB available)")
    resp = client.get("/alerts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_alert_not_found(client):
    """Non-existent alert ID should return 404."""
    token = _get_token(client)
    if not token:
        pytest.skip("Could not get auth token")
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/alerts/{fake_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_get_alerts_filter_params(client):
    """Alert list accepts optional filter parameters."""
    token = _get_token(client)
    if not token:
        pytest.skip("Could not get auth token")
    resp = client.get(
        "/alerts",
        headers={"Authorization": f"Bearer {token}"},
        params={"status": "open", "min_score": 5.0, "limit": 10},
    )
    assert resp.status_code == 200


# ─── Report Endpoint Tests ────────────────────────────────────────────────────

def test_generate_report(client):
    """Report generation for non-existent alert should return 404."""
    token = _get_token(client)
    if not token:
        pytest.skip("Could not get auth token")
    fake_id = str(uuid.uuid4())
    resp = client.post(
        f"/reports/case/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert resp.status_code == 404


def test_weekly_summary(client):
    """Weekly summary should return 200 with expected fields."""
    token = _get_token(client)
    if not token:
        pytest.skip("Could not get auth token")
    resp = client.get(
        "/reports/summary/weekly",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_alerts" in data
    assert "false_positive_rate_pct" in data


# ─── Account Endpoint Tests ────────────────────────────────────────────────────

def test_get_account_not_found(client):
    """Non-existent account should return 404."""
    token = _get_token(client)
    if not token:
        pytest.skip("Could not get auth token")
    resp = client.get(
        "/accounts/nonexistent123/dna",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_account_search(client):
    """Account search endpoint should return 200."""
    token = _get_token(client)
    if not token:
        pytest.skip("Could not get auth token")
    resp = client.get(
        "/accounts/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 10},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
