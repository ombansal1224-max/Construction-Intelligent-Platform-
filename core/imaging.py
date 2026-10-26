"""Image validation, preprocessing and lightweight computer-vision heuristics (Pillow + NumPy)."""
from __future__ import annotations

import hashlib
import io
import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

from .config import MAX_IMAGE_DIM, MAX_UPLOAD_MB


class ImageError(ValueError):
    """Raised for unusable uploads (empty, too large, corrupt, unsupported)."""


@dataclass
class PreparedImage:
    image: Image.Image
    jpeg_bytes: bytes
    mime_type: str
    width: int
    height: int
    signature: str


def prepare_image(data: bytes) -> PreparedImage:
    """Validate, orient, flatten to RGB, downscale and re-encode an upload as JPEG."""
    if not data:
        raise ImageError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ImageError(f"Image exceeds the {MAX_UPLOAD_MB} MB upload limit.")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageError("Unsupported or corrupt image. Please upload a valid JPG or PNG.") from exc

    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88, optimize=True)
    signature = hashlib.sha256(img.resize((32, 32)).tobytes()).hexdigest()
    return PreparedImage(img, buf.getvalue(), "image/jpeg", img.width, img.height, signature)


def visual_features(img: Image.Image) -> dict[str, float]:
    """Colour / luminance statistics used by the offline demo engine."""
    small = img.copy()
    small.thumbnail((256, 256))
    hsv = np.asarray(small.convert("HSV"), dtype=np.float32) / 255.0
    h, s, v = hsv[..., 0] * 360.0, hsv[..., 1], hsv[..., 2]
    hivis = (h >= 15) & (h <= 75) & (s > 0.6) & (v > 0.65)  # safety orange / lime-yellow
    lum = np.asarray(small.convert("L"), dtype=np.float32) / 255.0
    return {
        "hivis_ratio": float(hivis.mean()),
        "brightness": float(lum.mean()),
        "contrast": float(lum.std()),
        "dark_ratio": float((lum < 0.25).mean()),
    }


def crack_analysis(img: Image.Image) -> tuple[Image.Image, dict[str, float | str]]:
    """Locate thin dark linear features and return (overlay image, metrics).

    A crack is a thin region darker than its local neighbourhood, so we subtract a blurred
    background from a lightly smoothed image and threshold the residual.
    """
    work = img.copy()
    work.thumbnail((640, 640))
    gray = ImageOps.autocontrast(work.convert("L"))
    fine = np.asarray(gray.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.0
    background = np.asarray(gray.filter(ImageFilter.GaussianBlur(8)), dtype=np.float32) / 255.0
    mask = (background - fine) > 0.10

    crack_ratio = float(mask.mean())
    ys, xs = np.nonzero(mask)
    orientation, elongation = "Unspecified", 1.0
    if len(xs) > 30:
        cov = np.cov(np.vstack([xs, ys]))
        evals, _ = np.linalg.eigh(cov)
        elongation = float(math.sqrt(max(evals[1], 1e-6) / max(evals[0], 1e-6)))
        angle = abs(math.degrees(0.5 * math.atan2(2 * cov[0, 1], cov[0, 0] - cov[1, 1])))
        if angle < 20 or angle > 160:
            orientation = "Horizontal"
        elif 70 < angle < 110:
            orientation = "Vertical"
        else:
            orientation = "Diagonal"

    mask_img = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
    red = Image.new("RGB", work.size, (255, 45, 70))
    overlay = Image.composite(red, work, mask_img)
    lum = np.asarray(gray, dtype=np.float32) / 255.0
    return overlay, {
        "crack_ratio": crack_ratio,
        "orientation": orientation,
        "elongation": elongation,
        "dark_ratio": float((lum < 0.25).mean()),
        "brightness": float(lum.mean()),
    }
