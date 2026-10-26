"""Multimodal Construction Intelligence Platform - Streamlit entry point.

Run:  streamlit run app.py
"""
import streamlit as st

from core.config import APP_NAME
from ui import tab_assistant, tab_cracks, tab_dossier, tab_planning, tab_safety
from ui.components import html
from ui.sidebar import render_sidebar
from ui.state import init_state
from ui.styles import CSS

st.set_page_config(page_title=APP_NAME, page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
init_state()

client = render_sidebar()

html("""
<div class="hero">
  <div class="hero-kicker">AI · Construction · Real Estate Decision Support</div>
  <div class="hero-title">Multimodal Construction Intelligence Platform</div>
  <div class="hero-sub">Audit PPE compliance, diagnose concrete cracks, value your project in ₹ and get weather-aware
  daily protocols - powered by multimodal AI with strict JSON data contracts.</div>
</div>
""")

tab_safety_ui, tab_crack_ui, tab_plan_ui, tab_assist_ui, tab_dossier_ui = st.tabs(
    ["🦺 Site Safety & PPE", "🧱 Crack Diagnostics", "📐 Planning & Valuation", "🌦️ Site Assistant", "📁 Project Dossier"]
)
with tab_safety_ui:
    tab_safety.render(client)
with tab_crack_ui:
    tab_cracks.render(client)
with tab_plan_ui:
    tab_planning.render()
with tab_assist_ui:
    tab_assistant.render(client)
with tab_dossier_ui:
    tab_dossier.render()
