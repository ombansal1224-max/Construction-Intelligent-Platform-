"""Strict JSON data contracts + tolerant coercion of raw LLM output.

The frontends only ever see validated models, so a sloppy model response can never
break the UI: every field is clamped, enum-matched or back-filled with safe defaults.
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from .config import (
    DEFECT_TYPES,
    PPE_ITEMS,
    SEVERITY_LEVELS,
    SEVERITY_RANK,
    URGENCY_LEVELS,
)
from .formatting import clamp, utc_now_iso

Severity = Literal["Low", "Medium", "High", "Critical"]
PPEStatus = Literal["Compliant", "Violation", "Not Visible"]
SafetyStatus = Literal["Compliant", "Needs Attention", "High Risk", "Critical"]
DefectType = Literal["Hairline", "Settlement", "Structural Shear", "Thermal Expansion", "Spalling"]
Urgency = Literal["Routine Monitoring", "Within 30 Days", "Within 7 Days", "Immediate"]
Mode = Literal["gemini", "demo"]


# ------------------------------------------------------------------ contracts
class PPEItem(BaseModel):
    item: str
    label: str
    status: PPEStatus
    confidence: float = Field(0.5, ge=0, le=1)
    note: str = ""


class Hazard(BaseModel):
    hazard: str
    severity: Severity
    location: str = ""
    standard_reference: str = ""
    remedy: str


class SafetyReport(BaseModel):
    report_type: Literal["safety_audit"] = "safety_audit"
    safety_score: int = Field(ge=0, le=100)
    overall_status: SafetyStatus
    workers_detected: int = Field(0, ge=0)
    ppe_detection: list[PPEItem]
    hazards: list[Hazard]
    summary: str
    recommendations: list[str]
    standards_referenced: list[str]
    analysis_mode: Mode
    model: str
    generated_at: str
    notes: list[str] = []


class RepairStep(BaseModel):
    method: str
    description: str
    priority: Literal["Primary", "Secondary", "Preventive"] = "Primary"


class CrackReport(BaseModel):
    report_type: Literal["crack_diagnostic"] = "crack_diagnostic"
    defect_type: DefectType
    estimated_width_mm: float = Field(ge=0)
    orientation: str = "Unspecified"
    confidence: float = Field(0.5, ge=0, le=1)
    severity_score: int = Field(ge=0, le=100)
    severity_level: Severity
    structural_risk: str
    root_causes: list[str]
    recommended_repairs: list[RepairStep]
    urgency: Urgency
    monitoring_plan: str
    standards_referenced: list[str]
    summary: str
    analysis_mode: Mode
    model: str
    generated_at: str
    notes: list[str] = []


# ----------------------------------------------------------------- coercion
def to_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if m:
            return float(m.group())
    return default


def to_confidence(value: Any, default: float = 0.6) -> float:
    """Accept 0-1 or 0-100 confidence values and return a 0-1 float."""
    v = to_float(value, default)
    if v > 1:
        v = v / 100
    return clamp(v, 0, 1)


def match_choice(value: Any, choices: tuple[str, ...], default: str) -> str:
    """Case-insensitive exact, then containment match against a closed vocabulary."""
    if not isinstance(value, str):
        return default
    v = value.strip().lower()
    for c in choices:
        if v == c.lower():
            return c
    for c in choices:
        cl = c.lower()
        if cl in v or (v and v in cl):
            return c
    return default


def as_str_list(value: Any, limit: int = 12) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    out: list[str] = []
    for v in value:
        if isinstance(v, dict):
            v = v.get("text") or v.get("description") or v.get("cause") or " - ".join(str(x) for x in v.values())
        s = str(v).strip()
        if s:
            out.append(s)
    return out[:limit]


_POSITIVE = ("compliant", "detected", "present", "worn", "yes", "true", "wearing", "ok", "pass")
_NEGATIVE = ("violation", "missing", "absent", "non-compliant", "noncompliant", "not worn", "no", "false", "fail", "not wearing")


def ppe_status(value: Any) -> str:
    if isinstance(value, bool):
        return "Compliant" if value else "Violation"
    if isinstance(value, dict):
        return ppe_status(value.get("status", value.get("detected", value.get("compliant"))))
    if isinstance(value, str):
        v = value.strip().lower()
        if "not visible" in v or "unclear" in v or "n/a" in v or "unknown" in v or "cannot" in v:
            return "Not Visible"
        if any(v == n or v.startswith(n) for n in _NEGATIVE):
            return "Violation"
        if any(v == p or v.startswith(p) for p in _POSITIVE):
            return "Compliant"
    return "Not Visible"


def derive_safety_score(ppe: list[PPEItem], hazards: list[Hazard]) -> int:
    penalty = {"Low": 3, "Medium": 7, "High": 14, "Critical": 25}
    score = 100 - 12 * sum(1 for p in ppe if p.status == "Violation")
    score -= sum(penalty[h.severity] for h in hazards)
    return int(clamp(score, 0, 100))


def safety_status_from_score(score: int) -> str:
    if score >= 85:
        return "Compliant"
    if score >= 65:
        return "Needs Attention"
    if score >= 40:
        return "High Risk"
    return "Critical"


def severity_from_score(score: int) -> str:
    if score < 25:
        return "Low"
    if score < 50:
        return "Medium"
    if score < 75:
        return "High"
    return "Critical"


def urgency_from_severity(severity: str) -> str:
    return {
        "Low": "Routine Monitoring",
        "Medium": "Within 30 Days",
        "High": "Within 7 Days",
        "Critical": "Immediate",
    }[severity]


def coerce_safety(raw: dict, mode: str, model: str) -> SafetyReport:
    # ---- PPE checklist
    raw_ppe = raw.get("ppe_detection") or raw.get("ppe") or []
    lookup: dict[str, Any] = {}
    if isinstance(raw_ppe, dict):
        for k, v in raw_ppe.items():
            lookup[str(k).lower()] = v if isinstance(v, dict) else {"status": v}
    elif isinstance(raw_ppe, list):
        for entry in raw_ppe:
            if isinstance(entry, dict):
                key = str(entry.get("item") or entry.get("name") or entry.get("label") or "").lower()
                lookup[key] = entry
    ppe: list[PPEItem] = []
    for key, label, _std in PPE_ITEMS:
        spaced = key.replace("_", " ")
        entry = lookup.get(key)
        if entry is None:
            entry = next((v for k, v in lookup.items() if k and (spaced in k or label.lower() in k)), None)
        entry = entry if isinstance(entry, dict) else {}
        ppe.append(
            PPEItem(
                item=key,
                label=label,
                status=ppe_status(entry),
                confidence=to_confidence(entry.get("confidence"), 0.5),
                note=str(entry.get("note", entry.get("remarks", "")))[:240],
            )
        )

    # ---- hazards
    hazards: list[Hazard] = []
    for h in (raw.get("hazards") or raw.get("identified_hazards") or [])[:12]:
        if isinstance(h, str):
            h = {"hazard": h}
        if not isinstance(h, dict):
            continue
        name = str(h.get("hazard") or h.get("name") or h.get("description") or "").strip()
        if not name:
            continue
        hazards.append(
            Hazard(
                hazard=name,
                severity=match_choice(h.get("severity"), SEVERITY_LEVELS, "Medium"),
                location=str(h.get("location", ""))[:160],
                standard_reference=str(h.get("standard_reference") or h.get("standard") or "")[:160],
                remedy=str(h.get("remedy") or h.get("corrective_action") or h.get("recommendation")
                           or "Engage the site safety officer to assess and remediate.")[:400],
            )
        )
    hazards.sort(key=lambda x: -SEVERITY_RANK[x.severity])

    # ---- score & status (guard-railed)
    if raw.get("safety_score") is not None:
        score = int(clamp(round(to_float(raw["safety_score"], derive_safety_score(ppe, hazards))), 0, 100))
    else:
        score = derive_safety_score(ppe, hazards)
    if any(h.severity == "Critical" for h in hazards):
        score = min(score, 55)  # a critical hazard can never coexist with a 'good' score
    status = safety_status_from_score(score)

    return SafetyReport(
        safety_score=score,
        overall_status=status,
        workers_detected=max(0, int(to_float(raw.get("workers_detected"), 0))),
        ppe_detection=ppe,
        hazards=hazards,
        summary=str(raw.get("summary") or "Automated PPE and hazard audit completed.")[:900],
        recommendations=as_str_list(raw.get("recommendations")),
        standards_referenced=as_str_list(raw.get("standards_referenced"))
        or ["OSHA 29 CFR 1926", "IS 456:2000", "BOCW Central Rules 1998"],
        analysis_mode=mode,
        model=model,
        generated_at=utc_now_iso(),
    )


def coerce_crack(raw: dict, mode: str, model: str, playbook: dict[str, dict]) -> CrackReport:
    defect = match_choice(raw.get("defect_type") or raw.get("classification"), DEFECT_TYPES, "Hairline")
    book = playbook[defect]
    width = round(clamp(to_float(raw.get("estimated_width_mm"), 0.2), 0, 50), 2)

    floor = 0 if width < 0.3 else 25 if width < 1 else 50 if width < 3 else 75
    if defect == "Structural Shear":
        floor = max(floor, 50)
    if raw.get("severity_score") is not None:
        score = to_float(raw["severity_score"], floor)
    else:
        score = max(floor, min(100, width * 22 + book["base_score"]))
    score = int(clamp(max(score, floor), 0, 100))
    level = severity_from_score(score)

    repairs: list[RepairStep] = []
    for r in raw.get("recommended_repairs") or raw.get("repairs") or []:
        if isinstance(r, str):
            r = {"method": r, "description": r}
        if isinstance(r, dict):
            method = str(r.get("method") or r.get("name") or "").strip()
            if method:
                repairs.append(
                    RepairStep(
                        method=method[:120],
                        description=str(r.get("description") or r.get("details") or method)[:500],
                        priority=match_choice(r.get("priority"), ("Primary", "Secondary", "Preventive"), "Primary"),
                    )
                )
    if not repairs:
        repairs = [RepairStep(**s) for s in book["repairs"]]

    return CrackReport(
        defect_type=defect,
        estimated_width_mm=width,
        orientation=str(raw.get("orientation") or "Unspecified")[:60],
        confidence=to_confidence(raw.get("confidence"), 0.6),
        severity_score=score,
        severity_level=level,
        structural_risk=str(raw.get("structural_risk") or book["risk"])[:500],
        root_causes=as_str_list(raw.get("root_causes")) or list(book["causes"]),
        recommended_repairs=repairs[:8],
        urgency=match_choice(raw.get("urgency"), URGENCY_LEVELS, urgency_from_severity(level))
        if raw.get("urgency") else urgency_from_severity(level),
        monitoring_plan=str(raw.get("monitoring_plan") or book["monitoring"])[:600],
        standards_referenced=as_str_list(raw.get("standards_referenced")) or list(book["standards"]),
        summary=str(raw.get("summary") or f"{defect} defect identified, approx. {width} mm wide.")[:900],
        analysis_mode=mode,
        model=model,
        generated_at=utc_now_iso(),
    )
