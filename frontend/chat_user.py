import streamlit as st
import requests
import time

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
BACKEND_URL = "https://nox-ui84.onrender.com"

st.set_page_config(page_title="NOX SMART WORLD", page_icon="🤖", layout="wide")
st.markdown("<h1 style='text-align:center;'>NOX SMART WORLD</h1>", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────
defaults = {
    "messages": [],
    "token": None,
    "user_id": None,
    "credits": 0,
    "last_upsell": None,
    "last_download": False,
    "last_zip_bytes": None,
    "last_filename": "nox_app.zip",
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────
def safe_json(res):
    try:
        data = res.json()
    except Exception:
        st.error("Invalid response from server")
        return None

    if res.status_code != 200:
        detail = data.get("detail") or str(data)
        st.error(f"Error: {detail}")
        return None

    return data


def api_post(path, payload=None, auth=False, timeout=30):
    headers = {}
    if auth and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        res = requests.post(f"{BACKEND_URL}{path}", json=payload, headers=headers, timeout=timeout)
        return safe_json(res)
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def api_get(path, auth=False, timeout=10):
    headers = {}
    if auth and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        res = requests.get(f"{BACKEND_URL}{path}", headers=headers, timeout=timeout)
        return safe_json(res)
    except Exception:
        return None


def fetch_credits():
    data = api_get("/credits", auth=True)
    return data.get("credits", 0) if data else 0


# ────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("🛠️ NOX Controls")

    if not st.session_state.token:
        st.subheader("🔑 Login / Signup")

        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Login", use_container_width=True):
                if username and password:
                    data = api_post("/login", {"username": username, "password": password})
                    if data and "access_token" in data:
                        st.session_state.token = data["access_token"]
                        st.session_state.user_id = username.lower().strip()
                        st.success("✅ Login successful!")
                        st.rerun()

        with col2:
            if st.button("Sign Up", use_container_width=True):
                if username and password:
                    data = api_post("/signup", {"username": username, "password": password})
                    if data:
                        st.success("✅ Account created! Please login.")

    else:
        st.success(f"👤 {st.session_state.user_id}")
        st.metric("💰 Credits", st.session_state.credits)

        st.divider()

        st.subheader("💳 Recharge Credits")
        amount = st.number_input("Amount", min_value=500, step=500, value=500)

        if st.button("💰 Recharge Now", type="primary", use_container_width=True):
            with st.spinner("Connecting to Paystack..."):
                data = api_post("/paystack/initiate", {"amount": amount}, auth=True)

                if data and data.get("authorization_url"):
                    url = data["authorization_url"]
                    st.success("Redirecting to payment...")
                    st.markdown(f'<a href="{url}" target="_blank">Click here if not redirected</a>', unsafe_allow_html=True)
                else:
                    st.error("Payment failed to start")

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# ────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────
if st.session_state.user_id:
    st.caption(f"👤 {st.session_state.user_id} | 💰 {st.session_state.credits} credits")
else:
    st.caption("👤 Please login to start building")

# ────────────────────────────────────────────────
# CHAT HISTORY
# ────────────────────────────────────────────────
for role, content in st.session_state.messages:
    with st.chat_message("user" if role == "user" else "assistant"):
        st.markdown(content)

# ────────────────────────────────────────────────
# CHAT INPUT
# ────────────────────────────────────────────────
if st.session_state.token:
    if prompt := st.chat_input("What do you want to build today?"):
        st.session_state.messages.append(("user", prompt))

        with st.chat_message("assistant"):
            with st.spinner("⚙️ NOX is building your app..."):
                result = api_post("/chat", {"prompt": prompt}, auth=True, timeout=120)

                if result:
                    msg = result.get("response", "No response")

                    # ✅ ONLY trigger download when zip exists
                    if result.get("zip") is not None:
                        st.session_state.last_download = True
                        st.session_state.last_zip_bytes = None

                    st.session_state.last_upsell = result.get("upsell")

                else:
                    msg = "❌ Something went wrong. Try again."

            st.markdown(msg)

        st.session_state.messages.append(("assistant", msg))
        st.session_state.credits = fetch_credits()

# ────────────────────────────────────────────────
# DOWNLOAD SECTION
# ────────────────────────────────────────────────
if st.session_state.token and st.session_state.last_download:
    st.success("🎉 Your app is ready!")

    if st.session_state.last_zip_bytes is None:
        st.info("⚙️ Finalizing your app package...")

        with st.spinner("Preparing download..."):
            dl_res = requests.get(
                f"{BACKEND_URL}/download/latest",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                timeout=60
            )

            if dl_res.status_code == 200:
                st.session_state.last_zip_bytes = dl_res.content
                st.session_state.last_filename = f"nox_app_{int(time.time())}.zip"
            else:
                st.warning("Download not ready yet.")

    if st.session_state.last_zip_bytes:
        st.download_button(
            label="⬇️ Download Your App",
            data=st.session_state.last_zip_bytes,
            file_name=st.session_state.last_filename,
            mime="application/zip",
            use_container_width=True,
            type="primary"
        )

    # ✅ Retry Button
    if st.button("🔄 Retry Download", use_container_width=True):
        st.session_state.last_zip_bytes = None
        st.rerun()

# ────────────────────────────────────────────────
# BUILD HISTORY
# ────────────────────────────────────────────────
if st.session_state.token:
    st.subheader("📦 Your Build History")

    history = api_get("/builds", auth=True)

    if history and history.get("builds"):
        for build in history["builds"]:
            with st.expander(f"📁 {build.get('project_name', 'App')}"):
                st.caption(f"Built on: {build.get('created_at', '')}")
    else:
        st.info("No builds yet. Start building something!")

# ────────────────────────────────────────────────
# LOW CREDIT WARNING
# ────────────────────────────────────────────────
if st.session_state.token and st.session_state.credits <= 10:
    st.warning("⚠️ Low credits! Recharge to continue building.")