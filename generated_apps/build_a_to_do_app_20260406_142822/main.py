import streamlit as st

task = st.text_input('Enter a task')
button = st.button('Add task')
if button:
    st.write('Task added: ', task)
