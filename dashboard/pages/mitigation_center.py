"""
dashboard/pages/mitigation_center.py — ARGUS Mitigation Center Streamlit page.
Displays pending mitigations, severity breakdown, and action buttons.
"""
import time
from datetime import datetime

import requests
import streamlit as st

_SEVERITY_COLORS = {
    "critical": "#ff3355",
    "high": "#ff8c00",
    "medium": "#ffb300",
    "low": "#4caf50",
}

_ACTION_LABELS = {
    "freeze_accounts_and_escalate_sebi": "FREEZE + ESCALATE",
    "freeze_accounts_pending_review": "FREEZE ACCOUNTS",
    "flag_accounts_for_investigation": "FLAG INVESTIGATE",
    "block_social_signals_and_alert_compliance": "BLOCK SOCIAL",
    "flag_content_and_notify_exchange": "FLAG CONTENT",
    "block_domain_and_alert_users": "BLOCK DOMAIN",
    "isolate_entity_and_escalate": "ISOLATE + ESCALATE",
    "flag_entity_for_review": "FLAG ENTITY",
    "monitor_and_log": "MONITOR",
}


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _get_summary(api_base, token):
    try:
        r = requests.get(f"{api_base}/alerts/mitigation/summary",
                         headers=_headers(token), timeout=5)
        return r.json() if r.ok else {}
    except Exception:
        return {}


def _get_pending(api_base, token, severity=None):
    try:
        params = {"limit": 50}
        if severity and severity != "All":
            params["severity"] = severity.lower()
        r = requests.get(f"{api_base}/alerts/mitigation/pending",
                         headers=_headers(token), params=params, timeout=5)
        return r.json() if r.ok else []
    except Exception:
        return []


def _apply(api_base, token, alert_id, action):
    try:
        r = requests.post(
            f"{api_base}/alerts/{alert_id}/mitigate",
            headers=_headers(token),
            json={"action": action, "applied_by": "analyst", "notes": "Applied via dashboard"},
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def _dismiss(api_base, token, alert_id):
    try:
        r = requests.post(
            f"{api_base}/alerts/{alert_id}/dismiss-mitigation",
            headers=_headers(token),
            json={"dismissed_by": "analyst", "reason": "Dismissed via dashboard"},
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def _escalate(api_base, token, alert_id):
    try:
        r = requests.post(
            f"{api_base}/alerts/{alert_id}/escalate",
            headers=_headers(token),
            json={"escalated_by": "analyst"},
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def render(api_base: str, token: str):
    st.markdown("## ARGUS Mitigation Center")
    st.caption("Real-time alert triage — apply, dismiss, or escalate recommended actions.")

    # Auto-refresh
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)
    if auto_refresh:
        if "last_refresh" not in st.session_state:
            st.session_state["last_refresh"] = time.time()
        if time.time() - st.session_state["last_refresh"] > 30:
            st.session_state["last_refresh"] = time.time()
            st.rerun()

    # Severity filter
    sev_filter = st.selectbox(
        "Filter by severity", ["All", "Critical", "High", "Medium", "Low"], index=0
    )

    summary = _get_summary(api_base, token)
    pending_list = _get_pending(api_base, token, sev_filter)

    # ── Top metric cards ──
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Alerts", summary.get("total_alerts", 0))
    col2.metric("Pending", summary.get("pending_mitigation", 0), delta=None)
    col3.metric("Applied", summary.get("applied", 0))
    col4.metric("Escalated", summary.get("escalated", 0))
    col5.metric("Auto-Mitigated", summary.get("auto_mitigated", 0))

    st.markdown("---")

    # ── Severity breakdown ──
    by_sev = summary.get("by_severity", {})
    if by_sev:
        try:
            import plotly.graph_objects as go
            fig = go.Figure(go.Bar(
                x=list(by_sev.keys()),
                y=list(by_sev.values()),
                marker_color=[_SEVERITY_COLORS.get(k, "#888") for k in by_sev.keys()],
                text=list(by_sev.values()),
                textposition="outside",
            ))
            fig.update_layout(
                title="Alerts by Severity",
                paper_bgcolor="#0d1b2a",
                plot_bgcolor="#0d1b2a",
                font={"color": "#e0e0e0", "size": 11},
                height=220,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#1f3050"),
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            for sev, cnt in by_sev.items():
                st.write(f"**{sev.upper()}**: {cnt}")

    st.markdown("---")
    st.markdown(f"### Pending Mitigation ({len(pending_list)})")

    if not pending_list:
        st.success("No alerts pending mitigation action.")
        return

    # ── Pending table ──
    for alert in pending_list:
        a_id = str(alert.get("id", ""))
        scrip = alert.get("scrip", "N/A")
        sev = alert.get("severity", "medium")
        score = alert.get("impossibility_score", 0.0)
        action = alert.get("recommended_action") or "monitor_and_log"
        action_label = _ACTION_LABELS.get(action, action.upper().replace("_", " "))
        detected = alert.get("detected_at", "")[:16] if alert.get("detected_at") else ""
        sev_color = _SEVERITY_COLORS.get(sev, "#888")

        with st.expander(
            f"[{sev.upper()}] {scrip} — Score: {score:.1f}/10 — {action_label}",
            expanded=False,
        ):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"**Scrip:** {scrip}")
                st.markdown(f"**Score:** {score:.2f}/10")
                st.markdown(f"**Severity:** :{'red' if sev=='critical' else 'orange' if sev=='high' else 'yellow' if sev=='medium' else 'green'}[{sev.upper()}]")
            with c2:
                st.markdown(f"**Scheme:** {alert.get('scheme_type','N/A')}")
                st.markdown(f"**Threat:** {alert.get('threat_type','N/A')}")
                st.markdown(f"**Detected:** {detected}")
            with c3:
                st.markdown(f"**Recommended:** `{action_label}`")
                st.markdown(f"**Accounts involved:** {len(alert.get('accounts_involved', []))}")
                if alert.get("mitigation_notes"):
                    st.caption(f"Rationale: {alert['mitigation_notes'][:120]}...")

            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button(f"APPLY — {action_label}", key=f"apply_{a_id}",
                             type="primary", use_container_width=True):
                    if _apply(api_base, token, a_id, action):
                        st.success("Mitigation applied.")
                        st.rerun()
                    else:
                        st.error("Failed to apply. Is API running?")
            with b2:
                if st.button("DISMISS", key=f"dismiss_{a_id}", use_container_width=True):
                    if _dismiss(api_base, token, a_id):
                        st.warning("Mitigation dismissed.")
                        st.rerun()
                    else:
                        st.error("Failed to dismiss.")
            with b3:
                if st.button("ESCALATE TO SEBI", key=f"escalate_{a_id}",
                             use_container_width=True):
                    if _escalate(api_base, token, a_id):
                        st.error("Escalated to SEBI.")
                        st.rerun()
                    else:
                        st.error("Escalation failed.")
