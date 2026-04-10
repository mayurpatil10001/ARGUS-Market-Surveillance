"""
scoring/mitigation_engine.py — Real-Time Alert Mitigation Engine for ARGUS.
Recommends, applies, dismisses, and escalates mitigation actions for alerts.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

logger = logging.getLogger(__name__)

# ── Severity thresholds ───────────────────────────────────────────────────────
_CRITICAL_THRESHOLD = 9.0
_HIGH_THRESHOLD = 8.0
_MEDIUM_THRESHOLD = 7.5

# ── Action constants ──────────────────────────────────────────────────────────
ACTION_FREEZE_ESCALATE  = "freeze_accounts_and_escalate_sebi"
ACTION_FREEZE_REVIEW    = "freeze_accounts_pending_review"
ACTION_FLAG_INVESTIGATE = "flag_accounts_for_investigation"
ACTION_BLOCK_SOCIAL     = "block_social_signals_and_alert_compliance"
ACTION_FLAG_CONTENT     = "flag_content_and_notify_exchange"
ACTION_BLOCK_DOMAIN     = "block_domain_and_alert_users"
ACTION_ISOLATE_ESCALATE = "isolate_entity_and_escalate"
ACTION_FLAG_ENTITY      = "flag_entity_for_review"
ACTION_MONITOR          = "monitor_and_log"

# Schemes that trigger auto-mitigation at critical severity
_CRITICAL_AUTO_SCHEMES = {"pump_and_dump", "spoofing"}


class MitigationEngine:
    """
    Recommends and applies mitigation actions for ARGUS alerts.
    """

    # ── Core recommendation logic ─────────────────────────────────────────────

    def recommend(
        self,
        alert_score: float,
        threat_type: str,
        scheme_type: str,
        gnn_score: float = 0.0,
        dna_score: float = 0.0,
        zero_day_score: float = 0.0,
        social_signal_score: float = 0.0,
        misinfo_score: float = 0.0,
    ) -> dict:
        """
        Returns a recommendation dict:
          {recommended_action, severity, auto_mitigate, escalate_to_sebi, rationale}
        """
        severity = self._assign_severity(alert_score)
        action   = self._assign_action(threat_type, severity)
        auto     = self._should_auto_mitigate(threat_type, severity, scheme_type, misinfo_score)
        escalate = self._should_escalate(severity, gnn_score, social_signal_score, misinfo_score)
        rationale = self._build_rationale(
            severity, threat_type, scheme_type, alert_score,
            gnn_score, dna_score, zero_day_score,
            social_signal_score, misinfo_score,
            auto, escalate,
        )
        return {
            "recommended_action": action,
            "severity": severity,
            "auto_mitigate": auto,
            "escalate_to_sebi": escalate,
            "rationale": rationale,
        }

    # ── DB mutation methods ───────────────────────────────────────────────────

    def apply(
        self,
        db: Session,
        alert_id,
        action: str,
        applied_by: str,
        notes: Optional[str] = None,
    ):
        """Apply a mitigation action to an alert."""
        from data.db.models import Alert
        alert = db.query(Alert).filter(Alert.id == str(alert_id)).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        alert.mitigation_status = "applied"
        alert.mitigation_applied_at = datetime.now(tz=timezone.utc)
        alert.mitigation_applied_by = applied_by
        alert.recommended_action = action
        if notes:
            alert.mitigation_notes = notes
        db.commit()
        db.refresh(alert)
        logger.info(f"Mitigation applied to {alert_id} by {applied_by}: {action}")
        return alert

    def dismiss(
        self,
        db: Session,
        alert_id,
        dismissed_by: str,
        reason: str,
    ):
        """Dismiss the recommended mitigation for an alert."""
        from data.db.models import Alert
        alert = db.query(Alert).filter(Alert.id == str(alert_id)).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        alert.mitigation_status = "dismissed"
        alert.mitigation_notes = reason
        alert.mitigation_applied_by = dismissed_by
        alert.mitigation_applied_at = datetime.now(tz=timezone.utc)
        db.commit()
        db.refresh(alert)
        logger.info(f"Mitigation dismissed for {alert_id} by {dismissed_by}: {reason}")
        return alert

    def escalate(
        self,
        db: Session,
        alert_id,
        escalated_by: str,
    ):
        """Escalate alert to SEBI."""
        from data.db.models import Alert
        alert = db.query(Alert).filter(Alert.id == str(alert_id)).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        alert.mitigation_status = "escalated"
        alert.escalated_to_sebi = True
        alert.escalation_timestamp = datetime.now(tz=timezone.utc)
        alert.mitigation_applied_by = escalated_by
        alert.mitigation_applied_at = datetime.now(tz=timezone.utc)
        db.commit()
        db.refresh(alert)
        logger.info(f"Alert {alert_id} escalated to SEBI by {escalated_by}")
        return alert

    def get_mitigation_summary(self, db: Session) -> dict:
        """Return aggregated mitigation statistics."""
        from data.db.models import Alert
        from sqlalchemy import case as sa_case

        total = db.query(func.count(Alert.id)).scalar() or 0

        def _count(filter_expr):
            return db.query(func.count(Alert.id)).filter(filter_expr).scalar() or 0

        pending   = _count(Alert.mitigation_status == "pending")
        applied   = _count(Alert.mitigation_status == "applied")
        dismissed = _count(Alert.mitigation_status == "dismissed")
        escalated = _count(Alert.mitigation_status == "escalated")
        auto_mit  = _count(Alert.auto_mitigated == True)  # noqa: E712
        esc_sebi  = _count(Alert.escalated_to_sebi == True)  # noqa: E712

        # By severity
        by_severity = {}
        for sev in ("low", "medium", "high", "critical"):
            by_severity[sev] = _count(Alert.severity == sev)

        # By action
        rows = (
            db.query(Alert.recommended_action, func.count(Alert.id))
            .filter(Alert.recommended_action.isnot(None))
            .group_by(Alert.recommended_action)
            .all()
        )
        by_action = {r[0]: r[1] for r in rows}

        return {
            "total_alerts": total,
            "pending_mitigation": pending,
            "applied": applied,
            "dismissed": dismissed,
            "escalated": escalated,
            "auto_mitigated": auto_mit,
            "escalated_to_sebi": esc_sebi,
            "by_severity": by_severity,
            "by_action": by_action,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _assign_severity(self, score: float) -> str:
        if score >= _CRITICAL_THRESHOLD:
            return "critical"
        if score >= _HIGH_THRESHOLD:
            return "high"
        if score >= _MEDIUM_THRESHOLD:
            return "medium"
        return "low"

    def _assign_action(self, threat_type: str, severity: str) -> str:
        if threat_type == "market_manipulation":
            if severity == "critical":
                return ACTION_FREEZE_ESCALATE
            if severity == "high":
                return ACTION_FREEZE_REVIEW
            if severity == "medium":
                return ACTION_FLAG_INVESTIGATE
            return ACTION_MONITOR
        if threat_type == "social_media_threat":
            return ACTION_BLOCK_SOCIAL
        if threat_type == "misinformation":
            return ACTION_FLAG_CONTENT
        if threat_type == "phishing":
            return ACTION_BLOCK_DOMAIN
        if threat_type == "generic_digital_threat":
            if severity == "critical":
                return ACTION_ISOLATE_ESCALATE
            if severity in ("high", "medium"):
                return ACTION_FLAG_ENTITY
            return ACTION_MONITOR
        return ACTION_MONITOR

    def _should_auto_mitigate(
        self,
        threat_type: str,
        severity: str,
        scheme_type: str,
        misinfo_score: float,
    ) -> bool:
        if threat_type == "phishing":
            return True
        if threat_type == "misinformation" and misinfo_score > 0.85:
            return True
        if severity == "critical" and scheme_type in _CRITICAL_AUTO_SCHEMES:
            return True
        return False

    def _should_escalate(
        self,
        severity: str,
        gnn_score: float,
        social_signal_score: float,
        misinfo_score: float,
    ) -> bool:
        if severity == "critical":
            return True
        if severity == "high" and gnn_score > 0.8:
            return True
        if social_signal_score > 0.8 and misinfo_score > 0.7:
            return True
        return False

    def _build_rationale(
        self,
        severity: str,
        threat_type: str,
        scheme_type: str,
        score: float,
        gnn_score: float,
        dna_score: float,
        zero_day_score: float,
        social_signal_score: float,
        misinfo_score: float,
        auto: bool,
        escalate: bool,
    ) -> str:
        parts = [
            f"Score {score:.2f}/10 → severity={severity.upper()}.",
            f"Threat type: {threat_type}, scheme: {scheme_type}.",
        ]
        if gnn_score > 8.0:
            parts.append(f"GNN score {gnn_score:.1f} indicates high coordination probability.")
        if dna_score > 8.0:
            parts.append(f"DNA score {dna_score:.1f} matches known fraudster behavioral profile.")
        if zero_day_score > 8.0:
            parts.append(f"Zero-day score {zero_day_score:.1f} — novel unseen manipulation pattern.")
        if social_signal_score > 0.7:
            parts.append(f"Social signal score {social_signal_score:.2f} — coordinated campaign detected.")
        if misinfo_score > 0.7:
            parts.append(f"Misinformation score {misinfo_score:.2f} — likely fake content driving price action.")
        if auto:
            parts.append("AUTO-MITIGATION triggered.")
        if escalate:
            parts.append("Flagged for SEBI escalation.")
        return " ".join(parts)


# Singleton
_mitigation_engine: Optional[MitigationEngine] = None


def get_mitigation_engine() -> MitigationEngine:
    global _mitigation_engine
    if _mitigation_engine is None:
        _mitigation_engine = MitigationEngine()
    return _mitigation_engine
