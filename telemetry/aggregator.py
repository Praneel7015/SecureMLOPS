"""Dashboard aggregation queries over persisted security events."""

from __future__ import annotations

from typing import Any

from telemetry.event_store import execute_scalar, fetch_events_raw
from telemetry.queries import CATEGORY_EVENT_TYPES, SECURITY_EVENT_TYPES
from training.progress_tracker import list_jobs
from training.registry import list_models

from Detection.poisoning import detector_runtime_status


def _count_by_severity(owner: str | None = None) -> dict[str, int]:
    owner_clause = ""
    params: tuple[Any, ...] = ()
    if owner:
        owner_clause = "WHERE json_extract(metadata_json, '$.owner') = ?"
        params = (owner,)

    rows_query = f"""
        SELECT severity, COUNT(*) AS cnt
        FROM security_events
        {owner_clause}
        GROUP BY severity
    """
    # Use fetch via raw connection pattern
    from telemetry.event_store import _connect, _lock, init_event_store

    init_event_store()
    counts = {"INFO": 0, "WARNING": 0, "HIGH": 0, "CRITICAL": 0}
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(rows_query, params).fetchall()
            for row in rows:
                sev = row["severity"]
                if sev in counts:
                    counts[sev] = int(row["cnt"])
        finally:
            conn.close()
    return counts


def _count_event_types(event_types: tuple[str, ...], owner: str | None = None) -> int:
    placeholders = ", ".join("?" for _ in event_types)
    clauses = [f"event_type IN ({placeholders})"]
    params: list[Any] = list(event_types)
    if owner:
        clauses.append("json_extract(metadata_json, '$.owner') = ?")
        params.append(owner)
    where = "WHERE " + " AND ".join(clauses)
    return int(execute_scalar(f"SELECT COUNT(*) FROM security_events {where}", tuple(params)) or 0)


def _sum_poisoned_samples(owner: str | None = None) -> int:
    owner_clause = ""
    params: tuple[Any, ...] = ()
    if owner:
        owner_clause = "AND json_extract(metadata_json, '$.owner') = ?"
        params = (owner,)
    value = execute_scalar(
        f"""
        SELECT COALESCE(SUM(CAST(json_extract(metadata_json, '$.suspicious_count') AS INTEGER)), 0)
        FROM security_events
        WHERE event_type = 'poisoning.suspicious_dataset'
          {owner_clause}
        """,
        params,
    )
    return int(value or 0)


def _avg_drift_score(owner: str | None = None) -> float:
    owner_clause = ""
    params: tuple[Any, ...] = ()
    if owner:
        owner_clause = "AND json_extract(metadata_json, '$.owner') = ?"
        params = (owner,)
    value = execute_scalar(
        f"""
        SELECT AVG(CAST(json_extract(metadata_json, '$.drift_score') AS REAL))
        FROM security_events
        WHERE event_type LIKE 'drift.%'
          AND json_extract(metadata_json, '$.drift_score') IS NOT NULL
          {owner_clause}
        """,
        params,
    )
    return round(float(value or 0.0), 3)


def _last_timestamp(event_types: tuple[str, ...] | None = None, owner: str | None = None) -> str | None:
    clauses: list[str] = []
    params: list[Any] = []
    if event_types:
        placeholders = ", ".join("?" for _ in event_types)
        clauses.append(f"event_type IN ({placeholders})")
        params.extend(event_types)
    if owner:
        clauses.append("json_extract(metadata_json, '$.owner') = ?")
        params.append(owner)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    return execute_scalar(
        f"SELECT timestamp FROM security_events {where} ORDER BY timestamp DESC LIMIT 1",
        tuple(params),
    )


def get_recent_activity(limit: int = 20, owner: str | None = None) -> list[dict[str, Any]]:
    owner_clause = ""
    params: tuple[Any, ...] = ()
    if owner:
        owner_clause = "WHERE json_extract(metadata_json, '$.owner') = ?"
        params = (owner,)
    return fetch_events_raw(where_clause=owner_clause, params=params, limit=limit, offset=0)


def get_security_event_summary(limit: int = 10, owner: str | None = None) -> list[dict[str, Any]]:
    placeholders = ", ".join("?" for _ in SECURITY_EVENT_TYPES)
    clauses = [f"event_type IN ({placeholders})"]
    params: list[Any] = list(SECURITY_EVENT_TYPES)
    if owner:
        clauses.append("json_extract(metadata_json, '$.owner') = ?")
        params.append(owner)
    where = "WHERE " + " AND ".join(clauses)
    return fetch_events_raw(where_clause=where, params=tuple(params), limit=limit, offset=0)


def get_system_status(owner: str | None = None) -> dict[str, Any]:
    active_jobs = [j for j in list_jobs(owner=owner) if j.get("status") in {"queued", "running"}]
    return {
        "monitoring_status": "active",
        "drift_monitoring_status": "active",
        "security_engine_status": "active",
        "active_training_jobs": len(active_jobs),
        "last_inference_at": _last_timestamp(CATEGORY_EVENT_TYPES["inference"], owner),
        "last_drift_event_at": _last_timestamp(CATEGORY_EVENT_TYPES["drift"], owner),
        "last_poisoning_event_at": _last_timestamp(CATEGORY_EVENT_TYPES["poisoning"], owner),
        "last_security_event_at": _last_timestamp(SECURITY_EVENT_TYPES, owner),
        "poisoning_detector_status": "active" if detector_runtime_status().get("available") else "unavailable",
    }


def get_dashboard_summary(owner: str | None = None) -> dict[str, Any]:
    jobs = list_jobs(owner=owner)
    models = list_models(owner=owner)
    completed_jobs = [j for j in jobs if j.get("status") == "completed"]
    active_jobs = [j for j in jobs if j.get("status") in {"queued", "running"}]

    last_training_accuracy = None
    if completed_jobs:
        metrics = (completed_jobs[0].get("metrics") or {})
        last_training_accuracy = metrics.get("final_val_accuracy")

    return {
        "metrics": {
            "total_inferences": _count_event_types(CATEGORY_EVENT_TYPES["inference"], owner),
            "high_risk_events": _count_by_severity(owner).get("HIGH", 0)
            + _count_by_severity(owner).get("CRITICAL", 0),
            "drift_alerts": _count_event_types(
                (
                    "drift.threshold_exceeded",
                    "drift.high_warning",
                    "drift.severity_escalation",
                ),
                owner,
            ),
            "models_registered": len(models),
            "active_training_jobs": len(active_jobs),
            "last_training_accuracy": last_training_accuracy,
            "average_drift_score": _avg_drift_score(owner),
            "poisoning_alerts": _count_event_types(
                (
                    "poisoning.suspicious_dataset",
                    "poisoning.detected",
                    "poisoning.high_risk",
                ),
                owner,
            ),
            "poisoning_high_risk_events": _count_event_types(("poisoning.high_risk",), owner),
            "poisoning_scan_activity": _count_event_types(
                ("poisoning.dataset_scan_completed", "poisoning.dataset_scan_started"),
                owner,
            ),
            "suspicious_dataset_uploads": _count_event_types(("poisoning.suspicious_dataset",), owner),
            "high_risk_training_attempts": _count_event_types(
                ("poisoning.training_blocked", "poisoning.training_override"),
                owner,
            ),
            "poisoned_sample_count": _sum_poisoned_samples(owner),
            "poisoning_detector_available": detector_runtime_status().get("available", False),
            "severity_counts": _count_by_severity(owner),
            "total_events": sum(_count_by_severity(owner).values()),
        },
        "recent_training": _format_training_jobs(jobs[:5]),
        "recent_models": _format_models(models[:5]),
        "system_status": get_system_status(owner),
    }


def _format_training_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    formatted = []
    for job in jobs:
        metrics = job.get("metrics") or {}
        config = job.get("config") or {}
        formatted.append(
            {
                "job_id": job.get("job_id"),
                "dataset_id": job.get("dataset_id"),
                "status": job.get("status"),
                "model_type": config.get("model_type"),
                "epochs": job.get("epochs") or config.get("epochs"),
                "current_epoch": job.get("current_epoch"),
                "validation_accuracy": metrics.get("final_val_accuracy"),
                "created_at": job.get("created_at"),
                "updated_at": job.get("updated_at"),
                "model_id": job.get("model_id"),
            }
        )
    return formatted


def _format_models(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "model_id": model.get("model_id"),
            "model_type": model.get("model_type"),
            "model_label": model.get("model_label"),
            "class_names": model.get("class_names") or [],
            "num_classes": len(model.get("class_names") or []),
            "created_at": model.get("created_at"),
            "file_name": model.get("file_name"),
            "inference_ready": bool(model.get("file_path")),
            "metrics": model.get("metrics"),
        }
        for model in models
    ]
