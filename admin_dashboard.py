import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import time

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="NOX Admin Enterprise",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better aesthetics
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e2e;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #2a2a3c;
    }
    .stMetric {
        background-color: #1e1e2e;
        padding: 1rem;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 NOX Enterprise Dashboard")
st.caption("Real-time monitoring & insights | Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

BACKEND_URL = "http://127.0.0.1:8000"

# ────────────────────────────────────────────────
# CACHING HELPERS (Big performance win)
# ────────────────────────────────────────────────
@st.cache_data(ttl=60)  # Cache for 60 seconds
def get(path: str):
    try:
        response = requests.get(f"{BACKEND_URL}{path}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch {path}: {e}")
        return {}
    except Exception as e:
        st.error(f"Unexpected error fetching {path}: {e}")
        return {}

# ────────────────────────────────────────────────
# LOAD DATA
# ────────────────────────────────────────────────
with st.spinner("Loading dashboard data..."):
    dashboard = get("/admin/dashboard")
    timeseries = get("/admin/revenue-timeseries")
    mrr_data = get("/admin/mrr")

# ────────────────────────────────────────────────
# TOP KPI METRICS
# ────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4, gap="small")

with col1:
    st.metric(
        label="👥 Total Users",
        value=dashboard.get("users", 0),
        delta=None  # You can add delta later if backend supports it
    )

with col2:
    st.metric(
        label="💰 Total Credits",
        value=f"{dashboard.get('credits', 0):,}",
    )

with col3:
    st.metric(
        label="💵 Total Revenue",
        value=f"${dashboard.get('revenue_total', 0):,.2f}"
    )

with col4:
    st.metric(
        label="⚡ 24h Revenue",
        value=f"${dashboard.get('revenue_24h', 0):,.2f}",
        delta=f"+{dashboard.get('revenue_24h', 0) * 0.15:.1f}%"  # Example delta (customize)
    )

st.divider()

# ────────────────────────────────────────────────
# MRR SECTION - Enhanced
# ────────────────────────────────────────────────
st.markdown("## 💸 Monthly Recurring Revenue (MRR)")

mrr_value = mrr_data.get("mrr", 0)
col_mrr1, col_mrr2 = st.columns([2, 3])

with col_mrr1:
    st.metric("Current MRR", f"${mrr_value:,.2f}", delta=None)

with col_mrr2:
    breakdown = mrr_data.get("breakdown", {})
    if breakdown:
        df_mrr = pd.DataFrame(list(breakdown.items()), columns=["Plan", "Users"])
        fig = px.bar(
            df_mrr, 
            x="Plan", 
            y="Users",
            color="Plan",
            title="MRR Breakdown by Plan",
            text="Users"
        )
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ────────────────────────────────────────────────
# REVENUE TIMELINE - Upgraded with Plotly
# ────────────────────────────────────────────────
st.markdown("## 📈 Revenue Trend (Last 24 Hours)")

if timeseries:
    df = pd.DataFrame(timeseries)
    df["time"] = pd.to_datetime(df["time"], unit='s')
    
    # Resample if too many points (optional smoothness)
    if len(df) > 100:
        df = df.set_index("time").resample('5min').sum().reset_index()

    fig = px.line(
        df, 
        x="time", 
        y=df.columns[1] if len(df.columns) > 1 else "revenue",  # adjust column name if needed
        title="Revenue Over Time (Last 24h)",
        markers=True,
        line_shape="spline"
    )
    fig.update_layout(height=420, xaxis_title="Time", yaxis_title="Revenue ($)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No revenue timeseries data available yet.")

st.divider()

# ────────────────────────────────────────────────
# TABS SECTION
# ────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["👥 Users", "💳 Transactions", "🚨 Abuse Monitoring"])

with tab1:
    users = get("/admin/users")
    if users:
        df_users = pd.DataFrame(users)
        st.dataframe(
            df_users,
            use_container_width=True,
            hide_index=True,
            column_order=sorted(df_users.columns)  # nicer ordering
        )
        
        # Quick stats
        st.caption(f"Showing {len(df_users)} users")
    else:
        st.warning("No user data available.")

with tab2:
    tx = get("/admin/transactions")
    if tx:
        df_tx = pd.DataFrame(tx)
        st.dataframe(df_tx, use_container_width=True, hide_index=True)
        
        # Optional: Summary metrics in tabs
        total_tx = len(df_tx)
        total_amount = df_tx.get("amount", pd.Series([0])).sum()
        
        subcol1, subcol2 = st.columns(2)
        subcol1.metric("Total Transactions", total_tx)
        subcol2.metric("Total Amount Processed", f"${total_amount:,.2f}")
    else:
        st.info("No transactions recorded yet.")

with tab3:
    abuse = dashboard.get("abuse", [])
    if abuse:
        st.error(f"🚨 {len(abuse)} abuse events detected!")
        df_abuse = pd.DataFrame(abuse)
        st.dataframe(df_abuse, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No abuse detected. All systems clean.")

# ────────────────────────────────────────────────
# SIDEBAR - Enhanced
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Controls")
    
    if st.button("🔄 Refresh Dashboard", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    
    # Auto-refresh option
    auto_refresh = st.checkbox("Enable Auto-refresh (30s)", value=False)
    if auto_refresh:
        time.sleep(30)
        st.rerun()

    st.divider()
    
    st.markdown("### 🚀 Growth Insights")
    
    if mrr_value < 100:
        st.info("👉 Focus on free → Starter conversion")
    elif mrr_value < 1000:
        st.warning("👉 Optimize pricing tiers and upsells")
    elif mrr_value < 5000:
        st.success("🔥 Solid growth trajectory!")
    else:
        st.success("🏆 Excellent revenue performance!")

    st.divider()
    
    st.markdown("**Backend Status**")
    st.caption(f"Connected to: `{BACKEND_URL}`")

# Footer
st.caption("NOX Enterprise Admin Dashboard • Built with ❤️ using Streamlit")