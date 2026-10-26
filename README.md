# 🏗️ Multimodal Construction Intelligence Platform

AI-powered decision support for construction: **PPE safety audits**, **concrete crack diagnostics**, **cost & real-estate valuation in INR**, and **weather-aware daily protocols** — with an engineering chatbot. Skill Wallet Capstone Project 1.

Two interchangeable front-ends share one tested Python core:

| Delivery | Stack | Use it for |
|---|---|---|
| **Streamlit app** (`app.py`) | Streamlit + Pillow + Gemini REST | 1-click Streamlit Community Cloud deployment |
| **React + FastAPI** (`frontend/`, `backend/`) | React 18 (Vite) + FastAPI | Full-stack architecture from the project diagram |

## Architecture

```
React / Streamlit ──► User Input (text · images · project data)
                          │
                          ▼
              FastAPI backend  ⇄  Data storage (JSON files, no DB)
                          │
                          ▼
        Multimodal AI (Gemini LLM + Vision)  ──►  strict JSON data contracts
              │        │         │         │         │
           Safety   Cracks   Valuation  Planning  Site assistant
                                                  & weather advisory
```

```
core/          UI-agnostic engine (safety, cracks, valuation, weather, assistant, llm, schemas, storage)
ui/            Streamlit tabs, sidebar, theme
backend/       FastAPI app  (response envelope: {status, data, meta})
frontend/      React + Vite client
assets/        Bundled sample site & crack photos
tests/         50 tests: core, API contracts, Streamlit UI flows
```

## Features

1. **Site Safety & PPE Audit** — helmet / hi-vis vest / steel-toe boots / harness checklist, hazards with severity (Low → Critical) and remedies, safety score 0-100, downloadable JSON.
2. **Crack Diagnostics** — Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling; width (mm), severity score, root causes, repair plan (epoxy injection, re-grouting…), urgency, edge-detection overlay.
3. **Planning & Valuation** — structure type, sq ft, Tier 1/2/3 city, finish grade, completion slider → budget, capex, current & on-completion valuation (₹ Lakhs/Crores), steel & cement consumption, milestone progress, schedule, plus a **Pollinations / Flux 3D concept render** prompt generator.
4. **Site Assistant & Weather** — High Wind / Heavy Rain / Extreme Heat / Normal protocols (crane suspension, electrical hazard mitigation, curing), live weather auto-detect via Open-Meteo, context-aware multi-turn chatbot.
5. **Project Dossier** (Streamlit) — one consolidated JSON export.

### Demo mode & robustness
No API key? Everything still works through a deterministic offline engine (image-seeded heuristics, knowledge-base chatbot). With a key, Gemini is called via REST with model fallback (`gemini-2.5-flash → 2.0-flash → 1.5-flash`), retry, and automatic fallback to demo mode on errors. All model output is coerced into strict Pydantic contracts with guardrails (e.g. a *Critical* hazard caps the safety score; crack severity is floored by measured width).

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py                     # Streamlit app → http://localhost:8501
```

Optional Gemini key: paste it in the sidebar, or set `GEMINI_API_KEY` (or `.streamlit/secrets.toml`: `GEMINI_API_KEY = "..."`).

### React + FastAPI

```bash
pip install -r requirements-api.txt
uvicorn backend.main:app --reload --port 8000        # API docs: http://localhost:8000/docs

cd frontend && npm install && npm run dev            # UI → http://localhost:5173
```

The React app sends the key as an `X-Gemini-Key` header (kept in `sessionStorage`, never persisted server-side).

### API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/safety/analyze` | multipart image → `SafetyReport` |
| POST | `/api/cracks/analyze` | multipart image → `CrackReport` + overlay |
| POST | `/api/valuation` | JSON inputs → budget, valuation, materials, milestones |
| POST | `/api/render-prompt` | 3D concept prompt + Pollinations URL |
| GET | `/api/weather/advisory/{condition}` · `/api/weather/live?city=` | protocols · live weather |
| POST | `/api/chat` | multi-turn assistant |
| GET/DELETE | `/api/reports[/{id}]` | stored reports |

## Testing

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Deployment

- **Streamlit Community Cloud**: push to GitHub → *New app* → main file `app.py` → (optional) add `GEMINI_API_KEY` under *Secrets*.
- **Docker / AWS (EC2, App Runner, ECS)**: `docker build -t cip . && docker run -p 8501:8501 cip`. For the API run the same image with `uvicorn backend.main:app --host 0.0.0.0 --port 8000`; host `frontend/dist` (`npm run build`) on S3 + CloudFront and set `CORS_ORIGINS`.

## Hardware / software
i5 8th-gen / Ryzen 5, 8 GB RAM (16 GB recommended), 256 GB SSD, 10+ Mbps. Windows 10/11, macOS or Ubuntu 20.04+; Python 3.9+; Node 18+ for the React client; modern Chrome / Firefox / Edge; Git; AWS CLI for cloud deployment.

## Disclaimer
Outputs are AI-assisted estimates for decision support. Safety findings, structural diagnoses and valuations must be verified by a qualified safety officer, structural engineer or registered valuer.
