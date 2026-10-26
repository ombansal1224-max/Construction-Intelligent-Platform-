"""Epic 2a - Site Safety & PPE audit: prompt, hazard library, demo fallback and orchestration."""
from __future__ import annotations

import json
import random

from .config import PPE_ITEMS
from .imaging import PreparedImage, visual_features
from .llm import GeminiClient, LLMError
from .schemas import SafetyReport, coerce_safety

SAFETY_PROMPT = """You are a certified construction safety officer (OSHA 30-hour, NEBOSH IGC, Indian BOCW Rules).
Audit the attached construction-site photograph for PPE compliance and site hazards under
OSHA 29 CFR 1926, IS 456:2000 (structural concrete practice), IS 3696 (scaffolds), IS 2925 (helmets),
IS 15298 (PPE) and the BOCW Central Rules 1998.

PPE to check for every visible worker: helmet, high-visibility vest, steel-toe safety boots, full-body safety harness
(harness is only required when working at height / near unprotected edges - otherwise report "Not Visible").

Return ONLY one JSON object, no prose, with exactly this schema:
{
  "safety_score": <integer 0-100, 100 = fully compliant>,
  "overall_status": "Compliant" | "Needs Attention" | "High Risk" | "Critical",
  "workers_detected": <integer>,
  "ppe_detection": [
    {"item": "helmet",         "status": "Compliant" | "Violation" | "Not Visible", "confidence": <0-1>, "note": "<short evidence>"},
    {"item": "hi_vis_vest",    "status": "...", "confidence": <0-1>, "note": "..."},
    {"item": "safety_boots",   "status": "...", "confidence": <0-1>, "note": "..."},
    {"item": "safety_harness", "status": "...", "confidence": <0-1>, "note": "..."}
  ],
  "hazards": [
    {"hazard": "<specific hazard>", "severity": "Low" | "Medium" | "High" | "Critical",
     "location": "<where in the image>", "standard_reference": "<e.g. OSHA 1926.502>", "remedy": "<concrete corrective action>"}
  ],
  "summary": "<2-3 sentence executive summary>",
  "recommendations": ["<prioritised action>", "..."],
  "standards_referenced": ["OSHA 1926.xxx", "IS xxx", "..."]
}
Scoring rubric: start at 100; deduct 12 per PPE violation and 3/7/14/25 for Low/Medium/High/Critical hazards.
Only report what is visible. If the image is not a construction site, return safety_score 0, empty hazards and
explain in "summary". Be specific and actionable."""

# severity-tagged hazard library used by the offline demo engine
HAZARD_LIBRARY = [
    {"hazard": "Unprotected floor edge / open slab perimeter", "severity": "High", "location": "Upper slab edge",
     "standard_reference": "OSHA 1926.502; IS 7969",
     "remedy": "Install 1.0 m guardrails with mid-rail and 150 mm toe-board; use perimeter safety nets and anchor points."},
    {"hazard": "Exposed reinforcement bars without protective caps", "severity": "High", "location": "Column starter bars",
     "standard_reference": "OSHA 1926.701(b)",
     "remedy": "Fit mushroom caps or bend over rebar ends; barricade impalement zones."},
    {"hazard": "Scaffolding with missing bracing / incomplete decking", "severity": "High", "location": "Façade scaffold",
     "standard_reference": "IS 3696 (Pt 1); OSHA 1926.451",
     "remedy": "Tag out scaffold until inspected by a competent person; complete planking, bracing and ties."},
    {"hazard": "Poor housekeeping - debris and trip hazards on working deck", "severity": "Medium", "location": "Working platform",
     "standard_reference": "OSHA 1926.25",
     "remedy": "Assign housekeeping crew each shift; designate material stacking and waste zones."},
    {"hazard": "Temporary electrical cables on wet ground / damaged insulation", "severity": "Critical", "location": "Ground level",
     "standard_reference": "OSHA 1926.404; IS 732",
     "remedy": "De-energise, replace damaged cable, raise runs off the floor and protect circuits with 30 mA ELCB/RCCB."},
    {"hazard": "Unshored excavation / no edge barricade", "severity": "Critical", "location": "Foundation pit",
     "standard_reference": "OSHA 1926.652; IS 3764",
     "remedy": "Stop entry; install shoring or slope the walls, barricade the perimeter, and provide ladder access."},
    {"hazard": "Materials stacked unstably near edge", "severity": "Medium", "location": "Material yard",
     "standard_reference": "OSHA 1926.250",
     "remedy": "Restack on level dunnage, limit stack height, keep a 1.5 m setback from edges."},
    {"hazard": "Personnel working beneath suspended load / lifting zone", "severity": "Critical", "location": "Crane radius",
     "standard_reference": "OSHA 1926.1425; IS 3177",
     "remedy": "Establish an exclusion zone, use a signalman and tag lines, and enforce a lift plan."},
    {"hazard": "Inadequate barricading, signage and access control", "severity": "Low", "location": "Site perimeter",
     "standard_reference": "OSHA 1926.200",
     "remedy": "Post mandatory-PPE and danger signage, control entry with a visitor induction."},
    {"hazard": "Fire extinguisher / first-aid station not visible", "severity": "Low", "location": "Work zone",
     "standard_reference": "NBC 2016 Part 4; OSHA 1926.150",
     "remedy": "Place rated extinguishers and a stocked first-aid box within 25 m of each work front."},
]

NOTE_DEMO = "Demo heuristic - colour-based estimate, not a real vision model."


def demo_safety(prepared: PreparedImage) -> dict:
    """Deterministic, image-seeded offline analysis (same image -> same result)."""
    rng = random.Random(int(prepared.signature[:12], 16))
    feat = visual_features(prepared.image)
    vest_seen = feat["hivis_ratio"] > 0.001

    def pick(p_ok: float, p_hidden: float) -> str:
        r = rng.random()
        return "Not Visible" if r < p_hidden else ("Compliant" if r < p_hidden + p_ok else "Violation")

    status = {
        "helmet": pick(0.6, 0.05),
        "hi_vis_vest": "Compliant" if vest_seen else ("Violation" if rng.random() < 0.75 else "Not Visible"),
        "safety_boots": pick(0.55, 0.25),
        "safety_harness": pick(0.4, 0.45),
    }
    notes = {
        "hi_vis_vest": "High-visibility orange/yellow pixels detected." if vest_seen
        else "No high-visibility colour regions found.",
    }
    ppe = [{"item": k, "status": status[k], "confidence": round(rng.uniform(0.55, 0.82), 2),
            "note": notes.get(k, NOTE_DEMO)} for k, _, _ in PPE_ITEMS]
    hazards = rng.sample(HAZARD_LIBRARY, k=rng.randint(2, 4))
    violations = [k for k, v in status.items() if v == "Violation"]
    summary = (
        f"Offline demo audit: {len(violations)} PPE violation(s) flagged"
        + (f" ({', '.join(v.replace('_', ' ') for v in violations)})" if violations else "")
        + f" and {len(hazards)} site hazard(s) identified. Provide a Gemini API key for true multimodal analysis."
    )
    return {
        "workers_detected": rng.randint(1, 5),
        "ppe_detection": ppe,
        "hazards": hazards,
        "summary": summary,
        "recommendations": [
            "Hold a toolbox talk on mandatory PPE before the next shift.",
            "Rectify Critical/High hazards first and re-inspect within 24 hours.",
            "Enforce a no-PPE-no-entry rule at the site gate with a supervisor sign-off.",
        ],
        "standards_referenced": ["OSHA 29 CFR 1926", "IS 456:2000", "IS 3696", "BOCW Central Rules 1998"],
    }


def analyze_safety(prepared: PreparedImage, client: GeminiClient) -> SafetyReport:
    """Run a Gemini audit when a key is configured; otherwise (or on failure) use the demo engine."""
    notes: list[str] = []
    if client.enabled:
        try:
            raw = client.generate_json(SAFETY_PROMPT, prepared.jpeg_bytes, prepared.mime_type)
            report = coerce_safety(raw, "gemini", client.last_model)
            return report
        except LLMError as exc:
            notes.append(f"Live analysis failed ({exc}). Showing demo-mode results instead.")
    report = coerce_safety(demo_safety(prepared), "demo", "offline-heuristic")
    report.notes = notes or ["Demo mode: add a Gemini API key in the sidebar for live multimodal analysis."]
    return report


def report_json(report: SafetyReport) -> str:
    return json.dumps(report.model_dump(), indent=2)
