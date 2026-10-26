"""Tab 4 - Daily Site Assistant & Weather-Aware Advisory (Epic 5)."""
from __future__ import annotations

import streamlit as st

from core.assistant import ConstructionAssistant
from core.config import WEATHER_CONDITIONS
from core.knowledge_base import DEFAULT_SUGGESTIONS
from core.llm import GeminiClient
from core.weather import ADVISORIES, fetch_live_weather, get_advisory
from ui.components import SEVERITY_PILL, STATUS_PILL, callout, e, html, metric_card, metric_row, pill, section_header, subhead
from ui.state import assistant_context, log_activity

RISK_ACCENT = {"Low": "green", "High": "red"}


def render(client: GeminiClient) -> None:
    section_header("🌦️", "Daily Site Assistant & Weather-Aware Advisory",
                   "Weather-driven operating protocols plus an interactive construction engineering assistant.")
    _render_weather()
    st.divider()
    _render_chat(client)


# ------------------------------------------------------------------ weather
def _render_weather() -> None:
    options = list(WEATHER_CONDITIONS)
    chosen = st.radio("Today's site weather condition", options, horizontal=True, key="weather_radio",
                      index=options.index(st.session_state["weather_condition"]),
                      format_func=lambda c: f"{ADVISORIES[c]['icon']}  {c}")
    st.session_state["weather_condition"] = chosen

    with st.expander("📡 Auto-detect from live weather (Open-Meteo, no key needed)"):
        c1, c2 = st.columns([3, 1])
        city = c1.text_input("City", placeholder="e.g. Mumbai", key="wx_city", label_visibility="collapsed")
        if c2.button("Fetch live weather", width="stretch", key="wx_fetch"):
            try:
                with st.spinner("Fetching conditions..."):
                    st.session_state["live_weather"] = fetch_live_weather(city)
                log_activity(f"Live weather for {city}")
            except RuntimeError as exc:
                st.session_state["live_weather"] = None
                st.warning(str(exc))
        lw = st.session_state.get("live_weather")
        if lw:
            metric_row([
                metric_card("Location", lw["location"].split(",")[0], lw["location"], "cyan"),
                metric_card("Feels like", f"{lw['apparent_temperature_c']:.0f} °C", f"air {lw['temperature_c']:.0f} °C", "amber"),
                metric_card("Wind / gusts", f"{lw['wind_kmh']:.0f} km/h", f"gusts {lw['gusts_kmh']:.0f} km/h", "violet"),
                metric_card("Rain now", f"{lw['precipitation_mm']:.1f} mm", "current hour", "cyan"),
            ])
            st.info(f"Suggested advisory: **{lw['suggested_condition']}**. Select it above to apply the protocols.")

    adv = get_advisory(chosen)
    risk_kind = "ok" if adv["risk"] == "Low" else "crit"
    html(f'<div class="card" style="margin:.6rem 0 1rem"><div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap">'
         f'<div><div class="section-title" style="margin:0">{adv["icon"]} {e(adv["headline"])}</div>'
         f'<div class="metric-sub">Trigger: {e(adv["trigger"])}</div></div>{pill(adv["risk"].upper() + " RISK", risk_kind)}</div></div>')

    subhead("Dynamic Safety Alerts")
    cols = st.columns(2)
    for i, a in enumerate(adv["alerts"]):
        with cols[i % 2]:
            html(f'<div class="card hazard sev-{a["severity"]}" style="margin-bottom:.6rem"><div style="display:flex;justify-content:space-between;gap:.5rem">'
                 f'<div class="hazard-title">{e(a["title"])}</div>{pill(a["severity"], SEVERITY_PILL[a["severity"]])}</div>'
                 f'<div class="remedy">{e(a["detail"])}</div></div>')

    subhead("Operations Status Board")
    cols = st.columns(3)
    for i, (op, (status, note)) in enumerate(adv["operations"].items()):
        with cols[i % 3]:
            html(f'<div class="card" style="margin-bottom:.6rem"><div class="op"><div class="op-name">{e(op)}</div>'
                 f'{pill(status.upper(), STATUS_PILL[status])}</div><div class="op-note">{e(note)}</div></div>')

    left, right = st.columns([1.3, 1], gap="large")
    with left:
        subhead("Concrete Curing Protocol")
        for step in adv["curing"]:
            html(f'<div class="card" style="margin-bottom:.5rem">💧 {e(step)}</div>')
    with right:
        subhead("Required PPE Today")
        html("<div style='display:flex;flex-wrap:wrap;gap:.4rem'>" + "".join(pill(p, "info") for p in adv["ppe"]) + "</div>")
        subhead("Pre-shift Checklist")
        for i, item in enumerate(adv["checklist"]):
            st.checkbox(item, key=f"chk_{chosen}_{i}")
        st.caption("Standards: " + " · ".join(adv["standards"]))


# ------------------------------------------------------------------ chatbot
def _render_chat(client: GeminiClient) -> None:
    subhead("💬 Construction Engineering Assistant")
    mode_text = "Live Gemini" if client.enabled else "Offline knowledge base (add an API key for open-ended answers)"
    st.caption(f"Mode: **{mode_text}** · Context-aware: uses your latest audit, crack report, valuation and weather.")

    history: list[dict] = st.session_state["chat_history"]
    pending = None

    if not history:
        st.caption("Quick questions:")
        cols = st.columns(3)
        for i, q in enumerate(DEFAULT_SUGGESTIONS):
            if cols[i % 3].button(q, key=f"sugg_{i}", width="stretch"):
                pending = q

    for msg in history:
        with st.chat_message(msg["role"], avatar="🧑‍🔧" if msg["role"] == "user" else "🏗️"):
            st.markdown(msg["content"])

    typed = st.chat_input("Ask about concrete, safety, costs, codes, scheduling...", key="chat_box")
    question = typed or pending
    if question:
        history.append({"role": "user", "content": question})
        with st.chat_message("user", avatar="🧑‍🔧"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="🏗️"):
            with st.spinner("Thinking..."):
                try:
                    answer, _mode = ConstructionAssistant(client).reply(history, assistant_context())
                except Exception as exc:  # noqa: BLE001
                    answer = f"Sorry, something went wrong: {exc}"
            st.markdown(answer)
        history.append({"role": "assistant", "content": answer})
        log_activity("Assistant answered a question")
        st.rerun()

    if history and st.button("🗑️ Clear conversation", key="chat_clear"):
        st.session_state["chat_history"] = []
        st.rerun()
