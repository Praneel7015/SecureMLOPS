from __future__ import annotations

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from drift.baseline_manager import build_baseline, load_baseline
from drift.detector import analyze_drift, score_drift
from drift.embedding_extractor import extract_embedding


class DummyEfficientNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Identity()
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))

    def forward(self, x):
        return x


def _build_loader(samples: int = 6) -> DataLoader:
    images = torch.rand(samples, 3, 4, 4)
    labels = torch.zeros(samples, dtype=torch.long)
    dataset = TensorDataset(images, labels)
    return DataLoader(dataset, batch_size=2)


def _build_empty_loader() -> DataLoader:
    dataset = TensorDataset(torch.empty((0, 3, 4, 4)), torch.empty((0,), dtype=torch.long))
    return DataLoader(dataset, batch_size=2)


def test_extract_embedding_shape():
    model = DummyEfficientNet()
    input_tensor = torch.rand(1, 3, 4, 4)
    embedding = extract_embedding(model, "efficientnet-b0", input_tensor, torch.device("cpu"))
    assert isinstance(embedding, list)
    assert len(embedding) == 3


def test_build_baseline():
    model = DummyEfficientNet()
    loader = _build_loader()
    baseline = build_baseline(model, "efficientnet-b0", loader, torch.device("cpu"), max_samples=4)
    assert baseline["sample_count"] == 4
    assert len(baseline["centroid"]) == 3
    assert baseline["distance_std"] >= 0


def test_build_baseline_empty_loader_raises():
    model = DummyEfficientNet()
    loader = _build_empty_loader()
    try:
        build_baseline(model, "efficientnet-b0", loader, torch.device("cpu"), max_samples=4)
    except ValueError as exc:
        assert "no embeddings" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for empty loader")


def test_analyze_drift_with_baseline():
    model = DummyEfficientNet()
    loader = _build_loader()
    baseline = build_baseline(model, "efficientnet-b0", loader, torch.device("cpu"), max_samples=4)
    input_tensor = torch.rand(1, 3, 4, 4)
    result = analyze_drift(model, "efficientnet-b0", input_tensor, baseline, torch.device("cpu"))
    assert result["score"] is not None
    assert result["severity"] in {"LOW", "MEDIUM", "HIGH"}


def test_analyze_drift_without_baseline():
    model = DummyEfficientNet()
    input_tensor = torch.rand(1, 3, 4, 4)
    result = analyze_drift(model, "efficientnet-b0", input_tensor, None, torch.device("cpu"))
    assert result["severity"] == "UNAVAILABLE"


def test_score_drift_thresholds():
    baseline = {
        "centroid": [0.0, 0.0, 0.0],
        "distance_mean": 0.1,
        "distance_std": 0.01,
        "thresholds": {"low": 0.4, "medium": 0.7},
    }
    high = score_drift([1.0, 1.0, 1.0], baseline)
    assert high["severity"] in {"MEDIUM", "HIGH"}


def test_load_baseline_invalid_json(tmp_path):
    path = tmp_path / "baseline.json"
    path.write_text("not-json", encoding="utf-8")
    assert load_baseline(path) is None
