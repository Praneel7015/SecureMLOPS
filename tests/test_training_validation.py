import json
import zipfile
from pathlib import Path
import sys

import pytest
from PIL import Image

import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.runtime import get_device
from training.model_factory import build_model
from training.validator import safe_load_checkpoint, validate_dataset_zip, validate_training_config, validate_checkpoint_structure


def _write_image(path: Path) -> None:
    img = Image.new("RGB", (8, 8), color=(120, 20, 20))
    img.save(path, format="PNG")


def _build_dataset(root: Path, class_names=("cat", "dog")) -> Path:
    dataset_root = root / "dataset"
    dataset_root.mkdir(parents=True, exist_ok=True)
    for name in class_names:
        class_dir = dataset_root / name
        class_dir.mkdir(parents=True, exist_ok=True)
        _write_image(class_dir / f"{name}_1.png")
    (dataset_root / "classes.json").write_text(json.dumps({"classes": list(class_names)}), encoding="utf-8")
    return dataset_root


def _zip_folder(root: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for item in root.rglob("*"):
            zip_file.write(item, item.relative_to(root))


def test_validate_dataset_zip_success(tmp_path: Path):
    payload_root = tmp_path / "payload"
    dataset_root = _build_dataset(payload_root)
    zip_path = tmp_path / "dataset.zip"
    _zip_folder(payload_root, zip_path)

    extract_dir = tmp_path / "extract"
    result = validate_dataset_zip(zip_path, extract_dir)

    assert result.ok
    assert result.class_names == ["cat", "dog"]
    assert result.image_count == 2


def test_validate_dataset_missing_root(tmp_path: Path):
    zip_path = tmp_path / "broken.zip"
    with zipfile.ZipFile(zip_path, "w") as zip_file:
        zip_file.writestr("README.txt", "missing dataset root")

    result = validate_dataset_zip(zip_path, tmp_path / "extract")
    assert not result.ok
    assert "dataset" in result.message.lower()


def test_validate_dataset_malformed_classes_json(tmp_path: Path):
    payload_root = tmp_path / "payload"
    dataset_root = _build_dataset(payload_root)
    (dataset_root / "classes.json").write_text("{invalid}")
    zip_path = tmp_path / "dataset.zip"
    _zip_folder(payload_root, zip_path)

    result = validate_dataset_zip(zip_path, tmp_path / "extract")
    assert not result.ok
    assert "classes.json" in result.message.lower()


def test_validate_dataset_unsupported_file(tmp_path: Path):
    payload_root = tmp_path / "payload"
    dataset_root = _build_dataset(payload_root)
    (dataset_root / "cat" / "notes.txt").write_text("not an image")
    zip_path = tmp_path / "dataset.zip"
    _zip_folder(payload_root, zip_path)

    result = validate_dataset_zip(zip_path, tmp_path / "extract")
    assert not result.ok
    assert "unsupported" in result.message.lower()


def test_validate_dataset_corrupt_image(tmp_path: Path):
    payload_root = tmp_path / "payload"
    dataset_root = _build_dataset(payload_root)
    (dataset_root / "cat" / "bad.png").write_bytes(b"not-a-real-image")
    zip_path = tmp_path / "dataset.zip"
    _zip_folder(payload_root, zip_path)

    result = validate_dataset_zip(zip_path, tmp_path / "extract")
    assert not result.ok
    assert "corrupt" in result.message.lower()


def test_validate_dataset_empty_class(tmp_path: Path):
    payload_root = tmp_path / "payload"
    dataset_root = _build_dataset(payload_root)
    empty_dir = dataset_root / "empty"
    empty_dir.mkdir()
    (dataset_root / "classes.json").write_text(json.dumps({"classes": ["cat", "dog", "empty"]}))
    zip_path = tmp_path / "dataset.zip"
    _zip_folder(payload_root, zip_path)

    result = validate_dataset_zip(zip_path, tmp_path / "extract")
    assert not result.ok
    assert "empty" in result.message.lower()


def test_validate_dataset_nested_folder(tmp_path: Path):
    payload_root = tmp_path / "payload"
    dataset_root = _build_dataset(payload_root)
    nested_dir = dataset_root / "cat" / "extra"
    nested_dir.mkdir()
    _write_image(nested_dir / "nested.png")
    zip_path = tmp_path / "dataset.zip"
    _zip_folder(payload_root, zip_path)

    result = validate_dataset_zip(zip_path, tmp_path / "extract")
    assert not result.ok
    assert "nested" in result.message.lower()


def test_validate_training_config_rejects_model():
    ok, message, _ = validate_training_config({"model_type": "unsupported"})
    assert not ok
    assert "unsupported" in message.lower()


def test_validate_checkpoint_structure_missing_keys():
    ok, message = validate_checkpoint_structure({"model_state_dict": {}})
    assert not ok
    assert "missing" in message.lower()


def test_safe_load_checkpoint_roundtrip(tmp_path: Path):
    model = build_model("resnet18", num_classes=2, freeze_backbone=True)
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "class_names": ["cat", "dog"],
        "model_type": "resnet18",
        "image_size": 224,
        "num_classes": 2,
        "metrics": {"final_val_accuracy": 0.95},
        "created_at": "2026-05-08T12:00:00Z",
    }
    ckpt_path = tmp_path / "model.pt"
    torch.save(checkpoint, ckpt_path)

    ok, message, payload = safe_load_checkpoint(ckpt_path, get_device())
    assert ok
    assert payload is not None
    assert payload["model_type"] == "resnet18"
