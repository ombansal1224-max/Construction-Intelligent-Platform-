"""Thin, dependency-light Gemini REST client (text, vision and multi-turn chat)."""
from __future__ import annotations

import base64
import json
import re
import time
from typing import Any

import requests

from .config import GEMINI_BASE_URL, GEMINI_MODELS, REQUEST_TIMEOUT_S


class LLMError(RuntimeError):
    """Any failure talking to the model (network, auth, quota, malformed output)."""


def extract_json(text: str) -> dict:
    """Parse a JSON object out of model text, tolerating markdown fences and chatter."""
    cleaned = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.S)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        obj: Any = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("The model response did not contain a JSON object.")
        try:
            obj = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError("The model returned malformed JSON.") from exc
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        obj = obj[0]
    if not isinstance(obj, dict):
        raise LLMError("The model JSON was not an object.")
    return obj


class GeminiClient:
    """Calls the Gemini `generateContent` REST endpoint with model fallback and retry."""

    def __init__(self, api_key: str | None, models: tuple[str, ...] | list[str] = GEMINI_MODELS,
                 timeout: int = REQUEST_TIMEOUT_S, session: requests.Session | None = None):
        self.api_key = (api_key or "").strip()
        self.models = tuple(models)
        self.timeout = timeout
        self.session = session or requests.Session()
        self.last_model = self.models[0] if self.models else "gemini"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    # ---------------------------------------------------------------- internals
    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

    @staticmethod
    def _error_message(resp: requests.Response) -> str:
        try:
            return str(resp.json().get("error", {}).get("message", resp.text))[:300]
        except ValueError:
            return resp.text[:300]

    def _post(self, payload: dict) -> dict:
        if not self.enabled:
            raise LLMError("No Gemini API key configured.")
        last: LLMError | None = None
        for model in self.models:
            url = f"{GEMINI_BASE_URL}/models/{model}:generateContent"
            for attempt in range(2):
                try:
                    resp = self.session.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
                except requests.RequestException as exc:
                    last = LLMError(f"Network error contacting Gemini: {exc}")
                    time.sleep(1)
                    continue
                if resp.status_code == 200:
                    self.last_model = model
                    return resp.json()
                msg = self._error_message(resp)
                if resp.status_code in (401, 403) or (resp.status_code == 400 and "api key" in msg.lower()):
                    raise LLMError("Gemini rejected the API key (invalid or lacks access).")
                if resp.status_code in (429, 500, 503) and attempt == 0:
                    time.sleep(1.5)
                    continue
                last = LLMError(f"{model}: HTTP {resp.status_code} - {msg}")
                break
        raise last or LLMError("Gemini request failed.")

    @staticmethod
    def _text(data: dict) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            reason = (data.get("promptFeedback") or {}).get("blockReason", "no candidates returned")
            raise LLMError(f"Gemini returned no content ({reason}).")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text.strip():
            raise LLMError("Gemini returned an empty response.")
        return text

    def get_available_models(self) -> list[str]:
        """Fetch models dynamically supported for generateContent by the provided API key."""
        if not self.enabled:
            return list(self.models)
        try:
            resp = self.session.get(f"{GEMINI_BASE_URL}/models?pageSize=100", headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("models", [])
                supported = [
                    m["name"].replace("models/", "")
                    for m in data
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
                if supported:
                    return supported
        except Exception:
            pass
        return list(self.models)

    def validate_key(self) -> tuple[bool, str]:
        if not self.enabled:
            return False, "No key entered."
        try:
            resp = self.session.get(f"{GEMINI_BASE_URL}/models?pageSize=10", headers=self._headers(), timeout=15)
        except requests.RequestException as exc:
            return False, f"Network error: {exc}"
        if resp.status_code == 200:
            models = self.get_available_models()
            return True, f"API key verified. Available models: {', '.join(models[:4])}"
        return False, self._error_message(resp)

    def generate_json(self, prompt: str, image_bytes: bytes | None = None, mime_type: str = "image/jpeg",
                      temperature: float = 0.2) -> dict:
        parts: list[dict] = [{"text": prompt}]
        if image_bytes:
            parts.append({"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}})
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"},
        }
        return extract_json(self._text(self._post(payload)))

    def chat(self, messages: list[dict[str, str]], system: str, temperature: float = 0.5) -> str:
        contents = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in messages
            if m.get("content")
        ]
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 1400},
        }
        return self._text(self._post(payload)).strip()
