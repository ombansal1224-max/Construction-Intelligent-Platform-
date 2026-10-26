"""Shared image-input widget used by the safety and crack tabs."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def image_input(label: str, key: str, sample_name: str) -> tuple[bytes | None, str]:
    """Uploader + optional bundled sample. Returns (bytes, source label)."""
    uploaded = st.file_uploader(label, type=["jpg", "jpeg", "png"], key=f"{key}_upload")
    sample_path = ASSETS / sample_name
    use_sample = False
    if sample_path.exists():
        use_sample = st.checkbox("Use the bundled sample image instead", key=f"{key}_sample", disabled=uploaded is not None,
                                 help="Try the platform instantly without your own photo.")
    if uploaded is not None:
        return uploaded.getvalue(), uploaded.name
    if use_sample:
        return sample_path.read_bytes(), f"sample: {sample_name}"
    return None, ""
