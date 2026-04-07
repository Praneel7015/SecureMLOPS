import logging
import shutil
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from Detection.ml_pipeline import process_image
from auth.auth_service import authenticate_user
from decision.engine import decide_risk
from integrity.checker import verify_integrity
from rate_limit.service import RateLimiter
from utils.logging_setup import configure_logging, log_security_event
from validation.image_validator import validate_image_path, validate_image_upload

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
IMAGE_DIR = BASE_DIR / "images"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY", "mini-project-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

configure_logging(BASE_DIR / "logs" / "security.log")
rate_limiter = RateLimiter()


@app.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        result=None,
        selected_image_url=None,
        sample_images=list_sample_images(),
        selected_sample=None,
    )


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    success, message = authenticate_user(username, password)
    if not success:
        flash(message, "error")
        return redirect(url_for("index"))

    session["user"] = username
    flash("Login successful. You can now submit an image for secure inference.", "success")
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/analyze", methods=["POST"])
def analyze():
    username = session.get("user")
    if not username:
        flash("Please log in before submitting an image.", "error")
        return redirect(url_for("index"))

    result = {
        "timestamp": current_timestamp(),
        "username": username,
    }
    sample_images = list_sample_images()

    rate_limit_state = rate_limiter.check(username, request.remote_addr or "local")
    if not rate_limit_state["allowed"]:
        decision = decide_risk(
            suspicious=False,
            adversarial=False,
            rate_limited=True,
            integrity_ok=True,
        )
        result.update(
            {
                "status": decision["status"],
                "risk_level": decision["risk_level"],
                "decision_reason": rate_limit_state["message"],
                "rate_limit_message": rate_limit_state["message"],
                "integrity": {"ok": True, "message": "Integrity verified."},
            }
        )
        finalize_result(result)
        log_security_event(username, result)
        flash(rate_limit_state["message"], "error")
        return render_template(
            "index.html",
            result=result,
            selected_image_url=None,
            sample_images=sample_images,
            selected_sample=request.form.get("sample_image") or None,
        )

    uploaded_file = request.files.get("image")
    selected_sample = request.form.get("sample_image", "").strip()
    file_path = None
    filename = None
    selected_image_url = None

    if uploaded_file and uploaded_file.filename:
        is_valid, validation_message = validate_image_upload(uploaded_file, app.config["MAX_CONTENT_LENGTH"])
    elif selected_sample:
        sample_path = safe_sample_path(selected_sample)
        is_valid, validation_message = validate_image_path(sample_path, app.config["MAX_CONTENT_LENGTH"]) if sample_path else (False, "Selected sample image is invalid.")
    else:
        is_valid, validation_message = False, "Please upload an image or choose one from the sample gallery."

    if not is_valid:
        decision = decide_risk(
            suspicious=False,
            adversarial=False,
            rate_limited=False,
            integrity_ok=True,
            validation_error=validation_message,
        )
        result.update(
            {
                "status": decision["status"],
                "risk_level": decision["risk_level"],
                "decision_reason": validation_message,
                "rate_limit_message": rate_limit_state["message"],
                "validation_message": validation_message,
                "integrity": {"ok": True, "message": "Integrity verified."},
            }
        )
        finalize_result(result)
        log_security_event(username, result)
        flash(validation_message, "error")
        return render_template(
            "index.html",
            result=result,
            selected_image_url=get_selected_image_url(selected_sample),
            sample_images=sample_images,
            selected_sample=selected_sample or None,
        )

    integrity = verify_integrity()
    if not integrity["ok"]:
        decision = decide_risk(
            suspicious=False,
            adversarial=False,
            rate_limited=False,
            integrity_ok=False,
        )
        result.update(
            {
                "status": decision["status"],
                "risk_level": decision["risk_level"],
                "decision_reason": integrity["message"],
                "rate_limit_message": rate_limit_state["message"],
                "validation_message": validation_message,
                "integrity": integrity,
            }
        )
        finalize_result(result)
        log_security_event(username, result)
        flash(integrity["message"], "error")
        return render_template(
            "index.html",
            result=result,
            selected_image_url=get_selected_image_url(selected_sample),
            sample_images=sample_images,
            selected_sample=selected_sample or None,
        )

    if uploaded_file and uploaded_file.filename:
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(uploaded_file.filename)}"
        file_path = UPLOAD_DIR / filename
        uploaded_file.save(file_path)
        selected_image_url = url_for("uploaded_file", filename=filename)
    else:
        sample_path = safe_sample_path(selected_sample)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{sample_path.name}"
        file_path = UPLOAD_DIR / filename
        shutil.copy2(sample_path, file_path)
        selected_image_url = url_for("sample_image", filename=sample_path.name)

    detection_result = process_image(str(file_path))
    auth_failed = False  # since user already logged in

    decision = decide_risk(
        ml_result=detection_result,
        rate_limited=False,
        auth_failed=auth_failed,
    )

    action = decision["action"]
    if action == "ALLOW":
        status = "allowed"
    elif action == "MONITOR":
        status = "allowed_with_warning"
    elif action == "ALERT":
        status = "allowed_with_warning"
    else:
        status = "blocked"
    result.update(
        {
            "status": status,
            "risk_level": decision["risk"],
            "decision_reason": f"Risk score: {decision['risk']}",
            "risk_breakdown": decision["breakdown"],
            "rate_limit_message": rate_limit_state["message"],
            "validation_message": validation_message,
            "integrity": integrity,
            "filename": filename,
            "prediction": detection_result["label"] if status != "blocked" else None,
            "confidence": detection_result["confidence"] if status != "blocked" else None,
            "verdict": detection_result["verdict"],
            "anomaly": detection_result["anomaly"],
            "adversarial": detection_result["adversarial"],
            "issues": detection_result["issues"],
            "detection": detection_result,
        }
    )
    finalize_result(result)

    log_security_event(username, result)
    return render_template(
        "index.html",
        result=result,
        selected_image_url=selected_image_url,
        sample_images=sample_images,
        selected_sample=selected_sample or None,
    )


@app.route("/uploads/<path:filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/sample-images/<path:filename>", methods=["GET"])
def sample_image(filename):
    return send_from_directory(str(IMAGE_DIR), filename)


def current_timestamp():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def list_sample_images():
    allowed_suffixes = {".jpg", ".jpeg", ".png"}
    images = []
    for path in sorted(IMAGE_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in allowed_suffixes:
            images.append(
                {
                    "name": path.name,
                    "url": url_for("sample_image", filename=path.name),
                }
            )
    return images


def safe_sample_path(filename):
    if not filename:
        return None
    candidate = (IMAGE_DIR / filename).resolve()
    image_root = IMAGE_DIR.resolve()
    if image_root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def get_selected_image_url(selected_sample):
    sample_path = safe_sample_path(selected_sample)
    if not sample_path:
        return None
    return url_for("sample_image", filename=sample_path.name)


def finalize_result(result):
    result["pipeline_steps"] = build_pipeline_steps(result)
    result["audit_log"] = build_audit_log(result)
    result["verdict_style"] = verdict_style_for_status(result.get("status"))


def build_pipeline_steps(result):
    detection = result.get("detection") or {}
    status = result.get("status")
    failure_stage = determine_failure_stage(result)
    step_order = [
        "auth",
        "rate",
        "validate",
        "preprocess",
        "integrity",
        "predict",
        "anomaly",
        "adversarial",
        "decision",
    ]

    steps = [
        {
            "id": "auth",
            "number": "1",
            "title": "Authentication",
            "label": "Identity Check",
            "body": "User session was verified before request processing started.",
            "details": [
                {"label": "User", "value": result.get("username", "Guest")},
                {"label": "Session", "value": "Authenticated"},
            ],
        },
        {
            "id": "rate",
            "number": "2",
            "title": "Rate Limiting",
            "label": "Flood Protection",
            "body": "The request was checked against the per-user throttling policy.",
            "details": [
                {"label": "Policy", "value": "5 req / 60 sec"},
                {"label": "Result", "value": result.get("rate_limit_message", "Not evaluated")},
            ],
        },
        {
            "id": "validate",
            "number": "3",
            "title": "Input Validation",
            "label": "File Safety Check",
            "body": result.get("validation_message", "Uploaded image passed format, size, and readability checks."),
            "details": [
                {"label": "Formats", "value": "JPG, JPEG, PNG"},
                {"label": "Max Size", "value": "5 MB"},
            ],
        },
        {
            "id": "preprocess",
            "number": "4",
            "title": "Preprocessing",
            "label": "Image Preparation",
            "body": "The image was converted to RGB and transformed into a model-ready tensor.",
            "details": [
                {"label": "Color", "value": "RGB"},
                {"label": "Transform", "value": "EfficientNet-B0 default weights"},
            ],
        },
        {
            "id": "integrity",
            "number": "5",
            "title": "Model Integrity Check",
            "label": "Fingerprint Verify",
            "body": "Protected source files and the initialized model weights were hashed and compared against stored fingerprints.",
            "details": [
                {"label": "Config", "value": "config/integrity.json"},
                {"label": "Result", "value": (result.get("integrity") or {}).get("message", "Not evaluated")},
            ],
        },
        {
            "id": "predict",
            "number": "6",
            "title": "Initial AI Prediction",
            "label": "Model Inference",
            "body": "The classifier generated ranked labels for the input image.",
            "details": [
                {"label": "Model", "value": "EfficientNet-B0"},
                {"label": "Top Label", "value": detection.get("label", "Not available")},
                {"label": "Confidence", "value": format_percent(detection.get("confidence"))},
            ],
            "top5": detection.get("top5", []),
        },
        {
            "id": "anomaly",
            "number": "7",
            "title": "Anomaly Detection",
            "label": "Statistical Check",
            "body": join_reasons(
                detection.get("issues", []),
                "Prediction confidence distribution looks normal.",
                {"low top-1 confidence", "high prediction uncertainty", "small gap between top predictions"},
            ),
            "details": [
                {"label": "Top-1", "value": format_percent(detection.get("top1_confidence"))},
                {"label": "Top-2", "value": format_percent(detection.get("top2_confidence"))},
                {"label": "Margin", "value": format_decimal(detection.get("margin"))},
                {"label": "Norm Entropy", "value": format_decimal(detection.get("normalized_entropy"))},
            ],
        },
        {
            "id": "adversarial",
            "number": "8",
            "title": "Adversarial Detection",
            "label": "Attack Probe",
            "body": join_reasons(
                detection.get("issues", []),
                "Prediction remained stable under perturbation checks.",
                {"prediction is fragile to FGSM perturbation", "prediction is unstable under image transforms"},
            ),
            "details": [
                {"label": "FGSM Drop", "value": format_decimal(detection.get("fgsm_confidence_drop"))},
                {"label": "Transform Drop", "value": format_decimal(detection.get("transform_confidence_drop"))},
                {"label": "Unstable", "value": ", ".join(detection.get("transform_instability", [])) or "None"},
            ],
        },
        {
            "id": "decision",
            "number": "9",
            "title": "Risk Decision Engine",
            "label": "Final Verdict",
            "body": result.get("decision_reason", "No decision reason recorded."),
            "details": [
                {"label": "System Status", "value": (status or "unknown").replace("_", " ").title()},
                {"label": "Risk Level", "value": result.get("risk_level", "N/A")},
                {"label": "ML Verdict", "value": result.get("verdict", "Not available").title()},
            ],
        },
    ]

    for step in steps:
        step["status"] = "pass"
        step["badge"] = "PASS"
        step["top5"] = step.get("top5", [])

        if failure_stage:
            failure_index = step_order.index(failure_stage)
            current_index = step_order.index(step["id"])
            if current_index > failure_index:
                step["status"] = "pending"
                step["badge"] = "SKIPPED"
                continue
            if step["id"] == failure_stage:
                step["status"] = "fail"
                step["badge"] = "BLOCKED"
                continue

        if step["id"] == "anomaly" and status == "allowed_with_warning":
            step["status"] = "warn"
            step["badge"] = "WARN"
        elif step["id"] == "anomaly" and detection.get("anomaly"):
            step["status"] = "warn"
            step["badge"] = "SUSPICIOUS"
        elif step["id"] == "adversarial" and detection.get("adversarial"):
            step["status"] = "fail"
            step["badge"] = "ADVERSARIAL"
        elif step["id"] == "decision":
            if status == "allowed":
                step["badge"] = "ALLOW"
            elif status == "allowed_with_warning":
                step["status"] = "warn"
                step["badge"] = "WARN"
            elif status == "blocked":
                step["status"] = "fail"
                step["badge"] = "BLOCK"

    return steps


def build_audit_log(result):
    logs = [
        {"stage": "AUTH", "decision": "pass", "message": f'User "{result.get("username", "unknown")}" authenticated.'},
        {"stage": "RATE", "decision": "pass", "message": result.get("rate_limit_message", "Rate check completed.")},
    ]

    if result.get("validation_message"):
        logs.append({"stage": "VALIDATE", "decision": "pass", "message": result["validation_message"]})

    integrity = result.get("integrity")
    if integrity:
        logs.append(
            {
                "stage": "INTEGRITY",
                "decision": "pass" if integrity.get("ok") else "fail",
                "message": integrity.get("message", "Integrity verification completed."),
            }
        )

    detection = result.get("detection")
    if detection:
        logs.append(
            {
                "stage": "PREDICT",
                "decision": "pass",
                "message": f'Top label "{detection.get("label", "unknown")}" at {format_percent(detection.get("confidence"))}.',
            }
        )
        logs.append(
            {
                "stage": "ANOMALY",
                "decision": "warn" if detection.get("anomaly") else "pass",
                "message": "Suspicious confidence profile detected."
                if detection.get("anomaly")
                else "Confidence profile remained within expected bounds.",
            }
        )
        logs.append(
            {
                "stage": "ADVERSARIAL",
                "decision": "fail" if detection.get("adversarial") else "pass",
                "message": "Adversarial robustness checks were triggered."
                if detection.get("adversarial")
                else "Perturbation checks remained stable.",
            }
        )

    final_decision = "pass" if result.get("status") == "allowed" else "warn" if result.get("status") == "allowed_with_warning" else "fail"
    logs.append({"stage": "DECISION", "decision": final_decision, "message": result.get("decision_reason", "Decision completed.")})
    return logs


def determine_failure_stage(result):
    if result.get("status") != "blocked":
        return None

    decision_reason = (result.get("decision_reason") or "").lower()
    integrity = result.get("integrity") or {}
    detection = result.get("detection") or {}

    if not integrity.get("ok", True):
        return "integrity"
    if "rate limit" in decision_reason or "cooldown" in decision_reason or "too many" in decision_reason:
        return "rate"
    if result.get("validation_message") and result.get("decision_reason") == result.get("validation_message"):
        return "validate"
    if detection.get("adversarial"):
        return "adversarial"
    return "decision"


def verdict_style_for_status(status):
    return {
        "allowed": "allow",
        "allowed_with_warning": "warn",
        "blocked": "block",
    }.get(status, "warn")


def format_percent(value):
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def format_decimal(value):
    if value is None:
        return "N/A"
    return f"{value:.3f}"


def join_reasons(reasons, fallback, allowed_reasons):
    filtered = [reason for reason in reasons if reason in allowed_reasons]
    return "; ".join(filtered) if filtered else fallback


@app.errorhandler(413)
def file_too_large(_error):
    flash("File is too large. Maximum allowed size is 5 MB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    logging.getLogger(__name__).info("Starting secure ML web interface")
    app.run(debug=True)
