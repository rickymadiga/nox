import streamlit as st
from .agent_graph import render_agent_graph


def render_pipeline_view():

    st.subheader("Forge Pipeline")

    render_agent_graph()