"""Tab 1 - Site Safety & PPE Audit (Epic 2)."""
from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from core.imaging import ImageError, prepare_image
from core.llm import GeminiClient
from core.safety import analyze_safety
from ui.components import (callout, e, hazard_card, html, metric_card, metric_row, mode_badge, pill,
                           ppe_card, score_ring, section_header, subhead, STATUS_PILL)
from ui.inputs import image_input
from ui.state import log_activity


def render(client: GeminiClient) -> None:
    section_header("🦺", "Site Safety & PPE Audit",
                   "Multimodal audit of worker PPE compliance and site hazards under OSHA 1926 and Indian IS standards.")

    left, right = st.columns([1, 1], gap="large")
    with left:
        data, source = image_input("Upload a construction-site photo (JPG / PNG)", "safety", "sample_site.jpg")
        run = st.button("🔍 Run Safety Audit", type="primary", width="stretch", disabled=data is None,
                        key="run_safety")
    with right:
        if data:
            try:
                prepared = prepare_image(data)
                st.image(prepared.image, caption=f"{source} · {prepared.width}×{prepared.height}px", width="stretch")
            except ImageError as exc:
                st.error(str(exc))
                return
        else:
            callout("Upload a photo (or tick the sample) to begin. The model checks <b>helmets, hi-vis vests, "
                    "steel-toe boots and safety harnesses</b>, then lists site hazards with remedies.")

    if run and data:
        try:
            with st.spinner("Analysing site photograph with the multimodal engine..."):
                report = analyze_safety(prepare_image(data), client)
            st.session_state["safety_report"] = report
            log_activity(f"Safety audit: score {report.safety_score}")
        except ImageError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 - never crash the UI
            st.error(f"Unexpected error during analysis: {exc}")

    report = st.session_state["safety_report"]
    if report:
        _render_report(report)


def _render_report(report) -> None:
    st.divider()
    for note in report.notes:
        callout(e(note), "warn")

    top_l, top_r = st.columns([1, 3], gap="large")
    with top_l:
        html(score_ring(report.safety_score, "SAFETY SCORE"))
    with top_r:
        status_kind = STATUS_PILL[report.overall_status]
        html(f'<div style="margin-bottom:.5rem">{pill(report.overall_status.upper(), status_kind)} &nbsp; '
             f'{mode_badge(report.analysis_mode)}</div>')
        violations = sum(p.status == "Violation" for p in report.ppe_detection)
        crit = sum(h.severity in ("Critical", "High") for h in report.hazards)
        metric_row([
            metric_card("Workers detected", str(report.workers_detected), "in frame", "cyan"),
            metric_card("PPE violations", str(violations), f"of {len(report.ppe_detection)} categories",
                        "red" if violations else "green"),
            metric_card("Hazards", str(len(report.hazards)), f"{crit} high / critical", "red" if crit else "amber"),
        ])
        html(f'<div class="callout" style="margin-top:.8rem">{e(report.summary)}</div>')

    subhead("PPE Compliance Checklist")
    for col, item in zip(st.columns(len(report.ppe_detection)), report.ppe_detection):
        with col:
            html(ppe_card(item))

    subhead("Identified Site Hazards")
    if not report.hazards:
        callout("No hazards were identified in this image.", "info")
    for h in report.hazards:
        html(hazard_card(h))
        st.write("")

    if report.recommendations:
        subhead("Prioritised Recommendations")
        for rec in report.recommendations:
            st.markdown(f"- {rec}")
    st.caption("Standards referenced: " + " · ".join(report.standards_referenced))

    payload = json.dumps(report.model_dump(), indent=2)
    c1, c2 = st.columns([1, 3])
    with c1:
        st.download_button("⬇️ Download JSON report", payload, f"safety_audit_{datetime.now():%Y%m%d_%H%M%S}.json",
                           "application/json", width="stretch", key="dl_safety")
    with st.expander("View structured JSON contract"):
        st.code(payload, language="json")
