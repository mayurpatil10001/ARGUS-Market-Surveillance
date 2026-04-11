"""
dashboard/pages/mrfe_analysis.py — ARGUS MRFE Analysis Streamlit page.
Market Reaction Fingerprint Engine: text + file upload analysis.
Tab 1: Text Analysis | Tab 2: File Upload
"""
from __future__ import annotations

import requests
import streamlit as st


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _call_analyze_text(api_base: str, token: str, text: str, fetch_historical: bool) -> tuple:
    try:
        r = requests.post(
            f"{api_base}/mrfe/analyze/text",
            headers=_headers(token),
            json={"text": text, "fetch_historical": fetch_historical},
            timeout=30,
        )
        if r.ok:
            return r.json(), None
        return None, f"{r.status_code}: {r.text[:200]}"
    except Exception as exc:
        return None, str(exc)


def _call_analyze_file(api_base: str, token: str, file_bytes: bytes, filename: str, fetch_historical: bool) -> tuple:
    try:
        r = requests.post(
            f"{api_base}/mrfe/analyze/file?fetch_historical={str(fetch_historical).lower()}",
            headers=_headers(token),
            files={"file": (filename, file_bytes)},
            timeout=30,
        )
        if r.ok:
            return r.json(), None
        return None, f"{r.status_code}: {r.text[:200]}"
    except Exception as exc:
        return None, str(exc)


def _show_results(result: dict):
    """Display MRFE analysis results in a structured Streamlit layout."""
    if not result:
        return

    # ── Metric row ──────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Threat Score", f"{result.get('threat_score', 0):.1%}")
    m2.metric("Misinfo Score", f"{result.get('misinfo_score', 0):.1%}")
    m3.metric("Social Score", f"{result.get('social_score', 0):.1%}")
    m4.metric("Confidence", f"{result.get('confidence', 0):.1%}")
    m5.metric("Market Impact", result.get("market_impact", "low").upper())

    # Impact color
    impact = result.get("market_impact", "low")
    impact_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(impact, "⚪")

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Event Type:** {result.get('event_type', 'unknown').replace('_', ' ').title()}")
        st.warning(f"**Recommended Action:** `{result.get('recommended_action', 'log_only').replace('_', ' ')}`")

    with col2:
        st.info(f"**Market Impact:** {impact_emoji} {impact.upper()}")
        proc_ms = result.get("processing_time_ms", 0)
        st.caption(f"⏱ Processed in {proc_ms:.1f}ms")
        if result.get("pdf_pages") is not None:
            st.caption(f"📄 {result['pdf_pages']} page(s) | {result.get('pdf_word_count', 0):,} words")
        if result.get("synthetic_data"):
            st.caption("⚠ synthetic_data: true")

    # Affected scrips
    scrips = result.get("affected_scrips", [])
    if scrips:
        st.markdown("**Affected Scrips:**")
        st.code(" | ".join(scrips), language=None)

    # Evidence snippets
    evidence = result.get("evidence_snippets", [])
    if evidence:
        with st.expander(f"Evidence Snippets ({len(evidence)})", expanded=False):
            for i, snippet in enumerate(evidence, 1):
                st.markdown(f"**[{i}]** {snippet}")

    # Historical price sparklines
    historical = result.get("historical_context", {})
    if historical:
        st.markdown("**30-Day Price Context:**")
        try:
            import plotly.graph_objects as go
            for scrip, data in historical.items():
                if data.get("prices"):
                    prices = data["prices"]
                    dates = data.get("dates", list(range(len(prices))))
                    pct_chg = data.get("price_change_30d_pct", 0.0)
                    color = "#22c55e" if pct_chg >= 0 else "#ef4444"
                    synthetic_label = " (synthetic)" if data.get("synthetic_data") else ""

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=dates, y=prices,
                        mode="lines",
                        name=scrip,
                        line=dict(color=color, width=1.5),
                        fill="tozeroy",
                        fillcolor=f"rgba({'34,197,94' if pct_chg >= 0 else '239,68,68'},0.08)",
                    ))
                    fig.update_layout(
                        title=f"{scrip} — {pct_chg:+.2f}%{synthetic_label}",
                        height=160,
                        paper_bgcolor="#0d1b2a",
                        plot_bgcolor="#0d1b2a",
                        font={"color": "#e0e0e0", "size": 10},
                        margin=dict(l=10, r=10, t=30, b=10),
                        showlegend=False,
                        xaxis=dict(showgrid=False, showticklabels=False),
                        yaxis=dict(showgrid=True, gridcolor="#1f3050"),
                    )
                    st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            for scrip, data in historical.items():
                st.write(f"**{scrip}** — {data.get('price_change_30d_pct', 0):+.2f}%")

    # Note / disclaimer
    note = result.get("note")
    if note:
        st.caption(f"ℹ {note}")


def render(api_base: str, token: str):
    st.markdown("## 🔍 MRFE Analysis")
    st.caption("Market Reaction Fingerprint Engine — analyze text, PDFs and documents for financial threats.")

    tab_text, tab_file = st.tabs(["📝 Analyze Text", "📎 Upload File"])

    # ── Tab 1: Text Analysis ─────────────────────────────────────────────
    with tab_text:
        text_input = st.text_area(
            "Paste financial news, social media posts, or any text",
            height=180,
            placeholder=(
                "Example: XYZLTD targets 500% returns — operator call — "
                "buy now — guaranteed profit — upper circuit tomorrow..."
            ),
        )
        col_a, col_b = st.columns([3, 1])
        with col_a:
            fetch_hist_text = st.checkbox(
                "Fetch 30-day price history for detected scrips (may use synthetic fallback)",
                key="fetch_hist_text",
            )
        with col_b:
            analyze_btn_text = st.button("Analyze Text", type="primary", use_container_width=True)

        if analyze_btn_text:
            if not text_input.strip():
                st.warning("Please enter some text to analyze.")
            else:
                with st.spinner("Running MRFE analysis..."):
                    result, err = _call_analyze_text(api_base, token, text_input, fetch_hist_text)
                if err:
                    st.error(f"MRFE error: {err}")
                elif result:
                    st.success("Analysis complete.")
                    _show_results(result)

    # ── Tab 2: File Upload ───────────────────────────────────────────────
    with tab_file:
        uploaded = st.file_uploader(
            "Upload a document to analyze",
            type=["pdf", "txt", "csv", "docx"],
            help="Supported: PDF, TXT, CSV, DOCX. Max 10 MB.",
        )
        fetch_hist_file = st.checkbox(
            "Fetch 30-day price history for detected scrips",
            key="fetch_hist_file",
        )
        analyze_btn_file = st.button("Analyze File", type="primary")

        if analyze_btn_file:
            if uploaded is None:
                st.warning("Please upload a file first.")
            else:
                file_bytes = uploaded.read()
                if len(file_bytes) > 10 * 1024 * 1024:
                    st.error("File exceeds 10 MB limit.")
                else:
                    with st.spinner(f"Analyzing {uploaded.name}..."):
                        result, err = _call_analyze_file(
                            api_base, token, file_bytes, uploaded.name, fetch_hist_file
                        )
                    if err:
                        st.error(f"MRFE error: {err}")
                    elif result:
                        st.success(f"Analysis complete — {uploaded.name}")
                        _show_results(result)
