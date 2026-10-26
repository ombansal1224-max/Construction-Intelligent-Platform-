"""FastAPI backend - API & application logic layer of the architecture.

Run from the project root:  uvicorn backend.main:app --reload --port 8000
All responses use a strict envelope: {"status": "success"|"error", "data": {...}, "meta": {...}}.
"""
from __future__ import annotations

import base64
import io
import os
from typing import Literal

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.assistant import ConstructionAssistant
from core.config import APP_NAME, APP_VERSION, GEMINI_MODELS, MAX_UPLOAD_MB, WEATHER_CONDITIONS, resolve_api_key
from core.cracks import analyze_crack
from core.formatting import format_inr
from core.imaging import ImageError, prepare_image
from core.llm import GeminiClient
from core.safety import analyze_safety
from core.storage import ReportStore
from core.valuation import (ARCH_STYLES, GRADES, STRUCTURES, TIERS, TIMES_OF_DAY, build_pollinations_url,
                            build_render_prompt, compute_valuation)
from core.weather import fetch_live_weather, get_advisory

app = FastAPI(title=APP_NAME, version=APP_VERSION,
              description="Multimodal construction intelligence: PPE audit, crack diagnostics, valuation, weather advisory.")

origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

store = ReportStore(os.environ.get("REPORT_DIR", "data/reports"))


# ----------------------------------------------------------------- envelopes
def ok(data, **meta) -> dict:
    return {"status": "success", "data": data, "meta": meta}


def _error(code: str, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(status_code=http_status, content={"status": "error", "error": {"code": code, "message": message}})


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    return _error("http_error", str(exc.detail), exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    return _error("validation_error", f"{loc}: {first.get('msg', 'invalid request')}".strip(": "), 422)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    return _error("internal_error", "Unexpected server error.", 500)


# ----------------------------------------------------------------- dependencies
def get_client(x_gemini_key: str | None = Header(default=None)) -> GeminiClient:
    return GeminiClient(resolve_api_key(x_gemini_key), models=GEMINI_MODELS)


async def read_image(file: UploadFile):
    data = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    try:
        return prepare_image(data)
    except ImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ----------------------------------------------------------------- schemas
class ValuationRequest(BaseModel):
    structure: str
    sqft: float = Field(ge=100, le=5_000_000)
    tier: Literal["Tier 1", "Tier 2", "Tier 3"]
    completion_pct: float = Field(ge=0, le=100)
    grade: Literal["Standard", "Premium", "Luxury"] = "Standard"


class RenderRequest(BaseModel):
    structure: str
    tier: Literal["Tier 1", "Tier 2", "Tier 3"]
    completion_pct: float = Field(ge=0, le=100)
    style: str = ARCH_STYLES[0]
    city: str = ""
    time_of_day: str = TIMES_OF_DAY[0]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    context: dict | None = None


# ----------------------------------------------------------------- routes
@app.get("/api/health")
def health():
    return ok({"app": APP_NAME, "version": APP_VERSION}, models=list(GEMINI_MODELS))


@app.get("/api/config")
def config():
    """Static option lists the frontend uses to render its forms."""
    return ok({
        "structures": list(STRUCTURES),
        "tiers": {k: {"examples": t.examples} for k, t in TIERS.items()},
        "grades": list(GRADES),
        "weather_conditions": list(WEATHER_CONDITIONS),
        "styles": list(ARCH_STYLES),
        "times_of_day": list(TIMES_OF_DAY),
    })


@app.post("/api/key/validate")
def validate_key(client: GeminiClient = Depends(get_client)):
    valid, message = client.validate_key()
    return ok({"valid": valid, "message": message}, mode="gemini" if client.enabled else "demo")


@app.post("/api/safety/analyze")
async def safety_analyze(file: UploadFile = File(...), client: GeminiClient = Depends(get_client)):
    report = analyze_safety(await read_image(file), client)
    payload = report.model_dump()
    return ok(payload, report_id=store.save("safety_audit", payload), mode=report.analysis_mode)


@app.post("/api/cracks/analyze")
async def cracks_analyze(file: UploadFile = File(...), client: GeminiClient = Depends(get_client)):
    report, overlay = analyze_crack(await read_image(file), client)
    buf = io.BytesIO()
    overlay.save(buf, "JPEG", quality=85)
    payload = report.model_dump()
    return ok(payload, report_id=store.save("crack_diagnostic", payload), mode=report.analysis_mode,
              overlay_image="data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode())


@app.post("/api/valuation")
def valuation(req: ValuationRequest):
    try:
        result = compute_valuation(req.structure, req.sqft, req.tier, req.completion_pct, req.grade)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    v, b = result["valuation"], result["budget"]
    display = {"total_budget": format_inr(b["total"]), "capex_incurred": format_inr(b["capex_incurred"]),
               "current_value": format_inr(v["current_value"]), "value_on_completion": format_inr(v["value_on_completion"])}
    return ok(result, display=display)


@app.post("/api/render-prompt")
def render_prompt(req: RenderRequest):
    prompt = build_render_prompt(req.structure, req.tier, req.completion_pct, req.style, req.city, req.time_of_day)
    return ok({"prompt": prompt, "image_url": build_pollinations_url(prompt)})


@app.get("/api/weather/advisory/{condition}")
def weather_advisory(condition: str):
    try:
        return ok(get_advisory(condition), condition=condition)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/weather/live")
def weather_live(city: str):
    try:
        return ok(fetch_live_weather(city))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/chat")
def chat(req: ChatRequest, client: GeminiClient = Depends(get_client)):
    history = [m.model_dump() for m in req.messages]
    if history[-1]["role"] != "user":
        raise HTTPException(status_code=422, detail="The last message must come from the user.")
    answer, mode = ConstructionAssistant(client).reply(history, req.context)
    return ok({"answer": answer}, mode=mode)


@app.get("/api/reports")
def list_reports(kind: str | None = None):
    return ok(store.list(kind))


@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    record = store.get(report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Report not found.")
    return ok(record)


@app.delete("/api/reports/{report_id}")
def delete_report(report_id: str):
    if not store.delete(report_id):
        raise HTTPException(status_code=404, detail="Report not found.")
    return ok({"deleted": report_id})
