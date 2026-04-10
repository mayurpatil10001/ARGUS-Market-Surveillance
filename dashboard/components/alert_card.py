"""
dashboard/components/alert_card.py — Reusable alert card component.
"""
from __future__ import annotations

import streamlit as st


def render_alert_card(alert: dict) -> None:
    """Renders a styled alert card as a Streamlit container."""
    score = alert.get("impossibility_score", 0)
    scrip = alert.get("scrip", "UNKNOWN")
    scheme = alert.get("scheme_type", "unknown").replace("_", " ").title()
    status = alert.get("status", "open").upper()
    n_accounts = len(alert.get("accounts_involved", []))

    color = "#FF5252" if score >= 8 else "#FF9800" if score >= 6 else "#FFC107"
    icon = "🔴" if score >= 8 else "🟠" if score >= 6 else "🟡"

    st.markdown(
        f"""
        <div style="
            background: #1a2b5f;
            border-radius: 10px;
            padding: 1rem;
            border-left: 5px solid {color};
            margin-bottom: 0.5rem;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:1.1rem; font-weight:700; color:#C8A951;">{icon} {scrip}</span>
                <span style="font-size:1.4rem; font-weight:900; color:{color};">{score:.1f}/10</span>
            </div>
            <div style="color:#a0b0d0; font-size:0.85rem; margin-top:0.3rem;">
                {scheme} · {n_accounts} accounts · {status}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
