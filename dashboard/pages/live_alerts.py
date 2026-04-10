"""
dashboard/pages/live_alerts.py — Real-time alert monitoring page.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


def render(api_base: str, token: str) -> None:
    st.title("🚨 Live Alerts")
    st.caption("Real-time market manipulation detection — auto-refreshes every 30s")

    headers = {"Authorization": f"Bearer {token}"}

    # ── Fetch alerts ──────────────────────────────────────────────────────────
    alerts: list[dict] = []
    try:
        resp = requests.get(
            f"{api_base}/alerts",
            headers=headers,
            params={"limit": 100},
            timeout=10,
        )
        if resp.ok:
            alerts = resp.json()
    except Exception as exc:
        st.warning(f"API unavailable: {exc}. Showing demo data.")
        alerts = _demo_alerts()

    # ── Top metric cards ──────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    open_alerts = [a for a in alerts if a.get("status") == "open"]
    avg_score = sum(a.get("impossibility_score", 0) for a in alerts) / max(len(alerts), 1)
    flagged_today = len({acc for a in alerts for acc in a.get("accounts_involved", [])})
    sebi_cases = len([a for a in alerts if a.get("case_file_path")])

    with c1:
        st.metric("🔴 Active Alerts", len(open_alerts))
    with c2:
        st.metric("📊 Avg Score", f"{avg_score:.2f}/10")
    with c3:
        st.metric("👤 Accounts Flagged", flagged_today)
    with c4:
        st.metric("📁 Cases Sent", sebi_cases)

    st.markdown("---")

    # ── Filters ───────────────────────────────────────────────────────────────
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "open", "investigating", "closed", "false_positive"],
        )
    with col_filter2:
        min_score_filter = st.slider("Min Impossibility Score", 0.0, 10.0, 0.0, 0.5)
    with col_filter3:
        scrip_filter = st.text_input("Filter by Scrip", placeholder="e.g. RELIANCE")

    # Apply filters
    filtered = alerts
    if status_filter != "All":
        filtered = [a for a in filtered if a.get("status") == status_filter]
    if min_score_filter > 0:
        filtered = [a for a in filtered if a.get("impossibility_score", 0) >= min_score_filter]
    if scrip_filter:
        filtered = [a for a in filtered if scrip_filter.upper() in a.get("scrip", "").upper()]

    # ── Alerts table ──────────────────────────────────────────────────────────
    if not filtered:
        st.info("No alerts match the current filters.")
        return

    df = pd.DataFrame(filtered)
    if df.empty:
        st.info("No alerts found.")
        return

    # Color-code impossibility score
    def score_color(score: float) -> str:
        if score >= 8.0:
            return "🔴"
        elif score >= 6.0:
            return "🟠"
        else:
            return "🟡"

    df["score_badge"] = df["impossibility_score"].apply(
        lambda s: f"{score_color(s)} {s:.2f}"
    )
    df["detected_at"] = pd.to_datetime(df.get("detected_at", ""), errors="coerce")
    df["detected_at"] = df["detected_at"].dt.strftime("%Y-%m-%d %H:%M")

    display_cols = ["score_badge", "scrip", "exchange", "scheme_type", "status", "detected_at", "assigned_to"]
    display_cols = [c for c in display_cols if c in df.columns]
    display_df = df[display_cols].rename(columns={
        "score_badge": "Score",
        "scrip": "Scrip",
        "exchange": "Exchange",
        "scheme_type": "Scheme",
        "status": "Status",
        "detected_at": "Detected At",
        "assigned_to": "Assigned To",
    })

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Alert detail expander ─────────────────────────────────────────────────
    if filtered:
        st.markdown("### 🔍 Alert Detail")
        selected_scrip = st.selectbox(
            "Select alert to inspect",
            [f"{a['scrip']} — {a.get('impossibility_score', 0):.2f} ({a.get('scheme_type', '')})" for a in filtered],
        )
        sel_idx = [
            f"{a['scrip']} — {a.get('impossibility_score', 0):.2f} ({a.get('scheme_type', '')})"
            for a in filtered
        ].index(selected_scrip)
        sel_alert = filtered[sel_idx]

        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.markdown(f"**Scrip:** {sel_alert.get('scrip')}")
            st.markdown(f"**Scheme:** {sel_alert.get('scheme_type', '').replace('_', ' ').title()}")
            st.markdown(f"**Status:** {sel_alert.get('status', '').upper()}")
            st.markdown(f"**Accounts Involved:** {len(sel_alert.get('accounts_involved', []))}")
            with st.expander("View account IDs"):
                for acc in sel_alert.get("accounts_involved", [])[:20]:
                    st.code(acc)

        with col_right:
            # Score breakdown bar chart
            categories = ["GNN", "Zero-Day", "DNA", "Cross-Market"]
            scores = [
                sel_alert.get("gnn_score", 0),
                sel_alert.get("zero_day_score", 0),
                sel_alert.get("dna_score", 0),
                sel_alert.get("cross_market_score", 0),
            ]
            bar_colors = [
                "#FF5252" if s >= 8 else "#FF9800" if s >= 6 else "#FFC107"
                for s in scores
            ]
            fig = go.Figure(go.Bar(
                x=categories,
                y=scores,
                marker_color=bar_colors,
                text=[f"{s:.1f}" for s in scores],
                textposition="outside",
            ))
            fig.update_layout(
                title="Score Breakdown",
                yaxis=dict(range=[0, 10]),
                plot_bgcolor="#0d1b2a",
                paper_bgcolor="#0d1b2a",
                font_color="white",
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Auto-refresh ──────────────────────────────────────────────────────────
    st.caption(f"⏱️ Auto-refresh every 30 seconds. Last refresh: {datetime.utcnow().strftime('%H:%M:%S UTC')}")
    time.sleep(30)
    st.rerun()


def _demo_alerts() -> list[dict]:
    """Returns sample alert data for offline demo."""
    return [
        {
            "id": "demo-001",
            "scrip": "DEMOBROADCAST",
            "exchange": "NSE",
            "detected_at": datetime.utcnow().isoformat(),
            "impossibility_score": 9.4,
            "scheme_type": "pump_and_dump",
            "accounts_involved": [f"acc_{i}" for i in range(23)],
            "gnn_score": 9.4,
            "dna_score": 7.1,
            "cross_market_score": 6.8,
            "zero_day_score": 8.2,
            "status": "open",
            "case_file_path": None,
            "assigned_to": None,
        },
        {
            "id": "demo-002",
            "scrip": "DEMOSPOOF",
            "exchange": "NSE",
            "detected_at": datetime.utcnow().isoformat(),
            "impossibility_score": 8.1,
            "scheme_type": "spoofing",
            "accounts_involved": [f"spoof_{i}" for i in range(5)],
            "gnn_score": 7.8,
            "dna_score": 6.5,
            "cross_market_score": 5.9,
            "zero_day_score": 8.9,
            "status": "investigating",
            "case_file_path": None,
            "assigned_to": "analyst_01",
        },
    ]
