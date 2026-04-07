import streamlit as st

AGENTS = [
    "planner",
    "coder",
    "tester",
    "reviewer",
    "fixer",
    "assembler"
]


def init_pipeline_state():
    """Initialize pipeline state if not present."""
    if "pipeline_state" not in st.session_state:
        st.session_state.pipeline_state = {
            agent: "waiting" for agent in AGENTS
        }


def update_agent_state(agent, state):
    """
    Update the state of a pipeline agent.

    states:
    waiting
    running
    done
    """
    if "pipeline_state" not in st.session_state:
        init_pipeline_state()

    st.session_state.pipeline_state[agent] = state


def render_agent_graph():
    """Render horizontal pipeline visualization."""

    init_pipeline_state()

    st.subheader("Forge Agent Pipeline")

    cols = st.columns(len(AGENTS))

    for i, agent in enumerate(AGENTS):

        state = st.session_state.pipeline_state.get(agent, "waiting")

        if state == "done":
            icon = "✅"

        elif state == "running":
            icon = "⚙️"

        else:
            icon = "⏳"

        cols[i].metric(
            label=agent.capitalize(),
            value=icon
        )


def reset_pipeline():
    """Reset pipeline state for new task."""

    st.session_state.pipeline_state = {
        agent: "waiting" for agent in AGENTS
    }