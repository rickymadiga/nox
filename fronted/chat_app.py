import streamlit as st
import requests
import time

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
BACKEND_URL = "https://nox-backend.onrender.com"

st.set_page_config(
    page_title="NOX SMART WORLD",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ────────────────────────────────────────────────
# STYLING
# ────────────────────────────────────────────────
st.markdown("""
    <style>
    .stChatMessage.user {
        background-color: #2d3748 !important;
        border-radius: 12px;
    }
    .stChatMessage.assistant {
        background-color: #1a202c !important;
        border-radius: 12px;
        border-left: 4px solid #f6ad55;
    }
    .log-box {
        background: #111;
        color: #0f0;
        padding: 12px;
        border-radius: 8px;
        font-family: monospace;
        height: 320px;
        overflow-y: auto;
        white-space: pre-wrap;
    }
    .payment-link {
        background-color: #f6ad55;
        color: black;
        font-weight: bold;
        padding: 12px 20px;
        border-radius: 8px;
        text-align: center;
        display: inline-block;
        margin: 12px 0;
        text-decoration: none;
    }
    .payment-link:hover {
        background-color: #ffcc77;
    }
    </style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center;'>🤖 NOX SMART WORLD</h1>", unsafe_allow_html=True)
st.caption("AI Agent Builder • Real-time Build Monitoring")

# ────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"

if "credits" not in st.session_state:
    st.session_state.credits = 0

if "auto_recharge" not in st.session_state:
    st.session_state.auto_recharge = False

if "last_msg" not in st.session_state:
    st.session_state.last_msg = ""

if "last_upsell" not in st.session_state:
    st.session_state.last_upsell = None

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────
def fetch_credits():
    try:
        res = requests.get(f"{BACKEND_URL}/credits/{st.session_state.user_id}", timeout=5)
        data = res.json()
        st.session_state.is_admin = data.get("is_admin", False)
        return data.get("credits", 0)
    except:
        return st.session_state.credits


def buy_plan(plan: str):
    """Buy plan with better error handling"""
    try:
        res = requests.post(
            f"{BACKEND_URL}/create-checkout-session",
            json={
                "user_id": st.session_state.user_id,
                "plan": plan
            },
            timeout=12
        )

        # Safe JSON parsing
        try:
            data = res.json()
        except:
            st.error(f"Server returned non-JSON response (Status {res.status_code}):\n{res.text[:400]}")
            return

        if "url" in data:
            checkout_url = data["url"]
            st.success("Redirecting to Stripe checkout...")
            st.markdown(
                f"""
                <a href="{checkout_url}" target="_blank" class="payment-link">
                    👉 Complete Payment on Stripe
                </a>
                """,
                unsafe_allow_html=True
            )
            # Auto open
            st.components.v1.html(
                f'<script>window.open("{checkout_url}", "_blank");</script>', 
                height=0
            )

        else:
            st.error(data.get("error", f"Payment failed (Status {res.status_code})"))

    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")


# ────────────────────────────────────────────────
# INITIAL CREDIT LOAD
# ────────────────────────────────────────────────
if st.session_state.credits == 0:
    st.session_state.credits = fetch_credits()

# ────────────────────────────────────────────────
# HANDLE STRIPE REDIRECT
# ────────────────────────────────────────────────
params = st.query_params
if "success" in params:
    st.success("🎉 Payment successful! Credits updated.")
    st.session_state.credits = fetch_credits()
    st.query_params.clear()
elif "canceled" in params:
    st.warning("Payment was canceled.")
    st.query_params.clear()

# ────────────────────────────────────────────────
# LIVE BUILD ACTIVITY + STREAM
# ────────────────────────────────────────────────
st.markdown("## ⚙️ Live Build Activity")

col_logs, col_stream = st.columns([1, 1])

with col_logs:
    log_placeholder = st.empty()

    def fetch_logs():
        try:
            res = requests.get(
                f"{BACKEND_URL}/logs/{st.session_state.user_id}",
                timeout=3
            )
            return res.json().get("logs", [])
        except:
            return []

    logs = fetch_logs()
    log_placeholder.markdown(
        "\n\n".join([f"• {log}" for log in logs]) if logs else "No build activity yet."
    )

with col_stream:
    st.markdown("### Live Build Stream")
    user_id = st.session_state.user_id
    backend_stream_url = f"{BACKEND_URL}/stream/{user_id}"

    st.components.v1.html(
        f"""
        <div id="log-box" class="log-box"></div>

        <script>
        const evtSource = new EventSource("{backend_stream_url}");

        const logBox = document.getElementById("log-box");

        evtSource.onmessage = function(event) {{
            const line = document.createElement("div");
            line.textContent = "[" + new Date().toLocaleTimeString() + "] " + event.data;
            logBox.appendChild(line);
            logBox.scrollTop = logBox.scrollHeight;
        }};

        evtSource.onerror = function() {{
            const errorLine = document.createElement("div");
            errorLine.textContent = "[ERROR] Connection lost. Retrying...";
            errorLine.style.color = "#ff5555";
            logBox.appendChild(errorLine);
        }};
        </script>
        """,
        height=340,
    )

st.divider()

# ────────────────────────────────────────────────
# CHAT INTERFACE
# ────────────────────────────────────────────────
st.markdown("## 💬 Chat with NOX")

# Display chat history
for role, content in st.session_state.messages:
    avatar = "🙂" if role == "user" else "🤖"
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)

# Chat Input
if prompt := st.chat_input("Create with NOX... (e.g. Build me a SaaS dashboard)"):
    with st.chat_message("user", avatar="🙂"):
        st.markdown(prompt)

    st.session_state.messages.append(("user", prompt))

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("NOX is building..."):
            msg = "No response"
            upsell = None

            try:
                req = requests.post(
                    f"{BACKEND_URL}/chat",
                    json={"prompt": prompt, "user_id": st.session_state.user_id},
                    timeout=45
                )
                result = req.json()
                msg = result.get("response", "Sorry, something went wrong.")
                upsell = result.get("upsell")

            except Exception as e:
                msg = f"Error: {str(e)}"

        st.markdown(msg)

    # Update session
    st.session_state.last_msg = msg
    st.session_state.last_upsell = upsell
    st.session_state.messages.append(("assistant", msg))
    st.session_state.credits = fetch_credits()

# ────────────────────────────────────────────────
# CREDIT / UPSELL SECTION
# ────────────────────────────────────────────────
if (st.session_state.last_upsell or 
    "Not enough credits" in st.session_state.last_msg or 
    st.session_state.credits <= 5):

    st.error("🚫 You're low on credits")

    if st.session_state.last_upsell:
        st.info(st.session_state.last_upsell)

    st.markdown("## 💳 Get More Credits")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Starter ($5)", key=f"starter_{len(st.session_state.messages)}", use_container_width=True):
            buy_plan("starter")
    with col2:
        if st.button("Pro ($20) ⭐", key=f"pro_{len(st.session_state.messages)}", use_container_width=True):
            buy_plan("pro")
    with col3:
        if st.button("Mega ($50)", key=f"mega_{len(st.session_state.messages)}", use_container_width=True):
            buy_plan("mega")

# ────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("🛠️ NOX Controls")

    st.markdown("### 💰 Credits")
    st.metric("Available", f"{st.session_state.credits} credits")

    if st.session_state.credits <= 5:
        st.error("⚠ Low credits — Recharge recommended")
    elif st.session_state.credits <= 15:
        st.warning("⚡ Running low")

    st.divider()

    # Auto Recharge
    st.markdown("### ⚡ Auto Recharge")
    auto_toggle = st.toggle(
        "Enable auto top-up",
        value=st.session_state.auto_recharge,
        help="Automatically recharge when credits drop low"
    )

    if auto_toggle != st.session_state.auto_recharge:
        st.session_state.auto_recharge = auto_toggle
        try:
            requests.post(
                f"{BACKEND_URL}/toggle-auto-recharge",
                json={"user_id": st.session_state.user_id, "enabled": auto_toggle}
            )
        except:
            st.error("Failed to update auto-recharge setting")

    st.divider()

    # Buy Plans (Card Style)
    st.markdown("### 💳 Buy Plans")

    for title, price, credits_amount, plan_key in [
        ("Starter", 5, "50 credits", "starter"),
        ("Pro", 20, "250 credits", "pro"),
        ("Mega", 50, "800 credits", "mega")
    ]:
        st.markdown(f"""
            <div style="border:1px solid #333; border-radius:10px; padding:10px; margin:8px 0; background:#0f0f1a;">
                <strong>{title}</strong><br>
                <span style="font-size:1.4em;">${price}</span><br>
                <small>{credits_amount}</small>
            </div>
        """, unsafe_allow_html=True)

        if st.button(f"Buy {title}", key=f"sidebar_{plan_key}", use_container_width=True):
            buy_plan(plan_key)

    st.divider()

    # Admin Status
    if st.session_state.is_admin:
        st.success("✅ Admin Mode Active (Unlimited Access)")
    else:
        st.info("Standard User")

    st.caption(f"User ID: {st.session_state.user_id}")
    if st.button("🧹 Clear Chat History"):
        st.session_state.messages = []
        st.rerun()