"""Tab 5 - Project Dossier: consolidated export of every analysis."""
from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from core.formatting import format_inr
from ui.components import callout, metric_card, metric_row, section_header, subhead
from ui.state import build_dossier


def render() -> None:
    section_header("📁", "Project Dossier", "One consolidated, contract-validated JSON export of everything analysed this session.")
    s = st.session_state
    safety, crack, val = s["safety_report"], s["crack_report"], s["valuation"]
    metric_row([
        metric_card("Safety score", f"{safety.safety_score}/100" if safety else "-", safety.overall_status if safety else "Run an audit", "green"),
        metric_card("Crack severity", crack.severity_level if crack else "-", crack.defect_type if crack else "Run a diagnosis", "red"),
        metric_card("Current valuation", format_inr(val["valuation"]["current_value"]) if val else "-", "Planning tab", "amber"),
        metric_card("Weather protocol", s["weather_condition"], "Assistant tab", "cyan"),
    ])
    if not (safety or crack or val):
        callout("Nothing to export yet - run an analysis in the other tabs first.", "info")
    dossier = build_dossier()
    payload = json.dumps(dossier, indent=2, default=str)
    st.download_button("⬇️ Download full project dossier (JSON)", payload,
                       f"project_dossier_{datetime.now():%Y%m%d_%H%M%S}.json", "application/json", type="primary")
    subhead("Session Activity")
    if s["activity"]:
        st.code("\n".join(reversed(s["activity"])), language="text")
    else:
        st.caption("No activity yet.")
    with st.expander("Preview dossier JSON"):
        st.code(payload, language="json")
