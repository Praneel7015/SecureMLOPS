import json
import logging
import uuid
from pathlib import Path

from telemetry.events import emit_inference_event

logger = logging.getLogger("secureml.security")


def configure_logging(log_path):
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(message)s",
    )


def log_security_event(username, result):
    payload = {
        "user": username,
        "status": result.get("status"),
        "risk_level": result.get("risk_level"),
        "decision_reason": result.get("decision_reason"),
        "prediction": result.get("prediction"),
        "model_source": result.get("model_source"),
        "model_name": result.get("model_name"),
        "model_type": result.get("model_type"),
        "checkpoint_loaded": result.get("checkpoint_loaded"),
        "drift_score": result.get("drift_score"),
        "drift_severity": result.get("drift_severity"),
        "drift_status": result.get("drift_status"),
        "runtime_poison_suspicion": result.get("runtime_poison_suspicion"),
        "runtime_poison_probability": result.get("runtime_poison_probability"),
        "timestamp": result.get("timestamp"),
        "filename": result.get("filename"),
    }
    logging.info(json.dumps(payload))

    # Attach session correlation ID for traceability
    if not result.get("session_id"):
        result["session_id"] = uuid.uuid4().hex[:12]

    try:
        emit_inference_event(result, username=username)
    except Exception as exc:
        logger.exception("Telemetry emit failed: %s", exc)
