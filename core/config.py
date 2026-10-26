"""Central configuration and domain constants for the platform."""
from __future__ import annotations

import os

APP_NAME = "Multimodal Construction Intelligence Platform"
APP_VERSION = "1.0.0"

# ---------------------------------------------------------------- LLM settings
GEMINI_MODELS = (
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
)
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
REQUEST_TIMEOUT_S = 90

# -------------------------------------------------------------- Image settings
MAX_UPLOAD_MB = 10
MAX_IMAGE_DIM = 1600

# ----------------------------------------------------------- Safety vocabulary
SEVERITY_LEVELS = ("Low", "Medium", "High", "Critical")
SEVERITY_RANK = {name: i for i, name in enumerate(SEVERITY_LEVELS)}

PPE_STATUSES = ("Compliant", "Violation", "Not Visible")

# key, label, governing standards
PPE_ITEMS = (
    ("helmet", "Safety Helmet", "IS 2925 / OSHA 1926.100"),
    ("hi_vis_vest", "High-Visibility Vest", "IS 15298 / OSHA 1926.201"),
    ("safety_boots", "Steel-Toe Safety Boots", "IS 15298 Pt-2 / OSHA 1926.96"),
    ("safety_harness", "Full-Body Safety Harness", "IS 3521 / OSHA 1926.502"),
)

SAFETY_STATUSES = ("Compliant", "Needs Attention", "High Risk", "Critical")

# ------------------------------------------------------------ Crack vocabulary
DEFECT_TYPES = ("Hairline", "Settlement", "Structural Shear", "Thermal Expansion", "Spalling")
URGENCY_LEVELS = ("Routine Monitoring", "Within 30 Days", "Within 7 Days", "Immediate")

# ----------------------------------------------------------- Weather vocabulary
WEATHER_CONDITIONS = ("Normal", "High Wind", "Heavy Rain", "Extreme Heat")


def resolve_api_key(explicit: str | None = None) -> str:
    """Return the first available Gemini key: explicit arg > env vars > empty."""
    if explicit and explicit.strip():
        return explicit.strip()
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""
