"""FastAPI contract tests (no network, demo mode)."""
import io
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""

from backend import main  # noqa: E402
from core.storage import ReportStore  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "assets"


@pytest.fixture()
def client(tmp_path):
    main.store = ReportStore(tmp_path)
    return TestClient(main.app)


def test_health_and_config(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "success"
    cfg = client.get("/api/config").json()["data"]
    assert "Tier 1" in cfg["tiers"] and len(cfg["structures"]) >= 5


def test_safety_endpoint_returns_contract_and_persists(client):
    with open(ASSETS / "sample_site.jpg", "rb") as f:
        r = client.post("/api/safety/analyze", files={"file": ("site.jpg", f, "image/jpeg")})
    body = r.json()
    assert r.status_code == 200 and body["meta"]["mode"] == "demo"
    data = body["data"]
    assert 0 <= data["safety_score"] <= 100 and len(data["ppe_detection"]) == 4
    saved = client.get(f"/api/reports/{body['meta']['report_id']}").json()
    assert saved["data"]["payload"]["safety_score"] == data["safety_score"]
    assert len(client.get("/api/reports", params={"kind": "safety_audit"}).json()["data"]) == 1


def test_crack_endpoint_includes_overlay(client):
    with open(ASSETS / "sample_crack.jpg", "rb") as f:
        r = client.post("/api/cracks/analyze", files={"file": ("crack.jpg", f, "image/jpeg")})
    body = r.json()
    assert r.status_code == 200 and body["meta"]["overlay_image"].startswith("data:image/jpeg;base64,")
    assert body["data"]["defect_type"] in ("Hairline", "Settlement", "Structural Shear", "Thermal Expansion", "Spalling")


def test_invalid_upload_returns_error_envelope(client):
    r = client.post("/api/safety/analyze", files={"file": ("x.jpg", io.BytesIO(b"garbage"), "image/jpeg")})
    assert r.status_code == 400 and r.json()["status"] == "error"


def test_valuation_endpoint_and_validation(client):
    payload = {"structure": "Independent House / Villa", "sqft": 2000, "tier": "Tier 2", "completion_pct": 50}
    r = client.post("/api/valuation", json=payload)
    assert r.status_code == 200 and r.json()["data"]["budget"]["total"] > 0
    assert r.json()["meta"]["display"]["total_budget"].startswith("₹")
    assert client.post("/api/valuation", json={**payload, "completion_pct": 150}).status_code == 422
    assert client.post("/api/valuation", json={**payload, "structure": "Castle"}).status_code == 422
    assert client.post("/api/valuation", json={**payload, "tier": "Tier 9"}).json()["status"] == "error"


def test_weather_endpoints(client):
    r = client.get("/api/weather/advisory/Heavy Rain")
    assert r.status_code == 200 and r.json()["data"]["operations"]["Concrete pouring"][0] == "Suspend"
    assert client.get("/api/weather/advisory/Snow").status_code == 404


def test_chat_endpoint(client):
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "What PPE is required?"}]})
    assert r.status_code == 200 and "IS 2925" in r.json()["data"]["answer"] and r.json()["meta"]["mode"] == "offline"
    assert client.post("/api/chat", json={"messages": []}).status_code == 422
    bad = client.post("/api/chat", json={"messages": [{"role": "assistant", "content": "hi"}]})
    assert bad.status_code == 422


def test_render_prompt_endpoint(client):
    r = client.post("/api/render-prompt", json={"structure": "Independent House / Villa", "tier": "Tier 1", "completion_pct": 60})
    assert r.json()["data"]["image_url"].startswith("https://image.pollinations.ai/")


def test_report_not_found_and_traversal(client):
    assert client.get("/api/reports/" + "0" * 32).status_code == 404
    assert client.get("/api/reports/..%2F..%2Fsecret").status_code in (404, 422)
