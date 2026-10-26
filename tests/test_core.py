"""Unit tests for the UI-agnostic core engine."""
import io
from pathlib import Path

import pytest
from PIL import Image

from core.assistant import ConstructionAssistant, offline_answer
from core.cracks import DEFECT_PLAYBOOK, analyze_crack
from core.formatting import format_inr, indian_grouping
from core.imaging import ImageError, prepare_image
from core.llm import GeminiClient, LLMError, extract_json
from core.safety import analyze_safety
from core.schemas import coerce_crack, coerce_safety
from core.storage import ReportStore
from core.valuation import (STRUCTURES, build_pollinations_url, build_render_prompt, compute_valuation)
from core.weather import ADVISORIES, classify_conditions, get_advisory

ASSETS = Path(__file__).resolve().parent.parent / "assets"
NO_KEY = GeminiClient("")


def _png_bytes(color=(120, 120, 120), size=(200, 150)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


# ------------------------------------------------------------------ formatting
def test_indian_grouping_and_inr():
    assert indian_grouping(1234567) == "12,34,567"
    assert indian_grouping(999) == "999"
    assert format_inr(25_000_000) == "₹2.50 Cr"
    assert format_inr(4_560_000) == "₹45.60 L"
    assert format_inr(12_345) == "₹12,345"


# ------------------------------------------------------------------ imaging
def test_prepare_image_rejects_bad_input():
    with pytest.raises(ImageError):
        prepare_image(b"")
    with pytest.raises(ImageError):
        prepare_image(b"not an image")


def test_prepare_image_ok_and_deterministic_signature():
    a, b = prepare_image(_png_bytes()), prepare_image(_png_bytes())
    assert a.mime_type == "image/jpeg" and a.signature == b.signature


# ------------------------------------------------------------------ llm
def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json('Here you go: {"a": 3} thanks') == {"a": 3}
    with pytest.raises(LLMError):
        extract_json("no json here")


def test_client_without_key_raises():
    with pytest.raises(LLMError):
        NO_KEY.generate_json("hi")


# ------------------------------------------------------------------ safety
def test_coerce_safety_handles_messy_output():
    raw = {
        "safety_score": "72%",
        "ppe_detection": {"helmet": True, "hi_vis_vest": "missing", "safety_boots": {"status": "Compliant", "confidence": 90}},
        "hazards": [{"hazard": "Open edge", "severity": "critical"}, "Loose debris"],
    }
    r = coerce_safety(raw, "gemini", "test")
    status = {p.item: p.status for p in r.ppe_detection}
    assert status == {"helmet": "Compliant", "hi_vis_vest": "Violation", "safety_boots": "Compliant", "safety_harness": "Not Visible"}
    assert r.safety_score <= 55 and r.overall_status in ("High Risk", "Critical")  # critical-hazard guardrail
    assert r.hazards[0].severity == "Critical"
    assert r.ppe_detection[2].confidence == 0.9


def test_demo_safety_on_sample_is_deterministic():
    p = prepare_image((ASSETS / "sample_site.jpg").read_bytes())
    r1, r2 = analyze_safety(p, NO_KEY), analyze_safety(p, NO_KEY)
    assert r1.analysis_mode == "demo" and 0 <= r1.safety_score <= 100
    assert r1.safety_score == r2.safety_score and len(r1.ppe_detection) == 4
    assert r1.ppe_detection[1].status == "Compliant"  # orange vest visible in sample


# ------------------------------------------------------------------ cracks
def test_coerce_crack_guardrails():
    r = coerce_crack({"defect_type": "structural shear crack", "estimated_width_mm": "4.5 mm", "severity_score": 10},
                     "gemini", "t", DEFECT_PLAYBOOK)
    assert r.defect_type == "Structural Shear" and r.severity_level == "Critical" and r.urgency == "Immediate"
    assert len(r.recommended_repairs) >= 1 and r.root_causes


def test_demo_crack_sample_detects_serious_diagonal():
    p = prepare_image((ASSETS / "sample_crack.jpg").read_bytes())
    report, overlay = analyze_crack(p, NO_KEY)
    assert report.analysis_mode == "demo" and overlay.size[0] > 0
    assert report.estimated_width_mm > 0.3 and report.severity_score >= 25


def test_demo_crack_blank_surface_is_low_risk():
    p = prepare_image(_png_bytes((150, 150, 150)))
    report, _ = analyze_crack(p, NO_KEY)
    assert report.defect_type == "Hairline" and report.severity_level == "Low"


# ------------------------------------------------------------------ valuation
@pytest.mark.parametrize("structure", list(STRUCTURES))
@pytest.mark.parametrize("tier", ["Tier 1", "Tier 2", "Tier 3"])
def test_valuation_invariants(structure, tier):
    r = compute_valuation(structure, 2000, tier, 40)
    b, v = r["budget"], r["valuation"]
    assert b["capex_incurred"] == pytest.approx(b["total"] * 0.4)
    assert sum(x["amount"] for x in b["breakdown"]) == pytest.approx(b["total"])
    assert v["land_value"] < v["current_value"] < v["value_on_completion"]
    assert 0 <= r["materials"]["steel_consumed_kg"] <= r["materials"]["steel_total_kg"]


def test_valuation_extremes_and_milestones():
    zero, full = compute_valuation("Independent House / Villa", 1500, "Tier 2", 0), \
        compute_valuation("Independent House / Villa", 1500, "Tier 2", 100)
    assert zero["materials"]["steel_consumed_kg"] == 0 and all(m["status"] == "Pending" for m in zero["milestones"])
    assert full["materials"]["steel_consumed_kg"] == pytest.approx(full["materials"]["steel_total_kg"])
    assert all(m["status"] == "Completed" for m in full["milestones"])
    assert full["valuation"]["current_value"] == pytest.approx(full["valuation"]["value_on_completion"])
    mid = compute_valuation("Independent House / Villa", 1500, "Tier 2", 50)
    assert [m["status"] for m in mid["milestones"]][:3] == ["Completed", "Completed", "In Progress"]


def test_tier_ordering_and_validation():
    t1 = compute_valuation("Commercial Complex / Office", 5000, "Tier 1", 50)
    t3 = compute_valuation("Commercial Complex / Office", 5000, "Tier 3", 50)
    assert t1["budget"]["total"] > t3["budget"]["total"] and t1["valuation"]["current_value"] > t3["valuation"]["current_value"]
    with pytest.raises(ValueError):
        compute_valuation("Nope", 1000, "Tier 1", 10)
    with pytest.raises(ValueError):
        compute_valuation("Independent House / Villa", 10, "Tier 1", 10)
    with pytest.raises(ValueError):
        compute_valuation("Independent House / Villa", 1000, "Tier 1", 120)


def test_render_prompt_and_url():
    prompt = build_render_prompt("Independent House / Villa", "Tier 2", 35, city="Jaipur")
    assert "Jaipur" in prompt and "35%" in prompt
    url = build_pollinations_url(prompt)
    assert url.startswith("https://image.pollinations.ai/prompt/") and " " not in url
    assert build_pollinations_url(prompt) == url  # deterministic seed


# ------------------------------------------------------------------ weather
def test_weather_advisories_complete():
    for cond, a in ADVISORIES.items():
        assert a["alerts"] and a["operations"] and a["curing"] and a["checklist"], cond
        assert all(s in ("Go", "Restrict", "Suspend") for s, _ in a["operations"].values())
    assert get_advisory("High Wind")["operations"]["Crane & lifting"][0] == "Suspend"
    with pytest.raises(ValueError):
        get_advisory("Snow")


def test_classify_conditions():
    assert classify_conditions(10, 15, 0, 28) == "Normal"
    assert classify_conditions(40, 55, 0, 30) == "High Wind"
    assert classify_conditions(10, 15, 6, 28) == "Heavy Rain"
    assert classify_conditions(10, 15, 0, 44) == "Extreme Heat"
    assert classify_conditions(40, 55, 5, 44) == "Heavy Rain"


# ------------------------------------------------------------------ assistant
def test_offline_assistant_topics():
    assert "7 days" in offline_answer("How long should I cure concrete?")
    assert "IS 2925" in offline_answer("what ppe is needed?")
    assert "offline knowledge mode" in offline_answer("what's the capital of france")


def test_assistant_uses_project_context():
    ctx = {"valuation": compute_valuation("Independent House / Villa", 1500, "Tier 2", 50)}
    ans, mode = ConstructionAssistant(NO_KEY).reply([{"role": "user", "content": "What's my project budget?"}], ctx)
    assert mode == "offline" and "Total budget" in ans


# ------------------------------------------------------------------ storage
def test_report_store_roundtrip_and_traversal(tmp_path):
    store = ReportStore(tmp_path)
    rid = store.save("safety", {"x": 1})
    assert store.get(rid)["payload"] == {"x": 1}
    assert store.list("safety")[0]["id"] == rid and store.list("crack") == []
    assert store.get("../../etc/passwd") is None and store.delete(rid) and store.get(rid) is None
