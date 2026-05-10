from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from training.config import TRAINED_MODELS_DIR, SUPPORTED_MODELS
from training.registry import save_model_metadata


def _unique_filename(model_type: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_type = model_type.replace("/", "-")
    return f"{safe_type}_{ts}_{uuid.uuid4().hex[:8]}.pt"


def export_model(
    model: torch.nn.Module,
    model_type: str,
    class_names: list[str],
    image_size: int,
    metrics: dict[str, Any],
    owner: str | None = None,
) -> dict[str, Any]:
    TRAINED_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    filename = _unique_filename(model_type)
    model_path = TRAINED_MODELS_DIR / filename
    created_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "model_state_dict": model.state_dict(),
        "class_names": class_names,
        "model_type": model_type,
        "image_size": image_size,
        "num_classes": len(class_names),
        "metrics": metrics,
        "created_at": created_at,
    }

    torch.save(payload, model_path)

    metadata = {
        "model_type": model_type,
        "model_label": SUPPORTED_MODELS.get(model_type, {}).get("label", model_type),
        "class_names": class_names,
        "image_size": image_size,
        "num_classes": len(class_names),
        "metrics": metrics,
        "created_at": created_at,
        "file_name": filename,
        "file_path": str(model_path),
        "owner": owner,
    }

    model_id = uuid.uuid4().hex
    saved = save_model_metadata(model_id, metadata)
    saved["model_id"] = model_id
    return saved
