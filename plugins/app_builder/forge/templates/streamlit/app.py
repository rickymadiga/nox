# streamlit/app.py

import streamlit as st
from src.main import main

st.title("Forge App")

if st.button("Run"):
    main()