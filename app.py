import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from Detection.ml_pipeline import process_image
from auth.auth_service import authenticate_user
from decision.engine import decide_risk
from integrity.checker import verify_integrity
from rate_limit.service import RateLimiter
from validation.image_validator import validate_image_path, validate_image_upload

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
IMAGE_DIR = BASE_DIR / "images"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY", "mini-project-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

rate_limiter = RateLimiter()

# ── Terminal colour helpers ───────────────────────────────────────────────────

_R = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BLUE = "\033[94m"
_MAGENTA = "\033[95m"
_WHITE = "\033[97m"

_METHOD_COLORS = {
    "GET":    _BLUE,
    "POST":   _MAGENTA,
    "PUT":    _YELLOW,
    "DELETE": _RED,
}

_terminal_logger = logging.getLogger("secureml.access")


def _status_color(code: int) -> str:
    if code < 300:
        return _GREEN
    if code < 400:
        return _YELLOW
    return _RED


def _startup_banner(host: str, port: int) -> None:
    print(f"\n{_CYAN}{_BOLD}┌───────────────────────────────────────────┐{_R}")
    print(f"{_CYAN}{_BOLD}│        Secure ML Inference System         │{_R}")
    print(f"{_CYAN}{_BOLD}└───────────────────────────────────────────┘{_R}")
    print(f"  {_GREEN}●{_R} Running on {_BOLD}http://{host}:{port}{_R}")
    print(f"  {_DIM}Model:  EfficientNet-B0 (ImageNet pretrained){_R}")
    print(f"  {_DIM}Press Ctrl+C to stop{_R}\n")
    print(f"  {_DIM}{'TIME':8}  {'METHOD':6}  {'STATUS':6}  {'PATH':<42}  DURATION{_R}")
    print(f"  {_DIM}{'─'*80}{_R}")


# ── Request lifecycle hooks ───────────────────────────────────────────────────

@app.before_request
def _before():
    g.t0 = time.perf_counter()


@app.after_request
def _after(response):
    ms = (time.perf_counter() - g.t0) * 1000
    now = datetime.now().strftime("%H:%M:%S")
    method = request.method
    path = request.path
    code = response.status_code

    mc = _METHOD_COLORS.get(method, _WHITE)
    sc = _status_color(code)

    # Skip noisy static-file requests from terminal view
    if not path.startswith("/static"):
        print(
            f"  {_DIM}{now}{_R}  "
            f"{mc}{method:<6}{_R}  "
            f"{sc}{code}{_R}  "
            f"{path:<42}  "
            f"{_DIM}{ms:.1f}ms{_R}"
        )

    return response


# ── Routes ────────────────────────────────────────────────────────────────────

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
    _terminal_logger.info("LOGIN  user=%s ip=%s", username, request.remote_addr)
    flash("Login successful. You can now submit an image for secure inference.", "success")
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    user = session.get("user", "unknown")
    session.clear()
    _terminal_logger.info("LOGOUT user=%s ip=%s", user, request.remote_addr)
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/settings", methods=["GET"])
def settings():
    username = session.get("user")
    if not username:
        flash("Please log in to access settings.", "error")
        return redirect(url_for("index"))
    return render_template("settings.html", username=username)


@app.route("/analyze", methods=["POST"])
def analyze():
    username = session.get("user")
    if not username:
        flash("Please log in before submitting an image.", "error")
        return redirect(url_for("index"))

    result = {"timestamp": _now(), "username": username}
    sample_images = list_sample_images()

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_state = rate_limiter.check(username, request.remote_addr or "local")
    if not rate_state["allowed"]:
        _terminal_logger.warning("RATE_LIMIT user=%s", username)
        decision = decide_risk(rate_limited=True)
        result.update(
            status=decision["status"],
            risk_level=decision["risk_level"],
            decision_reason=rate_state["message"],
            rate_limit_message=rate_state["message"],
            integrity={"ok": True, "message": "Integrity verified."},
        )
        _finalise(result)
        flash(rate_state["message"], "error")
        return render_template(
            "index.html",
            result=result,
            selected_image_url=None,
            sample_images=sample_images,
            selected_sample=request.form.get("sample_image") or None,
        )

    # ── Input validation ──────────────────────────────────────────────────────
    uploaded_file = request.files.get("image")
    selected_sample = request.form.get("sample_image", "").strip()
    selected_image_url = None

    if uploaded_file and uploaded_file.filename:
        is_valid, validation_message = validate_image_upload(uploaded_file, app.config["MAX_CONTENT_LENGTH"])
    elif selected_sample:
        sample_path = _safe_sample(selected_sample)
        is_valid, validation_message = (
            validate_image_path(sample_path, app.config["MAX_CONTENT_LENGTH"])
            if sample_path
            else (False, "Selected sample image is invalid.")
        )
    else:
        is_valid, validation_message = False, "Please upload an image or choose one from the sample gallery."

    if not is_valid:
        _terminal_logger.warning("VALIDATE_FAIL user=%s reason=%s", username, validation_message)
        decision = decide_risk(validation_error=validation_message)
        result.update(
            status=decision["status"],
            risk_level=decision["risk_level"],
            decision_reason=validation_message,
            rate_limit_message=rate_state["message"],
            validation_message=validation_message,
            integrity={"ok": True, "message": "Integrity verified."},
        )
        _finalise(result)
        flash(validation_message, "error")
        return render_template(
            "index.html",
            result=result,
            selected_image_url=_sample_url(selected_sample),
            sample_images=sample_images,
            selected_sample=selected_sample or None,
        )

    # ── Integrity check ───────────────────────────────────────────────────────
    integrity = verify_integrity()
    if not integrity["ok"]:
        _terminal_logger.warning("INTEGRITY_FAIL details=%s", integrity.get("details"))
        decision = decide_risk(integrity_ok=False)
        result.update(
            status=decision["status"],
            risk_level=decision["risk_level"],
            decision_reason=integrity["message"],
            rate_limit_message=rate_state["message"],
            validation_message=validation_message,
            integrity=integrity,
        )
        _finalise(result)
        flash(integrity["message"], "error")
        return render_template(
            "index.html",
            result=result,
            selected_image_url=_sample_url(selected_sample),
            sample_images=sample_images,
            selected_sample=selected_sample or None,
        )

    # ── Save file ─────────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    if uploaded_file and uploaded_file.filename:
        filename = f"{ts}_{secure_filename(uploaded_file.filename)}"
        file_path = UPLOAD_DIR / filename
        uploaded_file.save(file_path)
        selected_image_url = url_for("uploaded_file", filename=filename)
    else:
        sample_path = _safe_sample(selected_sample)
        filename = f"{ts}_{sample_path.name}"
        file_path = UPLOAD_DIR / filename
        shutil.copy2(sample_path, file_path)
        selected_image_url = url_for("sample_image", filename=sample_path.name)

    # ── ML pipeline ───────────────────────────────────────────────────────────
    _terminal_logger.info("INFERENCE user=%s file=%s", username, filename)
    detection = process_image(str(file_path))

    decision = decide_risk(ml_result=detection)

    _terminal_logger.info(
        "DECISION user=%s verdict=%s risk=%s action=%s label=%s conf=%.2f",
        username,
        detection["verdict"],
        decision["risk"],
        decision["action"],
        detection["label"],
        detection["confidence"],
    )

    result.update(
        status=decision["status"],
        risk_level=decision["risk_level"],
        decision_reason=f"Risk score: {decision['risk']:.3f}",
        risk_breakdown=decision["breakdown"],
        rate_limit_message=rate_state["message"],
        validation_message=validation_message,
        integrity=integrity,
        filename=filename,
        prediction=detection["label"] if decision["status"] != "blocked" else None,
        confidence=detection["confidence"] if decision["status"] != "blocked" else None,
        verdict=detection["verdict"],
        anomaly=detection["anomaly"],
        adversarial=detection["adversarial"],
        issues=detection["issues"],
        detection=detection,
    )
    _finalise(result)

    return render_template(
        "index.html",
        result=result,
        selected_image_url=selected_image_url,
        sample_images=sample_images,
        selected_sample=selected_sample or None,
    )


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/sample-images/<path:filename>")
def sample_image(filename):
    return send_from_directory(str(IMAGE_DIR), filename)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def list_sample_images() -> list:
    allowed = {".jpg", ".jpeg", ".png"}
    return [
        {"name": p.name, "url": url_for("sample_image", filename=p.name)}
        for p in sorted(IMAGE_DIR.iterdir())
        if p.is_file() and p.suffix.lower() in allowed
    ]


def _safe_sample(filename: str):
    if not filename:
        return None
    candidate = (IMAGE_DIR / filename).resolve()
    if IMAGE_DIR.resolve() not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def _sample_url(selected_sample: str):
    path = _safe_sample(selected_sample)
    return url_for("sample_image", filename=path.name) if path else None


def _finalise(result: dict) -> None:
    result["pipeline_steps"] = _build_pipeline(result)
    result["audit_log"] = _build_audit(result)
    result["verdict_style"] = {"allowed": "allow", "allowed_with_warning": "warn", "blocked": "block"}.get(
        result.get("status"), "warn"
    )


# ── Pipeline builder (unchanged logic, same data fed to new template) ─────────

def _build_pipeline(result: dict) -> list:
    detection = result.get("detection") or {}
    status = result.get("status")
    failure_stage = _failure_stage(result)
    step_order = ["auth", "rate", "validate", "preprocess", "integrity", "predict", "anomaly", "adversarial", "decision"]

    steps = [
        {
            "id": "auth", "number": "1", "title": "Authentication", "label": "Identity Check",
            "body": "User session was verified before request processing started.",
            "details": [{"label": "User", "value": result.get("username", "Guest")}, {"label": "Session", "value": "Authenticated"}],
        },
        {
            "id": "rate", "number": "2", "title": "Rate Limiting", "label": "Flood Protection",
            "body": "The request was checked against the per-user throttling policy.",
            "details": [{"label": "Policy", "value": "5 req / 60 sec"}, {"label": "Result", "value": result.get("rate_limit_message", "Not evaluated")}],
        },
        {
            "id": "validate", "number": "3", "title": "Input Validation", "label": "File Safety Check",
            "body": result.get("validation_message", "Uploaded image passed format, size, and readability checks."),
            "details": [{"label": "Formats", "value": "JPG, JPEG, PNG"}, {"label": "Max Size", "value": "5 MB"}],
        },
        {
            "id": "preprocess", "number": "4", "title": "Preprocessing", "label": "Image Preparation",
            "body": "Image converted to RGB and transformed into a model-ready tensor.",
            "details": [{"label": "Color", "value": "RGB"}, {"label": "Transform", "value": "EfficientNet-B0 default"}],
        },
        {
            "id": "integrity", "number": "5", "title": "Model Integrity", "label": "Fingerprint Verify",
            "body": "Protected source files and model weights hashed and compared against stored fingerprints.",
            "details": [{"label": "Config", "value": "config/integrity.json"}, {"label": "Result", "value": (result.get("integrity") or {}).get("message", "Not evaluated")}],
        },
        {
            "id": "predict", "number": "6", "title": "AI Prediction", "label": "Model Inference",
            "body": "Classifier generated ranked labels for the input image.",
            "details": [
                {"label": "Model", "value": "EfficientNet-B0"},
                {"label": "Top Label", "value": detection.get("label", "N/A")},
                {"label": "Confidence", "value": _pct(detection.get("confidence"))},
            ],
            "top5": detection.get("top5", []),
        },
        {
            "id": "anomaly", "number": "7", "title": "Anomaly Detection", "label": "Statistical Check",
            "body": _join_reasons(detection.get("issues", []), "Confidence distribution within expected bounds.", {"low top-1 confidence", "high prediction uncertainty", "small gap between top predictions"}),
            "details": [
                {"label": "Top-1", "value": _pct(detection.get("top1_confidence"))},
                {"label": "Top-2", "value": _pct(detection.get("top2_confidence"))},
                {"label": "Margin", "value": _dec(detection.get("margin"))},
                {"label": "Norm Entropy", "value": _dec(detection.get("normalized_entropy"))},
            ],
        },
        {
            "id": "adversarial", "number": "8", "title": "Adversarial Detection", "label": "Attack Probe",
            "body": _join_reasons(detection.get("issues", []), "Prediction stable under perturbation checks.", {"prediction is fragile to FGSM perturbation", "prediction is unstable under image transforms"}),
            "details": [
                {"label": "FGSM Drop", "value": _dec(detection.get("fgsm_confidence_drop"))},
                {"label": "Transform Drop", "value": _dec(detection.get("transform_confidence_drop"))},
                {"label": "Unstable", "value": ", ".join(detection.get("transform_instability", [])) or "None"},
            ],
        },
        {
            "id": "decision", "number": "9", "title": "Risk Decision", "label": "Final Verdict",
            "body": result.get("decision_reason", "No decision recorded."),
            "details": [
                {"label": "System Status", "value": (status or "unknown").replace("_", " ").title()},
                {"label": "Risk Level", "value": result.get("risk_level", "N/A")},
                {"label": "ML Verdict", "value": result.get("verdict", "N/A").title()},
            ],
        },
    ]

    for step in steps:
        step.setdefault("top5", [])
        step["status"] = "pass"
        step["badge"] = "PASS"

        if failure_stage:
            fi = step_order.index(failure_stage)
            ci = step_order.index(step["id"])
            if ci > fi:
                step["status"] = "pending"
                step["badge"] = "SKIPPED"
                continue
            if step["id"] == failure_stage:
                step["status"] = "fail"
                step["badge"] = "BLOCKED"
                continue

        if step["id"] == "anomaly":
            if detection.get("anomaly"):
                step["status"] = "warn"
                step["badge"] = "WARN"
        elif step["id"] == "adversarial":
            if detection.get("adversarial"):
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


def _build_audit(result: dict) -> list:
    logs = [
        {"stage": "AUTH", "decision": "pass", "message": f'User "{result.get("username", "unknown")}" authenticated.'},
        {"stage": "RATE", "decision": "pass", "message": result.get("rate_limit_message", "Rate check completed.")},
    ]
    if result.get("validation_message"):
        logs.append({"stage": "VALIDATE", "decision": "pass", "message": result["validation_message"]})

    integrity = result.get("integrity")
    if integrity:
        logs.append({
            "stage": "INTEGRITY",
            "decision": "pass" if integrity.get("ok") else "fail",
            "message": integrity.get("message", "Integrity check completed."),
        })

    det = result.get("detection")
    if det:
        logs.append({"stage": "PREDICT", "decision": "pass", "message": f'"{det.get("label", "?")}" at {_pct(det.get("confidence"))}.'})
        logs.append({
            "stage": "ANOMALY",
            "decision": "warn" if det.get("anomaly") else "pass",
            "message": "Suspicious confidence profile detected." if det.get("anomaly") else "Confidence profile normal.",
        })
        logs.append({
            "stage": "ADVERSARIAL",
            "decision": "fail" if det.get("adversarial") else "pass",
            "message": "Adversarial checks triggered." if det.get("adversarial") else "Perturbation checks stable.",
        })

    final = {"allowed": "pass", "allowed_with_warning": "warn", "blocked": "fail"}.get(result.get("status"), "warn")
    logs.append({"stage": "DECISION", "decision": final, "message": result.get("decision_reason", "Decision completed.")})
    return logs


def _failure_stage(result: dict):
    if result.get("status") != "blocked":
        return None
    reason = (result.get("decision_reason") or "").lower()
    integrity = result.get("integrity") or {}
    detection = result.get("detection") or {}
    if not integrity.get("ok", True):
        return "integrity"
    if any(k in reason for k in ("rate limit", "cooldown", "too many", "burst", "bot")):
        return "rate"
    if result.get("validation_message") and result.get("decision_reason") == result.get("validation_message"):
        return "validate"
    if detection.get("adversarial"):
        return "adversarial"
    return "decision"


def _pct(v):
    return f"{v * 100:.2f}%" if v is not None else "N/A"


def _dec(v):
    return f"{v:.3f}" if v is not None else "N/A"


def _join_reasons(reasons, fallback, allowed):
    filtered = [r for r in reasons if r in allowed]
    return "; ".join(filtered) if filtered else fallback


@app.errorhandler(413)
def _too_large(_e):
    flash("File is too large. Maximum allowed size is 5 MB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    HOST = "127.0.0.1"
    PORT = int(os.environ.get("PORT", 5000))
    _startup_banner(HOST, PORT)
    # Suppress werkzeug's own request logger to avoid duplicate lines
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.run(host=HOST, port=PORT, debug=True)
