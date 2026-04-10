"""
models/dna/autoencoder.py — Behavioral DNA Autoencoder for account fingerprinting.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional

MODEL_PATH = os.path.join(os.path.dirname(__file__), "autoencoder_best.pt")
INPUT_DIM = 20
DNA_DIM = 32


def extract_features(account_trades: pd.DataFrame) -> np.ndarray:
    """
    Computes 20 behavioral features from an account's trade history.
    Returns 1D numpy array of shape (20,).
    """
    if account_trades.empty:
        return np.zeros(INPUT_DIM, dtype=np.float32)

    df = account_trades.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    vol = df["volume"] if "volume" in df.columns else pd.Series([1.0])
    price = df["price"] if "price" in df.columns else pd.Series([100.0])
    side = df["side"] if "side" in df.columns else pd.Series(["BUY"])
    scrip = df["scrip"] if "scrip" in df.columns else pd.Series(["X"])
    ts = df["timestamp"]

    ts_ms = ts.astype(np.int64) // 1_000_000
    inter_trade_ms = np.diff(ts_ms.values) if len(ts_ms) > 1 else np.array([0.0])

    buy_ratio = float((side == "BUY").mean())
    avg_vol = float(vol.mean())
    std_vol = float(vol.std()) if len(vol) > 1 else 0.0
    avg_price = float(price.mean())
    std_price = float(price.std()) if len(price) > 1 else 0.0
    price_autocorr = float(price.autocorr(lag=1)) if len(price) > 2 else 0.0
    trade_count = float(len(df))
    scrip_diversity = float(scrip.nunique())
    avg_inter_ms = float(inter_trade_ms.mean()) if len(inter_trade_ms) > 0 else 0.0
    std_inter_ms = float(inter_trade_ms.std()) if len(inter_trade_ms) > 1 else 0.0
    preferred_hour = float(ts.dt.hour.mode()[0] if len(ts) > 0 else 10)
    night_ratio = float((ts.dt.hour < 9).mean())
    large_order_ratio = float(
        (vol > vol.quantile(0.9)).mean() if len(vol) > 1 else 0.0
    )
    cancellation_rate = 0.0  # requires order cancellation data
    size_consistency = std_vol / (avg_vol + 1e-9)
    price_aggressiveness = float(price.diff().abs().mean() or 0.0)
    tod_std = float(ts.dt.hour.std() or 0.0)
    momentum_bias = float(price.diff().mean() or 0.0)
    activity_burst = float(
        df.groupby(ts.dt.floor("1min")).size().std() or 0.0 if len(df) > 1 else 0.0
    )
    order_imbalance = abs(
        float((side == "BUY").sum()) - float((side == "SELL").sum())
    ) / (trade_count + 1e-9)

    feats = np.array([
        avg_vol, std_vol, avg_price, std_price, buy_ratio,
        trade_count, scrip_diversity, avg_inter_ms, std_inter_ms, preferred_hour,
        cancellation_rate, size_consistency, price_aggressiveness, tod_std,
        night_ratio, large_order_ratio, momentum_bias, activity_burst,
        price_autocorr, order_imbalance,
    ], dtype=np.float32)

    # Clip and normalize to finite range
    feats = np.nan_to_num(feats, nan=0.0, posinf=100.0, neginf=-100.0)
    return feats


class BehavioralAutoencoder(nn.Module):
    """
    Autoencoder for behavioral DNA fingerprinting.
    Encoder: 20 → 256 → 128 → 32 (DNA fingerprint)
    Decoder: 32 → 128 → 256 → 20 (reconstruction)
    High reconstruction error = anomalous behavior.
    """

    def __init__(self, input_dim: int = INPUT_DIM, dna_dim: int = DNA_DIM):
        super().__init__()
        self.input_dim = input_dim
        self.dna_dim = dna_dim

        # Encoder
        self.enc1 = nn.Linear(input_dim, 256)
        self.enc_bn1 = nn.BatchNorm1d(256)
        self.enc_drop1 = nn.Dropout(0.3)
        self.enc2 = nn.Linear(256, 128)
        self.enc3 = nn.Linear(128, dna_dim)

        # Decoder
        self.dec1 = nn.Linear(dna_dim, 128)
        self.dec2 = nn.Linear(128, 256)
        self.dec3 = nn.Linear(256, input_dim)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.enc_bn1(self.enc1(x)))
        x = self.enc_drop1(x)
        x = F.relu(self.enc2(x))
        return self.enc3(x)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        z = F.relu(self.dec1(z))
        z = F.relu(self.dec2(z))
        return self.dec3(z)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        z = self.encode(x)
        recon = self.decode(z)
        return z, recon

    def encode_numpy(self, features: np.ndarray) -> np.ndarray:
        """Returns 32-dim DNA fingerprint for given feature vector."""
        self.eval()
        with torch.no_grad():
            x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
            z = self.encode(x)
            return z.squeeze(0).numpy()

    def reconstruction_error(self, features: np.ndarray) -> float:
        """MSE of reconstruction vs original. High error = anomalous behavior."""
        self.eval()
        with torch.no_grad():
            x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
            z = self.encode(x)
            recon = self.decode(z)
            mse = F.mse_loss(recon, x).item()
        return float(mse)


_global_ae: Optional[BehavioralAutoencoder] = None


def get_autoencoder() -> BehavioralAutoencoder:
    """Returns cached global autoencoder, loading from disk if needed."""
    global _global_ae
    if _global_ae is None:
        _global_ae = BehavioralAutoencoder()
        # Check both possible weight file locations
        alt_path = os.path.join(os.path.dirname(__file__), "autoencoder_weights.pt")
        chosen = MODEL_PATH if os.path.exists(MODEL_PATH) else (alt_path if os.path.exists(alt_path) else None)
        if chosen:
            _global_ae.load_state_dict(torch.load(chosen, map_location="cpu"))
        _global_ae.eval()
    return _global_ae


def train_autoencoder(normal_trades_df: pd.DataFrame, epochs: int = 200) -> None:
    """
    Trains autoencoder on normal (non-manipulated) accounts.
    Unsupervised: only non-flagged accounts are used.
    Saves best model (lowest val loss) to MODEL_PATH.
    """
    if normal_trades_df.empty:
        return

    # Filter to normal accounts only
    if "is_manipulated" in normal_trades_df.columns:
        normal_df = normal_trades_df[~normal_trades_df["is_manipulated"]]
    else:
        normal_df = normal_trades_df

    if "account_id" not in normal_df.columns:
        return

    # Extract per-account features
    feature_vecs = []
    for acc_id, grp in normal_df.groupby("account_id"):
        feats = extract_features(grp)
        feature_vecs.append(feats)

    if len(feature_vecs) < 4:
        return

    X = np.array(feature_vecs, dtype=np.float32)
    # Normalize
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0) + 1e-9
    X = (X - X_mean) / X_std

    X_tensor = torch.tensor(X, dtype=torch.float32)
    dataset = torch.utils.data.TensorDataset(X_tensor)
    split = int(len(X) * 0.8)
    train_ds = torch.utils.data.TensorDataset(X_tensor[:split])
    val_ds = torch.utils.data.TensorDataset(X_tensor[split:])
    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=32, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val_ds, batch_size=32)

    model = BehavioralAutoencoder()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10)

    best_val_loss = float("inf")
    for epoch in range(epochs):
        model.train()
        for (xb,) in train_loader:
            optimizer.zero_grad()
            _, recon = model(xb)
            loss = F.mse_loss(recon, xb)
            loss.backward()
            optimizer.step()

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for (xb,) in val_loader:
                _, recon = model(xb)
                val_loss += F.mse_loss(recon, xb).item()
        val_loss /= max(len(val_loader), 1)
        scheduler.step(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), MODEL_PATH)

    global _global_ae
    _global_ae = None  # invalidate cache so next call reloads from disk
