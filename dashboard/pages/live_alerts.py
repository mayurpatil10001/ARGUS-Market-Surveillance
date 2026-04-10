"""
dashboard/pages/live_alerts.py — Real-time threat alert monitoring page.
SENTINEL: Scalable ENTity Intelligence for NEtwork-Level threat detection
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
    st.title("🚨 Live Threat Alerts")
    st.caption("Real-time digital threat detection — auto-refreshes every 30s")

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
    open_alerts  = [a for a in alerts if a.get("status") == "open"]
    avg_score    = sum(a.get("impossibility_score", 0) for a in alerts) / max(len(alerts), 1)
    # PS-402: count entities_involved (fallback to accounts_involved)
    flagged_today = len({
        e
        for a in alerts
        for e in (a.get("entities_involved") or a.get("accounts_involved") or [])
    })
    reports_sent = len([a for a in alerts if a.get("case_file_path")])

    with c1:
        st.metric("🔴 Active Threats", len(open_alerts))
    with c2:
        st.metric("📊 Avg Threat Score", f"{avg_score:.2f}/10")
    with c3:
        st.metric("👤 Entities Flagged", flagged_today)
    with c4:
        st.metric("📁 Reports Sent", reports_sent)

    st.markdown("---")

    # ── Filters ───────────────────────────────────────────────────────────────
    col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
    with col_filter1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "open", "investigating", "closed", "false_positive"],
        )
    with col_filter2:
        min_score_filter = st.slider("Min Threat Score", 0.0, 10.0, 0.0, 0.5)
    with col_filter3:
        entity_filter = st.text_input("Filter by Entity", placeholder="e.g. BOTNET_RING_A")
    with col_filter4:
        platform_filter = st.selectbox(
            "Filter by Platform",
            ["All", "twitter", "reddit", "telegram", "web", "email"],
        )

    # Apply filters
    filtered = alerts
    if status_filter != "All":
        filtered = [a for a in filtered if a.get("status") == status_filter]
    if min_score_filter > 0:
        filtered = [a for a in filtered if a.get("impossibility_score", 0) >= min_score_filter]
    if entity_filter:
        filtered = [a for a in filtered if entity_filter.upper() in a.get("scrip", "").upper()]
    if platform_filter != "All":
        filtered = [
            a for a in filtered
            if (a.get("platform") or a.get("exchange") or "").lower() == platform_filter.lower()
        ]

    # ── Alerts table ──────────────────────────────────────────────────────────
    if not filtered:
        st.info("No threats match the current filters.")
        return

    df = pd.DataFrame(filtered)
    if df.empty:
        st.info("No threats found.")
        return

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

    # PS-402 column names: threat_category + platform over legacy scheme_type + exchange
    if "threat_category" not in df.columns and "scheme_type" in df.columns:
        df["threat_category"] = df["scheme_type"]
    if "platform" not in df.columns and "exchange" in df.columns:
        df["platform"] = df["exchange"]

    display_cols = ["score_badge", "scrip", "platform", "threat_category", "status", "detected_at", "assigned_to"]
    display_cols = [c for c in display_cols if c in df.columns]
    display_df = df[display_cols].rename(columns={
        "score_badge":      "Score",
        "scrip":            "Entity",
        "platform":         "Platform",
        "threat_category":  "Threat Category",
        "status":           "Status",
        "detected_at":      "Detected At",
        "assigned_to":      "Assigned To",
    })

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Alert detail expander ─────────────────────────────────────────────────
    if filtered:
        st.markdown("### 🔍 Threat Detail")
        tc_label = lambda a: a.get("threat_category") or a.get("scheme_type", "")
        selected_key = st.selectbox(
            "Select threat to inspect",
            [f"{a['scrip']} — {a.get('impossibility_score', 0):.2f} [{tc_label(a)}]" for a in filtered],
        )
        sel_idx = [
            f"{a['scrip']} — {a.get('impossibility_score', 0):.2f} [{tc_label(a)}]"
            for a in filtered
        ].index(selected_key)
        sel_alert = filtered[sel_idx]

        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.markdown(f"**Entity:** {sel_alert.get('scrip')}")
            st.markdown(f"**Platform:** {(sel_alert.get('platform') or sel_alert.get('exchange', '')).upper()}")
            st.markdown(f"**Threat Category:** {tc_label(sel_alert).replace('_', ' ').title()}")
            st.markdown(f"**Status:** {sel_alert.get('status', '').upper()}")
            entities = sel_alert.get("entities_involved") or sel_alert.get("accounts_involved") or []
            st.markdown(f"**Entities Involved:** {len(entities)}")
            if sel_alert.get("content_sample"):
                st.markdown("**Flagged Content Sample:**")
                st.code(sel_alert["content_sample"], language=None)
            with st.expander("View entity IDs"):
                for e in entities[:20]:
                    st.code(e)

        with col_right:
            # PS-402 score breakdown labels
            categories = [
                "Network Coordination",
                "Behavioral Anomaly",
                "Cross-Platform",
                "Novel Threat",
            ]
            scores = [
                sel_alert.get("gnn_score", 0),
                sel_alert.get("dna_score", 0),
                sel_alert.get("cross_market_score", 0),
                sel_alert.get("zero_day_score", 0),
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
                title="SENTINEL Score Breakdown",
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
    """Returns sample PS-402 threat alert data for offline demo."""
    return [
        {
            "id": "demo-001",
            "scrip": "BOTNET_RING_A",
            "platform": "twitter",
            "exchange": "twitter",
            "detected_at": datetime.utcnow().isoformat(),
            "impossibility_score": 9.4,
            "threat_category": "coordinated_attack",
            "scheme_type": "coordinated_attack",
            "entities_involved": [f"BOT_{i:03d}" for i in range(23)],
            "accounts_involved": [f"BOT_{i:03d}" for i in range(23)],
            "gnn_score": 9.4,
            "dna_score": 7.1,
            "cross_market_score": 6.8,
            "zero_day_score": 8.2,
            "content_sample": "BREAKING: Guaranteed 500% returns on XYZTECH! Buy before midnight! t.me/pump",
            "status": "open",
            "case_file_path": None,
            "assigned_to": None,
        },
        {
            "id": "demo-002",
            "scrip": "PHISH_OPR_RING",
            "platform": "web",
            "exchange": "web",
            "detected_at": datetime.utcnow().isoformat(),
            "impossibility_score": 8.1,
            "threat_category": "phishing",
            "scheme_type": "phishing",
            "entities_involved": [f"OPR_{i:03d}" for i in range(5)],
            "accounts_involved": [f"OPR_{i:03d}" for i in range(5)],
            "gnn_score": 7.8,
            "dna_score": 6.5,
            "cross_market_score": 5.9,
            "zero_day_score": 8.9,
            "content_sample": "http://bank-secure-login.xyz/verify?token=abc&redirect=account-suspended",
            "status": "investigating",
            "case_file_path": None,
            "assigned_to": "analyst_01",
        },
        {
            "id": "demo-003",
            "scrip": "REDDIT_MISINFO_RING",
            "platform": "reddit",
            "exchange": "reddit",
            "detected_at": datetime.utcnow().isoformat(),
            "impossibility_score": 8.8,
            "threat_category": "misinformation",
            "scheme_type": "misinformation",
            "entities_involved": [f"RING_{chr(65+i)}" for i in range(8)],
            "accounts_involved": [f"RING_{chr(65+i)}" for i in range(8)],
            "gnn_score": 8.5,
            "dna_score": 8.0,
            "cross_market_score": 10.0,
            "zero_day_score": 8.0,
            "content_sample": "CONFIRMED: AI regulation bill scrapped. Tech stocks to moon! 100% guaranteed.",
            "status": "open",
            "case_file_path": None,
            "assigned_to": None,
        },
    ]
