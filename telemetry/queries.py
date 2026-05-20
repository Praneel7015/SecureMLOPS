"""Filtered, paginated queries for security events."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from telemetry.event_store import count_events_raw, fetch_event_by_id, fetch_events_raw

# Event type groups for category filters
CATEGORY_EVENT_TYPES = {
    "inference": (
        "inference.completed",
        "inference.high_risk",
        "inference.blocked",
        "inference.rate_limited",
    ),
    "drift": (
        "drift.threshold_exceeded",
        "drift.high_warning",
        "drift.severity_escalation",
        "drift.baseline_load_failure",
        "drift.recorded",
    ),
    "training": (
        "training.started",
        "training.completed",
        "training.failed",
        "training.dataset_validation_warning",
        "training.dataset_uploaded",
        "training.dataset_validation_failed",
    ),
    "adversarial": (
        "adversarial.suspicion",
        "adversarial.blocked",
        "adversarial.allowed",
        "adversarial.escalation",
    ),
    "integrity": (
        "integrity.validation_success",
        "integrity.validation_failure",
        "integrity.architecture_mismatch",
        "integrity.malformed_checkpoint",
        "integrity.reconstruction_failure",
        "integrity.unsupported_architecture",
    ),
    "validation": (
        "validation.corrupted_image",
        "validation.unsupported_file",
        "validation.image_failed",
    ),
    "system": (
        "system.backend_failure",
        "system.telemetry_failure",
        "system.detector_exception",
        "system.db_failure",
        "system.monitoring_failure",
    ),
}

SECURITY_EVENT_TYPES = (
    *CATEGORY_EVENT_TYPES["adversarial"],
    *CATEGORY_EVENT_TYPES["integrity"],
    "inference.high_risk",
    "inference.blocked",
    "validation.corrupted_image",
    "validation.unsupported_file",
    "validation.image_failed",
    "training.dataset_validation_failed",
    "drift.threshold_exceeded",
    "drift.high_warning",
    "drift.severity_escalation",
)


def _build_filters(
    *,
    severity: str | None = None,
    event_type: str | None = None,
    source: str | None = None,
    model: str | None = None,
    owner: str | None = None,
    category: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    event_types: list[str] | None = None,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if severity:
        clauses.append("severity = ?")
        params.append(severity.upper())

    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)

    if source:
        clauses.append("source = ?")
        params.append(source)

    if category and category in CATEGORY_EVENT_TYPES:
        placeholders = ", ".join("?" for _ in CATEGORY_EVENT_TYPES[category])
        clauses.append(f"event_type IN ({placeholders})")
        params.extend(CATEGORY_EVENT_TYPES[category])

    if event_types:
        placeholders = ", ".join("?" for _ in event_types)
        clauses.append(f"event_type IN ({placeholders})")
        params.extend(event_types)

    if model:
        clauses.append(
            "(json_extract(metadata_json, '$.model_name') LIKE ? OR json_extract(metadata_json, '$.model_type') LIKE ?)"
        )
        pattern = f"%{model}%"
        params.extend([pattern, pattern])

    if owner:
        clauses.append("json_extract(metadata_json, '$.owner') = ?")
        params.append(owner)

    if search:
        pattern = f"%{search}%"
        clauses.append(
            "(title LIKE ? OR description LIKE ? OR event_type LIKE ? OR metadata_json LIKE ?)"
        )
        params.extend([pattern, pattern, pattern, pattern])

    if date_from:
        clauses.append("timestamp >= ?")
        params.append(date_from)

    if date_to:
        clauses.append("timestamp <= ?")
        params.append(date_to)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def query_events(
    *,
    severity: str | None = None,
    event_type: str | None = None,
    source: str | None = None,
    model: str | None = None,
    owner: str | None = None,
    category: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    event_types: list[str] | None = None,
    page: int = 1,
    page_size: int = 50,
    order: str = "DESC",
) -> dict[str, Any]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    where, params = _build_filters(
        severity=severity,
        event_type=event_type,
        source=source,
        model=model,
        owner=owner,
        category=category,
        search=search,
        date_from=date_from,
        date_to=date_to,
        event_types=event_types,
    )

    total = count_events_raw(where, tuple(params))
    events = fetch_events_raw(
        where_clause=where,
        params=tuple(params),
        order=order,
        limit=page_size,
        offset=offset,
    )

    return {
        "events": events,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "has_more": offset + len(events) < total,
        },
    }


def get_event_by_id(event_id: str) -> dict[str, Any] | None:
    return fetch_event_by_id(event_id)


def export_events(
    *,
    format: str = "json",
    owner: str | None = None,
    **filters: Any,
) -> tuple[str, str, str]:
    """Return (content, content_type, filename) for export."""
    where, params = _build_filters(owner=owner, **filters)
    events = fetch_events_raw(where_clause=where, params=tuple(params), order="DESC", limit=5000)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["id", "timestamp", "severity", "event_type", "source", "title", "description", "metadata_json"]
        )
        for event in events:
            writer.writerow(
                [
                    event["id"],
                    event["timestamp"],
                    event["severity"],
                    event["event_type"],
                    event["source"],
                    event["title"],
                    event["description"],
                    json.dumps(event.get("metadata") or {}),
                ]
            )
        return buffer.getvalue(), "text/csv", f"security_events_{timestamp}.csv"

    content = json.dumps({"events": events, "exported_at": timestamp}, indent=2)
    return content, "application/json", f"security_events_{timestamp}.json"
