"""
scoring/alert_engine.py — Central alert orchestration engine.
Runs all 4 AI detection models, computes composite score, creates DB alerts.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from scoring.impossibility import compute_composite_score, compute_poisson_impossibility

logger = logging.getLogger(__name__)

ALERT_THRESHOLD = float(os.getenv("ALERT_SCORE_THRESHOLD", "7.5"))


class AlertEngine:
    """
    Orchestrates all ARGUS detection models and creates DB alerts.
    """

    def __init__(self, session, redis_client=None, threshold: float = ALERT_THRESHOLD):
        self.session = session
        self.redis = redis_client
        self.threshold = threshold

        # Lazy-loaded models
        self._tcn_model = None
        self._autoencoder = None
        self._zero_day = None
        self._fp_store = None
        self._fusion = None

    def _get_tcn(self):
        if self._tcn_model is None:
            from models.gnn.train_tcn import load_model
            self._tcn_model = load_model()
        return self._tcn_model

    def _get_autoencoder(self):
        if self._autoencoder is None:
            from models.dna.autoencoder import get_autoencoder
            self._autoencoder = get_autoencoder()
        return self._autoencoder

    def _get_zero_day(self):
        if self._zero_day is None:
            from models.zero_day.anomaly import get_detector
            self._zero_day = get_detector()
        return self._zero_day

    def _get_fp_store(self):
        if self._fp_store is None:
            from models.dna.fingerprint_store import FingerprintStore
            self._fp_store = FingerprintStore()
        return self._fp_store

    def _get_fusion(self):
        if self._fusion is None:
            from models.cross_market.fusion import CrossMarketFusion
            self._fusion = CrossMarketFusion()
        return self._fusion

    def run_full_scan(
        self,
        scrip: str,
        from_dt: datetime,
        to_dt: datetime,
    ) -> Optional[object]:
        """
        Runs complete ARGUS scan for given scrip + window.
        Returns created Alert ORM object if score >= threshold, else None.
        """
        from data.db.crud import get_trades, create_alert
        from models.gnn.tcn import build_trade_graph
        from models.dna.autoencoder import extract_features
        from scoring.impossibility import compute_synchrony_chi2

        # 1. Load trades from DB
        trades = get_trades(
            self.session, scrip=scrip, from_dt=from_dt, to_dt=to_dt, limit=10000
        )
        if len(trades) < 5:
            return None

        trade_rows = [
            {
                "account_id": t.account_id,
                "scrip": t.scrip,
                "timestamp": t.timestamp,
                "price": t.price,
                "volume": t.volume,
                "side": t.side.value if hasattr(t.side, "value") else str(t.side),
            }
            for t in trades
        ]
        trades_df = pd.DataFrame(trade_rows)

        # 2. GNN — Temporal Coincidence Network
        gnn_score = 0.0
        accounts_involved = list(trades_df["account_id"].unique())
        try:
            graph = build_trade_graph(trades_df, window_ms=50, min_coincidences=3)
            tcn = self._get_tcn()
            import torch
            with torch.no_grad():
                _, prob = tcn(graph)
            gnn_raw = float(prob.squeeze().item())
            gnn_score = round(gnn_raw * 10.0, 3)

            # Poisson impossibility from edge count
            n_edges = graph.edge_index.shape[1] // 2
            poisson_score = compute_poisson_impossibility(
                observed_coincidences=n_edges,
                n_accounts=len(accounts_involved),
                n_trades=len(trades),
                window_ms=50.0,
            )
            gnn_score = round((gnn_score + poisson_score) / 2.0, 3)
        except Exception as exc:
            logger.warning(f"GNN scoring failed for {scrip}: {exc}")

        # 3. DNA — Behavioral fingerprint matching
        dna_score = 0.0
        try:
            ae = self._get_autoencoder()
            fp_store = self._get_fp_store()
            dna_sim_threshold = float(os.getenv("DNA_SIMILARITY_THRESHOLD", "0.85"))

            max_sim = 0.0
            for acc_id, acc_trades in trades_df.groupby("account_id"):
                feats = extract_features(acc_trades)
                dna = ae.encode_numpy(feats)
                # Store DNA for future reference
                fp_store.store(acc_id, dna)
                matches = fp_store.find_similar(dna, threshold=dna_sim_threshold)
                if matches:
                    max_sim = max(max_sim, matches[0]["similarity"])

            dna_score = round(max_sim * 10.0, 3)
        except Exception as exc:
            logger.warning(f"DNA scoring failed for {scrip}: {exc}")

        # 4. Cross-market fusion
        cross_market_score = 0.0
        try:
            fusion = self._get_fusion()
            cross_market_score = fusion.cross_market_score(
                scrip, from_dt, to_dt, self.session
            )
        except Exception as exc:
            logger.warning(f"Cross-market scoring failed for {scrip}: {exc}")

        # 5. Zero-day anomaly detection
        zero_day_score = 0.0
        try:
            detector = self._get_zero_day()
            feature_matrix = detector.build_session_features(trades_df, window_minutes=30)
            zd_scores = detector.score(feature_matrix)
            zero_day_score = round(float(zd_scores.max()), 3)
        except Exception as exc:
            logger.warning(f"Zero-day scoring failed for {scrip}: {exc}")

        # 6. Composite score
        overall = compute_composite_score(
            gnn_score, zero_day_score, dna_score, cross_market_score
        )

        # 7. Classify scheme type from relative scores
        scheme_type = _classify_scheme(
            gnn_score, dna_score, cross_market_score, zero_day_score
        )

        logger.info(
            f"ARGUS scan {scrip} [{from_dt.date()}–{to_dt.date()}]: "
            f"GNN={gnn_score} DNA={dna_score} CM={cross_market_score} "
            f"ZD={zero_day_score} OVERALL={overall} (threshold={self.threshold})"
        )

        # 8. Create Alert if above threshold
        if overall >= self.threshold:
            alert = create_alert(
                self.session,
                scrip=scrip,
                exchange="NSE",
                detected_at=datetime.utcnow(),
                impossibility_score=overall,
                scheme_type=scheme_type,
                accounts_involved=accounts_involved[:50],  # cap at 50
                gnn_score=gnn_score,
                dna_score=dna_score,
                cross_market_score=cross_market_score,
                zero_day_score=zero_day_score,
            )
            return alert

        return None

    def run_all_active_scrips(
        self,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list:
        """
        Fetches all scrips with trades in the window, runs scan for each.
        Returns alerts sorted by impossibility_score descending.
        """
        from data.db.crud import get_distinct_scrips

        scrips = get_distinct_scrips(self.session, from_dt, to_dt)
        alerts = []
        for scrip in scrips:
            try:
                alert = self.run_full_scan(scrip, from_dt, to_dt)
                if alert:
                    alerts.append(alert)
            except Exception as exc:
                logger.error(f"Scan failed for {scrip}: {exc}", exc_info=True)

        alerts.sort(key=lambda a: a.impossibility_score, reverse=True)
        return alerts


def _classify_scheme(
    gnn: float,
    dna: float,
    cross_market: float,
    zero_day: float,
) -> str:
    """Infers likely manipulation scheme from model scores."""
    if gnn > 8.0:
        return "pump_and_dump"
    if cross_market > 7.0:
        return "circular_trading"
    if dna > 7.0 and gnn > 5.0:
        return "spoofing"
    if zero_day > 8.0:
        return "zero_day_anomaly"
    if gnn > 6.0 and cross_market > 5.0:
        return "insider_trading"
    return "suspected_manipulation"
