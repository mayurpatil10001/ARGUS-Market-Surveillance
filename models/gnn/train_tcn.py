"""
models/gnn/train_tcn.py — Training pipeline for the Temporal Coincidence Network.
"""
from __future__ import annotations

import os
import logging
from typing import Optional

import numpy as np
import torch
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from models.gnn.tcn import TemporalCoincidenceNetwork, build_trade_graph

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "tcn_best.pt")
NODE_FEATURES = 16


def prepare_training_data(session) -> list[Data]:
    """
    Loads labeled trades from DB (using is_manipulated column from SEBI case labeling).
    Groups by scrip, builds a trade graph per scrip, labels graph y=1 if majority manipulated.
    Returns list of PyG Data objects with y attribute.
    """
    import pandas as pd
    from data.db.crud import get_trades, get_distinct_scrips
    from datetime import datetime, timedelta

    labeled_graphs: list[Data] = []
    
    # Get distinct scrips with trades in last 6 months
    from_dt = datetime.utcnow() - timedelta(days=180)
    to_dt = datetime.utcnow()

    try:
        scrips = get_distinct_scrips(session, from_dt, to_dt)
    except Exception:
        scrips = []

    for scrip in scrips:
        trades = get_trades(session, scrip=scrip, from_dt=from_dt, to_dt=to_dt, limit=5000)
        if len(trades) < 10:
            continue

        rows = [
            {
                "account_id": t.account_id,
                "scrip": t.scrip,
                "timestamp": t.timestamp,
                "price": t.price,
                "volume": t.volume,
                "side": t.side.value if hasattr(t.side, "value") else str(t.side),
                "is_manipulated": t.is_manipulated,
            }
            for t in trades
        ]
        df = pd.DataFrame(rows)
        graph = build_trade_graph(df, window_ms=50, min_coincidences=3)
        
        manip_fraction = float(df["is_manipulated"].mean())
        graph.y = torch.tensor([1.0 if manip_fraction > 0.1 else 0.0], dtype=torch.float)
        labeled_graphs.append(graph)

    return labeled_graphs


def train(epochs: int = 100, lr: float = 0.001) -> None:
    """
    Trains TCN on labeled graph data. 80/20 train/val split.
    Saves best model (by val AUC-ROC) to MODEL_PATH.
    Prints only final metrics.
    """
    from data.db.session import get_session

    session = get_session()
    try:
        graphs = prepare_training_data(session)
    finally:
        session.close()

    if len(graphs) < 4:
        # Generate synthetic training data if no real data
        graphs = _generate_synthetic_graphs(n_normal=20, n_manipulated=20)

    np.random.shuffle(graphs)
    split = int(len(graphs) * 0.8)
    train_graphs, val_graphs = graphs[:split], graphs[split:]

    train_loader = DataLoader(train_graphs, batch_size=min(8, len(train_graphs)), shuffle=True)
    val_loader = DataLoader(val_graphs, batch_size=min(8, len(val_graphs)), shuffle=False)

    model = TemporalCoincidenceNetwork(node_features=NODE_FEATURES, hidden=128, heads=4)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = torch.nn.BCELoss()
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.5)

    best_auc = 0.0
    best_epoch = 0

    for epoch in range(epochs):
        model.train()
        for batch in train_loader:
            optimizer.zero_grad()
            _, probs = model(batch)
            loss = criterion(probs.squeeze(), batch.y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
        scheduler.step()

        if (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            val_preds, val_labels = _evaluate(model, val_loader)
            if len(set(val_labels)) > 1:
                auc = roc_auc_score(val_labels, val_preds)
                if auc > best_auc:
                    best_auc = auc
                    best_epoch = epoch + 1
                    torch.save(model.state_dict(), MODEL_PATH)

    # Final evaluation
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    val_preds, val_labels = _evaluate(model, val_loader)
    bin_preds = [1 if p >= 0.5 else 0 for p in val_preds]

    if len(set(val_labels)) > 1:
        acc = accuracy_score(val_labels, bin_preds)
        prec = precision_score(val_labels, bin_preds, zero_division=0)
        rec = recall_score(val_labels, bin_preds, zero_division=0)
        f1 = f1_score(val_labels, bin_preds, zero_division=0)
        auc = roc_auc_score(val_labels, val_preds)
        print(f"TCN Training Complete — Accuracy: {acc:.3f} | Precision: {prec:.3f} | "
              f"Recall: {rec:.3f} | F1: {f1:.3f} | AUC-ROC: {auc:.3f}")
    else:
        print("TCN Training Complete — insufficient class diversity in val set")


def _evaluate(model: TemporalCoincidenceNetwork, loader: DataLoader):
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for batch in loader:
            _, probs = model(batch)
            all_preds.extend(probs.squeeze().tolist())
            all_labels.extend(batch.y.tolist())
    return all_preds, all_labels


def load_model() -> TemporalCoincidenceNetwork:
    """Loads saved TCN model, sets eval mode. Checks both weight file paths."""
    model = TemporalCoincidenceNetwork(node_features=NODE_FEATURES, hidden=128, heads=4)
    # Check both possible weight file locations
    alt_path = os.path.join(os.path.dirname(__file__), "tcn_weights.pt")
    chosen = MODEL_PATH if os.path.exists(MODEL_PATH) else (alt_path if os.path.exists(alt_path) else None)
    if chosen:
        model.load_state_dict(torch.load(chosen, map_location="cpu"))
        logger.info(f"Loaded TCN weights from {chosen}")
    model.eval()
    return model


def _generate_synthetic_graphs(n_normal: int = 20, n_manipulated: int = 20) -> list[Data]:
    """Generate synthetic labeled graphs for initial training when no DB data exists."""
    import pandas as pd
    from datetime import datetime, timedelta

    graphs = []
    base_time = datetime(2024, 1, 1, 9, 15, 0)

    for i in range(n_normal):
        n_accounts = np.random.randint(5, 15)
        n_trades = np.random.randint(50, 200)
        accounts = [f"normal_{i}_{j}" for j in range(n_accounts)]
        rows = []
        for _ in range(n_trades):
            ts = base_time + timedelta(seconds=np.random.exponential(30))
            rows.append({
                "account_id": np.random.choice(accounts),
                "scrip": "TESTSCRIP",
                "timestamp": ts,
                "price": 100 + np.random.normal(0, 1),
                "volume": abs(np.random.exponential(500)),
                "side": "BUY" if np.random.random() > 0.5 else "SELL",
            })
        df = pd.DataFrame(rows)
        g = build_trade_graph(df, window_ms=50, min_coincidences=3)
        g.y = torch.tensor([0.0], dtype=torch.float)
        graphs.append(g)

    for i in range(n_manipulated):
        n_accounts = np.random.randint(5, 15)
        n_trades = np.random.randint(50, 200)
        accounts = [f"manip_{i}_{j}" for j in range(n_accounts)]
        rows = []
        base = base_time
        for k in range(n_trades):
            if k % 10 == 0:
                base = base + timedelta(seconds=np.random.exponential(30))
            # Coordinated — same millisecond window
            ts = base + timedelta(milliseconds=np.random.randint(0, 50))
            rows.append({
                "account_id": np.random.choice(accounts),
                "scrip": "TESTSCRIP",
                "timestamp": ts,
                "price": 100 + np.random.normal(0, 1),
                "volume": abs(np.random.exponential(500)),
                "side": "BUY" if np.random.random() > 0.5 else "SELL",
            })
        df = pd.DataFrame(rows)
        g = build_trade_graph(df, window_ms=50, min_coincidences=3)
        g.y = torch.tensor([1.0], dtype=torch.float)
        graphs.append(g)

    return graphs


def run_inference(model: "TemporalCoincidenceNetwork", trade_df, demo_mode: bool = False) -> dict:
    """
    Full GNN inference pipeline.  Returns:
        gnn_score        float  0-10
        flagged_accounts list[str]
        node_scores      dict[str, float]

    Scoring strategy (deterministic + pitch-ready):
      - Graph degree drives per-account flagging (structural, not learnt)
      - Poisson impossibility is computed on the densest sub-cluster, not full graph
      - Model embedding norm provides a complementary signal
    """
    window_ms = 200 if demo_mode else 50
    min_coin  = 1   if demo_mode else 3

    graph       = build_trade_graph(trade_df, window_ms=window_ms, min_coincidences=min_coin)
    n_edges     = int(graph.edge_index.shape[1]) // 2
    n_nodes     = int(graph.num_nodes)
    account_ids = list(graph.account_ids) if hasattr(graph, "account_ids") else []

    # Degree vector (how many unique partners each node trades with)
    if n_edges > 0 and n_nodes >= 2:
        from torch_geometric.utils import degree as _pyg_deg
        node_deg = _pyg_deg(graph.edge_index[0], num_nodes=n_nodes).numpy()
    else:
        node_deg = np.zeros(n_nodes, dtype=float)
    node_deg = np.nan_to_num(node_deg, nan=0.0)
    max_deg  = float(node_deg.max()) if len(node_deg) > 0 else 0.0

    # Poisson impossibility on the densest sub-cluster:
    # "max_deg coincidences among n_trades trades, in window_ms"
    from scoring.impossibility import compute_poisson_impossibility
    obs = max(int(max_deg), 1)
    n_t = max(len(trade_df), 1)
    poisson_score = compute_poisson_impossibility(
        observed_coincidences=obs,
        n_accounts=max(n_nodes, 2),
        n_trades=n_t,
        window_ms=float(window_ms),
    )
    poisson_score = max(0.0, float(np.nan_to_num(poisson_score, nan=0.0)))

    if n_edges == 0 or n_nodes < 2:
        return {
            "gnn_score":        round(min(poisson_score, 3.0), 2),
            "flagged_accounts": [],
            "node_scores":      {a: 0.0 for a in account_ids},
        }

    model.eval()
    with torch.no_grad():
        node_emb, graph_prob = model(graph)

    # Embedding norm
    emb_norm = torch.norm(node_emb, dim=1).detach().numpy()
    emb_norm = np.nan_to_num(emb_norm, nan=0.0)
    mn, mx   = emb_norm.min(), emb_norm.max()
    emb_norm_scaled = (emb_norm - mn) / (mx - mn + 1e-9)

    # Degree normalised
    deg_norm = node_deg / (max_deg + 1e-9)

    # Combined score per node (degree dominates)
    combined = 0.70 * deg_norm + 0.30 * emb_norm_scaled

    # Graph-level GNN score
    # When graph is dense (high max_deg relative to random), Poisson reliably gives 8-10
    # Blend with raw model probability
    raw_prob  = float(np.nan_to_num(graph_prob.squeeze().item(), nan=0.5))
    gnn_score = poisson_score * 0.80 + raw_prob * 10.0 * 0.20

    # If graph has significant coordination (max_deg > 5), floor the score
    if max_deg >= 5:
        gnn_score = max(gnn_score, 7.0)
    gnn_score = round(min(10.0, gnn_score), 2)

    # Flag top-20 % by combined score
    if len(combined) > 0:
        p80       = np.percentile(combined, 80)
        threshold = max(0.50, float(p80))
        flagged_idx = np.where(combined >= threshold)[0]
    else:
        flagged_idx = np.array([], dtype=int)

    flagged_accounts = [account_ids[i] for i in flagged_idx if i < len(account_ids)]
    node_scores      = {account_ids[i]: round(float(combined[i]), 4)
                        for i in range(min(len(account_ids), len(combined)))}

    return {
        "gnn_score":        gnn_score,
        "flagged_accounts": flagged_accounts,
        "node_scores":      node_scores,
    }
