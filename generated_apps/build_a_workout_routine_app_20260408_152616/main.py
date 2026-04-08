import streamlit as st

days = st.selectbox('Choose a day', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
workout_type = st.selectbox('Choose a workout type', ['Cardio', 'Strength Training', 'Yoga'])

if st.button('Generate Workout Routine'):
    st.write(f'On {days}, do {workout_type} for 30 minutes.')
