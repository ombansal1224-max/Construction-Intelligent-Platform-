"""File-based JSON report store (the 'Data Storage' box of the architecture) - no external DB needed."""
from __future__ import annotations

import json
import re
import threading
import uuid
from pathlib import Path

from .formatting import utc_now_iso

_ID_RE = re.compile(r"^[a-f0-9]{32}$")


class ReportStore:
    def __init__(self, directory: str | Path = "data/reports"):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def save(self, kind: str, payload: dict) -> str:
        report_id = uuid.uuid4().hex
        record = {"id": report_id, "kind": kind, "saved_at": utc_now_iso(), "payload": payload}
        with self._lock:
            (self.dir / f"{report_id}.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
        return report_id

    def get(self, report_id: str) -> dict | None:
        if not _ID_RE.match(report_id):  # blocks path traversal
            return None
        path = self.dir / f"{report_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self, kind: str | None = None, limit: int = 50) -> list[dict]:
        items = []
        for path in sorted(self.dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if kind and rec.get("kind") != kind:
                continue
            items.append({"id": rec["id"], "kind": rec["kind"], "saved_at": rec["saved_at"]})
            if len(items) >= limit:
                break
        return items

    def delete(self, report_id: str) -> bool:
        if not _ID_RE.match(report_id):
            return False
        path = self.dir / f"{report_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
