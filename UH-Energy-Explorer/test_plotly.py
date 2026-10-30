import streamlit as st
import plotly.express as px

st.title("Plotly Warning Test")

fig = px.line(
    x=[2022, 2023, 2024, 2025],
    y=[100, 150, 120, 200]
)

st.plotly_chart(
    fig,
    width="stretch"
)