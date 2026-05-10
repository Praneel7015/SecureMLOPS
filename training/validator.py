from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image
import torch

from training.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_DATASET_UPLOAD_BYTES,
    MAX_IMAGE_COUNT,
    MAX_IMAGE_SIDE,
    SUPPORTED_MODELS,
)


@dataclass
class DatasetValidationResult:
    ok: bool
    message: str
    dataset_dir: Path | None = None
    class_names: list[str] | None = None
    image_count: int = 0
    class_distribution: dict[str, int] | None = None
    issues: list[str] | None = None


class ValidationError(Exception):
    pass


def _safe_zip_members(zip_file: zipfile.ZipFile, target_dir: Path) -> list[zipfile.ZipInfo]:
    members = []
    for member in zip_file.infolist():
        if member.is_dir():
            members.append(member)
            continue
        entry_path = PurePosixPath(member.filename)
        if entry_path.is_absolute() or ".." in entry_path.parts:
            raise ValidationError("ZIP contains unsafe paths.")
        resolved = (target_dir / entry_path.as_posix()).resolve()
        if target_dir.resolve() not in resolved.parents and resolved != target_dir.resolve():
            raise ValidationError("ZIP path traversal attempt detected.")
        members.append(member)
    return members


def _validate_classes_json(classes_path: Path, folder_classes: list[str]) -> list[str]:
    try:
        data = json.loads(classes_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationError(f"classes.json is malformed: {exc}")

    classes = data.get("classes")
    if not isinstance(classes, list) or not all(isinstance(c, str) and c.strip() for c in classes):
        raise ValidationError("classes.json must contain a non-empty 'classes' list of strings.")

    normalized = [c.strip() for c in classes]
    if len(normalized) != len(set(normalized)):
        raise ValidationError("classes.json contains duplicate class names.")

    if sorted(normalized) != sorted(folder_classes):
        raise ValidationError("classes.json does not match dataset folder names.")

    return normalized


def validate_dataset_zip(zip_path: Path, extract_dir: Path) -> DatasetValidationResult:
    if not zip_path.exists():
        return DatasetValidationResult(ok=False, message="Dataset ZIP not found.")

    if zip_path.stat().st_size > MAX_DATASET_UPLOAD_BYTES:
        return DatasetValidationResult(ok=False, message="Dataset ZIP exceeds the 600 MB limit.")

    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            members = _safe_zip_members(zip_file, extract_dir)
            zip_file.extractall(extract_dir, members)
    except ValidationError as exc:
        return DatasetValidationResult(ok=False, message=str(exc))
    except zipfile.BadZipFile:
        return DatasetValidationResult(ok=False, message="Uploaded ZIP is corrupted or invalid.")

    dataset_root = extract_dir / "dataset"
    if not dataset_root.exists() or not dataset_root.is_dir():
        return DatasetValidationResult(ok=False, message="ZIP must contain a top-level 'dataset/' folder.")

    classes_path = dataset_root / "classes.json"
    if not classes_path.exists():
        return DatasetValidationResult(ok=False, message="classes.json is missing in dataset root.")

    class_dirs = [p for p in dataset_root.iterdir() if p.is_dir()]
    class_names = sorted([p.name for p in class_dirs])
    if not class_names:
        return DatasetValidationResult(ok=False, message="Dataset contains no class folders.")

    image_count = 0
    class_distribution: dict[str, int] = {}
    issues: list[str] = []

    for class_dir in class_dirs:
        files = [p for p in class_dir.iterdir() if p.is_file()]
        if not files:
            return DatasetValidationResult(ok=False, message=f"Class folder '{class_dir.name}' is empty.")
        class_distribution[class_dir.name] = len(files)
        for file_path in files:
            if file_path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
                return DatasetValidationResult(ok=False, message=f"Unsupported file type in '{class_dir.name}'.")
            try:
                with Image.open(file_path) as img:
                    img.verify()
                with Image.open(file_path) as img:
                    if max(img.size) > MAX_IMAGE_SIDE:
                        return DatasetValidationResult(
                            ok=False,
                            message=f"Image '{file_path.name}' exceeds max resolution {MAX_IMAGE_SIDE}px.",
                        )
            except Exception:
                return DatasetValidationResult(ok=False, message=f"Corrupt image detected: {file_path.name}.")
            image_count += 1

    if image_count == 0:
        return DatasetValidationResult(ok=False, message="Dataset contains no images.")
    if image_count > MAX_IMAGE_COUNT:
        return DatasetValidationResult(ok=False, message="Dataset exceeds maximum image count.")

    for item in dataset_root.rglob("*"):
        if item.is_dir():
            continue
        rel = item.relative_to(dataset_root)
        if len(rel.parts) > 2:
            return DatasetValidationResult(ok=False, message="Nested folder structures are not supported.")

    try:
        validated_classes = _validate_classes_json(classes_path, class_names)
    except ValidationError as exc:
        return DatasetValidationResult(ok=False, message=str(exc))

    return DatasetValidationResult(
        ok=True,
        message="Dataset validated successfully.",
        dataset_dir=dataset_root,
        class_names=validated_classes,
        image_count=image_count,
        class_distribution=class_distribution,
        issues=issues,
    )


def validate_training_config(config: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    cleaned = {
        "epochs": int(config.get("epochs", 5)),
        "batch_size": int(config.get("batch_size", 16)),
        "learning_rate": float(config.get("learning_rate", 0.001)),
        "freeze_backbone": bool(config.get("freeze_backbone", False)),
        "model_type": str(config.get("model_type", "efficientnet-b0")).strip().lower(),
        "seed": int(config.get("seed", 42)),
    }

    if cleaned["epochs"] < 1 or cleaned["epochs"] > 50:
        return False, "Epoch count out of bounds.", cleaned
    if cleaned["batch_size"] < 1 or cleaned["batch_size"] > 256:
        return False, "Batch size out of bounds.", cleaned
    if cleaned["learning_rate"] < 1e-6 or cleaned["learning_rate"] > 1e-1:
        return False, "Learning rate out of bounds.", cleaned

    if cleaned["model_type"] not in SUPPORTED_MODELS:
        return False, "Unsupported model type.", cleaned

    return True, "OK", cleaned


def validate_checkpoint_structure(checkpoint: dict[str, Any]) -> tuple[bool, str]:
    required = {
        "model_state_dict",
        "class_names",
        "model_type",
        "image_size",
        "num_classes",
        "metrics",
        "created_at",
    }

    if not isinstance(checkpoint, dict):
        return False, "Checkpoint payload is not a dictionary."

    missing = required - checkpoint.keys()
    if missing:
        return False, f"Checkpoint missing keys: {', '.join(sorted(missing))}."

    model_type = str(checkpoint.get("model_type", "")).lower()
    if model_type not in SUPPORTED_MODELS:
        return False, "Checkpoint model type is not supported."

    class_names = checkpoint.get("class_names")
    if not isinstance(class_names, list) or not all(isinstance(c, str) for c in class_names):
        return False, "Checkpoint class_names must be a list of strings."

    num_classes = checkpoint.get("num_classes")
    if not isinstance(num_classes, int) or num_classes != len(class_names):
        return False, "Checkpoint num_classes does not match class_names length."

    image_size = checkpoint.get("image_size")
    if not isinstance(image_size, int) or image_size <= 0:
        return False, "Checkpoint image_size is invalid."

    return True, "Checkpoint is valid."


def safe_load_checkpoint(file_path: Path, device: torch.device) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Load a checkpoint using the safest available torch.load mode.
    Returns (ok, message, checkpoint_dict).
    """
    try:
        try:
            checkpoint = torch.load(file_path, map_location=device, weights_only=True)
        except TypeError:
            return False, "Safe checkpoint loading is not supported in this environment.", None
    except Exception as exc:
        return False, f"Failed to load checkpoint: {exc}", None

    ok, message = validate_checkpoint_structure(checkpoint)
    if not ok:
        return False, message, None

    return True, "Checkpoint loaded.", checkpoint
