import json
import logging
from pathlib import Path


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
        "timestamp": result.get("timestamp"),
        "filename": result.get("filename"),
    }
    logging.info(json.dumps(payload))
