from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from training.config import (
    DATASET_REGISTRY_PATH,
    MODEL_REGISTRY_PATH,
    ensure_training_dirs,
)

_registry_lock = threading.Lock()


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, payload: dict) -> None:
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def list_datasets(owner: str | None = None) -> list[dict[str, Any]]:
    ensure_training_dirs()
    with _registry_lock:
        payload = _load_json(DATASET_REGISTRY_PATH)
    datasets = payload.get("datasets", {})
    values = datasets.values()
    if owner:
        values = [item for item in values if item.get("owner") == owner]
    return sorted(values, key=lambda item: item.get("created_at", ""), reverse=True)


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    ensure_training_dirs()
    with _registry_lock:
        payload = _load_json(DATASET_REGISTRY_PATH)
    return payload.get("datasets", {}).get(dataset_id)


def save_dataset_metadata(dataset_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    ensure_training_dirs()
    now = datetime.now(timezone.utc).isoformat()
    record = {**metadata, "dataset_id": dataset_id, "created_at": metadata.get("created_at", now)}

    with _registry_lock:
        payload = _load_json(DATASET_REGISTRY_PATH)
        payload.setdefault("datasets", {})[dataset_id] = record
        _write_json(DATASET_REGISTRY_PATH, payload)

    return record


def list_models(owner: str | None = None) -> list[dict[str, Any]]:
    ensure_training_dirs()
    with _registry_lock:
        payload = _load_json(MODEL_REGISTRY_PATH)
    models = payload.get("models", {})
    values = models.values()
    if owner:
        values = [item for item in values if item.get("owner") == owner]
    return sorted(values, key=lambda item: item.get("created_at", ""), reverse=True)


def get_model(model_id: str) -> dict[str, Any] | None:
    ensure_training_dirs()
    with _registry_lock:
        payload = _load_json(MODEL_REGISTRY_PATH)
    return payload.get("models", {}).get(model_id)


def save_model_metadata(model_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    ensure_training_dirs()
    now = datetime.now(timezone.utc).isoformat()
    record = {**metadata, "model_id": model_id, "created_at": metadata.get("created_at", now)}

    with _registry_lock:
        payload = _load_json(MODEL_REGISTRY_PATH)
        payload.setdefault("models", {})[model_id] = record
        _write_json(MODEL_REGISTRY_PATH, payload)

    return record
