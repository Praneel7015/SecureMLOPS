"""Normalized security event schema and centralized emit utility."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from telemetry.event_store import insert_event

logger = logging.getLogger("secureml.telemetry")


class EventSeverity:
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EventSource:
    INFERENCE = "inference"
    DRIFT = "drift"
    ADVERSARIAL = "adversarial"
    POISONING = "poisoning"
    INTEGRITY = "integrity"
    TRAINING = "training"
    VALIDATION = "validation"
    SYSTEM = "system"
    ACCESS = "access"


class EventType:
    # Inference
    INFERENCE_COMPLETED = "inference.completed"
    INFERENCE_HIGH_RISK = "inference.high_risk"
    INFERENCE_BLOCKED = "inference.blocked"
    INFERENCE_RATE_LIMITED = "inference.rate_limited"

    # Drift
    DRIFT_THRESHOLD_EXCEEDED = "drift.threshold_exceeded"
    DRIFT_HIGH_WARNING = "drift.high_warning"
    DRIFT_SEVERITY_ESCALATION = "drift.severity_escalation"
    DRIFT_BASELINE_LOAD_FAILURE = "drift.baseline_load_failure"
    DRIFT_RECORDED = "drift.recorded"

    # Adversarial
    ADVERSARIAL_SUSPICION = "adversarial.suspicion"
    ADVERSARIAL_BLOCKED = "adversarial.blocked"
    ADVERSARIAL_ALLOWED = "adversarial.allowed"
    ADVERSARIAL_ESCALATION = "adversarial.escalation"

    # Poisoning
    POISONING_DETECTED = "poisoning.detected"
    POISONING_HIGH_RISK = "poisoning.high_risk"
    POISONING_UNAVAILABLE = "poisoning.unavailable"
    POISONING_UNSUPPORTED_ARCHITECTURE = "poisoning.unsupported_architecture"
    POISONING_DETECTOR_FAILURE = "poisoning.detector_failure"
    POISONING_EMBEDDING_MISMATCH = "poisoning.embedding_mismatch"
    POISONING_DIMENSION_MISMATCH = "poisoning.dimension_mismatch"
    POISONING_SCAN_COMPLETED = "poisoning.scan_completed"
    POISONING_DATASET_SCAN_STARTED = "poisoning.dataset_scan_started"
    POISONING_DATASET_SCAN_COMPLETED = "poisoning.dataset_scan_completed"
    POISONING_SUSPICIOUS_DATASET = "poisoning.suspicious_dataset"
    POISONING_TRAINING_BLOCKED = "poisoning.training_blocked"
    POISONING_TRAINING_OVERRIDE = "poisoning.training_override"

    # Integrity
    INTEGRITY_SUCCESS = "integrity.validation_success"
    INTEGRITY_FAILURE = "integrity.validation_failure"
    INTEGRITY_ARCHITECTURE_MISMATCH = "integrity.architecture_mismatch"
    INTEGRITY_MALFORMED_CHECKPOINT = "integrity.malformed_checkpoint"
    INTEGRITY_RECONSTRUCTION_FAILURE = "integrity.reconstruction_failure"
    INTEGRITY_UNSUPPORTED_ARCHITECTURE = "integrity.unsupported_architecture"

    # Training
    TRAINING_STARTED = "training.started"
    TRAINING_COMPLETED = "training.completed"
    TRAINING_FAILED = "training.failed"
    TRAINING_DATASET_VALIDATION_WARNING = "training.dataset_validation_warning"
    TRAINING_DATASET_UPLOADED = "training.dataset_uploaded"
    TRAINING_DATASET_VALIDATION_FAILED = "training.dataset_validation_failed"

    # Validation
    VALIDATION_CORRUPTED_IMAGE = "validation.corrupted_image"
    VALIDATION_UNSUPPORTED_FILE = "validation.unsupported_file"
    VALIDATION_IMAGE_FAILED = "validation.image_failed"

    # System
    SYSTEM_BACKEND_FAILURE = "system.backend_failure"
    SYSTEM_TELEMETRY_FAILURE = "system.telemetry_failure"
    SYSTEM_DETECTOR_EXCEPTION = "system.detector_exception"
    SYSTEM_DB_FAILURE = "system.db_failure"
    SYSTEM_MONITORING_FAILURE = "system.monitoring_failure"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_event(
    *,
    severity: str,
    event_type: str,
    source: str,
    title: str,
    description: str = "",
    metadata: dict[str, Any] | None = None,
    event_id: str | None = None,
    timestamp: str | None = None,
    owner: str | None = None,
) -> str | None:
    """
    Central entry point for all security-relevant operational events.
    Never raises — failures are logged as system events.
    """
    normalized_id = event_id or uuid.uuid4().hex
    payload = {
        "id": normalized_id,
        "timestamp": timestamp or _now_iso(),
        "severity": severity,
        "event_type": event_type,
        "source": source,
        "title": title,
        "description": description or title,
        "metadata": metadata or {},
    }
    if owner:
        payload["metadata"]["owner"] = owner

    try:
        insert_event(payload)
        return normalized_id
    except Exception as exc:
        logger.exception("Failed to persist telemetry event: %s", exc)
        try:
            insert_event(
                {
                    "id": uuid.uuid4().hex,
                    "timestamp": _now_iso(),
                    "severity": EventSeverity.WARNING,
                    "event_type": EventType.SYSTEM_TELEMETRY_FAILURE,
                    "source": EventSource.SYSTEM,
                    "title": "Telemetry persistence failure",
                    "description": str(exc),
                    "metadata": {"original_event_type": event_type, "original_title": title},
                }
            )
        except Exception:
            logger.exception("Telemetry failure event could not be persisted.")
        return None


def severity_from_drift(drift_severity: str | None) -> str:
    mapping = {
        "LOW": EventSeverity.INFO,
        "MEDIUM": EventSeverity.WARNING,
        "HIGH": EventSeverity.HIGH,
        "CRITICAL": EventSeverity.CRITICAL,
    }
    return mapping.get(str(drift_severity or "").upper(), EventSeverity.INFO)


def severity_from_risk_level(risk_level: str | None) -> str:
    mapping = {
        "LOW": EventSeverity.INFO,
        "MEDIUM": EventSeverity.WARNING,
        "HIGH": EventSeverity.HIGH,
        "CRITICAL": EventSeverity.CRITICAL,
    }
    return mapping.get(str(risk_level or "").upper(), EventSeverity.INFO)


def emit_inference_event(result: dict[str, Any], username: str | None = None) -> None:
    """Emit telemetry from an inference/analysis result dict."""
    status = result.get("status", "")
    risk_level = result.get("risk_level", "LOW")
    metadata = {
        "prediction": result.get("prediction"),
        "confidence": result.get("confidence"),
        "risk_level": risk_level,
        "risk_score": (result.get("risk_breakdown") or {}).get("total"),
        "model_name": result.get("model_name"),
        "model_type": result.get("model_type"),
        "model_source": result.get("model_source"),
        "filename": result.get("filename"),
        "drift_score": result.get("drift_score"),
        "drift_severity": result.get("drift_severity"),
        "adversarial": result.get("adversarial"),
        "anomaly": result.get("anomaly"),
        "poisoning": result.get("poisoning"),
        "poisoning_probability": result.get("poisoning_probability"),
        "poisoning_severity": result.get("poisoning_severity"),
        "poisoning_available": result.get("poisoning_available"),
        "runtime_poison_suspicion": result.get("runtime_poison_suspicion"),
        "runtime_poison_probability": result.get("runtime_poison_probability"),
        "runtime_poison_severity": result.get("runtime_poison_severity"),
        "verdict": result.get("verdict"),
        "session_id": result.get("session_id"),
    }
    metadata = {k: v for k, v in metadata.items() if v is not None}

    if status == "blocked":
        emit_event(
            severity=severity_from_risk_level(risk_level),
            event_type=EventType.INFERENCE_BLOCKED,
            source=EventSource.INFERENCE,
            title="Inference blocked",
            description=result.get("decision_reason") or "Request blocked by security pipeline.",
            metadata=metadata,
            owner=username,
        )
    elif status == "allowed_with_warning" or risk_level in {"HIGH", "CRITICAL", "MEDIUM"}:
        emit_event(
            severity=severity_from_risk_level(risk_level),
            event_type=EventType.INFERENCE_HIGH_RISK,
            source=EventSource.INFERENCE,
            title="High-risk inference detected",
            description=result.get("decision_reason") or "Inference completed with elevated risk.",
            metadata=metadata,
            owner=username,
        )
    else:
        emit_event(
            severity=EventSeverity.INFO,
            event_type=EventType.INFERENCE_COMPLETED,
            source=EventSource.INFERENCE,
            title="Inference completed",
            description=f"Prediction: {result.get('prediction') or 'N/A'}",
            metadata=metadata,
            owner=username,
        )

    if result.get("adversarial"):
        emit_event(
            severity=EventSeverity.HIGH,
            event_type=EventType.ADVERSARIAL_SUSPICION,
            source=EventSource.ADVERSARIAL,
            title="Adversarial input suspected",
            description="Adversarial detector flagged the input.",
            metadata=metadata,
            owner=username,
        )

    if result.get("runtime_poison_suspicion"):
        emit_event(
            severity=EventSeverity.WARNING,
            event_type=EventType.POISONING_DETECTED,
            source=EventSource.POISONING,
            title="Runtime poisoning suspicion",
            description=result.get("runtime_poison_status") or "Optional runtime suspicion signal triggered.",
            metadata=metadata,
            owner=username,
        )
    elif result.get("poisoning"):
        emit_event(
            severity=EventSeverity.HIGH,
            event_type=EventType.POISONING_DETECTED,
            source=EventSource.POISONING,
            title="Potential poisoned sample detected",
            description=result.get("poisoning_status") or "Poisoning detector flagged the input.",
            metadata=metadata,
            owner=username,
        )
        if str(result.get("poisoning_severity", "")).upper() == "HIGH":
            emit_event(
                severity=EventSeverity.HIGH,
                event_type=EventType.POISONING_HIGH_RISK,
                source=EventSource.POISONING,
                title="High poison risk event",
                description=f"Poison probability {result.get('poisoning_probability')}",
                metadata=metadata,
                owner=username,
            )
    elif result.get("runtime_poison_available") is False and result.get("runtime_poison_status"):
        emit_event(
            severity=EventSeverity.INFO,
            event_type=EventType.POISONING_UNAVAILABLE,
            source=EventSource.POISONING,
            title="Runtime poisoning suspicion unavailable",
            description=str(result.get("runtime_poison_status")),
            metadata=metadata,
            owner=username,
        )
