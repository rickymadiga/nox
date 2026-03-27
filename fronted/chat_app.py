import streamlit as st
import requests
import json

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
BACKEND_URL = "https://your-backend.onrender.com"  # 🔥 CHANGE THIS

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
    </style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center;'>🤖 NOX SMART WORLD</h1>", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────
for key, default in {
    "messages": [],
    "token": None,
    "user_id": None,
    "credits": 0,
    "auto_recharge": False,
    "last_msg": "",
    "last_upsell": None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ────────────────────────────────────────────────
# SAFE JSON HELPER
# ────────────────────────────────────────────────
def safe_json(res, show_error=True):
    if res.status_code != 200:
        if show_error:
            st.error(res.text)
        return None
    try:
        return res.json()
    except:
        if show_error:
            st.error("Invalid JSON response from server")
        return None

# ────────────────────────────────────────────────
# BACKEND CONNECTION TEST
# ────────────────────────────────────────────────
try:
    res = requests.get(f"{BACKEND_URL}/", timeout=5)
    if res.status_code == 200:
        st.success("✅ Backend Connected")
    else:
        st.error(res.text)
except:
    st.error("❌ Cannot reach backend. Check BACKEND_URL")

# ────────────────────────────────────────────────
# AUTH UI (Sidebar)
# ────────────────────────────────────────────────
st.sidebar.title("🔐 Account")

username = st.sidebar.text_input("Username", key="auth_username")
password = st.sidebar.text_input("Password", type="password", key="auth_password")

col1, col2 = st.sidebar.columns(2)

def login():
    try:
        res = requests.post(
            f"{BACKEND_URL}/login",
            json={"username": username, "password": password}
        )

        data = safe_json(res)
        if not data:
            return

        if "token" in data:
            st.session_state.token = data["token"]
            st.session_state.user_id = username
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error(data.get("detail", "Login failed"))

    except Exception as e:
        st.error(f"Login error: {str(e)}")


def signup():
    try:
        res = requests.post(
            f"{BACKEND_URL}/signup",
            json={"username": username, "password": password}
        )

        data = safe_json(res)
        if not data:
             return

        st.success("✅ Account created! Please login.")

    except Exception as e:
        st.error(f"Signup error: {str(e)}")


with col1:
    if st.button("Login", use_container_width=True):
        login()

with col2:
    if st.button("Signup", use_container_width=True):
        signup()

# ────────────────────────────────────────────────
# BLOCK UI IF NOT LOGGED IN
# ────────────────────────────────────────────────
if not st.session_state.token:
    st.title("🔐 Please login or signup to continue")
    st.stop()

# ────────────────────────────────────────────────
# FETCH CREDITS
# ────────────────────────────────────────────────
def fetch_credits():
    try:
        res = requests.get(
            f"{BACKEND_URL}/credits/{st.session_state.user_id}",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )

        data = safe_json(res, show_error=False)
        if not data:
            return st.session_state.credits

        return data.get("credits", 0)

    except:
        return st.session_state.credits

# Refresh credits
st.session_state.credits = fetch_credits()

# ────────────────────────────────────────────────
# HEADER WITH USER INFO
# ────────────────────────────────────────────────
st.caption(f"👤 **{st.session_state.user_id}** | 💰 **{st.session_state.credits}** credits")

# ────────────────────────────────────────────────
# CHAT HISTORY
# ────────────────────────────────────────────────
for role, content in st.session_state.messages:
    avatar = "🙂" if role == "user" else "🤖"
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)

# ────────────────────────────────────────────────
# CHAT INPUT
# ────────────────────────────────────────────────
if prompt := st.chat_input("Create with NOX..."):

    st.session_state.messages.append(("user", prompt))

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("NOX is thinking..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/chat",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    json={"prompt": prompt},
                    timeout=60
                )

                if response.status_code != 200:
                    msg = f"❌ Error: {response.text}"
                    upsell = None
                else:
                    result = response.json()
                    msg = result.get("response", "No response")
                    upsell = result.get("upsell")

            except Exception as e:
                msg = f"❌ Error: {str(e)}"
                upsell = None

        st.markdown(msg)

    st.session_state.messages.append(("assistant", msg))
    st.session_state.last_msg = msg
    st.session_state.last_upsell = upsell

    # Refresh credits
    st.session_state.credits = fetch_credits()

# ────────────────────────────────────────────────
# GLOBAL UPSELL / LOW CREDITS BLOCK
# ────────────────────────────────────────────────
if (
    st.session_state.last_upsell
    or "Not enough credits" in st.session_state.last_msg
    or st.session_state.credits <= 5
):
    st.error("🚫 You're low on credits")

    if st.session_state.last_upsell:
        st.info(st.session_state.last_upsell)

    st.markdown("## 💳 Get more credits")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Starter ($5)", key=f"starter_{len(st.session_state.messages)}"):
            buy_plan("starter")

    with col2:
        if st.button("Pro ($20) ⭐", key=f"pro_{len(st.session_state.messages)}"):
            buy_plan("pro")

    with col3:
        if st.button("Mega ($50)", key=f"mega_{len(st.session_state.messages)}"):
            buy_plan("mega")

# ────────────────────────────────────────────────
# BUY PLAN FUNCTION
# ────────────────────────────────────────────────
def buy_plan(plan: str):
    try:
        res = requests.post(
            f"{BACKEND_URL}/create-checkout-session",
            json={
                "user_id": st.session_state.user_id,
                "plan": plan
            }
        )

        data = safe_json(res)
        if not data:
            return

        if "url" in data:
            st.success("Redirecting to payment...")
            st.markdown(
                f'<a href="{data["url"]}" target="_blank">👉 Complete Payment</a>',
                unsafe_allow_html=True
            )
        else:
            st.error(data.get("error", "Payment failed"))

    except Exception as e:
        st.error(f"Payment error: {str(e)}")

# ────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("🛠️ NOX Controls")

    st.metric("💰 Credits", st.session_state.credits)

    if st.session_state.credits <= 5:
        st.error("Low credits")
    elif st.session_state.credits <= 15:
        st.warning("Running low")
    else:
        st.success("Healthy")

    st.divider()

    # Auto Recharge
    toggle = st.toggle("Auto Recharge", value=st.session_state.auto_recharge)

    if toggle != st.session_state.auto_recharge:
        st.session_state.auto_recharge = toggle
        try:
            res = requests.post(
                f"{BACKEND_URL}/toggle-auto-recharge",
                json={
                    "user_id": st.session_state.user_id,
                    "enabled": toggle
                }
            )
            if res.status_code != 200:
                st.error(res.text)
        except:
            st.error("Failed to update auto recharge")

    st.divider()

    # Logout
    if st.button("🚪 Logout"):
        st.session_state.token = None
        st.session_state.user_id = None
        st.session_state.messages = []
        st.rerun()