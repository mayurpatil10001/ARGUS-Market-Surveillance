"""
models/dna/train_on_synthetic.py — Train DNA Autoencoder on synthetic normal accounts.

Generates 500 normal account trade histories, trains for 50 epochs,
saves weights to models/dna/autoencoder_weights.pt.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import torch
import torch.nn.functional as F
import pandas as pd
from datetime import datetime, timedelta

from models.dna.autoencoder import BehavioralAutoencoder, extract_features

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "autoencoder_weights.pt")


def generate_normal_accounts(n_accounts: int = 500, seed: int = 0):
    """Generate synthetic normal (non-manipulated) trade histories."""
    rng = np.random.default_rng(seed)
    all_features = []

    for i in range(n_accounts):
        n_trades = int(rng.integers(15, 100))
        base_time = datetime(2024, 1, 2, 9, 15, 0)
        records = []
        price = rng.uniform(50, 500)

        for _ in range(n_trades):
            price += rng.normal(0, price * 0.005)
            price = max(price, 1.0)
            inter_s = rng.exponential(scale=23000.0 / max(n_trades, 1))
            base_time += timedelta(seconds=float(inter_s))
            records.append({
                "account_id": f"normal_{i:04d}",
                "scrip": f"SCRIP{rng.integers(1, 20):02d}",
                "timestamp": base_time,
                "price": round(float(price), 2),
                "volume": float(abs(rng.exponential(scale=500))),
                "side": "BUY" if rng.random() > 0.5 else "SELL",
            })

        df = pd.DataFrame(records)
        feats = extract_features(df)
        all_features.append(feats)

    return np.array(all_features, dtype=np.float32)


def main():
    print("Generating 500 normal account feature vectors...")
    X = generate_normal_accounts(500)

    # Normalize
    X_mean = X.mean(axis=0)
    X_std  = X.std(axis=0) + 1e-9
    X_norm = (X - X_mean) / X_std
    X_norm = np.nan_to_num(X_norm, nan=0.0, posinf=5.0, neginf=-5.0)

    split = int(len(X_norm) * 0.85)
    X_train = torch.tensor(X_norm[:split], dtype=torch.float32)
    X_val   = torch.tensor(X_norm[split:], dtype=torch.float32)

    train_ds = torch.utils.data.TensorDataset(X_train)
    val_ds   = torch.utils.data.TensorDataset(X_val)
    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=32, shuffle=True)
    val_loader   = torch.utils.data.DataLoader(val_ds,   batch_size=32)

    model     = BehavioralAutoencoder()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    best_val_loss = float("inf")
    print(f"Training for 50 epochs on {len(X_train)} train / {len(X_val)} val samples...")

    for epoch in range(50):
        model.train()
        for (xb,) in train_loader:
            optimizer.zero_grad()
            z, recon = model(xb)
            loss = F.mse_loss(recon, xb)
            loss.backward()
            optimizer.step()

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for (xb,) in val_loader:
                z, recon = model(xb)
                val_loss += F.mse_loss(recon, xb).item()
        val_loss /= max(len(val_loader), 1)
        scheduler.step(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), WEIGHTS_PATH)

        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1:3d}/50 — val_loss: {val_loss:.6f}")

    print(f"Best val loss: {best_val_loss:.6f}")
    print(f"DNA Autoencoder trained and saved to {WEIGHTS_PATH}")


if __name__ == "__main__":
    main()
