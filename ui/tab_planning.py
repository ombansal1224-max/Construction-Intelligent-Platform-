"""Tab 3 - Project Planning & Real Estate Valuation (Epic 3)."""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from core.formatting import format_inr, indian_grouping
from core.valuation import (ARCH_STYLES, GRADES, STRUCTURES, TIERS, TIMES_OF_DAY, build_pollinations_url,
                            build_render_prompt, compute_valuation, human_months)
from ui.components import (STATUS_PILL, callout, e, html, metric_card, metric_row, pill, progress_bar,
                           section_header, subhead)
from ui.state import log_activity


def render() -> None:
    section_header("📐", "Planning & Real Estate Valuation",
                   "Interactive cost model for Indian construction: budget, capex, market valuation, materials and schedule.")

    with st.container(border=True):
        c1, c2, c3 = st.columns([1.4, 1, 1])
        structure = c1.selectbox("Structure type", list(STRUCTURES), key="pl_structure")
        sqft = c2.number_input("Built-up area (sq ft)", min_value=100, max_value=5_000_000, value=2400, step=100, key="pl_sqft")
        tier = c3.selectbox("Location tier", list(TIERS), index=1, key="pl_tier",
                            help="Tier 1: metros · Tier 2: large cities · Tier 3: smaller towns")
        c4, c5 = st.columns([2.2, 1])
        completion = c4.slider("Completion percentage (earned value)", 0, 100, 45, key="pl_completion",
                               help="Physical progress weighted by phase cost.")
        grade = c5.selectbox("Finish grade", list(GRADES), key="pl_grade")
        st.caption(f"📍 {tier} examples: {TIERS[tier].examples}")

    try:
        result = compute_valuation(structure, float(sqft), tier, float(completion), grade)
    except ValueError as exc:
        st.error(str(exc))
        return
    st.session_state["valuation"] = result
    b, v, m, sch = result["budget"], result["valuation"], result["materials"], result["schedule"]

    subhead("Financial Overview")
    metric_row([
        metric_card("Total project budget", format_inr(b["total"]), f"₹{indian_grouping(b['per_sqft'])}/sq ft · incl. {b['contingency_pct']:.0f}% contingency", "amber"),
        metric_card("Capital expenditure incurred", format_inr(b["capex_incurred"]), f"{completion}% of budget · {format_inr(b['remaining'])} remaining", "cyan"),
        metric_card("Current market valuation", format_inr(v["current_value"]), f"land {format_inr(v['land_value'])} + built value", "green"),
        metric_card("Value on completion", format_inr(v["value_on_completion"]),
                    f"ROI {v['roi_pct']:.0f}% · ₹{indian_grouping(v['market_rate_per_sqft'])}/sq ft", "violet"),
    ])

    subhead("Material Requirements")
    metric_row([
        metric_card("Steel required", f"{m['steel_total_tonnes']:,.1f} t", f"{m['steel_consumed_kg'] / 1000:,.1f} t used · {m['steel_remaining_kg'] / 1000:,.1f} t to procure", "amber"),
        metric_card("Cement required", f"{indian_grouping(m['cement_total_bags'])} bags", f"{indian_grouping(m['cement_consumed_bags'])} used · {indian_grouping(m['cement_remaining_bags'])} to procure", "cyan"),
        metric_card("Steel procurement", format_inr(m["steel_cost"]), "at ₹65 / kg (indicative)", "green"),
        metric_card("Cement procurement", format_inr(m["cement_cost"]), "at ₹390 / 50 kg bag (indicative)", "violet"),
    ])

    subhead("Milestone Progress")
    html(f'<div class="card"><div class="ms-head"><b>Overall completion · {result["current_phase"]}</b>'
         f'<span>{completion}% · {human_months(sch["elapsed_months"])} of {human_months(sch["total_months"])} elapsed '
         f'({human_months(sch["remaining_months"])} remaining)</span></div>{progress_bar(completion)}</div>')
    st.write("")
    cols = st.columns(2)
    for i, ms in enumerate(result["milestones"]):
        with cols[i % 2]:
            html(f'<div class="card ms-row"><div class="ms-head"><span>{e(ms["name"])}</span>'
                 f'{pill(ms["status"], STATUS_PILL[ms["status"]])}</div>{progress_bar(ms["progress_pct"])}'
                 f'<div class="metric-sub" style="margin-top:.4rem">Budget {format_inr(ms["budget"])} · '
                 f'Month {ms["start_month"]:g} → {ms["start_month"] + ms["duration_months"]:g}</div></div>')
            st.write("")

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        subhead("Budget Allocation vs. Spend")
        df = pd.DataFrame(b["breakdown"])
        chart = pd.DataFrame({"Planned (₹ Lakhs)": df["amount"] / 1e5, "Spent (₹ Lakhs)": df["spent"] / 1e5},
                             index=df["category"])
        st.bar_chart(chart, color=["#ffb020", "#22d3ee"], height=320)
    with right:
        subhead("Phase-wise Schedule")
        sched = pd.DataFrame([{"Phase": x["name"], "Start (mo)": x["start_month"], "Duration (mo)": x["duration_months"],
                               "Status": x["status"], "Budget": format_inr(x["budget"])} for x in result["milestones"]])
        st.dataframe(sched, hide_index=True, width="stretch", height=290)

    _render_concept(structure, tier, completion)

    with st.expander("Download valuation model (JSON)"):
        payload = json.dumps(result, indent=2, default=str)
        st.download_button("⬇️ Download JSON", payload, f"valuation_{datetime.now():%Y%m%d_%H%M%S}.json",
                           "application/json", key="dl_valuation")
        st.code(payload, language="json")
    callout("Estimates are indicative planning figures from tier-adjusted benchmarks (Tier-2 standard grade baseline) - "
            "not a certified valuation. Obtain a registered valuer's report for lending or sale.", "warn")


def _render_concept(structure: str, tier: str, completion: int) -> None:
    subhead("Conceptual 3D Architectural Rendering (Pollinations AI · Flux)")
    c1, c2, c3 = st.columns([1, 1, 1])
    style = c1.selectbox("Architectural style", ARCH_STYLES, key="pl_style")
    tod = c2.selectbox("Lighting", TIMES_OF_DAY, key="pl_tod")
    city = c3.text_input("City (optional)", placeholder="e.g. Pune", key="pl_city")
    default_prompt = build_render_prompt(structure, tier, completion, style, city, tod)
    prompt = st.text_area("Image prompt (editable)", default_prompt, height=100,
                          key=f"pl_prompt_{abs(hash(default_prompt)) % 10**8}")
    b1, b2 = st.columns([1, 1])
    if b1.button("🎨 Generate concept render", type="primary", width="stretch", key="pl_render"):
        seed = int(datetime.now().timestamp()) % 100000
        st.session_state["render_url"] = build_pollinations_url(prompt, seed=seed)
        log_activity("Generated 3D concept prompt")
    url = st.session_state.get("render_url")
    if url:
        b2.link_button("↗ Open full-size render", url, width="stretch")
        html(f'<div class="render-frame"><img src="{e(url)}" alt="AI concept render" loading="lazy" '
             f'onerror="this.replaceWith(Object.assign(document.createElement(\'div\'),'
             f'{{style:\'padding:2rem;color:#94a0b8\',innerText:\'Render service is busy - use the Open full-size link or retry.\'}}))"/></div>')
        st.caption("Images are generated on demand by Pollinations AI; first load can take 10-30 seconds.")
