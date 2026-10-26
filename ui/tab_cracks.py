"""Tab 2 - Crack Diagnostics & Structural Integrity (Epic 2)."""
from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from core.cracks import analyze_crack
from core.imaging import ImageError, prepare_image
from core.llm import GeminiClient
from ui.components import (SEVERITY_PILL, callout, e, html, metric_card, metric_row, mode_badge, numbered_steps,
                           pill, progress_bar, score_ring, section_header, subhead)
from ui.inputs import image_input
from ui.state import log_activity

IS_LIMIT_MM = 0.3


def render(client: GeminiClient) -> None:
    section_header("🧱", "Crack Diagnostics & Structural Integrity",
                   "Classify defects, estimate crack width, score severity and get an engineering repair plan.")

    left, right = st.columns([1, 1], gap="large")
    with left:
        data, source = image_input("Upload a concrete / wall surface photo (JPG / PNG)", "crack", "sample_crack.jpg")
        run = st.button("🔬 Diagnose Defect", type="primary", width="stretch", disabled=data is None,
                        key="run_crack")
    with right:
        if data:
            try:
                prepared = prepare_image(data)
                st.image(prepared.image, caption=f"{source} · {prepared.width}×{prepared.height}px", width="stretch")
            except ImageError as exc:
                st.error(str(exc))
                return
        else:
            callout("Upload a close-up of the surface. Tip: include a coin or scale reference so the model can "
                    "estimate crack width more accurately.")

    if run and data:
        try:
            with st.spinner("Running multimodal structural diagnosis..."):
                report, overlay = analyze_crack(prepare_image(data), client)
            st.session_state["crack_report"] = report
            st.session_state["crack_overlay"] = overlay
            log_activity(f"Crack diagnosis: {report.defect_type} ({report.severity_level})")
        except ImageError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unexpected error during analysis: {exc}")

    report = st.session_state["crack_report"]
    if report:
        _render_report(report, st.session_state["crack_overlay"])


def _render_report(report, overlay) -> None:
    st.divider()
    for note in report.notes:
        callout(e(note), "warn")

    sev_kind = SEVERITY_PILL[report.severity_level]
    c_ring, c_main = st.columns([1, 3], gap="large")
    with c_ring:
        html(score_ring(report.severity_score, "SEVERITY", higher_is_better=False))
    with c_main:
        html(f'<div style="margin-bottom:.5rem">{pill(report.severity_level.upper() + " SEVERITY", sev_kind)} &nbsp; '
             f'{pill("URGENCY: " + report.urgency.upper(), sev_kind)} &nbsp; {mode_badge(report.analysis_mode)}</div>')
        metric_row([
            metric_card("Defect type", report.defect_type, report.orientation, "amber"),
            metric_card("Est. crack width", f"{report.estimated_width_mm:g} mm",
                        f"IS 456 limit {IS_LIMIT_MM} mm", "red" if report.estimated_width_mm > IS_LIMIT_MM else "green"),
            metric_card("Confidence", f"{report.confidence:.0%}", "model self-assessment", "cyan"),
        ])
        ratio = min(report.estimated_width_mm / (IS_LIMIT_MM * 10) * 100, 100)
        html(f'<div class="callout"><b>Structural risk:</b> {e(report.structural_risk)}'
             f'<div class="metric-sub" style="margin-top:.5rem">Width vs. 3 mm critical reference</div>{progress_bar(ratio)}</div>')

    if overlay is not None:
        subhead("Visual Evidence")
        col_a, col_b = st.columns(2)
        col_a.image(overlay, caption="Edge-detection overlay (assistive local analysis - red = linear dark features)",
                    width="stretch")
        with col_b:
            html(f'<div class="card"><div class="hazard-title">Engineering summary</div><div class="remedy">{e(report.summary)}</div>'
                 f'<div class="hazard-meta" style="margin-top:.7rem">Monitoring plan</div>'
                 f'<div class="remedy">{e(report.monitoring_plan)}</div></div>')

    cause_col, repair_col = st.columns([1, 1.4], gap="large")
    with cause_col:
        subhead("Probable Root Causes")
        for cause in report.root_causes:
            html(f'<div class="card" style="margin-bottom:.5rem">• {e(cause)}</div>')
    with repair_col:
        subhead("Recommended Engineering Repairs")
        numbered_steps([(r.method, r.description, r.priority) for r in report.recommended_repairs])
    st.caption("Standards referenced: " + " · ".join(report.standards_referenced))

    payload = json.dumps(report.model_dump(), indent=2)
    st.download_button("⬇️ Download JSON report", payload, f"crack_diagnostic_{datetime.now():%Y%m%d_%H%M%S}.json",
                       "application/json", key="dl_crack")
    with st.expander("View structured JSON contract"):
        st.code(payload, language="json")
