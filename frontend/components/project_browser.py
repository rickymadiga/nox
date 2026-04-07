import streamlit as st
import os

PROJECT_DIR = "plugins/app_builder/generated_apps"


def render_project_browser():

    st.sidebar.header("Generated Apps")

    if not os.path.exists(PROJECT_DIR):
        st.sidebar.info("No projects yet.")
        return

    apps = os.listdir(PROJECT_DIR)

    if not apps:
        st.sidebar.info("No generated apps.")
        return

    for app in apps:
        st.sidebar.write("📦", app)