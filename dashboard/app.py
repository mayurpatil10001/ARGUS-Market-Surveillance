"""
dashboard/app.py — SENTINEL Streamlit multi-page dashboard main entry point.
SENTINEL: Scalable ENTity Intelligence for NEtwork-Level threat detection
"""
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
import streamlit as st

API_BASE = os.getenv("ARGUS_API_URL", "http://argus-api:8000")

st.set_page_config(
    page_title="SENTINEL — Digital Threat Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #0f1f3d 100%);
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    .sentinel-logo {
        font-size: 2.0rem;
        font-weight: 900;
        color: #00ff88;
        letter-spacing: 0.12em;
        text-align: center;
        padding: 1rem 0 0.3rem 0;
    }
    .sentinel-tagline {
        font-size: 0.72rem;
        color: #8890a8;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .status-dot-green { color: #00e676; font-size: 1.1rem; }
    .status-dot-red { color: #ff5252; font-size: 1.1rem; }
    .metric-card {
        background: #1a2b5f;
        border-radius: 12px;
        padding: 1.2rem;
        border-left: 4px solid #00ff88;
    }
</style>
""", unsafe_allow_html=True)


def _get_health():
    try:
        token = st.session_state.get("token", "")
        resp = requests.get(
            f"{API_BASE}/health",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        return resp.json() if resp.ok else {}
    except Exception:
        return {}


def _get_token():
    """Gets auth token, caches in session state."""
    if "token" not in st.session_state:
        try:
            resp = requests.post(
                f"{API_BASE}/auth/token",
                data={"username": "admin", "password": os.getenv("ADMIN_PASSWORD", "argus2024")},
                timeout=10,
            )
            if resp.ok:
                st.session_state["token"] = resp.json().get("access_token", "")
        except Exception:
            st.session_state["token"] = ""
    return st.session_state.get("token", "")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sentinel-logo">🛡️ SENTINEL</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sentinel-tagline">Scalable ENTity Intelligence for<br>NEtwork-Level Threat Detection</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Auto-authenticate
    token = _get_token()
    health = _get_health()
    sys_status = health.get("status", "unknown")
    dot = "🟢" if sys_status == "ok" else "🔴"
    st.markdown(f"{dot} **System Status:** {sys_status.upper()}")

    last_scan = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    st.caption(f"🕐 Last Scan: {last_scan}")

    st.markdown("---")
    st.markdown("**Navigation**")

    page = st.radio(
        "Go to page:",
        ["🚨 Live Threat Alerts", "🧬 Behavioral DNA", "🕸️ Threat Network", "📁 Threat Report Builder", "🔍 PS-402 Signals", "🛡️ Mitigation Center"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    model_vers = health.get("model_versions", {})
    if model_vers:
        st.caption("**AI Engines:**")
        for name, status in model_vers.items():
            icon = "✅" if status == "loaded" else "⚠️"
            st.caption(f"  {icon} {name}: {status}")

# ── Page routing ──────────────────────────────────────────────────────────────
if page == "🚨 Live Threat Alerts":
    from dashboard.pages.live_alerts import render
    render(API_BASE, token)
elif page == "🧬 Behavioral DNA":
    from dashboard.pages.account_dna import render
    render(API_BASE, token)
elif page == "🕸️ Threat Network":
    from dashboard.pages.network_graph import render
    render(API_BASE, token)
elif page == "📁 Threat Report Builder":
    from dashboard.pages.case_builder import render
    render(API_BASE, token)
elif page == "🔍 PS-402 Signals":
    from dashboard.pages.ps402_signals import render
    render(API_BASE, token)
elif page == "🛡️ Mitigation Center":
    from dashboard.pages.mitigation_center import render
    render(API_BASE, token)
