"""Sidebar: secure API-key input, mode indicator, architecture overview and feature navigation."""
from __future__ import annotations

import streamlit as st

from core.config import APP_NAME, APP_VERSION, GEMINI_MODELS, resolve_api_key
from core.llm import GeminiClient
from ui.components import html, mode_badge, pill

ARCHITECTURE_DOT = """
digraph G {
  rankdir=LR; bgcolor="transparent"; nodesep=0.28; ranksep=0.35;
  node [shape=box, style="rounded,filled", fillcolor="#1b2742", color="#ffb020", fontcolor="white", fontname="Helvetica", fontsize=10, margin="0.12,0.06"];
  edge [color="#7f8aa6", fontcolor="#94a0b8", fontname="Helvetica", fontsize=8, arrowsize=0.6];
  UI   [label="Streamlit / React\\nFrontend"];
  IN   [label="User Input\\nText · Images · Project Data"];
  API  [label="FastAPI Backend\\n+ Core Engine"];
  DB   [label="Data Storage\\n(JSON files)", fillcolor="#142238", color="#22d3ee"];
  AI   [label="Multimodal AI\\nGemini LLM + Vision", fillcolor="#3a2a10"];
  S [label="Site Safety\\nMonitoring"]; C [label="Crack\\nAnalysis"]; V [label="Real Estate\\nValuation"];
  P [label="Project\\nPlanning"]; W [label="Site Assistant\\n& Weather"];
  UI -> IN; IN -> API [dir=both]; API -> DB [dir=both]; IN -> AI [label="process"];
  AI -> S; AI -> C; AI -> V; AI -> P; AI -> W;
}
"""


def _secret_key() -> str:
    try:
        return str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:  # no secrets file configured
        return ""


def render_sidebar() -> GeminiClient:
    with st.sidebar:
        html(f'<div class="brand"><div class="brand-logo">🏗️</div><div><div class="brand-name">{APP_NAME}</div>'
             f'<div class="brand-sub">Skill Wallet Capstone · v{APP_VERSION}</div></div></div>')

        st.markdown("##### 🔐 Gemini API Access")
        entered = st.text_input("Google Gemini API key", type="password", key="api_key_input",
                                placeholder="Paste key for live multimodal AI",
                                help="Stored only in this browser session memory. Leave empty to run in demonstration mode.")
        key = resolve_api_key(entered) or _secret_key()
        temp_client = GeminiClient(key)
        available_models = tuple(temp_client.get_available_models()) if key else GEMINI_MODELS
        model = st.selectbox("Preferred model", available_models, index=0, help="Others are used as automatic fallbacks.")
        ordered = (model, *[m for m in available_models if m != model])
        client = GeminiClient(key, models=ordered)

        mode = "gemini" if client.enabled else "demo"
        html(f'<div style="margin:.4rem 0 .2rem">{mode_badge(mode)}</div>')
        if not client.enabled:
            st.caption("No key detected - the platform runs a deterministic offline engine so every feature stays usable.")
        elif st.button("Validate key", width="stretch"):
            with st.spinner("Contacting Gemini..."):
                ok, msg = client.validate_key()
            (st.success if ok else st.error)(msg)
        st.caption("Get a free key at aistudio.google.com/apikey")

        st.divider()
        st.markdown("##### 🧭 Feature Navigation")
        nav = [
            ("🦺", "Site Safety & PPE Audit", "Upload a site photo → PPE checklist, hazards, score (0-100)."),
            ("🧱", "Crack Diagnostics", "Classify defects, width (mm), severity score, repair plan."),
            ("📐", "Planning & Valuation", "Budget, capex, market value in ₹ Lakhs/Crores, steel & cement, 3D concept."),
            ("🌦️", "Site Assistant & Weather", "Weather protocols, live conditions and multi-turn engineering chat."),
            ("📁", "Project Dossier", "Consolidated JSON export of every analysis."),
        ]
        for icon, title, desc in nav:
            with st.expander(f"{icon} {title}"):
                st.caption(desc + " Open it from the tab bar above.")

        st.divider()
        st.markdown("##### 🧩 Architecture")
        try:
            st.graphviz_chart(ARCHITECTURE_DOT, width="stretch")
        except Exception:
            st.caption("Frontend → Input → FastAPI + Core Engine ⇄ Storage → Multimodal AI → 5 intelligence modules.")

        st.divider()
        s = st.session_state
        done = [("Safety audit", s["safety_report"]), ("Crack diagnosis", s["crack_report"]),
                ("Valuation", s["valuation"]), ("Chat", s["chat_history"])]
        html("<div style='display:flex;flex-wrap:wrap;gap:.35rem'>" +
             "".join(pill(name, "ok" if val else "muted") for name, val in done) + "</div>")
        st.caption("⚠️ Decision-support only. Verify all findings with a licensed engineer / safety officer.")
    return client
