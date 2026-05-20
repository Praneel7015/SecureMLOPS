from __future__ import annotations

from typing import Any

from telemetry.events import (
    EventSeverity,
    EventSource,
    EventType,
    emit_event,
    severity_from_drift,
)
from telemetry.queries import query_events


def record_event(event: dict[str, Any]) -> None:
    """Record a drift event through the centralized telemetry service."""
    severity = event.get("severity", "LOW")
    drift_score = event.get("score")
    status = event.get("status", "")

    if severity == "HIGH":
        event_type = EventType.DRIFT_THRESHOLD_EXCEEDED
        title = "Drift threshold exceeded"
    elif severity == "MEDIUM":
        event_type = EventType.DRIFT_HIGH_WARNING
        title = "High drift warning"
    else:
        event_type = EventType.DRIFT_RECORDED
        title = "Drift event recorded"

    metadata = {
        "drift_score": drift_score,
        "severity": severity,
        "status": status,
        "distance": event.get("distance"),
        "reference": event.get("reference"),
        "model_name": event.get("model_name"),
        "model_type": event.get("model_type"),
        "projection_x": event.get("projection_x"),
        "projection_y": event.get("projection_y"),
        "filename": event.get("filename"),
        "owner": event.get("owner"),
    }
    metadata = {k: v for k, v in metadata.items() if v is not None}

    emit_event(
        severity=severity_from_drift(severity),
        event_type=event_type,
        source=EventSource.DRIFT,
        title=title,
        description=status or title,
        metadata=metadata,
        owner=event.get("owner"),
    )


def list_events(limit: int = 50, owner: str | None = None) -> list[dict[str, Any]]:
    """List drift events from centralized telemetry (backward compatible shape)."""
    result = query_events(
        category="drift",
        owner=owner,
        page_size=limit,
        page=1,
    )
    events = []
    for event in result["events"]:
        meta = event.get("metadata") or {}
        events.append(
            {
                "timestamp": event["timestamp"],
                "score": meta.get("drift_score"),
                "severity": meta.get("severity") or event["severity"],
                "status": meta.get("status") or event["description"],
                "distance": meta.get("distance"),
                "reference": meta.get("reference"),
                "model_name": meta.get("model_name"),
                "model_type": meta.get("model_type"),
                "projection_x": meta.get("projection_x"),
                "projection_y": meta.get("projection_y"),
                "filename": meta.get("filename"),
                "owner": meta.get("owner"),
            }
        )
    return events


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
