import streamlit as st
import requests


API_URL = "http://localhost:8000/prompt"


def init_chat():
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


def render_chat():

    init_chat()

    st.subheader("Chat")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Send a task to NOX...")

    if prompt:

        st.session_state.chat_messages.append(
            {"role": "user", "content": prompt}
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        try:

            response = requests.post(
                API_URL,
                json={"prompt": prompt},
                timeout=60
            )

            result = response.json()

            reply = str(result)

        except Exception as e:
            reply = f"Error contacting backend: {e}"

        st.session_state.chat_messages.append(
            {"role": "assistant", "content": reply}
        )

        with st.chat_message("assistant"):
            st.markdown(reply)