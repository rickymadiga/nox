import streamlit as st
import requests
import time

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
BACKEND_URL = "http://i84.onrender.com"

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
    if st.session_state.get("user_id") in ["nox", "admin", "cosmic ethic"]:
        return 999999
    data = api_get("/credits", auth=True)
    return data.get("credits", 0) if data else 0


# ────────────────────────────────────────────────
# BEAUTIFUL LIVE LOGS WITH TYPING ILLUSION
# ────────────────────────────────────────────────

def show_live_logs():
    if not st.session_state.token:
        return

    st.subheader("✨ Live Build Process")

    log_box = st.empty()
    logs = []

    # Poll logs for ~20 seconds
    for _ in range(40):  # 40 × 0.5s = 20s
        try:
            res = requests.get(
                f"{BACKEND_URL}/stream",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                timeout=5,
                stream=True
            )

            if res.status_code == 200:
                for line in res.iter_lines():
                    if line:
                        decoded = line.decode("utf-8").replace("data: ", "")
                        logs.append(decoded)

                        log_box.markdown(
                            f"""
                            <div style="
                                background:#0f0f0f;
                                color:#00ff9d;
                                padding:15px;
                                border-radius:10px;
                                height:300px;
                                overflow-y:auto;
                                font-family:monospace;
                            ">
                            {"<br>".join(logs[-30:])}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            time.sleep(0.5)

        except Exception:
            break

# ────────────────────────────────────────────────
# BACKEND HEALTH CHECK
# ────────────────────────────────────────────────
try:
    if requests.get(f"{BACKEND_URL}/", timeout=5).status_code == 200:
        st.success("✅ Backend Connected")
except Exception:
    st.error("❌ Cannot reach backend")

# ────────────────────────────────────────────────
# SIDEBAR (Final Updated Version)
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("🛠️ NOX Controls")

    if not st.session_state.token:
        st.subheader("🔑 Login / Signup")

        username = st.text_input("Username", key="login_username", placeholder="Enter username")
        password = st.text_input("Password", type="password", key="login_password")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Login", use_container_width=True):
                if username and password:
                    data = api_post("/login", {"username": username, "password": password})
                    if data and "access_token" in data:
                        st.session_state.token = data["access_token"]
                        st.session_state.user_id = username.lower().strip()
                        st.success("✅ Login successful!")
                        time.sleep(0.8)
                        st.rerun()

        with col2:
            if st.button("Sign Up", use_container_width=True):
                if username and password:
                    data = api_post("/signup", {"username": username, "password": password})
                    if data:
                        st.success("✅ Account created! Please login now.")

                # ==================== DEV LOGIN ====================
        st.divider()
        st.subheader("🔥 Developer Mode")
        st.caption("Bypass auth • Unlimited credits")

        if st.button("🚀 Login as **admin** (God Mode)", type="primary", use_container_width=True):
            data = api_post("/dev_login", {"username": "admin"})
            if data and "access_token" in data:
                st.session_state.token = data["access_token"]
                st.session_state.user_id = "admin"
                st.success("✅ God Mode Activated (admin)")
                time.sleep(0.8)
                st.rerun()
            else:
                st.error("DEV login failed on backend")

        if st.button("🚀 Login as **nox**", use_container_width=True):
            data = api_post("/dev_login", {"username": "nox"})
            if data and "access_token" in data:
                st.session_state.token = data["access_token"]
                st.session_state.user_id = "nox"
                st.success("✅ God Mode Activated (nox)")
                time.sleep(0.8)
                st.rerun()

        if st.button("🚀 Login as **cosmic ethic**", use_container_width=True):
            data = api_post("/dev_login", {"username": "cosmic ethic"})
            if data and "access_token" in data:
                st.session_state.token = data["access_token"]
                st.session_state.user_id = "cosmic ethic"
                st.success("✅ God Mode Activated")
                time.sleep(0.8)
                st.rerun()
        # ===================================================

    else:
        # === Logged in view ===
        is_dev = st.session_state.user_id in ["nox", "admin", "cosmic ethic"]

        if is_dev:
            st.success("🔥 GOD MODE ACTIVE")
            st.metric("💰 Credits", "∞ Unlimited", delta="DEV")
            st.caption(f"👤 **{st.session_state.user_id}**")
        else:
            st.metric("💰 Credits", st.session_state.credits)
            st.caption(f"👤 **{st.session_state.user_id}**")

        st.divider()

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
                            <script>window.open("{url}", "_blank");</script>
                            <p>✅ Payment page opened in new tab.</p>
                            <p>If it didn't open, <a href="{url}" target="_blank">click here</a></p>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("No payment URL received from server")
                else:
                    error_msg = data.get("detail", "Unknown error") if data else "Failed to connect to server"
                    st.error(f"Payment initialization failed: {error_msg}")

        toggle = st.toggle("Auto Recharge", value=st.session_state.auto_recharge)
        if toggle != st.session_state.auto_recharge:
            st.session_state.auto_recharge = toggle
            api_post("/toggle-auto-recharge", {"enabled": toggle}, auth=True)

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()


# ────────────────────────────────────────────────
# HEADER + USER INFO (Final)
# ────────────────────────────────────────────────
if st.session_state.user_id:
    is_dev = st.session_state.user_id in ["nox", "admin", "cosmic ethic"]

    if is_dev:
        st.markdown("""
            <h2 style='text-align:center; color:#00ff9d;'>
                🔥 GOD MODE ENABLED — Unlimited Credits
            </h2>
        """, unsafe_allow_html=True)
        st.caption(f"👤 **{st.session_state.user_id}** | 💰 **∞ Unlimited** credits")
    else:
        st.caption(f"👤 **{st.session_state.user_id}** | 💰 **{st.session_state.credits}** credits")
else:
    st.caption("👤 Please login to start building")


# ────────────────────────────────────────────────
# CHAT INTERFACE (Updated for God Mode + Download)
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

                        # Improved zip detection for both normal + dev users
                        if result.get("zip") or "God Mode" in msg or "FREE - Unlimited" in msg:
                            st.session_state.last_download = True
                            st.session_state.last_zip_bytes = None  # Force refresh download
                    else:
                        msg = "❌ Server error"

                except requests.exceptions.Timeout:
                    msg = "⏳ Still building... try again shortly."
                except Exception as e:
                    msg = f"❌ {e}"

            st.markdown(msg)

        st.session_state.messages.append(("assistant", msg))

        # Show live logs
        show_live_logs()

# ────────────────────────────────────────────────
# DOWNLOAD SECTION (Fixed & Improved for God Mode)
# ────────────────────────────────────────────────
if st.session_state.token:
    is_dev = st.session_state.user_id in ["nox", "admin", "cosmic ethic"]

    # Show download when flagged or dev build succeeded
    if st.session_state.last_download:
        st.success("🎉 Project Ready!")

        if is_dev:
            st.success("🔥 God Mode: Build completed instantly with unlimited credits!")

        if st.session_state.last_zip_bytes is None:
            with st.spinner("Preparing your download..."):
                dl_res = requests.get(
                    f"{BACKEND_URL}/download/latest",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    timeout=60
                )

                if dl_res.status_code == 200 and dl_res.content:
                    st.session_state.last_zip_bytes = dl_res.content
                    # Auto-update filename with timestamp
                    st.session_state.last_filename = f"nox_app_{int(time.time())}.zip"
                else:
                    st.warning("Download not ready yet. Try clicking the button again in a few seconds.")

        if st.session_state.last_zip_bytes:
            st.download_button(
                label="⬇️ Download Full App",
                data=st.session_state.last_zip_bytes,
                file_name=st.session_state.last_filename,
                mime="application/zip",
                use_container_width=True,
                type="primary"
            )
            st.caption("📁 Your app is ready — click above to download the ZIP file")

st.subheader("📦 Your Build History")

history = api_get("/builds", auth=True)

if history and history.get("builds"):
    for build in history["builds"]:
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**{build['project_name']}**")
            st.caption(f"{build['created_at']}")

        with col2:
            if st.button("⬇️", key=f"dl_{build['id']}"):
                res = requests.get(
                    f"{BACKEND_URL}/download/{build['id']}",
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )

                if res.status_code == 200:
                    st.download_button(
                        label="Download",
                        data=res.content,
                        file_name=build["filename"],
                        mime="application/zip",
                        key=f"btn_{build['id']}"
                    )
                else:
                    st.error("Download failed")
else:
    st.info("No builds yet")            

# Low credits warning (only for normal users)
if st.session_state.token and not is_dev and (st.session_state.last_upsell or st.session_state.credits <= 5):
    st.error("🚫 Low on credits")
    if st.session_state.last_upsell:
        st.info(st.session_state.last_upsell)


# ────────────────────────────────────────────────
# REFRESH CREDITS (Final)
# ────────────────────────────────────────────────
if st.session_state.token:
    st.session_state.credits = fetch_credits()