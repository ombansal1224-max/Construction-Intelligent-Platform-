"""Small formatting helpers (INR, clamping, timestamps)."""
from __future__ import annotations

from datetime import datetime, timezone


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def indian_grouping(number: float) -> str:
    """Format an integer with Indian digit grouping (12,34,567)."""
    n = int(round(number))
    sign = "-" if n < 0 else ""
    digits = str(abs(n))
    if len(digits) <= 3:
        return sign + digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return sign + ",".join(parts + [tail])


def format_inr(value: float) -> str:
    """Render a rupee amount as Crores / Lakhs / plain rupees."""
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1e7:
        return f"{sign}₹{v / 1e7:,.2f} Cr"
    if v >= 1e5:
        return f"{sign}₹{v / 1e5:,.2f} L"
    return f"{sign}₹{indian_grouping(v)}"
