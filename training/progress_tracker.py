from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from training.config import JOB_REGISTRY_PATH, ensure_training_dirs

_lock = threading.Lock()


def _load_jobs() -> dict:
    if not JOB_REGISTRY_PATH.exists():
        return {"jobs": {}}
    try:
        return json.loads(JOB_REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"jobs": {}}


def _write_jobs(payload: dict) -> None:
    tmp_path = JOB_REGISTRY_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(JOB_REGISTRY_PATH)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_jobs() -> list[dict[str, Any]]:
    ensure_training_dirs()
    with _lock:
        payload = _load_jobs()
    jobs = payload.get("jobs", {})
    return sorted(jobs.values(), key=lambda item: item.get("created_at", ""), reverse=True)


def get_job(job_id: str) -> dict[str, Any] | None:
    ensure_training_dirs()
    with _lock:
        payload = _load_jobs()
    return payload.get("jobs", {}).get(job_id)


def init_job(job_id: str, dataset_id: str, config: dict[str, Any]) -> dict[str, Any]:
    ensure_training_dirs()
    job = {
        "job_id": job_id,
        "dataset_id": dataset_id,
        "status": "queued",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "epochs": config.get("epochs"),
        "current_epoch": 0,
        "progress": 0.0,
        "metrics": {
            "train_loss": [],
            "val_loss": [],
            "train_accuracy": [],
            "val_accuracy": [],
            "precision": [],
            "recall": [],
            "f1": [],
            "epoch_durations": [],
            "confusion_matrix": [],
            "per_class_accuracy": {},
            "class_names": [],
        },
        "logs": [],
        "error": None,
        "model_id": None,
        "config": config,
    }

    with _lock:
        payload = _load_jobs()
        payload.setdefault("jobs", {})[job_id] = job
        _write_jobs(payload)

    return job


def update_job(job_id: str, **updates: Any) -> dict[str, Any] | None:
    ensure_training_dirs()
    with _lock:
        payload = _load_jobs()
        job = payload.get("jobs", {}).get(job_id)
        if not job:
            return None
        job.update(updates)
        job["updated_at"] = _now_iso()
        payload["jobs"][job_id] = job
        _write_jobs(payload)
    return job


def append_log(job_id: str, message: str) -> dict[str, Any] | None:
    ensure_training_dirs()
    with _lock:
        payload = _load_jobs()
        job = payload.get("jobs", {}).get(job_id)
        if not job:
            return None
        logs = job.get("logs", [])
        logs.append({"timestamp": _now_iso(), "message": message})
        job["logs"] = logs[-200:]
        job["updated_at"] = _now_iso()
        payload["jobs"][job_id] = job
        _write_jobs(payload)
    return job


def append_metrics(job_id: str, metrics_payload: dict[str, Any]) -> dict[str, Any] | None:
    ensure_training_dirs()
    with _lock:
        payload = _load_jobs()
        job = payload.get("jobs", {}).get(job_id)
        if not job:
            return None
        metrics = job.get("metrics", {})
        for key, value in metrics_payload.items():
            if key in {"confusion_matrix", "per_class_accuracy", "class_names"}:
                metrics[key] = value
            else:
                metrics.setdefault(key, []).append(value)
        job["metrics"] = metrics
        job["updated_at"] = _now_iso()
        payload["jobs"][job_id] = job
        _write_jobs(payload)
    return job


def reconcile_incomplete_jobs() -> None:
    """Mark queued/running jobs as failed after a server restart."""
    ensure_training_dirs()
    with _lock:
        payload = _load_jobs()
        jobs = payload.get("jobs", {})
        for job_id, job in jobs.items():
            if job.get("status") in {"queued", "running"}:
                job["status"] = "failed"
                job["error"] = "Training interrupted by server restart."
                job["updated_at"] = _now_iso()
        payload["jobs"] = jobs
        _write_jobs(payload)
