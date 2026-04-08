import streamlit as st
st.title('Daily Health Check')
st.subheader('How are you feeling today?')
name = st.text_input('Name')
age = st.number_input('Age')
feelings = st.selectbox('Feelings', ['Good', 'Bad', 'Neutral'])
submit = st.button('Submit')
if submit:
    st.write('Hello, ' + name + '! You are ' + str(age) + ' years old and feeling ' + feelings + '.')
