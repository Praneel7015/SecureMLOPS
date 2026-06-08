from __future__ import annotations

from pathlib import Path

import pytest

import Detection.poisoning as poisoning
from training.dataset_scanner import (
    collect_dataset_image_paths,
    evaluate_training_start,
    scan_dataset_for_poisoning,
)

_ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "Detection" / "security_models"
requires_poisoning_artifacts = pytest.mark.skipif(
    not all((_ARTIFACTS_DIR / name).is_file() for name in (
        "attacked_model_multi_attack.pth",
        "detector_mlp.pkl",
        "scaler.pkl",
        "detector_config.json",
    )),
    reason="Poisoning detector artifacts missing",
)


@pytest.fixture(autouse=True)
def reset_poisoning_state() -> None:
    poisoning.reset_poisoning_cache()
    yield
    poisoning.reset_poisoning_cache()


def test_collect_dataset_image_paths(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    cat = root / "cat"
    dog = root / "dog"
    cat.mkdir(parents=True)
    dog.mkdir(parents=True)
    (cat / "a.jpg").write_bytes(b"fake")
    (dog / "b.png").write_bytes(b"fake")
    (root / "classes.json").write_text('["cat","dog"]', encoding="utf-8")

    pairs = collect_dataset_image_paths(root)
    assert len(pairs) == 2
    assert pairs[0][0].startswith("cat/") or pairs[0][0].startswith("dog/")


@requires_poisoning_artifacts
def test_scan_dataset_for_poisoning(tmp_path: Path) -> None:
    from PIL import Image

    root = tmp_path / "dataset"
    cls = root / "apple"
    cls.mkdir(parents=True)
    for idx in range(3):
        Image.new("RGB", (96, 96), color=(idx * 40, 20, 10)).save(cls / f"img_{idx}.jpg")

    report = scan_dataset_for_poisoning(
        root,
        dataset_id="ds-test",
        owner="tester",
        source_name="sample.zip",
    )

    assert report["scan_status"] in {"completed", "unavailable"}
    assert report["images_scanned"] == 3
    assert "dataset_risk_level" in report
    assert "training_decision" in report
    assert "recommendation" in report


def test_evaluate_training_start_blocks_high_risk_dataset() -> None:
    dataset = {
        "dataset_id": "blocked-ds",
        "poisoning_scan": {
            "scan_available": True,
            "training_decision": "block",
            "allow_override": True,
            "recommendation": "Review flagged samples before training.",
            "dataset_risk_level": "HIGH",
            "suspicious_count": 5,
        },
    }
    allowed, message, _ = evaluate_training_start(dataset, security_override=False, owner="tester")
    assert allowed is False
    assert "Review" in message


def test_evaluate_training_start_allows_override() -> None:
    dataset = {
        "dataset_id": "blocked-ds",
        "poisoning_scan": {
            "scan_available": True,
            "training_decision": "block",
            "allow_override": True,
            "dataset_risk_level": "HIGH",
            "suspicious_count": 5,
        },
    }
    allowed, message, _ = evaluate_training_start(dataset, security_override=True, owner="tester")
    assert allowed is True
    assert "override" in message.lower()


@requires_poisoning_artifacts
def test_dataset_scan_mode_skips_inference_architecture_gate() -> None:
    import torch

    results = poisoning.evaluate_poisoning_batch(
        [torch.rand(3, 128, 128)],
        model_type="efficientnet-b0",
        scan_mode="dataset",
    )
    assert results[0]["poisoning_available"] is True


def test_runtime_optional_scan_mode_runs_without_architecture_gate() -> None:
    import torch

    results = poisoning.evaluate_poisoning_batch(
        [torch.rand(3, 128, 128)],
        model_type="efficientnet-b0",
        scan_mode="runtime_optional",
    )
    assert "poisoning_available" in results[0]
