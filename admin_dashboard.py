import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.express as px
import os

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="NOX Admin Enterprise",
    page_icon="📊",
    layout="wide"
)

st.title("📊 NOX Enterprise Command Center")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────
if "god_mode" not in st.session_state:
    st.session_state.god_mode = False

# ────────────────────────────────────────────────
# API HELPER
# ────────────────────────────────────────────────
@st.cache_data(ttl=20)
def api_get(path: str):
    try:
        res = requests.get(f"{BACKEND_URL}{path}", timeout=10)
        if res.status_code != 200:
            return {"error": res.text}
        return res.json()
    except Exception as e:
        return {"error": str(e)}

# ────────────────────────────────────────────────
# SIDEBAR (CONTROL PANEL)
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("🛠 NOX Control Panel")

    st.session_state.god_mode = st.toggle(
        "🔥 God Mode",
        value=st.session_state.god_mode
    )

    if st.session_state.god_mode:
        st.success("Unlimited access enabled")

    st.divider()

    st.markdown("### ⚡ System Actions")

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ────────────────────────────────────────────────
# HEALTH CHECK
# ────────────────────────────────────────────────
health = api_get("/")

if "error" in health:
    st.error(f"❌ Backend Offline → {BACKEND_URL}")
    st.stop()
else:
    st.success(f"✅ Backend Connected")

# ────────────────────────────────────────────────
# LOAD DATA
# ────────────────────────────────────────────────
dashboard = api_get("/admin/dashboard")
timeseries = api_get("/admin/revenue-timeseries")
mrr_data = api_get("/admin/mrr")
forge_stats = api_get("/admin/forge-stats")
builds = api_get("/admin/builds")

# Safe fallback
dashboard = dashboard if isinstance(dashboard, dict) else {}
forge_stats = forge_stats if isinstance(forge_stats, dict) else {}
builds = builds if isinstance(builds, list) else []

# ────────────────────────────────────────────────
# KPI METRICS
# ────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("👥 Users", dashboard.get("users", 0))
col2.metric("💰 Credits", f"{dashboard.get('credits', 0):,}")
col3.metric("💵 Revenue", f"${dashboard.get('revenue_total', 0):,.2f}")
col4.metric("⚡ 24h", f"${dashboard.get('revenue_24h', 0):,.2f}")
col5.metric("🛠 Apps Built", forge_stats.get("apps_built", 0))

st.divider()

# ────────────────────────────────────────────────
# REVENUE CHART
# ────────────────────────────────────────────────
if isinstance(timeseries, list) and timeseries:
    df = pd.DataFrame(timeseries)

    if "date" in df.columns and "revenue" in df.columns:
        fig = px.line(df, x="date", y="revenue", title="Revenue Over Time")
        st.plotly_chart(fig, use_container_width=True)

# ────────────────────────────────────────────────
# MRR SECTION
# ────────────────────────────────────────────────
if isinstance(mrr_data, dict):
    st.subheader("💰 Monthly Recurring Revenue")
    st.metric("MRR", f"${mrr_data.get('mrr', 0):,.2f}")

# ────────────────────────────────────────────────
# BUILD ANALYTICS
# ────────────────────────────────────────────────
st.subheader("🛠 Build Intelligence")

if builds:
    df_builds = pd.DataFrame(builds)

    # Convert timestamp
    if "created_at" in df_builds.columns:
        df_builds["created_at"] = pd.to_datetime(df_builds["created_at"])

    colA, colB = st.columns(2)

    with colA:
        st.markdown("### 📦 Recent Builds")
        st.dataframe(df_builds.tail(10), use_container_width=True)

    with colB:
        if "created_at" in df_builds.columns:
            grouped = df_builds.groupby(df_builds["created_at"].dt.date).size().reset_index(name="builds")

            fig2 = px.bar(grouped, x="created_at", y="builds", title="Builds per Day")
            st.plotly_chart(fig2, use_container_width=True)

else:
    st.info("No build history available")

# ────────────────────────────────────────────────
# GOD MODE PANEL (REAL POWER)
# ────────────────────────────────────────────────
if st.session_state.god_mode:
    st.divider()
    st.subheader("🔥 God Mode Control")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💣 Reset Cache"):
            st.cache_data.clear()
            st.success("Cache cleared")

    with col2:
        if st.button("📡 Ping Backend"):
            res = api_get("/")
            st.json(res)

    with col3:
        if st.button("🧠 Inspect Runtime"):
            runtime_info = api_get("/admin/runtime")
            st.json(runtime_info)

    st.divider()

    st.markdown("### 🧪 Raw System Data")

    with st.expander("Dashboard JSON"):
        st.json(dashboard)

    with st.expander("Forge Stats JSON"):
        st.json(forge_stats)

    with st.expander("Builds JSON"):
        st.json(builds)

# ────────────────────────────────────────────────
# FOOTER
# ────────────────────────────────────────────────
st.divider()
st.caption("⚡ NOX Enterprise System • Real-time Intelligence • Build. Scale. Dominate.")