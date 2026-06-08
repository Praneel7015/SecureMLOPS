"""Dataset-level poisoning scan orchestration for the training pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from Detection.poisoning import evaluate_poisoning_batch
from telemetry.events import EventSeverity, EventSource, EventType, emit_event

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def collect_dataset_image_paths(dataset_root: Path) -> list[tuple[str, Path]]:
    """Return (relative_path, absolute_path) pairs for all dataset images."""
    pairs: list[tuple[str, Path]] = []
    if not dataset_root.exists():
        return pairs

    for class_dir in sorted(path for path in dataset_root.iterdir() if path.is_dir()):
        for file_path in sorted(class_dir.iterdir()):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
                continue
            relative = file_path.relative_to(dataset_root).as_posix()
            pairs.append((relative, file_path))
    return pairs


def _load_training_security(config: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "sample_threshold": float(config.get("threshold", 0.67)),
        "warning_threshold": 0.5,
        "dataset_high_risk_ratio": 0.08,
        "dataset_medium_risk_ratio": 0.03,
        "dataset_high_max_probability": 0.85,
        "allow_override": True,
        "default_decision": "warn_or_block",
    }
    overrides = config.get("training_security") or {}
    if isinstance(overrides, dict):
        defaults.update(overrides)
    return defaults


def _dataset_risk_level(
    flagged_ratio: float,
    max_probability: float,
    average_probability: float,
    rules: dict[str, Any],
) -> str:
    high_ratio = float(rules.get("dataset_high_risk_ratio", 0.08))
    medium_ratio = float(rules.get("dataset_medium_risk_ratio", 0.03))
    high_max = float(rules.get("dataset_high_max_probability", 0.85))

    if flagged_ratio >= high_ratio or max_probability >= high_max:
        return "HIGH"
    if flagged_ratio >= medium_ratio or average_probability >= 0.35:
        return "MEDIUM"
    return "LOW"


def _training_decision(risk_level: str, flagged_count: int, rules: dict[str, Any]) -> str:
    if flagged_count == 0:
        return "allow"
    if risk_level == "HIGH":
        return "block"
    if risk_level == "MEDIUM":
        return "warn"
    return "allow"


def _recommendation(decision: str, flagged_count: int, total: int) -> str:
    if decision == "block":
        return (
            f"Review {flagged_count} flagged sample(s) before training. "
            "Dataset risk is HIGH — training is blocked until manual override."
        )
    if decision == "warn":
        return (
            f"Review {flagged_count} flagged sample(s) before training. "
            "Training may proceed with caution or manual override."
        )
    if flagged_count:
        return f"{flagged_count} low-severity sample(s) flagged out of {total}; training may proceed."
    return "No suspicious poisoning indicators detected. Training may proceed."


def scan_dataset_for_poisoning(
    dataset_root: Path,
    *,
    dataset_id: str,
    owner: str | None = None,
    source_name: str | None = None,
) -> dict[str, Any]:
    """Run batched poisoning analysis and return an aggregated security report."""
    image_pairs = collect_dataset_image_paths(dataset_root)
    total_images = len(image_pairs)

    emit_event(
        severity=EventSeverity.INFO,
        event_type=EventType.POISONING_DATASET_SCAN_STARTED,
        source=EventSource.POISONING,
        title="Dataset poisoning scan started",
        description=f"Scanning {total_images} images for dataset {dataset_id}.",
        metadata={
            "dataset_id": dataset_id,
            "image_count": total_images,
            "source_name": source_name,
        },
        owner=owner,
    )

    if total_images == 0:
        report = {
            "scan_status": "unavailable",
            "scan_available": False,
            "images_scanned": 0,
            "suspicious_count": 0,
            "flagged_samples": [],
            "average_poison_probability": None,
            "highest_poison_probability": None,
            "dataset_risk_level": "UNAVAILABLE",
            "training_decision": "allow",
            "recommendation": "No images available for poisoning scan.",
            "detector_type": "MLP",
        }
        emit_event(
            severity=EventSeverity.WARNING,
            event_type=EventType.POISONING_DETECTOR_FAILURE,
            source=EventSource.POISONING,
            title="Dataset poisoning scan unavailable",
            description="No scannable images found in dataset.",
            metadata={"dataset_id": dataset_id},
            owner=owner,
        )
        return report

    absolute_paths = [path for _, path in image_pairs]
    per_image = evaluate_poisoning_batch(absolute_paths, scan_mode="dataset")

    if not per_image or not per_image[0].get("poisoning_available", False):
        status = per_image[0].get("poisoning_status") if per_image else "Scan unavailable."
        report = {
            "scan_status": "unavailable",
            "scan_available": False,
            "images_scanned": total_images,
            "suspicious_count": 0,
            "flagged_samples": [],
            "average_poison_probability": None,
            "highest_poison_probability": None,
            "dataset_risk_level": "UNAVAILABLE",
            "training_decision": "warn",
            "recommendation": status,
            "detector_type": per_image[0].get("poisoning_detector") if per_image else "MLP",
            "scan_message": status,
        }
        emit_event(
            severity=EventSeverity.WARNING,
            event_type=EventType.POISONING_UNAVAILABLE,
            source=EventSource.POISONING,
            title="Dataset poisoning scan unavailable",
            description=str(status),
            metadata={"dataset_id": dataset_id, "image_count": total_images},
            owner=owner,
        )
        return report

    from Detection.poisoning import _load_config

    config = _load_config() or {}
    rules = _load_training_security(config)
    sample_threshold = float(rules.get("sample_threshold", config.get("threshold", 0.67)))

    flagged_samples: list[dict[str, Any]] = []
    probabilities: list[float] = []

    for (relative_path, abs_path), result in zip(image_pairs, per_image):
        probability = float(result.get("poisoning_probability") or 0.0)
        probabilities.append(probability)
        class_name = relative_path.split("/", 1)[0] if "/" in relative_path else "unknown"
        if result.get("poisoning_flag") or probability >= sample_threshold:
            flagged_samples.append(
                {
                    "relative_path": relative_path,
                    "filename": abs_path.name,
                    "class_name": class_name,
                    "poison_probability": round(probability, 4),
                    "severity": result.get("poisoning_severity", "HIGH"),
                    "preview_url": f"/api/training/datasets/{dataset_id}/images/{relative_path}",
                }
            )

    flagged_samples.sort(key=lambda item: item["poison_probability"], reverse=True)
    suspicious_count = len(flagged_samples)
    average_probability = round(sum(probabilities) / len(probabilities), 4) if probabilities else 0.0
    highest_probability = round(max(probabilities), 4) if probabilities else 0.0
    flagged_ratio = suspicious_count / total_images if total_images else 0.0

    dataset_risk_level = _dataset_risk_level(
        flagged_ratio,
        highest_probability,
        average_probability,
        rules,
    )
    training_decision = _training_decision(dataset_risk_level, suspicious_count, rules)
    recommendation = _recommendation(training_decision, suspicious_count, total_images)

    report = {
        "scan_status": "completed",
        "scan_available": True,
        "images_scanned": total_images,
        "suspicious_count": suspicious_count,
        "flagged_ratio": round(flagged_ratio, 4),
        "flagged_samples": flagged_samples[:100],
        "average_poison_probability": average_probability,
        "highest_poison_probability": highest_probability,
        "dataset_risk_level": dataset_risk_level,
        "training_decision": training_decision,
        "allow_override": bool(rules.get("allow_override", True)),
        "recommendation": recommendation,
        "detector_type": config.get("detector_type", "MLP"),
        "sample_threshold": sample_threshold,
        "scanned_at": None,
    }

    metadata = {
        "dataset_id": dataset_id,
        "source_name": source_name,
        "images_scanned": total_images,
        "suspicious_count": suspicious_count,
        "average_poison_probability": average_probability,
        "highest_poison_probability": highest_probability,
        "dataset_risk_level": dataset_risk_level,
        "training_decision": training_decision,
    }

    emit_event(
        severity=EventSeverity.INFO,
        event_type=EventType.POISONING_DATASET_SCAN_COMPLETED,
        source=EventSource.POISONING,
        title="Dataset poisoning scan completed",
        description=recommendation,
        metadata=metadata,
        owner=owner,
    )

    if suspicious_count:
        emit_event(
            severity=EventSeverity.HIGH if dataset_risk_level == "HIGH" else EventSeverity.WARNING,
            event_type=EventType.POISONING_SUSPICIOUS_DATASET,
            source=EventSource.POISONING,
            title="Suspicious dataset detected",
            description=f"{suspicious_count} suspicious sample(s) found in uploaded dataset.",
            metadata=metadata,
            owner=owner,
        )

    high_samples = [sample for sample in flagged_samples if sample.get("severity") == "HIGH"]
    if high_samples:
        emit_event(
            severity=EventSeverity.HIGH,
            event_type=EventType.POISONING_HIGH_RISK,
            source=EventSource.POISONING,
            title="High poison probability samples detected",
            description=f"{len(high_samples)} sample(s) exceeded poisoning threshold.",
            metadata={**metadata, "high_risk_sample_count": len(high_samples)},
            owner=owner,
        )

    return report


def evaluate_training_start(
    dataset: dict[str, Any],
    *,
    security_override: bool = False,
    owner: str | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Return whether training may start based on stored dataset security scan."""
    scan = dataset.get("poisoning_scan") or {}
    decision = str(scan.get("training_decision", "allow")).lower()
    allow_override = bool(scan.get("allow_override", True))

    if not scan.get("scan_available", False):
        if scan.get("scan_status") == "unavailable":
            return True, "Training allowed; dataset poisoning scan was unavailable.", scan
        return True, "Training allowed; no poisoning scan recorded.", scan

    if decision == "allow":
        return True, "Dataset security scan passed.", scan

    if decision == "warn":
        if security_override:
            return True, "Training started with manual security override.", scan
        return True, scan.get("recommendation") or "Dataset flagged with warnings.", scan

    if decision == "block":
        if security_override and allow_override:
            emit_event(
                severity=EventSeverity.WARNING,
                event_type=EventType.POISONING_TRAINING_OVERRIDE,
                source=EventSource.POISONING,
                title="Training override for flagged dataset",
                description="Training started despite HIGH dataset poisoning risk.",
                metadata={
                    "dataset_id": dataset.get("dataset_id"),
                    "dataset_risk_level": scan.get("dataset_risk_level"),
                    "suspicious_count": scan.get("suspicious_count"),
                },
                owner=owner,
            )
            return True, "Training started with manual security override.", scan

        emit_event(
            severity=EventSeverity.HIGH,
            event_type=EventType.POISONING_TRAINING_BLOCKED,
            source=EventSource.POISONING,
            title="Training blocked due to poisoning risk",
            description=scan.get("recommendation") or "Dataset poisoning risk is too high.",
            metadata={
                "dataset_id": dataset.get("dataset_id"),
                "dataset_risk_level": scan.get("dataset_risk_level"),
                "suspicious_count": scan.get("suspicious_count"),
            },
            owner=owner,
        )
        return False, scan.get("recommendation") or "Training blocked due to dataset poisoning risk.", scan

    return True, "Training allowed.", scan
