"""Session-state helpers + consolidated project dossier."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.formatting import utc_now_iso

DEFAULTS = {
    "safety_report": None,
    "crack_report": None,
    "crack_overlay": None,
    "valuation": None,
    "render_url": None,
    "weather_condition": "Normal",
    "live_weather": None,
    "chat_history": [],
    "activity": [],
}


def init_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = list(value) if isinstance(value, list) else value


def log_activity(message: str) -> None:
    st.session_state["activity"].append(f"{datetime.now():%H:%M:%S}  {message}")
    st.session_state["activity"] = st.session_state["activity"][-30:]


def assistant_context() -> dict:
    """Compact project context handed to the chatbot."""
    ctx: dict = {"weather_condition": st.session_state["weather_condition"]}
    if st.session_state["valuation"]:
        ctx["valuation"] = st.session_state["valuation"]
    if st.session_state["safety_report"]:
        r = st.session_state["safety_report"]
        ctx["safety"] = {"safety_score": r.safety_score, "overall_status": r.overall_status, "summary": r.summary,
                         "hazards": [h.hazard for h in r.hazards]}
    if st.session_state["crack_report"]:
        c = st.session_state["crack_report"]
        ctx["crack"] = c.model_dump(include={"defect_type", "estimated_width_mm", "severity_level", "severity_score", "urgency"})
    return ctx


def build_dossier() -> dict:
    s = st.session_state
    return {
        "report_type": "project_dossier",
        "generated_at": utc_now_iso(),
        "safety_audit": s["safety_report"].model_dump() if s["safety_report"] else None,
        "crack_diagnostic": s["crack_report"].model_dump() if s["crack_report"] else None,
        "planning_valuation": s["valuation"],
        "weather_condition": s["weather_condition"],
        "live_weather": s["live_weather"],
        "assistant_transcript": s["chat_history"],
    }
