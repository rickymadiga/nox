import streamlit as st


def init_logs():
    """Initialize log storage."""
    if "agent_logs" not in st.session_state:
        st.session_state.agent_logs = []


def add_log(message: str):
    """Add a log entry."""
    init_logs()
    st.session_state.agent_logs.append(message)


def clear_logs():
    """Clear log history."""
    st.session_state.agent_logs = []


def render_activity_log():
    """Render activity log panel."""

    init_logs()

    st.subheader("Agent Activity")

    if not st.session_state.agent_logs:
        st.info("No activity yet.")
        return

    for log in st.session_state.agent_logs[-50:]:
        st.code(log)