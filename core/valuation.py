"""Epic 3 - Project planning, costing and real-estate valuation (INR) + Pollinations render prompts."""
from __future__ import annotations

import math
import zlib
from dataclasses import dataclass
from urllib.parse import quote

from .formatting import clamp


@dataclass(frozen=True)
class StructureSpec:
    label: str
    cost_per_sqft: float        # INR build cost, Tier-2 standard grade
    steel_kg_per_sqft: float
    cement_bags_per_sqft: float
    market_factor: float        # multiplier on city market rate
    base_months: float          # duration at 1,000 sq ft


STRUCTURES: dict[str, StructureSpec] = {
    "Independent House / Villa": StructureSpec("Independent House / Villa", 2600, 3.8, 0.45, 1.10, 8),
    "Residential Apartment (Mid-rise)": StructureSpec("Residential Apartment (Mid-rise)", 2200, 4.2, 0.42, 1.00, 9),
    "High-Rise Tower (G+15 and above)": StructureSpec("High-Rise Tower (G+15 and above)", 3400, 6.0, 0.50, 1.25, 12),
    "Commercial Complex / Office": StructureSpec("Commercial Complex / Office", 2900, 4.8, 0.45, 1.35, 9),
    "Institutional (School / Hospital)": StructureSpec("Institutional (School / Hospital)", 2400, 4.0, 0.42, 0.90, 7),
    "Industrial Warehouse / PEB Shed": StructureSpec("Industrial Warehouse / PEB Shed", 1700, 7.0, 0.25, 0.70, 4),
}


@dataclass(frozen=True)
class TierSpec:
    cost_multiplier: float
    market_rate_per_sqft: float
    land_share: float
    examples: str


TIERS: dict[str, TierSpec] = {
    "Tier 1": TierSpec(1.30, 11500, 0.40, "Mumbai, Delhi NCR, Bengaluru, Hyderabad, Chennai, Kolkata, Pune"),
    "Tier 2": TierSpec(1.00, 6200, 0.28, "Jaipur, Lucknow, Indore, Nagpur, Coimbatore, Kochi, Chandigarh"),
    "Tier 3": TierSpec(0.82, 3400, 0.20, "Bhopal outskirts, Mysuru, Nashik, Guntur, Dehradun, smaller district towns"),
}

# grade -> (build-cost multiplier, market-value uplift)
GRADES: dict[str, tuple[float, float]] = {
    "Standard": (1.00, 1.00),
    "Premium": (1.25, 1.12),
    "Luxury": (1.60, 1.30),
}

CONTINGENCY = 0.05
STEEL_RATE_PER_KG = 65.0
CEMENT_RATE_PER_BAG = 390.0

COST_BREAKDOWN = (
    ("Civil & Structure", 0.38),
    ("Finishing & Interiors", 0.22),
    ("MEP (Electrical, Plumbing, HVAC)", 0.15),
    ("Labour & Supervision", 0.15),
    ("Approvals, Overheads & Contingency", 0.10),
)


@dataclass(frozen=True)
class Milestone:
    name: str
    cost_weight: float
    steel_share: float
    cement_share: float
    duration_share: float


MILESTONES = (
    Milestone("Site Preparation & Foundation", 0.14, 0.22, 0.25, 0.12),
    Milestone("Plinth & Substructure", 0.08, 0.12, 0.15, 0.08),
    Milestone("Superstructure (Columns, Beams, Slabs)", 0.30, 0.58, 0.45, 0.35),
    Milestone("Masonry & Plastering", 0.14, 0.04, 0.12, 0.15),
    Milestone("MEP Rough-in", 0.12, 0.02, 0.01, 0.12),
    Milestone("Finishing & Handover", 0.22, 0.02, 0.02, 0.18),
)


def compute_valuation(structure: str, sqft: float, tier: str, completion_pct: float, grade: str = "Standard") -> dict:
    """Deterministic costing/valuation model. Raises ValueError on invalid inputs."""
    if structure not in STRUCTURES:
        raise ValueError(f"Unknown structure type: {structure}")
    if tier not in TIERS:
        raise ValueError(f"Unknown location tier: {tier}")
    if grade not in GRADES:
        raise ValueError(f"Unknown finish grade: {grade}")
    if not 100 <= sqft <= 5_000_000:
        raise ValueError("Built-up area must be between 100 and 5,000,000 sq ft.")
    if not 0 <= completion_pct <= 100:
        raise ValueError("Completion percentage must be between 0 and 100.")

    spec, tier_spec = STRUCTURES[structure], TIERS[tier]
    cost_mult, market_uplift = GRADES[grade]
    progress = completion_pct / 100.0

    # ---- budget & capex
    base_cost = sqft * spec.cost_per_sqft * tier_spec.cost_multiplier * cost_mult
    budget = base_cost * (1 + CONTINGENCY)
    capex = budget * progress
    breakdown = [{"category": c, "share": s, "amount": budget * s, "spent": budget * s * progress}
                 for c, s in COST_BREAKDOWN]

    # ---- valuation
    market_rate = tier_spec.market_rate_per_sqft * spec.market_factor * market_uplift
    completed_value = sqft * market_rate
    land_value = completed_value * tier_spec.land_share
    structure_value = completed_value - land_value
    current_value = land_value + structure_value * progress
    valuation = {
        "market_rate_per_sqft": market_rate,
        "land_value": land_value,
        "structure_value_full": structure_value,
        "current_value": current_value,
        "value_on_completion": completed_value,
        "appreciation_potential": completed_value - current_value,
        "profit_on_completion": completed_value - budget,
        "roi_pct": (completed_value - budget) / budget * 100,
    }

    # ---- milestones (earned-value walk by cost weight)
    steel_total = sqft * spec.steel_kg_per_sqft
    cement_total = sqft * spec.cement_bags_per_sqft
    total_months = int(clamp(round(spec.base_months * (sqft / 1000) ** 0.4), 4, 60))

    cum_cost, steel_frac, cement_frac, time_frac = 0.0, 0.0, 0.0, 0.0
    start_month = 0.0
    milestones = []
    for m in MILESTONES:
        done = clamp((progress - cum_cost) / m.cost_weight, 0, 1)
        cum_cost += m.cost_weight
        steel_frac += m.steel_share * done
        cement_frac += m.cement_share * done
        time_frac += m.duration_share * done
        duration = m.duration_share * total_months
        milestones.append({
            "name": m.name,
            "cost_weight_pct": m.cost_weight * 100,
            "progress_pct": round(done * 100, 1),
            "status": "Completed" if done >= 0.999 else "In Progress" if done > 0 else "Pending",
            "budget": budget * m.cost_weight,
            "start_month": round(start_month, 1),
            "duration_months": round(duration, 1),
        })
        start_month += duration

    materials = {
        "steel_total_kg": steel_total,
        "steel_total_tonnes": steel_total / 1000,
        "steel_consumed_kg": steel_total * steel_frac,
        "steel_remaining_kg": steel_total * (1 - steel_frac),
        "steel_cost": steel_total * STEEL_RATE_PER_KG,
        "cement_total_bags": cement_total,
        "cement_consumed_bags": cement_total * cement_frac,
        "cement_remaining_bags": cement_total * (1 - cement_frac),
        "cement_cost": cement_total * CEMENT_RATE_PER_BAG,
    }
    elapsed = total_months * time_frac
    return {
        "inputs": {"structure": structure, "sqft": sqft, "tier": tier, "completion_pct": completion_pct, "grade": grade},
        "budget": {"total": budget, "per_sqft": budget / sqft, "capex_incurred": capex,
                   "remaining": budget - capex, "contingency_pct": CONTINGENCY * 100, "breakdown": breakdown},
        "valuation": valuation,
        "materials": materials,
        "milestones": milestones,
        "schedule": {"total_months": total_months, "elapsed_months": round(elapsed, 1),
                     "remaining_months": round(total_months - elapsed, 1)},
        "current_phase": next((m["name"] for m in milestones if m["status"] == "In Progress"),
                              "Handover complete" if progress >= 1 else "Not started"),
    }


# ----------------------------------------------------------- 3D concept render
ARCH_STYLES = ("Contemporary Indian", "Modern Minimalist", "Neo-Classical", "Sustainable Green Building",
               "Glass & Steel Corporate", "Industrial Loft")
TIMES_OF_DAY = ("Golden hour", "Bright midday", "Blue hour dusk", "Overcast monsoon")


def _phase_descriptor(pct: float) -> str:
    if pct < 15:
        return "early excavation and foundation works with rebar cages, excavators and shuttering"
    if pct < 40:
        return "reinforced concrete frame rising with scaffolding, formwork and a tower crane"
    if pct < 70:
        return "concrete structure with brick masonry walls, scaffolding and partial plastering"
    if pct < 100:
        return "nearly finished building with facade cladding, window fitting and finishing crews"
    return "fully completed, landscaped and handed-over building"


def build_render_prompt(structure: str, tier: str, completion_pct: float, style: str = ARCH_STYLES[0],
                        city: str = "", time_of_day: str = TIMES_OF_DAY[0]) -> str:
    place = f"in {city}, India" if city.strip() else f"in a {tier} Indian city"
    return (
        f"Photorealistic 3D architectural rendering of a {structure.lower()} {place}, {style} design, "
        f"shown at {int(completion_pct)}% construction progress: {_phase_descriptor(completion_pct)}. "
        f"{time_of_day} lighting, wide-angle aerial perspective, highly detailed, 8k, cinematic."
    )


def build_pollinations_url(prompt: str, width: int = 1024, height: int = 640, seed: int | None = None,
                           model: str = "flux") -> str:
    seed = seed if seed is not None else zlib.crc32(prompt.encode("utf-8")) % 100000
    return (f"https://image.pollinations.ai/prompt/{quote(prompt, safe='')}"
            f"?width={width}&height={height}&seed={seed}&model={model}&nologo=true")


def human_months(months: float) -> str:
    years, rem = divmod(int(math.ceil(months)), 12)
    parts = []
    if years:
        parts.append(f"{years} yr")
    if rem or not years:
        parts.append(f"{rem} mo")
    return " ".join(parts)
