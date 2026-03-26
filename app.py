import streamlit as st
import requests

# -------------------------
# CONFIG
# -------------------------

BACKEND_URL = "http://192.168.100.106:8000/chat"

st.set_page_config(
    page_title="NOX Assistant",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 NOX ASSISTANT")

# -------------------------
# SESSION MEMORY
# -------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# -------------------------
# DISPLAY CHAT HISTORY
# -------------------------

for msg in st.session_state.messages:

    if msg["role"] == "user":
        with st.chat_message("user", avatar="🙂"):
            st.markdown(msg["content"])

    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(msg["content"])

# -------------------------
# USER INPUT
# -------------------------

user_input = st.chat_input("Message NOX...")

if user_input:

    # Save user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user", avatar="🙂"):
        st.markdown(user_input)

    # Assistant response container
    with st.chat_message("assistant", avatar="🤖"):
        thinking = st.empty()
        thinking.markdown("⏳ NOX thinking...")

        try:

            response = requests.post(
                BACKEND_URL,
                json={"prompt": user_input},
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            # Flexible response handling
            if isinstance(data, dict):

                if "engine_result" in data and "response" in data["engine_result"]:
                    ai_text = data["engine_result"]["response"].get("message", "")

                elif "message" in data:
                    ai_text = data["message"]

                elif "response" in data:
                    ai_text = data["response"]

                else:
                    ai_text = str(data)

            else:
                ai_text = str(data)

        except Exception as e:
            ai_text = f"⚠ Backend error: {str(e)}"

        thinking.markdown(ai_text)

    # Save assistant reply
    st.session_state.messages.append({
        "role": "assistant",
        "content": ai_text
    })

# -------------------------
# SIDEBAR DEBUG
# -------------------------

st.sidebar.title("NOX System")

st.sidebar.write("Backend URL:")
st.sidebar.code(BACKEND_URL)

st.sidebar.write("Messages in session:")
st.sidebar.write(len(st.session_state.messages))