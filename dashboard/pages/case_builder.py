"""
dashboard/pages/case_builder.py — SEBI case file builder page.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import requests
import streamlit as st


def render(api_base: str, token: str) -> None:
    st.title("📁 Case Builder")
    st.caption("Build and generate SEBI-compliant enforcement case files")

    headers = {"Authorization": f"Bearer {token}"}

    # ── Load alerts for dropdown ───────────────────────────────────────────────
    alerts: list[dict] = []
    try:
        resp = requests.get(
            f"{api_base}/alerts",
            headers=headers,
            params={"limit": 200},
            timeout=10,
        )
        if resp.ok:
            alerts = resp.json()
    except Exception:
        alerts = _demo_alerts_list()

    if not alerts:
        st.info("No alerts available. Run a detection scan first.")
        return

    alert_options = {
        f"{a['scrip']} — Score {a.get('impossibility_score', 0):.1f} — {a.get('scheme_type', '')} "
        f"[{a.get('status', '').upper()}]": a
        for a in alerts
    }

    st.markdown("### 1. Select Alert")
    selected_label = st.selectbox("Choose alert to build case for:", list(alert_options.keys()))
    selected_alert = alert_options[selected_label]

    st.markdown("---")
    st.markdown("### 2. Case Details")

    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input(
            "Investigation From Date",
            value=(datetime.utcnow() - timedelta(days=30)).date(),
        )
        to_date = st.date_input("Investigation To Date", value=datetime.utcnow().date())
        estimated_gain = st.number_input(
            "Estimated Gain (₹)", min_value=0.0, step=10000.0, format="%.2f"
        )

    with col2:
        entity_names_raw = st.text_area(
            "Entity Names (one per line)",
            value="\n".join(selected_alert.get("accounts_involved", [])[:5]),
            help="Provide human-readable entity names for the case file",
        )
        notes = st.text_area("Additional Notes for Case File", height=80)

    entity_names = [n.strip() for n in entity_names_raw.strip().splitlines() if n.strip()]

    # ── Evidence preview ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 3. Evidence Summary")

    ev_col1, ev_col2 = st.columns(2)
    with ev_col1:
        st.markdown(f"**Scrip:** {selected_alert.get('scrip')}")
        st.markdown(f"**Exchange:** {selected_alert.get('exchange', 'NSE')}")
        st.markdown(f"**Scheme:** {selected_alert.get('scheme_type', '').replace('_', ' ').title()}")
        st.markdown(f"**Accounts Involved:** {len(selected_alert.get('accounts_involved', []))}")
    with ev_col2:
        st.markdown(f"**Overall Score:** {selected_alert.get('impossibility_score', 0):.2f}/10")
        st.markdown(f"**GNN Score:** {selected_alert.get('gnn_score', 0):.2f}")
        st.markdown(f"**DNA Score:** {selected_alert.get('dna_score', 0):.2f}")
        st.markdown(f"**Cross-Market:** {selected_alert.get('cross_market_score', 0):.2f}")
        st.markdown(f"**Zero-Day:** {selected_alert.get('zero_day_score', 0):.2f}")

    st.markdown("---")
    st.markdown("### 4. Generate Case File")

    if st.button("📄 Generate SEBI Case PDF", type="primary", use_container_width=True):
        alert_id = selected_alert.get("id")
        if not alert_id:
            st.error("Invalid alert ID")
            return

        payload = {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "estimated_gain": float(estimated_gain) if estimated_gain > 0 else None,
            "entity_names": entity_names,
            "notes": notes,
        }

        with st.spinner("Generating SEBI case file PDF..."):
            try:
                resp = requests.post(
                    f"{api_base}/reports/case/{alert_id}",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                if resp.ok:
                    result = resp.json()
                    st.success(f"✅ Case file generated! Case Number: **{result['case_number']}**")
                    download_url = f"{api_base}{result['download_url']}"
                    st.markdown(
                        f"📥 **[Download PDF Case File]({download_url})**",
                        unsafe_allow_html=False,
                    )
                    with st.expander("Case Details"):
                        st.json(result)
                else:
                    st.error(f"❌ Generation failed: {resp.status_code} — {resp.text}")
            except Exception as exc:
                st.error(f"❌ API error: {exc}")
                st.info("Demo mode: PDF would be generated and stored at /tmp/argus_reports/")


def _demo_alerts_list() -> list[dict]:
    return [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "scrip": "DEMOBROADCAST",
            "exchange": "NSE",
            "impossibility_score": 9.4,
            "scheme_type": "pump_and_dump",
            "accounts_involved": ["acc_001", "acc_002", "acc_003"],
            "gnn_score": 9.4,
            "dna_score": 7.1,
            "cross_market_score": 6.8,
            "zero_day_score": 8.2,
            "status": "open",
        }
    ]
