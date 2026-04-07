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

st.title("📊 NOX Enterprise Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ────────────────────────────────────────────────
# API HELPER
# ────────────────────────────────────────────────
@st.cache_data(ttl=30)
def api_get(path: str):
    try:
        res = requests.get(f"{BACKEND_URL}{path}", timeout=10)
        if res.status_code != 200:
            return {"error": res.text}
        return res.json()
    except Exception as e:
        return {"error": str(e)}

# ────────────────────────────────────────────────
# HEALTH CHECK
# ────────────────────────────────────────────────
health = api_get("/")

if "error" in health:
    st.error(f"❌ Backend Offline → {BACKEND_URL}")
else:
    st.success(f"✅ Backend Connected → {BACKEND_URL}")

# ────────────────────────────────────────────────
# LOAD DATA
# ────────────────────────────────────────────────
dashboard = api_get("/admin/dashboard")
timeseries = api_get("/admin/revenue-timeseries")
mrr_data = api_get("/admin/mrr")
forge_stats = api_get("/admin/forge-stats")  # 🔥 NEW (optional backend)

# ────────────────────────────────────────────────
# KPI METRICS
# ────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("👥 Users", dashboard.get("users", 0))
col2.metric("💰 Credits", f"{dashboard.get('credits', 0):,}")
col3.metric("💵 Revenue", f"${dashboard.get('revenue_total', 0):,.2f}")
col4.metric("⚡ 24h", f"${dashboard.get('revenue_24h', 0):,.2f}")

# 🔥 NEW METRIC
col5.metric(
    "🛠 Apps Built",
    forge_stats.get("apps_built", 0) if isinstance(forge_stats, dict) else 0
)

st.divider()

# ─────────────────────────────────────────────