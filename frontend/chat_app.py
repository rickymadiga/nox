import streamlit as st
import requests
import time

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
BACKEND_URL = "http://127.0.0.1:8000"

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
    "auto_recharge": False,
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


def api_post(path, payload=None, auth=False, timeout=20):
    headers = {}
    if auth and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        res = requests.post(
            f"{BACKEND_URL}{path}",
            json=payload,
            headers=headers,
            timeout=timeout
        )
        return safe_json(res)
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def api_get(path, auth=False, timeout=10):
    headers = {}
    if auth and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        res = requests.get(
            f"{BACKEND_URL}{path}",
            headers=headers,
            timeout=timeout
        )
        return safe_json(res)
    except Exception:
        return None


def fetch_credits():
    data = api_get("/credits", auth=True)
    return data.get("credits", 0) if data else 0


# ────────────────────────────────────────────────
# BACKEND HEALTH CHECK
# ────────────────────────────────────────────────
try:
    if requests.get(f"{BACKEND_URL}/", timeout=5).status_code == 200:
        st.success("✅ Backend Connected")
except Exception:
    st.error("❌ Cannot reach backend")


# ────────────────────────────────────────────────
# SIDEBAR - Now auto-hides login after successful login
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("🛠️ NOX Controls")

    if not st.session_state.token:
        # === LOGIN / SIGNUP SECTION (only visible when NOT logged in) ===
        st.subheader("🔑 Login / Signup")

        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Login", use_container_width=True):
                if username and password:
                    data = api_post("/login", {
                        "username": username,
                        "password": password
                    })

                    if data and "access_token" in data:
                        st.session_state.token = data["access_token"]
                        st.session_state.user_id = username.lower()

                        st.success("✅ Login successful!")
                        time.sleep(0.8)
                        st.rerun()   # This refreshes and hides the login form

        with col2:
            if st.button("Sign Up", use_container_width=True):
                if username and password:
                    data = api_post("/signup", {
                        "username": username,
                        "password": password
                    })

                    if data:
                        st.success("✅ Account created! Please login now.")

    else:
        # === LOGGED IN SECTION (recharge, auto-recharge, logout) ===
        st.metric("💰 Credits", st.session_state.credits)

        # 💳 Recharge Credits
        st.subheader("💳 Recharge Credits")
        amount = st.number_input("Enter credits amount", 
                                min_value=500, 
                                step=500, 
                                value=500,
                                help="Minimum 500 credits")

        if st.button("💰 Recharge Now", use_container_width=True, type="primary"):
            with st.spinner("Initializing payment..."):
                data = api_post("/paystack/initiate", {"amount": amount}, auth=True)

                if data and data.get("status") == "success":
                    url = data.get("authorization_url")
                    if url:
                        st.success("Redirecting to Paystack...")
                        st.markdown(f"""
                            <script>
                                window.open("{url}", "_blank");
                            </script>
                            <p>✅ Payment page opened in new tab.</p>
                            <p>If it didn't open, <a href="{url}" target="_blank">click here</a></p>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("No payment URL received from server")
                else:
                    error_msg = data.get("detail", "Unknown error") if data else "Failed to connect to server"
                    st.error(f"Payment initialization failed: {error_msg}")

        # 🔁 Auto Recharge
        toggle = st.toggle("Auto Recharge", value=st.session_state.auto_recharge)

        if toggle != st.session_state.auto_recharge:
            st.session_state.auto_recharge = toggle
            api_post("/toggle-auto-recharge", {"enabled": toggle}, auth=True)

        # 🚪 Logout
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()


# ────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────
if st.session_state.user_id:
    st.caption(f"👤 **{st.session_state.user_id}** | 💰 **{st.session_state.credits}** credits")
else:
    st.caption("👤 Please login to start building")


# ────────────────────────────────────────────────
# CHAT HISTORY, CHAT INPUT, DOWNLOAD, LOW CREDITS, REFRESH CREDITS
# (rest of your code remains the same)
# ────────────────────────────────────────────────

for role, content in st.session_state.messages:
    with st.chat_message("user" if role == "user" else "assistant"):
        st.markdown(content)

if st.session_state.token:
    if prompt := st.chat_input("Create with NOX..."):
        st.session_state.messages.append(("user", prompt))

        with st.chat_message("assistant"):
            with st.spinner("NOX is working... (20–60s)"):
                try:
                    result = api_post("/chat", {"prompt": prompt}, auth=True, timeout=120)

                    if result:
                        msg = result.get("response", "No response")
                        st.session_state.last_upsell = result.get("upsell")

                        if result.get("zip"):
                            st.session_state.last_download = True
                            st.session_state.last_zip_bytes = None
                    else:
                        msg = "❌ Server error"

                except requests.exceptions.Timeout:
                    msg = "⏳ Still building... try download shortly."
                except Exception as e:
                    msg = f"❌ {e}"

            st.markdown(msg)

        st.session_state.messages.append(("assistant", msg))


if st.session_state.last_download and st.session_state.token:
    st.success("🎉 Project Ready!")

    if st.session_state.last_zip_bytes is None:
        dl_res = requests.get(
            f"{BACKEND_URL}/download/latest",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=60
        )

        if dl_res.status_code == 200:
            st.session_state.last_zip_bytes = dl_res.content
        else:
            st.error("Download not ready yet.")

    if st.session_state.last_zip_bytes:
        st.download_button(
            label="⬇️ Download Full App",
            data=st.session_state.last_zip_bytes,
            file_name=st.session_state.last_filename,
            mime="application/zip",
            use_container_width=True
        )


if st.session_state.token and (st.session_state.last_upsell or st.session_state.credits <= 5):
    st.error("🚫 Low on credits")
    if st.session_state.last_upsell:
        st.info(st.session_state.last_upsell)


if st.session_state.token:
    st.session_state.credits = fetch_credits()