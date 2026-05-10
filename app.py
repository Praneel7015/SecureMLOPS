import json
import logging
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, flash, g, redirect, render_template, request, send_from_directory, session, url_for, jsonify
from werkzeug.utils import secure_filename

from auth.auth_service import authenticate_user
from core.runtime import get_device
from Detection.custom_pipeline import process_custom_image
from decision.engine import decide_risk
from rate_limit.service import RateLimiter
from training.config import MAX_DATASET_UPLOAD_BYTES, MAX_MODEL_UPLOAD_BYTES, SUPPORTED_MODELS
from training.job_manager import bootstrap_job_manager, submit_training_job
from training.model_factory import load_model_from_checkpoint
from training.registry import get_dataset, get_model, list_datasets, list_models, save_dataset_metadata
from training.validator import safe_load_checkpoint, validate_dataset_zip, validate_training_config
from utils.logging_setup import configure_logging, log_security_event
from validation.image_validator import validate_image_path, validate_image_upload

from access_analysis import analyse_request


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATASET_UPLOAD_DIR = UPLOAD_DIR / "datasets"
MODEL_UPLOAD_DIR = UPLOAD_DIR / "models"
IMAGE_DIR = BASE_DIR / "images"
MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024
_REACT_DIST_CANDIDATES = [
    BASE_DIR / "frontend" / "dist",
    BASE_DIR / "Design SecureMLOPS UI" / "dist",  # legacy folder name fallback
]
REACT_DIST_DIR = next((p for p in _REACT_DIST_CANDIDATES if p.exists()), _REACT_DIST_CANDIDATES[0])
REACT_ASSETS_DIR = REACT_DIST_DIR / "assets"
UPLOAD_DIR.mkdir(exist_ok=True)
DATASET_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MODEL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY", "mini-project-secret-key")
app.config["MAX_CONTENT_LENGTH"] = MAX_DATASET_UPLOAD_BYTES
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

rate_limiter = RateLimiter()
configure_logging(BASE_DIR / "logs" / "security.log")
bootstrap_job_manager()

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


def _wants_json() -> bool:
    return (
        request.is_json
        or request.args.get("format") == "json"
        or "application/json" in request.headers.get("Accept", "")
    )


def _serve_react_index():
    react_index = REACT_DIST_DIR / "index.html"
    if react_index.exists():
        return send_from_directory(str(REACT_DIST_DIR), "index.html")
    return "React frontend build not found. Run npm run build in frontend.", 503


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return _serve_react_index()


@app.route("/assets/<path:filename>", methods=["GET"])
def react_assets(filename):
    if REACT_ASSETS_DIR.exists():
        return send_from_directory(str(REACT_ASSETS_DIR), filename)
    return "", 404


@app.route("/vite.svg", methods=["GET"])
def react_vite_icon():
    if REACT_DIST_DIR.exists():
        return send_from_directory(str(REACT_DIST_DIR), "vite.svg")
    return "", 404


@app.route("/api/bootstrap", methods=["GET"])
def api_bootstrap():
    username = session.get("user")
    return jsonify(
        {
            "authenticated": bool(username),
            "username": username,
            "sample_images": list_sample_images(),
            "max_upload_size_mb": MAX_IMAGE_UPLOAD_BYTES // (1024 * 1024),
            "max_dataset_upload_mb": MAX_DATASET_UPLOAD_BYTES // (1024 * 1024),
            "max_model_upload_mb": MAX_MODEL_UPLOAD_BYTES // (1024 * 1024),
            "supported_models": [
                {"id": key, "label": value["label"]} for key, value in SUPPORTED_MODELS.items()
            ],
        }
    )


@app.route("/login", methods=["POST"])
def login():
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
    else:
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

    success, message = authenticate_user(username, password)
    if not success:
        if _wants_json():
            return jsonify({"success": False, "message": message}), 401
        return redirect(url_for("index", login_error=message))

    session["user"] = username
    _terminal_logger.info("LOGIN  user=%s ip=%s", username, request.remote_addr)
    if _wants_json():
        return jsonify({"success": True, "message": "Login successful.", "username": username})
    return redirect(url_for("index"))


@app.route("/api/inference", methods=["POST"])
def api_inference():
    return analyze()


@app.route("/api/training/datasets", methods=["POST"])
def api_training_dataset_upload():
    username = session.get("user")
    if not username:
        return jsonify({"success": False, "message": "Please log in to upload datasets."}), 401

    rate_state = rate_limiter.check(username, request.remote_addr or "local", mode="training")
    if not rate_state["allowed"]:
        return jsonify({"success": False, "message": rate_state["message"]}), 429

    dataset_file = request.files.get("dataset")
    if not dataset_file or not dataset_file.filename:
        return jsonify({"success": False, "message": "Dataset ZIP is required."}), 400

    access_result = analyse_request(
        user_id=username,
        input_identifier=dataset_file.filename,
        request_type="training",
        response_status="200",
    )
    if not access_result["allowed"]:
        return jsonify({"success": False, "message": access_result["reason"]}), 403

    dataset_id = uuid.uuid4().hex
    dataset_dir = DATASET_UPLOAD_DIR / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dataset_dir / secure_filename(dataset_file.filename)
    dataset_file.save(zip_path)

    validation = validate_dataset_zip(zip_path, dataset_dir)
    if not validation.ok:
        shutil.rmtree(dataset_dir, ignore_errors=True)
        return jsonify({"success": False, "message": validation.message}), 400

    metadata = {
        "dataset_dir": str(validation.dataset_dir),
        "class_names": validation.class_names,
        "image_count": validation.image_count,
        "class_distribution": validation.class_distribution,
        "source_name": dataset_file.filename,
        "owner": username,
    }
    record = save_dataset_metadata(dataset_id, metadata)
    zip_path.unlink(missing_ok=True)

    return jsonify(
        {
            "success": True,
            "message": "Dataset uploaded and validated.",
            "dataset": record,
        }
    )


@app.route("/api/training/datasets", methods=["GET"])
def api_training_dataset_list():
    username = session.get("user")
    if not username:
        return jsonify({"success": False, "message": "Please log in to view datasets."}), 401
    return jsonify({"success": True, "datasets": list_datasets(owner=username)})


@app.route("/api/training/start", methods=["POST"])
def api_training_start():
    username = session.get("user")
    if not username:
        return jsonify({"success": False, "message": "Please log in to start training."}), 401

    rate_state = rate_limiter.check(username, request.remote_addr or "local", mode="training")
    if not rate_state["allowed"]:
        return jsonify({"success": False, "message": rate_state["message"]}), 429

    payload = request.get_json(silent=True) or {}
    dataset_id = str(payload.get("dataset_id", "")).strip()
    if not dataset_id:
        return jsonify({"success": False, "message": "dataset_id is required."}), 400

    dataset = get_dataset(dataset_id)
    if not dataset:
        return jsonify({"success": False, "message": "Dataset not found."}), 404
    if dataset.get("owner") != username:
        return jsonify({"success": False, "message": "Dataset access denied."}), 403

    access_result = analyse_request(
        user_id=username,
        input_identifier=f"training:{dataset_id}",
        request_type="training",
        response_status="200",
    )
    if not access_result["allowed"]:
        return jsonify({"success": False, "message": access_result["reason"]}), 403

    ok, message, cleaned = validate_training_config(payload)
    if not ok:
        return jsonify({"success": False, "message": message}), 400

    dataset_dir = dataset.get("dataset_dir")
    if not dataset_dir or not Path(dataset_dir).exists():
        return jsonify({"success": False, "message": "Dataset directory missing."}), 400

    try:
        job = submit_training_job(dataset_id, dataset_dir, cleaned, owner=username)
    except RuntimeError as exc:
        return jsonify({"success": False, "message": str(exc)}), 429

    return jsonify({"success": True, "job": job})


@app.route("/api/training/jobs", methods=["GET"])
def api_training_jobs():
    username = session.get("user")
    if not username:
        return jsonify({"success": False, "message": "Please log in to view jobs."}), 401
    from training.progress_tracker import list_jobs
    return jsonify({"success": True, "jobs": list_jobs(owner=username)})


@app.route("/api/training/jobs/<job_id>", methods=["GET"])
def api_training_job_status(job_id: str):
    username = session.get("user")
    if not username:
        return jsonify({"success": False, "message": "Please log in to view jobs."}), 401
    from training.progress_tracker import get_job
    job = get_job(job_id)
    if not job:
        return jsonify({"success": False, "message": "Job not found."}), 404
    if job.get("owner") != username:
        return jsonify({"success": False, "message": "Job access denied."}), 403
    return jsonify({"success": True, "job": job})


@app.route("/api/training/models", methods=["GET"])
def api_training_models():
    username = session.get("user")
    if not username:
        return jsonify({"success": False, "message": "Please log in to view models."}), 401
    return jsonify({"success": True, "models": list_models(owner=username)})


@app.route("/api/training/models/<model_id>/download", methods=["GET"])
def api_training_model_download(model_id: str):
    username = session.get("user")
    if not username:
        return jsonify({"success": False, "message": "Please log in to download models."}), 401

    model = get_model(model_id)
    if not model:
        return jsonify({"success": False, "message": "Model not found."}), 404
    if model.get("owner") != username:
        return jsonify({"success": False, "message": "Model access denied."}), 403

    file_path = Path(model.get("file_path", ""))
    if not file_path.exists():
        return jsonify({"success": False, "message": "Model file missing."}), 404

    return send_from_directory(str(file_path.parent), file_path.name, as_attachment=True)


@app.route("/logout", methods=["POST"])
def logout():
    user = session.get("user", "unknown")
    session.clear()
    _terminal_logger.info("LOGOUT user=%s ip=%s", user, request.remote_addr)
    if _wants_json():
        return jsonify({"success": True, "message": "Logged out."})
    return redirect(url_for("index"))


@app.route("/settings", methods=["GET"])
def settings():
    username = session.get("user")
    if not username:
        if _wants_json():
            return jsonify({"success": False, "message": "Please log in to access settings."}), 401
        return _serve_react_index()

    if _wants_json():
        return jsonify({"success": True, "username": username})
    return _serve_react_index()


@app.route("/analyze", methods=["POST"])
def analyze():
    username = session.get("user")
    wants_json = _wants_json()

    if not username:
        if wants_json:
            return jsonify({"success": False, "message": "Please log in before submitting an image."}), 401
        return redirect(url_for("index"))

    result = {"timestamp": _now(), "username": username}
    sample_images = list_sample_images()

    # ── Rate limiting ─────────────────────────────────────────────────────────
    pipeline_mode = request.form.get("pipeline_mode", "inference")
    rate_state = rate_limiter.check(
        username,
        request.remote_addr or "local",
        mode=pipeline_mode,
    )
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
        log_security_event(username, result)
        if wants_json:
            return jsonify(
                {
                    "success": False,
                    "message": rate_state["message"],
                    "result": result,
                    "selected_image_url": None,
                    "sample_images": sample_images,
                    "selected_sample": request.form.get("sample_image") or None,
                }
            ), 429
        return redirect(url_for("index"))

    # ── Input validation ──────────────────────────────────────────────────────
    uploaded_file = request.files.get("image")
    uploaded_model = request.files.get("model")
    selected_sample = request.form.get("sample_image", "").strip()
    selected_image_url = None

    if uploaded_file and uploaded_file.filename:
        is_valid, validation_message = validate_image_upload(uploaded_file, MAX_IMAGE_UPLOAD_BYTES)
        input_identifier = uploaded_file.filename
    elif selected_sample:
        sample_path = _safe_sample(selected_sample)
        is_valid, validation_message = (
            validate_image_path(sample_path, MAX_IMAGE_UPLOAD_BYTES)
            if sample_path
            else (False, "Selected sample image is invalid.")
        )
        input_identifier = selected_sample

    else:
        is_valid, validation_message = False, "Please upload an image or choose one from the sample gallery."
        input_identifier = "__no_input__"

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
        log_security_event(username, result)
        if wants_json:
            return jsonify(
                {
                    "success": False,
                    "message": validation_message,
                    "result": result,
                    "selected_image_url": _sample_url(selected_sample),
                    "sample_images": sample_images,
                    "selected_sample": selected_sample or None,
                }
            ), 400
        return redirect(url_for("index"))

    # ── Integrity check ───────────────────────────────────────────────────────
    try:
        from integrity.checker import verify_integrity
    except Exception as exc:
        _terminal_logger.exception("INTEGRITY_RUNTIME_UNAVAILABLE error=%s", exc)
        verify_integrity = None

    if verify_integrity is None:
        integrity = {"ok": False, "message": "Integrity runtime unavailable on this machine."}
    else:
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
        log_security_event(username, result)
        flash(integrity["message"], "error")
        return render_template(
            "index.html",
            result=result,
            selected_image_url=_sample_url(selected_sample),
            sample_images=sample_images,
            selected_sample=selected_sample or None,
        )
    # ────────────────────────────────────────────────────────────────────────
    # ── ACCESS ANALYSIS  ───────────────────────
    # ────────────────────────────────────────────────────────────────────────
    access_result = analyse_request(
        user_id          = username,
        input_identifier = input_identifier,
        request_type     = pipeline_mode,
        response_status  = "200",           # optimistic; updated below if blocked
    )

    if not access_result["allowed"]:
        _terminal_logger.warning(
            "ACCESS_BLOCK user=%s risk=%.3f reason=%s",
            username, access_result["final_risk"], access_result["reason"],
        )
        result.update(
            status              = "blocked",
            risk_level          = _access_risk_level(access_result["final_risk"]),
            decision_reason     = access_result["reason"],
            rate_limit_message  = rate_state["message"],
            validation_message  = validation_message,
            integrity           = integrity,
            access_analysis     = access_result,
        )
        _finalise(result)
        log_security_event(username, result)
        flash(f"Access blocked: {access_result['reason']}", "error")
        return render_template(
            "index.html",
            result=result,
            selected_image_url=_sample_url(selected_sample),
            sample_images=sample_images,
            selected_sample=selected_sample or None,
        )
    # ── Optional custom model validation ───────────────────────────────────
    custom_model = None
    model_meta = None
    model_path = None
    if uploaded_model and uploaded_model.filename:
        custom_model, model_meta, model_error, model_path = _load_custom_model(uploaded_model)
        if model_error:
            _terminal_logger.warning("MODEL_VALIDATE_FAIL user=%s reason=%s", username, model_error)
            decision = decide_risk(validation_error=model_error)
            result.update(
                status=decision["status"],
                risk_level=decision["risk_level"],
                decision_reason=model_error,
                rate_limit_message=rate_state["message"],
                validation_message=model_error,
                integrity=integrity,
                access_analysis=access_result,
            )
            _finalise(result)
            log_security_event(username, result)
            if wants_json:
                return jsonify(
                    {
                        "success": False,
                        "message": model_error,
                        "result": result,
                        "selected_image_url": _sample_url(selected_sample),
                        "sample_images": sample_images,
                        "selected_sample": selected_sample or None,
                    }
                ), 400
            return redirect(url_for("index"))
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
    model_source = "default"
    model_type = "efficientnet-b0"
    model_name = "EfficientNet-B0"
    model_info = {
        "model_source": "default",
        "model_name": "EfficientNet-B0",
        "model_type": "EfficientNet-B0",
        "checkpoint_loaded": True,
        "class_names": _default_class_names(),
        "num_classes": 1000,
        "model_created_at": None,
        "reconstruction_status": "default_loaded",
    }
    try:
        if custom_model is not None and model_meta is not None:
            model_source = "uploaded"
            model_type = model_meta["model_type"]
            model_name = model_meta.get("model_name", model_type)
            model_info = {
                "model_source": "uploaded",
                "model_name": model_name,
                "model_type": model_type,
                "checkpoint_loaded": bool(model_meta.get("checkpoint_loaded")),
                "class_names": model_meta.get("class_names"),
                "num_classes": model_meta.get("num_classes"),
                "model_created_at": model_meta.get("created_at"),
                "reconstruction_status": "success",
            }
            _terminal_logger.info(
                "MODEL_LOAD user=%s source=uploaded name=%s type=%s classes=%s",
                username,
                model_name,
                model_type,
                model_meta.get("num_classes"),
            )
            _terminal_logger.info("INFERENCE user=%s file=%s model=%s", username, filename, model_name)
            detection = process_custom_image(
                str(file_path),
                custom_model,
                model_meta["class_names"],
                model_meta["image_size"],
                get_device(),
            )
        else:
            from Detection.ml_pipeline import process_image
            _terminal_logger.info("MODEL_LOAD user=%s source=default name=%s", username, model_name)
            _terminal_logger.info("INFERENCE user=%s file=%s", username, filename)
            detection = process_image(str(file_path))
    except Exception as exc:
        _terminal_logger.exception("ML_RUNTIME_UNAVAILABLE error=%s", exc)
        _terminal_logger.warning(
            "MODEL_FALLBACK user=%s source=%s name=%s reason=%s",
            username,
            model_source,
            model_name,
            exc,
        )
        decision = decide_risk(validation_error="ML runtime unavailable")
        result.update(
            status=decision["status"],
            risk_level=decision["risk_level"],
            decision_reason="ML runtime is unavailable on this machine. Frontend remains operational.",
            rate_limit_message=rate_state["message"],
            validation_message=validation_message,
            integrity=integrity,
            filename=filename,
            prediction=None,
            confidence=None,
            verdict="unknown",
            anomaly=True,
            adversarial=False,
            issues=["ml runtime unavailable"],
            detection={
                "label": "N/A",
                "confidence": None,
                "verdict": "unknown",
                "anomaly": True,
                "adversarial": False,
                "issues": ["ml runtime unavailable"],
                "top5": [],
                "top1_confidence": None,
                "top2_confidence": None,
                "margin": None,
                "normalized_entropy": None,
                "fgsm_confidence_drop": None,
                "transform_confidence_drop": None,
                "transform_instability": [],
            },
        )
        _finalise(result)
        log_security_event(username, result)
        if model_path:
            model_path.unlink(missing_ok=True)
        if wants_json:
            return jsonify(
                {
                    "success": False,
                    "message": "ML runtime unavailable",
                    "result": result,
                    "selected_image_url": selected_image_url,
                    "sample_images": sample_images,
                    "selected_sample": selected_sample or None,
                }
            ), 503
        return redirect(url_for("index"))
    finally:
        if model_path:
            model_path.unlink(missing_ok=True)

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
        model_type=model_info.get("model_type"),
        model_source=model_info.get("model_source"),
        model_name=model_info.get("model_name"),
        checkpoint_loaded=model_info.get("checkpoint_loaded"),
        class_names=model_info.get("class_names"),
        num_classes=model_info.get("num_classes"),
        model_created_at=model_info.get("model_created_at"),
        reconstruction_status=model_info.get("reconstruction_status"),
        prediction=detection["label"] if decision["status"] != "blocked" else None,
        confidence=detection["confidence"] if decision["status"] != "blocked" else None,
        verdict=detection["verdict"],
        anomaly=detection["anomaly"],
        adversarial=detection["adversarial"],
        issues=detection["issues"],
        detection=detection,
        access_analysis=access_result,
    )
    _finalise(result)
    log_security_event(username, result)
    if wants_json:
        return jsonify(
            {
                "success": True,
                "message": "Analysis completed.",
                "result": result,
                "selected_image_url": selected_image_url,
                "sample_images": sample_images,
                "selected_sample": selected_sample or None,
            }
        )
    return redirect(url_for("index"))


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


def _default_class_names() -> list[str] | None:
    try:
        from torchvision.models import EfficientNet_B0_Weights
        return list(EfficientNet_B0_Weights.DEFAULT.meta.get("categories", []))
    except Exception:
        return None


def _load_custom_model(uploaded_model):
    if not uploaded_model or not uploaded_model.filename:
        return None, None, None, None

    filename = secure_filename(uploaded_model.filename)
    if not filename.lower().endswith((".pt", ".pth")):
        return None, None, "Only .pt checkpoints are supported.", None

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    model_path = MODEL_UPLOAD_DIR / f"{ts}_{filename}"
    uploaded_model.save(model_path)

    if model_path.stat().st_size > MAX_MODEL_UPLOAD_BYTES:
        model_path.unlink(missing_ok=True)
        return None, None, "Model file exceeds upload limit.", None

    device = get_device()
    ok, message, checkpoint = safe_load_checkpoint(model_path, device)
    if not ok:
        model_path.unlink(missing_ok=True)
        return None, None, message, None

    try:
        model, meta = load_model_from_checkpoint(checkpoint, device)
    except Exception as exc:
        model_path.unlink(missing_ok=True)
        return None, None, f"Failed to load model: {exc}", None

    meta["model_name"] = filename
    meta["checkpoint_loaded"] = True
    return model, meta, None, model_path

def _access_risk_level(risk: float) -> str:
    if risk <= 0.35:
        return "LOW"
    elif risk <= 0.65:
        return "MEDIUM"
    return "HIGH"

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
    access = result.get("access_analysis") or {}

    step_order = ["auth", "rate", "validate", "preprocess", "integrity","access", "predict", "anomaly", "adversarial", "decision"]

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
            "details": [
                {"label": "Color", "value": "RGB"},
                {"label": "Transform", "value": f"{result.get('model_name', 'EfficientNet-B0')} default"},
            ],
        },
        {
            "id": "integrity", "number": "5", "title": "Model Integrity", "label": "Fingerprint Verify",
            "body": "Protected source files and model weights hashed and compared against stored fingerprints.",
            "details": [{"label": "Config", "value": "config/integrity.json"}, {"label": "Result", "value": (result.get("integrity") or {}).get("message", "Not evaluated")}],
        },
        # ── NEW: Access Analysis pipeline step ────────────────────────────
        {
            "id": "access", "number": "6", "title": "Access Analysis", "label": "Behaviour Check",
            "body": access.get("reason", "Behavioural access analysis completed."),
            "details": [
                {"label": "Access Risk",  "value": f"{access.get('final_risk', 0):.3f}"},
                {"label": "Frequency",    "value": f"{(access.get('breakdown') or {}).get('frequency_risk', 0):.3f}"},
                {"label": "Timing",       "value": f"{(access.get('breakdown') or {}).get('timing_risk', 0):.3f}"},
                {"label": "Repetition",   "value": f"{(access.get('breakdown') or {}).get('repetition_risk', 0):.3f}"},
                {"label": "Hist. Avg",    "value": f"{access.get('historical_avg'):.3f}" if access.get("historical_avg") is not None else "N/A"},
                {"label": "Decision",     "value": access.get("decision", "N/A")},
            ],
        },
        {
            "id": "predict", "number": "6", "title": "AI Prediction", "label": "Model Inference",
            "body": "Classifier generated ranked labels for the input image.",
            "details": [
                {"label": "Model", "value": result.get("model_name", "EfficientNet-B0")},
                {"label": "Source", "value": result.get("model_source", "default").title()},
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
    access = result.get("access_analysis") or {}
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

    # ── Access Analysis audit entry ───────────────────────────────────────────
    if access:
        _dec_map = {"ALLOW": "pass", "MONITOR": "warn", "BLOCK": "fail"}
        logs.append({
            "stage":    "ACCESS",
            "decision": _dec_map.get(access.get("decision", "ALLOW"), "pass"),
            "message":  (
                f"{access.get('reason', 'Access analysis completed.')} "
                f"(risk={access.get('final_risk', 0):.3f})"
            ),
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
    access = result.get("access_analysis") or {}

    if not integrity.get("ok", True):
        return "integrity"
    if any(k in reason for k in ("rate limit", "cooldown", "too many", "burst", "bot")):
        return "rate"
    if result.get("validation_message") and result.get("decision_reason") == result.get("validation_message"):
        return "validate"
    if access.get("decision") == "BLOCK":
        return "access"
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
    if _wants_json():
        return jsonify({"success": False, "message": "File is too large. Maximum allowed size is 600 MB."}), 413
    return redirect(url_for("index"))


if __name__ == "__main__":
    HOST = "127.0.0.1"
    PORT = int(os.environ.get("PORT", 5000))
    _startup_banner(HOST, PORT)
    # Suppress werkzeug's own request logger to avoid duplicate lines
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.run(host=HOST, port=PORT, debug=True)
