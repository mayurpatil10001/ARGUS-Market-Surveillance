"""
scoring/alert_engine.py — Central alert orchestration engine.
Runs all AI detection models, computes composite threat score, creates DB alerts.
SENTINEL: Scalable ENTity Intelligence for NEtwork-Level threat detection
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

THREAT_CATEGORIES = [
    "coordinated_attack",
    "malicious_content",
    "phishing",
    "misinformation",
    "platform_abuse",
    "novel_threat",
]


class AlertEngine:
    """
    Orchestrates all SENTINEL detection models and creates DB alerts.
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
        """Network Coordination Detector (GNN/TCN)."""
        if self._tcn_model is None:
            from models.gnn.train_tcn import load_model
            self._tcn_model = load_model()
        return self._tcn_model

    def _get_autoencoder(self):
        """Behavioral Anomaly Profiler (DNA Autoencoder)."""
        if self._autoencoder is None:
            from models.dna.autoencoder import get_autoencoder
            self._autoencoder = get_autoencoder()
        return self._autoencoder

    def _get_zero_day(self):
        """Novel Threat Detector (Zero-Day Ensemble)."""
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
        """Cross-Platform Threat Correlator (Cross-Market Fusion)."""
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
        Runs complete SENTINEL scan for given entity/platform + window.
        Returns created Alert ORM object if score >= threshold, else None.
        """
        from data.db.crud import get_trades, create_alert
        from models.gnn.tcn import build_trade_graph
        from models.dna.autoencoder import extract_features
        from scoring.impossibility import compute_synchrony_chi2

        # 1. Load data from DB
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

        # 2. Network Coordination Detector (GNN/TCN)
        # Detects coordinated bot networks, troll farms, fake account rings
        coordination_score = 0.0
        entities_involved = list(trades_df["account_id"].unique())
        try:
            graph = build_trade_graph(trades_df, window_ms=50, min_coincidences=3)
            tcn = self._get_tcn()
            import torch
            with torch.no_grad():
                _, prob = tcn(graph)
            gnn_raw = float(prob.squeeze().item())
            coordination_score = round(gnn_raw * 10.0, 3)

            # Poisson impossibility from edge count
            n_edges = graph.edge_index.shape[1] // 2
            poisson_score = compute_poisson_impossibility(
                observed_coincidences=n_edges,
                n_accounts=len(entities_involved),
                n_trades=len(trades),
                window_ms=50.0,
            )
            coordination_score = round((coordination_score + poisson_score) / 2.0, 3)
        except Exception as exc:
            logger.warning(f"Network Coordination Detector failed for {scrip}: {exc}")

        # 3. Behavioral Anomaly Profiler (DNA Autoencoder)
        # Flags abnormal user behavior patterns on platforms
        behavior_score = 0.0
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

            behavior_score = round(max_sim * 10.0, 3)
        except Exception as exc:
            logger.warning(f"Behavioral Anomaly Profiler failed for {scrip}: {exc}")

        # 4. Cross-Platform Threat Correlator
        # Correlates threats across Twitter, Reddit, Telegram, web
        cross_platform_score = 0.0
        try:
            fusion = self._get_fusion()
            cross_platform_score = fusion.cross_market_score(
                scrip, from_dt, to_dt, self.session
            )
        except Exception as exc:
            logger.warning(f"Cross-Platform Threat Correlator failed for {scrip}: {exc}")

        # 5. Novel Threat Detector (Zero-Day Ensemble)
        # Catches unseen attack patterns
        novelty_score = 0.0
        try:
            detector = self._get_zero_day()
            feature_matrix = detector.build_session_features(trades_df, window_minutes=30)
            zd_scores = detector.score(feature_matrix)
            novelty_score = round(float(zd_scores.max()), 3)
        except Exception as exc:
            logger.warning(f"Novel Threat Detector failed for {scrip}: {exc}")

        # 6. Composite threat score
        overall = compute_composite_score(
            coordination_score, novelty_score, behavior_score, cross_platform_score
        )

        # 7. Classify threat category from relative scores
        threat_category = _classify_threat(
            coordination_score, behavior_score, cross_platform_score, novelty_score
        )

        logger.info(
            f"SENTINEL scan {scrip} [{from_dt.date()}–{to_dt.date()}]: "
            f"COORD={coordination_score} BEHAV={behavior_score} "
            f"CROSS={cross_platform_score} NOVEL={novelty_score} "
            f"OVERALL={overall} (threshold={self.threshold})"
        )

        # 7.5 Attempt real-time social threat signal (best-effort, never blocks alert flow)
        social_signal_score_raw: float = 0.0
        try:
            from data.ingest.social_signal_fetcher import get_social_score_for_scrip
            social_signal_score_raw = get_social_score_for_scrip(scrip)  # returns [0, 10]
        except Exception as exc:
            logger.debug(f"Social threat monitor fetch skipped for {scrip}: {exc}")

        # 8. Create Alert if above threshold
        if overall >= self.threshold:
            alert = create_alert(
                self.session,
                scrip=scrip,
                exchange="web",
                detected_at=datetime.utcnow(),
                impossibility_score=overall,
                scheme_type=threat_category,
                accounts_involved=entities_involved[:50],  # cap at 50
                gnn_score=coordination_score,
                dna_score=behavior_score,
                cross_market_score=cross_platform_score,
                zero_day_score=novelty_score,
                social_signal_score=social_signal_score_raw,
                # misinfo_score stays 0.0 at creation — no text input from raw data
            )

            # 9. Populate mitigation recommendation immediately
            try:
                from scoring.mitigation_engine import get_mitigation_engine
                me = get_mitigation_engine()
                rec = me.recommend(
                    alert_score=overall,
                    threat_type=getattr(alert, "threat_type", "generic_digital_threat"),
                    scheme_type=threat_category,
                    gnn_score=coordination_score,
                    dna_score=behavior_score,
                    zero_day_score=novelty_score,
                    social_signal_score=social_signal_score_raw / 10.0,  # normalize to [0,1]
                    misinfo_score=0.0,
                )
                alert.recommended_action = rec["recommended_action"]
                alert.severity = rec["severity"]
                alert.auto_mitigated = rec["auto_mitigate"]
                alert.escalated_to_sebi = rec["escalate_to_sebi"]
                alert.mitigation_notes = rec["rationale"]
                if rec["auto_mitigate"]:
                    alert.mitigation_status = "applied"
                    alert.mitigation_applied_at = datetime.utcnow()
                    alert.mitigation_applied_by = "sentinel_auto"
                self.session.commit()
                self.session.refresh(alert)
            except Exception as exc:
                logger.warning(f"Mitigation recommendation failed: {exc}")

            return alert

        return None


    def run_all_active_scrips(
        self,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list:
        """
        Fetches all entities/scrips with signals in the window, runs scan for each.
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


def _classify_threat(
    coordination: float,
    behavior: float,
    cross_platform: float,
    novelty: float,
) -> str:
    """Infers likely digital threat category from model scores."""
    if coordination > 8.0:
        return "coordinated_attack"
    if cross_platform > 7.0:
        return "malicious_content"
    if behavior > 7.0 and coordination > 5.0:
        return "phishing"
    if novelty > 8.0:
        return "novel_threat"
    if coordination > 6.0 and cross_platform > 5.0:
        return "platform_abuse"
    return "misinformation"
