"""
dashboard/pages/account_dna.py — Behavioral DNA analysis page.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


def render(api_base: str, token: str) -> None:
    st.title("🧬 Account DNA Profiler")
    st.caption("Behavioral fingerprint analysis and known fraudster matching")

    headers = {"Authorization": f"Bearer {token}"}

    account_id = st.text_input(
        "🔍 Enter Account ID",
        placeholder="e.g. a1b2c3d4e5f6g7h8",
        help="16-character anonymized account hash",
    )

    if not account_id:
        st.info("Enter an account ID to analyze its behavioral DNA.")
        _show_sample_dna()
        return

    col1, col2 = st.columns([1, 1])

    # ── DNA Radar Chart ───────────────────────────────────────────────────────
    dna_data: dict = {}
    try:
        resp = requests.get(
            f"{api_base}/accounts/{account_id}/dna",
            headers=headers,
            timeout=10,
        )
        if resp.ok:
            dna_data = resp.json()
        else:
            st.error(f"Account not found: {resp.status_code}")
            return
    except Exception as exc:
        st.warning(f"API unavailable: {exc}. Showing demo data.")
        dna_data = _demo_dna(account_id)

    dna_vector = dna_data.get("dna_vector", [])
    is_anomalous = dna_data.get("is_anomalous", False)
    recon_error = dna_data.get("reconstruction_error", 0.0)
    matches = dna_data.get("fraudster_matches", [])

    with col1:
        st.markdown(f"### Account: `{account_id}`")
        status_icon = "🔴 ANOMALOUS" if is_anomalous else "🟢 NORMAL"
        st.markdown(f"**Behavioral Status:** {status_icon}")
        st.metric("Reconstruction Error", f"{recon_error:.4f}", help="Higher = more anomalous")

        if dna_vector and len(dna_vector) >= 8:
            radar_labels = [
                "Avg Volume", "Buy Ratio", "Trade Freq",
                "Scrip Div", "Night Trades", "Large Orders",
                "Price Aggr", "Activity Burst",
            ]
            radar_vals = [abs(float(v)) for v in dna_vector[:8]]
            max_val = max(radar_vals) or 1.0
            radar_norm = [v / max_val for v in radar_vals]

            fig_radar = go.Figure(go.Scatterpolar(
                r=radar_norm + [radar_norm[0]],
                theta=radar_labels + [radar_labels[0]],
                fill="toself",
                fillcolor="rgba(200, 169, 81, 0.3)",
                line_color="#C8A951",
                name="Account DNA",
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 1], gridcolor="#2a3a5f"),
                    angularaxis=dict(gridcolor="#2a3a5f"),
                    bgcolor="#0d1b2a",
                ),
                paper_bgcolor="#0d1b2a",
                font_color="white",
                title="Behavioral DNA Radar",
                height=350,
            )
            st.plotly_chart(fig_radar, use_container_width=True)

    with col2:
        st.markdown("### 🕵️ Known Fraudster Similarity")
        if matches:
            sim_labels = [m.get("entity_name", "Unknown")[:20] for m in matches[:5]]
            sim_vals = [m.get("similarity", 0) * 100 for m in matches[:5]]
            bar_colors = ["#FF5252" if s >= 85 else "#FF9800" for s in sim_vals]

            fig_bar = go.Figure(go.Bar(
                x=sim_vals,
                y=sim_labels,
                orientation="h",
                marker_color=bar_colors,
                text=[f"{v:.1f}%" for v in sim_vals],
                textposition="outside",
            ))
            fig_bar.update_layout(
                title="Similarity to Known Fraudsters (%)",
                xaxis=dict(range=[0, 110], gridcolor="#2a3a5f"),
                plot_bgcolor="#0d1b2a",
                paper_bgcolor="#0d1b2a",
                font_color="white",
                height=300,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            for m in matches[:3]:
                with st.expander(f"🚨 {m.get('entity_name', 'Unknown')} — {m.get('similarity', 0)*100:.1f}% match"):
                    st.markdown(f"**Scheme:** {m.get('scheme_type', 'N/A')}")
                    st.markdown(f"**Order Ref:** {m.get('sebi_order_ref', 'N/A')}")
                    st.markdown(f"**Scrips:** {', '.join(m.get('scrips_involved', []))}")
                    st.markdown(f"**Conviction:** {m.get('conviction_date', 'N/A')}")
        else:
            st.success("✅ No matches found in known fraudster database.")

    # ── Trade History ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Trade History")
    trades_data: list[dict] = []
    try:
        resp = requests.get(
            f"{api_base}/accounts/{account_id}/trades",
            headers=headers,
            params={"limit": 200},
            timeout=10,
        )
        if resp.ok:
            trades_data = resp.json()
    except Exception:
        trades_data = []

    if trades_data:
        df = pd.DataFrame(trades_data)
        df["timestamp"] = pd.to_datetime(df.get("timestamp", ""), errors="coerce")
        df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

        def highlight_manip(row):
            if row.get("is_manipulated"):
                return ["background-color: rgba(255,82,82,0.2)"] * len(row)
            return [""] * len(row)

        cols = ["timestamp", "scrip", "exchange", "side", "price", "volume", "is_manipulated"]
        cols = [c for c in cols if c in df.columns]
        st.dataframe(
            df[cols].style.apply(highlight_manip, axis=1),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("🔴 Red-highlighted rows = flagged as potentially manipulated")
    else:
        st.info("No trade history available for this account.")


def _demo_dna(account_id: str) -> dict:
    np.random.seed(hash(account_id) % 1000)
    dna = np.random.randn(32).tolist()
    return {
        "account_id": account_id,
        "dna_vector": dna,
        "fraudster_matches": [
            {
                "entity_name": "Demo Fraudster Corp",
                "similarity": 0.91,
                "scheme_type": "pump_and_dump",
                "sebi_order_ref": "WTM/RKA/ISD/195/2017",
                "scrips_involved": ["DEMOBROADCAST"],
                "conviction_date": "2017-09-15",
            }
        ],
        "reconstruction_error": 0.62,
        "is_anomalous": True,
    }


def _show_sample_dna() -> None:
    """Shows a sample DNA radar for illustration."""
    labels = ["Avg Volume", "Buy Ratio", "Trade Freq", "Scrip Div",
              "Night Trades", "Large Orders", "Price Aggr", "Activity Burst"]
    normal = [0.3, 0.5, 0.4, 0.6, 0.1, 0.2, 0.3, 0.4]
    manip = [0.9, 0.8, 0.95, 0.2, 0.7, 0.85, 0.9, 0.95]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=normal + [normal[0]], theta=labels + [labels[0]],
        fill="toself", name="Normal Account",
        fillcolor="rgba(0,230,118,0.2)", line_color="#00e676",
    ))
    fig.add_trace(go.Scatterpolar(
        r=manip + [manip[0]], theta=labels + [labels[0]],
        fill="toself", name="Manipulator Profile",
        fillcolor="rgba(255,82,82,0.2)", line_color="#FF5252",
    ))
    fig.update_layout(
        polar=dict(bgcolor="#0d1b2a"),
        paper_bgcolor="#0d1b2a",
        font_color="white",
        title="Sample: Normal vs. Manipulator DNA Profile",
    )
    st.plotly_chart(fig, use_container_width=True)
