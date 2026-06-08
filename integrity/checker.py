import json
import logging
from pathlib import Path

from Detection.model_loader import load_model, loaded_with_pretrained_weights
from utils.file_hash import sha256_for_file
from utils.model_fingerprint import sha256_for_model

BASE_DIR = Path(__file__).resolve().parent.parent
INTEGRITY_FILE = BASE_DIR / "config" / "integrity.json"
logger = logging.getLogger("secureml.access.integrity")


def verify_integrity():
    integrity_config = json.loads(INTEGRITY_FILE.read_text(encoding="utf-8"))
    expected_hashes = integrity_config.get("files")
    if expected_hashes is None:
        expected_hashes = {
            key: value
            for key, value in integrity_config.items()
            if key != "model_weights"
        }

    mismatches = []
    for relative_path, expected_hash in expected_hashes.items():
        target_path = BASE_DIR / relative_path
        current_hash = sha256_for_file(target_path)
        if current_hash != expected_hash:
            mismatches.append(relative_path)

    model_config = integrity_config.get("model_weights")
    if model_config:
        try:
            model = load_model()
            if loaded_with_pretrained_weights():
                current_model_hash = sha256_for_model(model)
                if current_model_hash != model_config.get("fingerprint"):
                    mismatches.append("model_weights")
            else:
                logger.warning("Model weights integrity check skipped because pretrained weights were unavailable.")
        except Exception as exc:
            logger.warning("Model weights integrity check skipped: %s", exc)

    if mismatches:
        files = ", ".join(mismatches)
        return {
            "ok": False,
            "message": f"Integrity check failed for: {files}",
            "details": mismatches,
        }

    return {
        "ok": True,
        "message": "Integrity verified for protected files.",
        "details": [],
    }
