"""
dashboard/pages/ps402_signals.py — PS-402 Digital Threat Signals Streamlit page.
Matches the pattern of all other pages in dashboard/pages/.

Usage:
    from dashboard.pages import ps402_signals
    ps402_signals.render(api_base, token)
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import requests
import streamlit as st


# ── API helpers ───────────────────────────────────────────────────────────────

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _get_summary(api_base: str, token: str) -> dict:
    try:
        r = requests.get(f"{api_base}/ps402/summary", headers=_headers(token), timeout=10)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}


def _get_signals(
    api_base: str,
    token: str,
    *,
    platform: Optional[str] = None,
    is_market_moving: Optional[bool] = None,
    scrip: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    params: dict = {"limit": limit}
    if platform:
        params["platform"] = platform
    if is_market_moving is not None:
        params["is_market_moving"] = str(is_market_moving).lower()
    if scrip:
        params["scrip"] = scrip
    try:
        r = requests.get(
            f"{api_base}/ps402/signals",
            headers=_headers(token),
            params=params,
            timeout=10,
        )
        if r.ok:
            return r.json().get("signals", [])
    except Exception:
        pass
    return []


# ── Main render function ──────────────────────────────────────────────────────

def render(api_base: str, token: str) -> None:
    st.header("🔍 PS-402: Digital Threat Signals")
    st.caption(
        "Real-time market-signal surveillance — phishing URLs, social manipulation, "
        "WhatsApp forwards, and news misinformation."
    )

    # ── 1. Summary metrics ────────────────────────────────────────────────────
    summary = _get_summary(api_base, token)
    if summary:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Signals (7d)",  summary.get("total_signals", 0))
        c2.metric("Market-Moving",       summary.get("market_moving", 0))
        c3.metric("Avg Threat Score",    round(summary.get("avg_threat_score", 0.0), 3))
        c4.metric("Phishing URLs",       summary.get("by_type", {}).get("url_threat", 0))
        c5.metric("Social Posts",        summary.get("by_type", {}).get("social_post", 0))
    else:
        st.warning("⚠️ Could not fetch PS-402 summary. Is the API running?")

    st.markdown("---")

    # ── 2. Filters ────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
    with col_f1:
        platform_options = ["(all)", "web", "twitter", "reddit", "telegram", "whatsapp", "news"]
        platform_sel = st.selectbox("Platform", platform_options, key="ps402_platform")
        platform_val = None if platform_sel == "(all)" else platform_sel
    with col_f2:
        mm_options = ["All", "Market-Moving Only", "Non-Market-Moving"]
        mm_sel = st.selectbox("Market-Moving Filter", mm_options, key="ps402_mm")
        mm_val: Optional[bool] = None
        if mm_sel == "Market-Moving Only":
            mm_val = True
        elif mm_sel == "Non-Market-Moving":
            mm_val = False
    with col_f3:
        scrip_input = st.text_input("Scrip (e.g. RELIANCE)", key="ps402_scrip").strip().upper()
        scrip_val = scrip_input if scrip_input else None
    with col_f4:
        st.markdown("<br>", unsafe_allow_html=True)
        refresh = st.button("↺ Refresh", key="ps402_refresh")

    # Auto-refresh on page load; also on button press
    signals = _get_signals(
        api_base, token,
        platform=platform_val,
        is_market_moving=mm_val,
        scrip=scrip_val,
    )

    st.caption(f"**{len(signals)}** signals returned")
    st.markdown("---")

    # ── 3. Market-moving warnings ─────────────────────────────────────────────
    mm_signals = [s for s in signals if s.get("is_market_moving")]
    if mm_signals:
        st.subheader(f"⚡ {len(mm_signals)} Market-Moving Signal(s)")
        for sig in mm_signals[:5]:
            scrips = ", ".join(sig.get("scrips_mentioned") or ["(none)"])
            alert_str = f" — Alert: `{sig['alert_id']}`" if sig.get("alert_id") else ""
            st.warning(
                f"**{sig['signal_type'].upper()}** via **{sig['platform']}** "
                f"| Scrips: **{scrips}** | Threat: **{sig.get('threat_score', 0):.3f}**"
                f"{alert_str}"
            )

    # ── 4. Signals table ──────────────────────────────────────────────────────
    if signals:
        import pandas as pd

        rows = []
        for s in signals:
            rows.append({
                "Time": s.get("ingested_at", "")[:19].replace("T", " "),
                "Type": s.get("signal_type", ""),
                "Platform": s.get("platform", ""),
                "Scrips": ", ".join(s.get("scrips_mentioned") or []),
                "Threat": round(s.get("threat_score", 0.0), 3),
                "Misinfo": round(s.get("misinfo_score", 0.0), 3),
                "Social": round(s.get("social_signal_score", 0.0), 3),
                "Market-Moving": "⚡ Yes" if s.get("is_market_moving") else "–",
                "Alert": (s.get("alert_id") or "")[:8] or "–",
            })

        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        # ── 5. Raw signal detail expander ─────────────────────────────────────
        with st.expander("🔎 Raw signal details (select index above)"):
            idx = st.number_input(
                "Signal index (0-based)", min_value=0, max_value=max(0, len(signals) - 1),
                value=0, step=1, key="ps402_detail_idx",
            )
            if 0 <= idx < len(signals):
                st.json(signals[int(idx)])
    else:
        st.info("No signals found for the current filters.")
