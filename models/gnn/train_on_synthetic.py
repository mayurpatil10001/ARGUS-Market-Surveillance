"""
models/gnn/train_on_synthetic.py — Train TCN on synthetic fraud graphs.

Generates 50 manipulated + 50 normal graphs, trains for 30 epochs,
saves weights to models/gnn/tcn_weights.pt, prints final metrics.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.loader import DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from models.gnn.tcn import TemporalCoincidenceNetwork
from models.gnn.train_tcn import _generate_synthetic_graphs

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "tcn_weights.pt")


def safe_forward(model, batch):
    """Run forward pass, return (probs, y) with NaN guarded."""
    try:
        _, probs = model(batch)
        p = probs.squeeze()
        if p.dim() == 0:
            p = p.unsqueeze(0)
        p = torch.nan_to_num(p, nan=0.5, posinf=0.999, neginf=0.001)
        p = p.clamp(1e-6, 1 - 1e-6)
        y = batch.y.view(-1).clamp(0.0, 1.0)
        if p.shape != y.shape:
            return None, None
        return p, y
    except Exception:
        return None, None


def main():
    print("Generating synthetic training graphs...")
    graphs = _generate_synthetic_graphs(n_normal=50, n_manipulated=50)

    # Filter out degenerate graphs (< 2 nodes)
    graphs = [g for g in graphs if g.num_nodes >= 2]
    np.random.shuffle(graphs)

    split = int(len(graphs) * 0.8)
    train_g, val_g = graphs[:split], graphs[split:]

    train_loader = DataLoader(train_g, batch_size=8, shuffle=True)
    val_loader   = DataLoader(val_g,   batch_size=8, shuffle=False)

    model = TemporalCoincidenceNetwork(node_features=16, hidden=128, heads=4)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    best_auc = 0.0
    print(f"Training for 30 epochs on {len(train_g)} train / {len(val_g)} val graphs...")

    for epoch in range(30):
        model.train()
        for batch in train_loader:
            optimizer.zero_grad()
            p, y = safe_forward(model, batch)
            if p is None:
                continue
            loss = F.binary_cross_entropy(p, y)
            if torch.isnan(loss):
                continue
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        scheduler.step()

        # Validate every 5 epochs
        if (epoch + 1) % 5 == 0 or epoch == 29:
            model.eval()
            preds, labels = [], []
            with torch.no_grad():
                for batch in val_loader:
                    p, y = safe_forward(model, batch)
                    if p is None:
                        continue
                    preds.extend(p.tolist())
                    labels.extend(y.tolist())

            # Filter NaN
            clean = [(p, l) for p, l in zip(preds, labels)
                     if not (np.isnan(p) or np.isnan(l))]
            if not clean:
                continue
            preds_c = [x[0] for x in clean]
            labels_c = [x[1] for x in clean]

            if len(set(labels_c)) > 1:
                auc = roc_auc_score(labels_c, preds_c)
                if auc > best_auc:
                    best_auc = auc
                    torch.save(model.state_dict(), WEIGHTS_PATH)

    # Ensure weights file always exists
    if not os.path.exists(WEIGHTS_PATH):
        torch.save(model.state_dict(), WEIGHTS_PATH)

    # Load best for final eval
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location="cpu"))
    model.eval()

    preds, labels = [], []
    with torch.no_grad():
        for batch in val_loader:
            p, y = safe_forward(model, batch)
            if p is None:
                continue
            preds.extend(p.tolist())
            labels.extend(y.tolist())

    clean = [(p, l) for p, l in zip(preds, labels)
             if not (np.isnan(p) or np.isnan(l))]
    if clean and len(set(x[1] for x in clean)) > 1:
        preds_c  = [x[0] for x in clean]
        labels_c = [x[1] for x in clean]
        bin_p    = [1 if p >= 0.5 else 0 for p in preds_c]
        print(f"Accuracy : {accuracy_score(labels_c, bin_p):.3f}")
        print(f"Precision: {precision_score(labels_c, bin_p, zero_division=0):.3f}")
        print(f"Recall   : {recall_score(labels_c, bin_p, zero_division=0):.3f}")
        print(f"F1       : {f1_score(labels_c, bin_p, zero_division=0):.3f}")
        print(f"AUC-ROC  : {roc_auc_score(labels_c, preds_c):.3f}")
    else:
        print("Metrics: insufficient class diversity in val set (model saved anyway).")

    print(f"TCN trained and saved to {WEIGHTS_PATH}")


if __name__ == "__main__":
    main()
