from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from drift.embedding_extractor import extract_embedding
from drift.metrics import cosine_distance
from training.config import DRIFT_BASELINE_DIR, ensure_training_dirs


def build_baseline(
    model: torch.nn.Module,
    model_type: str,
    dataloader: torch.utils.data.DataLoader,
    device: torch.device,
    max_samples: int = 500,
) -> dict[str, Any]:
    """Generate a lightweight embedding baseline (centroid + distance stats).

    Uses a small sample of embeddings to avoid slowing down training.
    """
    ensure_training_dirs()
    embeddings: list[list[float]] = []
    for batch in dataloader:
        images, _ = batch
        for image in images:
            emb = extract_embedding(model, model_type, image.unsqueeze(0), device)
            embeddings.append(emb)
            if len(embeddings) >= max_samples:
                break
        if len(embeddings) >= max_samples:
            break

    if not embeddings:
        raise ValueError("Unable to compute drift baseline: no embeddings collected.")

    dim = len(embeddings[0])
    centroid = [0.0] * dim
    for emb in embeddings:
        for idx, val in enumerate(emb):
            centroid[idx] += val
    centroid = [val / len(embeddings) for val in centroid]

    distances = [cosine_distance(emb, centroid) for emb in embeddings]
    mean_dist = sum(distances) / len(distances)
    variance = sum((d - mean_dist) ** 2 for d in distances) / len(distances)
    std_dist = variance ** 0.5

    pca_components = None
    pca_mean = None
    try:
        matrix = torch.tensor(embeddings, dtype=torch.float32)
        pca_mean = matrix.mean(dim=0, keepdim=True)
        centered = matrix - pca_mean
        if centered.shape[0] >= 2 and centered.shape[1] >= 2:
            _, _, v = torch.pca_lowrank(centered, q=2)
            pca_components = v[:, :2]
    except Exception:
        pca_components = None
        pca_mean = None

    return {
        "method": "cosine_centroid",
        "model_type": model_type,
        "embedding_dim": dim,
        "centroid": centroid,
        "distance_mean": mean_dist,
        "distance_std": std_dist,
        "sample_count": len(embeddings),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pca_components": pca_components.cpu().tolist() if pca_components is not None else None,
        "pca_mean": pca_mean.squeeze(0).cpu().tolist() if pca_mean is not None else None,
    }


def save_baseline(baseline: dict[str, Any], filename: str) -> Path:
    ensure_training_dirs()
    path = DRIFT_BASELINE_DIR / filename
    path.write_text(json.dumps(baseline, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_baseline(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
