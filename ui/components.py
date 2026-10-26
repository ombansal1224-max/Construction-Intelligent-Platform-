"""Reusable HTML building blocks for the Streamlit UI."""
from __future__ import annotations

from html import escape

import streamlit as st

SEVERITY_PILL = {"Low": "info", "Medium": "warn", "High": "bad", "Critical": "crit"}
STATUS_PILL = {"Compliant": "ok", "Needs Attention": "warn", "High Risk": "bad", "Critical": "crit",
               "Violation": "crit", "Not Visible": "muted", "Go": "ok", "Restrict": "warn", "Suspend": "crit",
               "Completed": "ok", "In Progress": "warn", "Pending": "muted", "Primary": "bad", "Secondary": "warn",
               "Preventive": "info"}
PPE_ICONS = {"helmet": "⛑️", "hi_vis_vest": "🦺", "safety_boots": "🥾", "safety_harness": "🪢"}


def compact(markup: str) -> str:
    """Strip indentation/newlines so Markdown never treats indented HTML as a code block."""
    return " ".join(line.strip() for line in markup.splitlines() if line.strip())


def html(markup: str) -> None:
    st.markdown(compact(markup), unsafe_allow_html=True)


def e(value) -> str:
    return escape(str(value))


def pill(text: str, kind: str = "muted", extra: str = "") -> str:
    return f'<span class="pill pill-{kind} {extra}">{e(text)}</span>'


def metric_card(label: str, value: str, sub: str = "", accent: str = "amber") -> str:
    return (f'<div class="card accent-{accent}"><div class="metric-label">{e(label)}</div>'
            f'<div class="metric-value">{e(value)}</div><div class="metric-sub">{e(sub)}</div></div>')


def metric_row(cards: list[str]) -> None:
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            html(card)


def section_header(icon: str, title: str, subtitle: str) -> None:
    html(f'<div class="section-title">{icon} {e(title)}</div><div class="section-sub">{e(subtitle)}</div>')


def subhead(text: str) -> None:
    html(f'<div class="subhead">{e(text)}</div>')


def callout(text: str, kind: str = "info") -> None:
    html(f'<div class="callout callout-{kind}">{text}</div>')


def score_ring(score: int, label: str, higher_is_better: bool = True) -> str:
    good = score if higher_is_better else 100 - score
    color = "#34d399" if good >= 75 else "#ffb020" if good >= 50 else "#ff7a1a" if good >= 30 else "#fb5470"
    return (f'<div class="ring-wrap"><div class="ring" style="--p:{int(score)};--c:{color}">'
            f'<div class="ring-num">{int(score)}<small>{e(label)}</small></div></div></div>')


def mode_badge(mode: str) -> str:
    return pill("LIVE · GEMINI", "ok", "pill-live") if mode == "gemini" else pill("DEMO MODE", "warn")


def progress_bar(pct: float) -> str:
    return f'<div class="bar"><span style="width:{max(0, min(100, pct)):.1f}%"></span></div>'


def ppe_card(item) -> str:
    kind = STATUS_PILL[item.status]
    return (f'<div class="card"><div class="ppe-icon">{PPE_ICONS.get(item.item, "🛡️")}</div>'
            f'<div class="ppe-label">{e(item.label)}</div>{pill(item.status, kind)}'
            f'{progress_bar(item.confidence * 100)}'
            f'<div class="ppe-note">Confidence {item.confidence:.0%}. {e(item.note)}</div></div>')


def hazard_card(h) -> str:
    meta = " · ".join(x for x in (h.location, h.standard_reference) if x)
    return (f'<div class="card hazard sev-{h.severity}"><div style="display:flex;justify-content:space-between;gap:.6rem;">'
            f'<div class="hazard-title">{e(h.hazard)}</div>{pill(h.severity, SEVERITY_PILL[h.severity])}</div>'
            f'<div class="hazard-meta">{e(meta)}</div><div class="remedy"><b>Remedy:</b> {e(h.remedy)}</div></div>')


def numbered_steps(items: list[tuple[str, str, str | None]]) -> None:
    """items: (title, body, optional pill text)"""
    for i, (title, body, tag) in enumerate(items, 1):
        tag_html = pill(tag, STATUS_PILL.get(tag, "muted")) if tag else ""
        html(f'<div class="card step" style="margin-bottom:.55rem"><div class="step-num">{i}</div><div>'
             f'<div class="hazard-title">{e(title)} {tag_html}</div><div class="remedy">{e(body)}</div></div></div>')
