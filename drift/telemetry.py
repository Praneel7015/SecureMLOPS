from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from training.config import DRIFT_EVENTS_PATH, ensure_training_dirs


def _load_events() -> list[dict[str, Any]]:
    if not DRIFT_EVENTS_PATH.exists():
        return []
    try:
        payload = json.loads(DRIFT_EVENTS_PATH.read_text(encoding="utf-8"))
        return payload.get("events", [])
    except Exception:
        return []


def _write_events(events: list[dict[str, Any]]) -> None:
    payload = {"events": events[-200:]}
    DRIFT_EVENTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def record_event(event: dict[str, Any]) -> None:
    ensure_training_dirs()
    events = _load_events()
    events.append({
        **event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _write_events(events)


def list_events(limit: int = 50, owner: str | None = None) -> list[dict[str, Any]]:
    ensure_training_dirs()
    events = _load_events()
    if owner:
        events = [event for event in events if event.get("owner") == owner]
    return list(reversed(events[-limit:]))


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "total": 0,
            "severity_counts": {"LOW": 0, "MEDIUM": 0, "HIGH": 0},
            "avg_score": 0.0,
            "latest": None,
        }
    scores = [event.get("score", 0.0) for event in events if event.get("score") is not None]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for event in events:
        severity = event.get("severity")
        if severity in severity_counts:
            severity_counts[severity] += 1
    return {
        "total": len(events),
        "severity_counts": severity_counts,
        "avg_score": round(avg_score, 3),
        "latest": events[0],
    }
