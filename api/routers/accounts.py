"""
api/routers/accounts.py — Account DNA, trade history, and network graph endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import networkx as nx
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.schemas import AccountDNAOut, AccountNetworkOut, AccountOut, TradeOut
from data.db.crud import get_account, get_trades, search_accounts
from data.db.session import get_db

router = APIRouter()


@router.get("/search", response_model=list[AccountOut])
async def search_accounts_endpoint(
    broker: Optional[str] = Query(None),
    is_flagged: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Searches accounts by broker, flagged status."""
    accounts = search_accounts(db, broker=broker, is_flagged=is_flagged, limit=limit, offset=offset)
    return [AccountOut.model_validate(a) for a in accounts]


@router.get("/{account_id}/dna", response_model=AccountDNAOut)
async def get_account_dna(
    account_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Returns the 32-dim behavioral DNA vector for an account
    plus similarity to known fraudsters.
    """
    account = get_account(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    dna_vector = account.behavioral_dna or []
    fraudster_matches: list[dict] = []
    reconstruction_error = 0.0
    is_anomalous = False

    if dna_vector:
        try:
            import numpy as np
            from models.dna.fingerprint_store import FingerprintStore
            from models.dna.autoencoder import get_autoencoder, extract_features

            dna_arr = np.array(dna_vector, dtype=np.float32)
            fp_store = FingerprintStore()
            fraudster_matches = fp_store.find_similar(dna_arr, threshold=0.80)

            ae = get_autoencoder()
            # Re-extract features for reconstruction error
            trades = get_trades(db, account_id=account_id, limit=500)
            if trades:
                rows = [{
                    "account_id": t.account_id, "scrip": t.scrip,
                    "timestamp": t.timestamp, "price": t.price,
                    "volume": t.volume, "side": t.side.value if hasattr(t.side, "value") else str(t.side),
                } for t in trades]
                trade_df = pd.DataFrame(rows)
                feats = extract_features(trade_df)
                reconstruction_error = ae.reconstruction_error(feats)
                is_anomalous = reconstruction_error > 0.5
        except Exception:
            pass

    return AccountDNAOut(
        account_id=account_id,
        dna_vector=dna_vector,
        fraudster_matches=fraudster_matches,
        reconstruction_error=round(reconstruction_error, 4),
        is_anomalous=is_anomalous,
    )


@router.get("/{account_id}/trades", response_model=list[TradeOut])
async def get_account_trades(
    account_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Paginated trade history for an account."""
    trades = get_trades(
        db,
        account_id=account_id,
        from_dt=from_date,
        to_dt=to_date,
        limit=limit,
        offset=offset,
    )
    result = []
    for t in trades:
        result.append(TradeOut(
            id=t.id,
            account_id=t.account_id,
            scrip=t.scrip,
            exchange=t.exchange.value if hasattr(t.exchange, "value") else str(t.exchange),
            timestamp=t.timestamp,
            price=t.price,
            volume=t.volume,
            side=t.side.value if hasattr(t.side, "value") else str(t.side),
            order_type=t.order_type,
            is_manipulated=t.is_manipulated,
            created_at=t.created_at,
        ))
    return result


@router.get("/{account_id}/network", response_model=AccountNetworkOut)
async def get_account_network(
    account_id: str,
    scrip: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Returns NetworkX graph of connected accounts within 2 hops
    in the temporal coincidence graph. Returned as JSON nodes/edges.
    """
    from models.gnn.tcn import build_trade_graph

    trades = get_trades(
        db,
        account_id=account_id,
        scrip=scrip,
        from_dt=from_date,
        to_dt=to_date,
        limit=5000,
    )
    if not trades:
        return AccountNetworkOut(account_id=account_id, nodes=[], edges=[])

    rows = [{
        "account_id": t.account_id,
        "scrip": t.scrip,
        "timestamp": t.timestamp,
        "price": t.price,
        "volume": t.volume,
        "side": t.side.value if hasattr(t.side, "value") else str(t.side),
    } for t in trades]
    trade_df = pd.DataFrame(rows)

    graph_data = build_trade_graph(trade_df, window_ms=50, min_coincidences=2)

    account_ids = list(graph_data.account_ids)
    nodes = [
        {
            "id": acc,
            "label": acc[:8],
            "is_target": acc == account_id,
            "index": i,
        }
        for i, acc in enumerate(account_ids)
    ]

    edges = []
    if graph_data.edge_index.shape[1] > 0:
        ei = graph_data.edge_index.numpy()
        ea = graph_data.edge_attr.numpy() if graph_data.edge_attr is not None else [1.0] * (ei.shape[1])
        for k in range(0, ei.shape[1], 2):  # step 2 to avoid duplicate undirected
            src = int(ei[0, k])
            dst = int(ei[1, k])
            w = float(ea[k]) if k < len(ea) else 1.0
            edges.append({
                "source": account_ids[src],
                "target": account_ids[dst],
                "weight": round(w, 4),
            })

    # Limit to 2-hop from target account
    target_idx = next((i for i, n in enumerate(nodes) if n["id"] == account_id), None)
    if target_idx is not None:
        two_hop_ids = {account_id}
        for edge in edges:
            if edge["source"] == account_id or edge["target"] == account_id:
                two_hop_ids.add(edge["source"])
                two_hop_ids.add(edge["target"])
        second_hop_edges = [e for e in edges if e["source"] in two_hop_ids or e["target"] in two_hop_ids]
        for edge in second_hop_edges:
            two_hop_ids.add(edge["source"])
            two_hop_ids.add(edge["target"])
        nodes = [n for n in nodes if n["id"] in two_hop_ids]
        edges = [e for e in edges if e["source"] in two_hop_ids and e["target"] in two_hop_ids]

    return AccountNetworkOut(account_id=account_id, nodes=nodes, edges=edges)
