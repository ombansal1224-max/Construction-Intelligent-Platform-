"""Epic 5b - Multi-turn construction engineering assistant (Gemini, with offline knowledge-base fallback)."""
from __future__ import annotations

import json
import re

from .formatting import format_inr
from .knowledge_base import DEFAULT_SUGGESTIONS, KB
from .llm import GeminiClient, LLMError

SYSTEM_PROMPT = """You are "SiteMind", a senior construction engineering and site-safety assistant for Indian construction projects.
- Ground answers in IS codes (IS 456, IS 800, IS 1893, IS 3696 ...), NBC 2016, OSHA 1926 and BOCW rules; cite the clause when you are confident.
- Quote costs in INR (Lakhs / Crores). Be concise, practical and structured (short bullets, tables when comparing).
- Safety first: if a question implies imminent danger, say so up front and tell the user to stop work and call a licensed engineer.
- You are decision support, not a substitute for a licensed structural engineer or site inspection. Say when information is uncertain.
- Use the PROJECT CONTEXT JSON below (if present) to personalise answers; do not invent project data that is not in it."""


def build_context_text(context: dict | None) -> str:
    if not context:
        return "PROJECT CONTEXT: none provided."
    return "PROJECT CONTEXT (JSON):\n" + json.dumps(context, default=str)[:4000]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _score(question: str, entry: dict) -> float:
    q = question.lower()
    qt = _tokens(question)
    score = 0.0
    for kw in entry["keywords"]:
        if re.search(r"\b" + re.escape(kw) + r"(?:s|es|d|ed|ing)?\b", q):
            score += 2.0 + len(kw.split()) * 0.5
        else:
            kt = _tokens(kw)
            if kt and kt <= qt:
                score += 1.5
    return score


def _context_answer(question: str, context: dict | None) -> str | None:
    q = question.lower()
    if not context:
        return None
    val = context.get("valuation")
    if val and any(w in q for w in ("my project", "this project", "budget", "my cost", "capex", "valuation of my", "how much have")):
        b, v = val["budget"], val["valuation"]
        return (
            f"**Your project snapshot** ({val['inputs']['structure']}, {val['inputs']['sqft']:,.0f} sq ft, "
            f"{val['inputs']['tier']}, {val['inputs']['completion_pct']:.0f}% complete)\n"
            f"- Total budget: **{format_inr(b['total'])}** (incl. {b['contingency_pct']:.0f}% contingency)\n"
            f"- Capex incurred: **{format_inr(b['capex_incurred'])}**; remaining {format_inr(b['remaining'])}\n"
            f"- Current valuation: **{format_inr(v['current_value'])}**; on completion {format_inr(v['value_on_completion'])}\n"
            f"- Current phase: {val['current_phase']}"
        )
    saf = context.get("safety")
    if saf and any(w in q for w in ("my safety", "last audit", "safety score", "site audit", "my site")):
        return (f"**Latest safety audit**: score **{saf['safety_score']}/100** ({saf['overall_status']}). "
                f"{len(saf.get('hazards', []))} hazards recorded. {saf.get('summary', '')}")
    crack = context.get("crack")
    if crack and any(w in q for w in ("my crack", "last crack", "crack report", "defect")):
        return (f"**Latest crack diagnosis**: {crack['defect_type']}, ~{crack['estimated_width_mm']} mm, severity "
                f"{crack['severity_level']} ({crack['severity_score']}/100); urgency: **{crack['urgency']}**.")
    return None


def offline_answer(question: str, context: dict | None = None) -> str:
    ctx = _context_answer(question, context)
    if ctx:
        return ctx
    ranked = sorted(((_score(question, e), e) for e in KB), key=lambda x: -x[0])
    best = [(s, e) for s, e in ranked if s >= 2.0][:2]
    if not best:
        suggestions = "\n".join(f"- {s}" for s in DEFAULT_SUGGESTIONS[:4])
        return ("I'm running in **offline knowledge mode** and couldn't match that to my built-in topics "
                "(concrete, curing, PPE, scaffolding, cracks, valuation, RERA...). Try asking:\n" + suggestions +
                "\n\nAdd a Gemini API key in the sidebar for open-ended, multi-turn expert answers.")
    parts = [e["answer"] for _, e in best]
    return "\n\n---\n\n".join(parts)


class ConstructionAssistant:
    """Stateless chat orchestrator; the caller owns the message history."""

    def __init__(self, client: GeminiClient):
        self.client = client

    def reply(self, history: list[dict[str, str]], context: dict | None = None) -> tuple[str, str]:
        """Returns (answer, mode) where mode is 'gemini' or 'offline'. `history` ends with the user's turn."""
        if not history or history[-1]["role"] != "user":
            raise ValueError("History must end with a user message.")
        if self.client.enabled:
            try:
                system = SYSTEM_PROMPT + "\n\n" + build_context_text(context)
                return self.client.chat(history[-12:], system), "gemini"
            except LLMError as exc:
                return (offline_answer(history[-1]["content"], context) +
                        f"\n\n_(Live model unavailable: {exc} - answered from the offline knowledge base.)_"), "offline"
        return offline_answer(history[-1]["content"], context), "offline"
