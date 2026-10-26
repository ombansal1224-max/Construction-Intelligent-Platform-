"""Epic 2b - Concrete crack diagnostics: engineering playbook, prompt, demo fallback, orchestration."""
from __future__ import annotations

import json
import random

from PIL import Image

from .imaging import PreparedImage, crack_analysis
from .llm import GeminiClient, LLMError
from .schemas import CrackReport, coerce_crack
from .formatting import clamp

# Engineering knowledge per defect type: used to ground prompts and back-fill any missing model fields.
DEFECT_PLAYBOOK: dict[str, dict] = {
    "Hairline": {
        "base_score": 8,
        "risk": "Low - cosmetic/durability concern; no loss of load-carrying capacity expected below 0.3 mm.",
        "causes": [
            "Plastic shrinkage from rapid surface moisture loss in early hours",
            "Drying shrinkage and inadequate curing (IS 456 Cl. 13.5)",
            "Excessive water-cement ratio or over-trowelling of the surface",
        ],
        "repairs": [
            {"method": "Surface sealing", "priority": "Primary",
             "description": "Apply polymer-modified cementitious slurry or elastomeric coating over the cleaned crack."},
            {"method": "Low-viscosity crack filling", "priority": "Secondary",
             "description": "For cracks above 0.2 mm, gravity-fill or inject low-viscosity epoxy / acrylic sealant."},
            {"method": "Improved curing regime", "priority": "Preventive",
             "description": "Cure new pours for at least 7 days (10 days in hot weather or with blended cements)."},
        ],
        "monitoring": "Mark crack ends with dated pencil lines and re-inspect after the next monsoon; escalate if width exceeds 0.3 mm.",
        "standards": ["IS 456:2000 Cl. 35.3.2 (0.3 mm crack-width limit)", "IS 456:2000 Cl. 13.5 (curing)"],
    },
    "Settlement": {
        "base_score": 40,
        "risk": "Moderate to High - differential foundation movement can progressively distress the superstructure.",
        "causes": [
            "Differential settlement from weak, expansive or poorly compacted founding soil",
            "Leaking drains / water ingress softening the sub-grade near the foundation",
            "Nearby excavation, dewatering or tree-root moisture extraction",
            "Foundation overloading or inadequate footing size",
        ],
        "repairs": [
            {"method": "Geotechnical investigation", "priority": "Primary",
             "description": "Commission soil bearing-capacity tests and a structural audit to confirm cause and extent."},
            {"method": "Arrest the source", "priority": "Primary",
             "description": "Repair leaking services, restore drainage and control ground-water before any repair."},
            {"method": "Underpinning / sub-foundation grouting", "priority": "Secondary",
             "description": "Micro-piles, jet or cement/chemical grouting beneath footings to stabilise the foundation."},
            {"method": "Crack stitching with epoxy", "priority": "Secondary",
             "description": "After 3-6 months of stable readings, epoxy-inject and stitch the cracks with helical bars."},
        ],
        "monitoring": "Install tell-tales/crack gauges and record weekly readings for 3-6 months before cosmetic repair.",
        "standards": ["IS 1904:1986 (Foundations)", "IS 6403 (Bearing capacity)", "IS 456:2000"],
    },
    "Structural Shear": {
        "base_score": 60,
        "risk": "High / Critical - diagonal shear cracking near supports signals possible brittle failure and reduced capacity.",
        "causes": [
            "Insufficient shear reinforcement (stirrup spacing or diameter)",
            "Overloading beyond design capacity or change of use",
            "Seismic or dynamic loading, poor beam-column joint detailing",
            "Poor concrete quality / honeycombing at supports",
        ],
        "repairs": [
            {"method": "Immediate propping and load restriction", "priority": "Primary",
             "description": "Install temporary shoring, restrict occupancy and remove imposed loads until assessed."},
            {"method": "NDT and structural audit", "priority": "Primary",
             "description": "Rebound hammer / UPV (IS 13311), core tests and rebar scanning by a licensed structural engineer."},
            {"method": "Epoxy injection with strengthening", "priority": "Secondary",
             "description": "Pressure epoxy injection followed by jacketing: RC jacket, steel plates or FRP wrap with added stirrups."},
        ],
        "monitoring": "Fit crack gauges with daily readings until stabilised; evacuate the zone if width grows.",
        "standards": ["IS 456:2000 Cl. 40 (shear)", "IS 15988:2013 (retrofit of RC buildings)", "IS 13311 (NDT)"],
    },
    "Thermal Expansion": {
        "base_score": 25,
        "risk": "Low to Moderate - serviceability and water-ingress risk; seasonal width variation expected.",
        "causes": [
            "Absence or insufficient spacing of expansion / control joints",
            "Restrained thermal movement in roof slabs, parapets and long walls",
            "Large diurnal temperature swings on dark, unprotected terrace surfaces",
        ],
        "repairs": [
            {"method": "Retrofit expansion joints", "priority": "Primary",
             "description": "Saw-cut and install joints with flexible polyurethane / polysulphide sealant (IS 3414)."},
            {"method": "Rout and seal moving cracks", "priority": "Secondary",
             "description": "Use flexible sealants - avoid rigid epoxy on cracks that are still moving."},
            {"method": "Heat-reflective roof coating", "priority": "Preventive",
             "description": "Apply a high-SRI reflective coating or China-mosaic/brick-bat insulation to cut thermal range."},
        ],
        "monitoring": "Measure crack width in summer vs winter; seasonal opening/closing confirms thermal movement.",
        "standards": ["IS 456:2000 Cl. 29 (expansion joints, max 45 m spacing)", "IS 3414 (joints in buildings)"],
    },
    "Spalling": {
        "base_score": 45,
        "risk": "Moderate to High - cover loss exposes reinforcement to corrosion and reduces section capacity over time.",
        "causes": [
            "Reinforcement corrosion from carbonation or chloride ingress (expansive rust pushes cover off)",
            "Inadequate concrete cover (IS 456 Cl. 26.4 / Table 16)",
            "Poor compaction, high permeability or water-logged zones",
            "Impact damage or fire exposure",
        ],
        "repairs": [
            {"method": "Break out unsound concrete", "priority": "Primary",
             "description": "Remove delaminated concrete to sound substrate, 25 mm behind the corroded bars."},
            {"method": "Rebar treatment", "priority": "Primary",
             "description": "Wire-brush/abrasive-clean to near-white metal and coat with zinc-rich or epoxy anti-corrosive primer."},
            {"method": "Structural re-grouting / polymer-modified repair mortar", "priority": "Secondary",
             "description": "Apply bonding agent, then pack polymer-modified mortar or micro-concrete / non-shrink grout."},
            {"method": "Protective anti-carbonation coating", "priority": "Preventive",
             "description": "Finish with an elastomeric anti-carbonation coat; consider cathodic protection if chloride-contaminated."},
        ],
        "monitoring": "Half-cell potential and cover-meter survey; inspect annually, especially after monsoon.",
        "standards": ["IS 456:2000 Cl. 26.4 & Table 16 (cover)", "IS 456:2000 Table 3 (exposure)", "IS 13311 (NDT)"],
    },
}

_playbook_text = "\n".join(
    f"- {name}: causes -> {'; '.join(b['causes'][:2])}; repair -> {b['repairs'][0]['method']}"
    for name, b in DEFECT_PLAYBOOK.items()
)

CRACK_PROMPT = f"""You are a senior structural engineer (IS 456:2000, IS 15988, ACI 224R) diagnosing a concrete / masonry surface defect
from the attached photograph.

Classify the defect into EXACTLY one of: Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling.
Guidance: hairline < 0.3 mm random/map pattern; settlement = vertical/stepped, tapered width; structural shear = ~45 degree
diagonal near supports/joints; thermal expansion = straight, regular, seasonal movement; spalling = delaminated cover, exposed/rusted steel.
Reference engineering knowledge:
{_playbook_text}

Estimate crack width in mm using any visible scale references (coins, rebar, brick joints ~10 mm) and state your confidence.

Return ONLY one JSON object with exactly this schema:
{{
  "defect_type": "Hairline" | "Settlement" | "Structural Shear" | "Thermal Expansion" | "Spalling",
  "estimated_width_mm": <number>,
  "orientation": "Horizontal" | "Vertical" | "Diagonal" | "Map/Random",
  "confidence": <0-1>,
  "severity_score": <integer 0-100; 0-24 Low, 25-49 Medium, 50-74 High, 75-100 Critical>,
  "structural_risk": "<one sentence>",
  "root_causes": ["<likely cause>", "..."],
  "recommended_repairs": [{{"method": "<e.g. Epoxy injection>", "description": "<how>", "priority": "Primary" | "Secondary" | "Preventive"}}],
  "urgency": "Routine Monitoring" | "Within 30 Days" | "Within 7 Days" | "Immediate",
  "monitoring_plan": "<what to measure and how often>",
  "standards_referenced": ["IS 456:2000 Cl. 35.3.2", "..."],
  "summary": "<2-3 sentence engineering summary>"
}}
If the image is not a concrete/masonry surface, set severity_score 0 and explain in "summary"."""


def demo_crack(prepared: PreparedImage, metrics: dict) -> dict:
    """Offline estimate from detected crack coverage, orientation and darkness (clearly labelled demo)."""
    rng = random.Random(int(prepared.signature[:12], 16))
    ratio = float(metrics["crack_ratio"])
    orientation = str(metrics["orientation"])
    width = round(clamp(0.1 + ratio * 40, 0.1, 8.0), 1)

    if float(metrics["dark_ratio"]) > 0.30:
        defect = "Spalling"
    elif orientation == "Diagonal" and width >= 1.0:
        defect = "Structural Shear"
    elif orientation == "Vertical" and width >= 0.5:
        defect = "Settlement"
    elif width < 0.3:
        defect = "Hairline"
    elif orientation == "Horizontal" or float(metrics["elongation"]) > 6:
        defect = "Thermal Expansion"
    else:
        defect = rng.choice(["Settlement", "Thermal Expansion"])
    return {
        "defect_type": defect,
        "estimated_width_mm": width,
        "orientation": orientation if orientation != "Unspecified" else "Map/Random",
        "confidence": round(rng.uniform(0.5, 0.7), 2),
        "summary": (
            f"Offline demo diagnosis: {defect.lower()} pattern, approx. {width} mm wide, {orientation.lower()} trend. "
            "Heuristic edge analysis only - supply a Gemini API key for multimodal engineering assessment."
        ),
    }


def analyze_crack(prepared: PreparedImage, client: GeminiClient) -> tuple[CrackReport, Image.Image]:
    """Returns (report, local edge-detection overlay)."""
    overlay, metrics = crack_analysis(prepared.image)
    notes: list[str] = []
    if client.enabled:
        try:
            raw = client.generate_json(CRACK_PROMPT, prepared.jpeg_bytes, prepared.mime_type)
            return coerce_crack(raw, "gemini", client.last_model, DEFECT_PLAYBOOK), overlay
        except LLMError as exc:
            notes.append(f"Live analysis failed ({exc}). Showing demo-mode results instead.")
    report = coerce_crack(demo_crack(prepared, metrics), "demo", "offline-heuristic", DEFECT_PLAYBOOK)
    report.notes = notes or ["Demo mode: add a Gemini API key in the sidebar for live multimodal analysis."]
    return report, overlay


def report_json(report: CrackReport) -> str:
    return json.dumps(report.model_dump(), indent=2)
