from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image

import Detection.poisoning as poisoning

_ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "Detection" / "security_models"
_VICTIM_PATH = _ARTIFACTS_DIR / "attacked_model_multi_attack.pth"
_MLP_PATH = _ARTIFACTS_DIR / "detector_mlp.pkl"
_SCALER_PATH = _ARTIFACTS_DIR / "scaler.pkl"
_CONFIG_PATH = _ARTIFACTS_DIR / "detector_config.json"

requires_poisoning_artifacts = pytest.mark.skipif(
    not all(path.is_file() for path in (_VICTIM_PATH, _MLP_PATH, _SCALER_PATH, _CONFIG_PATH)),
    reason="Poisoning detector artifacts missing in Detection/security_models",
)


@pytest.fixture(autouse=True)
def reset_poisoning_state() -> None:
    poisoning.reset_poisoning_cache()
    yield
    poisoning.reset_poisoning_cache()


def test_config_loads_expected_fields() -> None:
    config = poisoning._load_config()
    assert config is not None
    assert config["detector_type"] == "MLP"
    assert config["embedding_dimension_before_augmentation"] == 896
    assert config["embedding_dimension_after_augmentation"] == 899
    assert config["threshold"] == 0.67


@requires_poisoning_artifacts
def test_victim_model_loads() -> None:
    model = poisoning._load_victim_model(torch.device("cpu"))
    assert model is not None
    assert poisoning._feature_extractor is not None


@requires_poisoning_artifacts
def test_mlp_and_scaler_load() -> None:
    detector = poisoning._load_mlp_detector()
    scaler = poisoning._load_scaler()
    assert detector is not None
    assert scaler is not None
    assert scaler.n_features_in_ == 896
    assert detector.n_features_in_ == 899


@requires_poisoning_artifacts
def test_multilayer_embedding_dimensions() -> None:
    device = torch.device("cpu")
    poisoning._load_victim_model(device)
    batch = torch.rand(2, 3, 128, 128)
    logits, embeddings = poisoning._extract_batch_features(batch, device, poisoning._load_config())
    assert logits.shape[0] == 2
    assert embeddings.shape == (2, 896)


@requires_poisoning_artifacts
def test_feature_augmentation_dimensions() -> None:
    device = torch.device("cpu")
    batch = torch.rand(3, 3, 128, 128)
    logits, embeddings = poisoning._extract_batch_features(batch, device, poisoning._load_config())
    scaler = poisoning._load_scaler()
    scaled = scaler.transform(embeddings.cpu().numpy())
    augmented = poisoning._augment_features(torch.from_numpy(scaled).to(device), logits)
    assert augmented.shape == (3, 899)


@requires_poisoning_artifacts
def test_batch_inference_runs() -> None:
    tensors = [torch.rand(3, 128, 128) for _ in range(5)]
    results = poisoning.evaluate_poisoning_batch(tensors, model_type="resnet18")
    assert len(results) == 5
    for item in results:
        assert "poisoning_probability" in item
        assert item["poisoning_available"] is True
        assert item["poisoning_severity"] in {"LOW", "MEDIUM", "HIGH"}


@requires_poisoning_artifacts
def test_single_image_inference_from_path(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (160, 120), color=(120, 80, 40)).save(image_path)
    result = poisoning.evaluate_poisoning(image_path, model_type="resnet18")
    assert result["poisoning_available"] is True
    assert isinstance(result["poisoning_probability"], float)


def test_unsupported_architecture_is_unavailable() -> None:
    result = poisoning.evaluate_poisoning(torch.rand(3, 128, 128), model_type="efficientnet-b0")
    assert result["poisoning_available"] is False
    assert "ResNet18" in result["poisoning_status"]


@requires_poisoning_artifacts
def test_artifacts_load_once() -> None:
    poisoning.evaluate_poisoning(torch.rand(3, 128, 128), model_type="resnet18")
    victim_ref = poisoning._victim_model
    mlp_ref = poisoning._mlp_detector
    scaler_ref = poisoning._scaler
    poisoning.evaluate_poisoning(torch.rand(3, 128, 128), model_type="resnet18")
    assert poisoning._victim_model is victim_ref
    assert poisoning._mlp_detector is mlp_ref
    assert poisoning._scaler is scaler_ref


def test_dimension_mismatch_is_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    config = {
        "detector_type": "MLP",
        "victim_model": "attacked_model_multi_attack.pth",
        "layers": ["layer2", "layer3", "avgpool"],
        "embedding_dimension_before_augmentation": 896,
        "embedding_dimension_after_augmentation": 899,
        "threshold": 0.67,
        "input_size": 128,
        "batch_size": 32,
        "classes": ["clean", "poisoned"],
    }
    monkeypatch.setattr(poisoning, "_load_config", lambda: config)
    monkeypatch.setattr(poisoning, "_load_mlp_detector", lambda: type("Det", (), {"predict_proba": lambda self, x: np.zeros((x.shape[0], 2)), "classes_": np.array([0, 1])})())
    monkeypatch.setattr(poisoning, "_load_scaler", lambda: type("Scaler", (), {"n_features_in_": 896, "transform": lambda self, x: x})())
    monkeypatch.setattr(
        poisoning,
        "_extract_batch_features",
        lambda batch, device, cfg: (
            torch.zeros(batch.size(0), 1000),
            torch.zeros(batch.size(0), 100),
        ),
    )
    result = poisoning.evaluate_poisoning(torch.rand(3, 128, 128), model_type="resnet18")
    assert result["poisoning_available"] is False
    assert "dimension mismatch" in result["poisoning_status"].lower()


def test_merge_poisoning_updates_verdict() -> None:
    detection = {"verdict": "reliable", "issues": []}
    poisoning.merge_poisoning_into_detection(
        detection,
        {
            "poisoning_flag": True,
            "poisoning_reasons": ["poison probability 91.0% exceeds threshold 67.0%"],
        },
    )
    assert detection["verdict"] == "uncertain"
    assert detection["issues"]


def test_detector_runtime_status_reports_availability() -> None:
    status = poisoning.detector_runtime_status()
    assert "available" in status
    assert "detector_type" in status


def test_risk_engine_includes_runtime_poison_signal() -> None:
    from decision.risk_scoring import compute_input_risk

    base = {
        "adversarial": False,
        "anomaly": False,
        "anomaly_score": 0.0,
        "normalized_entropy": 0.1,
        "margin": 0.8,
        "fgsm_confidence_drop": 0.0,
        "drift_score": 0.0,
        "drift_severity": "LOW",
    }
    low = compute_input_risk({**base, "runtime_poison_suspicion": False, "runtime_poison_probability": 0.1})
    high = compute_input_risk({**base, "runtime_poison_suspicion": True, "runtime_poison_probability": 0.91})
    assert high > low


def test_result_shape_is_frontend_ready() -> None:
    suspicion = poisoning.evaluate_runtime_poison_suspicion(torch.rand(3, 128, 128))
    expected_keys = {
        "runtime_poison_suspicion",
        "runtime_poison_probability",
        "runtime_poison_severity",
        "runtime_poison_status",
        "runtime_poison_available",
    }
    assert expected_keys.issubset(suspicion.keys())
