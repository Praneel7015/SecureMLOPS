from __future__ import annotations

from typing import Any

from drift.embedding_extractor import extract_embedding
from drift.metrics import cosine_distance, sigmoid, z_score


DEFAULT_THRESHOLDS = {
    "low": 0.55,
    "medium": 0.8,
}


def score_drift(embedding: list[float], baseline: dict[str, Any]) -> dict[str, Any]:
    """Score drift using cosine distance from the baseline centroid.

    Score is a sigmoid of the z-score to keep values in [0, 1].
    """
    centroid = baseline["centroid"]
    distance = cosine_distance(embedding, centroid)
    mean_dist = baseline.get("distance_mean", 0.0)
    std_dist = baseline.get("distance_std", 1e-6) or 1e-6
    z = z_score(distance, mean_dist, std_dist)
    score = sigmoid(z)

    thresholds = baseline.get("thresholds", DEFAULT_THRESHOLDS)
    if score >= thresholds.get("medium", 0.7):
        severity = "HIGH"
        status = "Distribution shift detected"
    elif score >= thresholds.get("low", 0.4):
        severity = "MEDIUM"
        status = "Moderate drift detected"
    else:
        severity = "LOW"
        status = "Drift within expected bounds"

    return {
        "score": round(float(score), 3),
        "severity": severity,
        "status": status,
        "distance": round(float(distance), 4),
        "z_score": round(float(z), 3),
    }


def project_embedding(embedding: list[float], baseline: dict[str, Any]) -> tuple[float, float] | None:
    components = baseline.get("pca_components")
    mean = baseline.get("pca_mean")
    if not components or not mean:
        return None
    if len(components) < 2:
        return None
    centered = [val - mean[idx] for idx, val in enumerate(embedding)]
    x = sum(centered[idx] * components[idx][0] for idx in range(len(centered)))
    y = sum(centered[idx] * components[idx][1] for idx in range(len(centered)))
    return float(x), float(y)


def analyze_drift(
    model: Any,
    model_type: str,
    input_tensor,
    baseline: dict[str, Any] | None,
    device,
) -> dict[str, Any]:
    if baseline is None:
        return {
            "score": None,
            "severity": "UNAVAILABLE",
            "status": "No drift baseline available",
            "distance": None,
            "z_score": None,
            "reference": None,
        }

    embedding = extract_embedding(model, model_type, input_tensor, device)
    scored = score_drift(embedding, baseline)
    projection = project_embedding(embedding, baseline)
    return {
        **scored,
        "reference": baseline.get("reference", "baseline"),
        "projection": projection,
    }
