"""
MLP-based data poisoning detector for ResNet18 multilayer embedding space.

Uses a fixed victim model (attacked_model_multi_attack.pth) to extract layer2,
layer3, and avgpool embeddings, scales them, augments with L2 norm / confidence /
entropy, and scores with a persisted sklearn MLP classifier.

Poisoning detection is only active when the active inference architecture is
ResNet18-compatible; other architectures receive an explicit unavailable state.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models, transforms

from training.model_factory import resolve_model_type

logger = logging.getLogger("secureml.poisoning")

_MODELS_DIR = Path(__file__).resolve().parent / "security_models"
_CONFIG_PATH = _MODELS_DIR / "detector_config.json"

_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]

_MLP_CANDIDATES = ("poisoning_mlp.pkl", "detector_mlp.pkl")
_SCALER_NAME = "scaler.pkl"

_config: dict[str, Any] | None = None
_victim_model: nn.Module | None = None
_victim_device: torch.device | None = None
_feature_extractor: "ResNet18MultilayerFeatureExtractor | None" = None
_mlp_detector: Any | None = None
_scaler: Any | None = None
_load_warnings_emitted: set[str] = set()
_events_emitted: set[str] = set()


class ResNet18MultilayerFeatureExtractor:
    """Forward hooks on layer2, layer3, avgpool with adaptive average pooling."""

    LAYER_DIMS = {"layer2": 128, "layer3": 256, "avgpool": 512}
    LAYER_ORDER = ("layer2", "layer3", "avgpool")

    def __init__(self, model: nn.Module, layers: tuple[str, ...] | None = None) -> None:
        self.model = model
        self.layers = layers or self.LAYER_ORDER
        self._activations: dict[str, torch.Tensor] = {}
        self._handles: list[Any] = []

        for layer_name in self.layers:
            module = getattr(model, layer_name, None)
            if module is None:
                raise ValueError(f"Victim model missing layer hook target: {layer_name}")
            self._handles.append(module.register_forward_hook(self._make_hook(layer_name)))

    def _make_hook(self, name: str):
        def hook(_module: nn.Module, _inputs: tuple[torch.Tensor, ...], output: torch.Tensor) -> None:
            tensor = output
            if tensor.dim() == 4:
                tensor = F.adaptive_avg_pool2d(tensor, 1).flatten(1)
            self._activations[name] = tensor

        return hook

    def close(self) -> None:
        for handle in self._handles:
            handle.remove()
        self._handles.clear()

    @torch.no_grad()
    def forward(self, x_norm: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        self._activations.clear()
        logits = self.model(x_norm)
        missing = [layer for layer in self.layers if layer not in self._activations]
        if missing:
            raise RuntimeError(f"Missing activations for layers: {missing}")

        parts = [self._activations[layer] for layer in self.layers]
        embeddings = torch.cat(parts, dim=1).float()
        return logits.float(), embeddings

    @staticmethod
    def expected_embedding_dim(layers: tuple[str, ...] | None = None) -> int:
        order = layers or ResNet18MultilayerFeatureExtractor.LAYER_ORDER
        return sum(ResNet18MultilayerFeatureExtractor.LAYER_DIMS[name] for name in order)


def _resolve_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _warn_once(key: str, message: str) -> None:
    if key in _load_warnings_emitted:
        return
    _load_warnings_emitted.add(key)
    logger.warning(message)


def _emit_poisoning_event(
    event_type: str,
    title: str,
    description: str,
    metadata: dict[str, Any] | None = None,
    *,
    once: bool = False,
) -> None:
    if once:
        once_key = f"{event_type}:{title}"
        if once_key in _events_emitted:
            return
        _events_emitted.add(once_key)
    try:
        from telemetry.events import EventSeverity, EventSource, emit_event

        severity = EventSeverity.WARNING
        if event_type.endswith(".detected") or event_type.endswith(".high_risk"):
            severity = EventSeverity.HIGH
        elif event_type.endswith(".unavailable"):
            severity = EventSeverity.INFO

        emit_event(
            severity=severity,
            event_type=event_type,
            source=EventSource.POISONING,
            title=title,
            description=description,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.exception("Failed to emit poisoning telemetry event: %s", exc)


def reset_poisoning_cache() -> None:
    global _config, _victim_model, _victim_device, _feature_extractor, _mlp_detector, _scaler
    if _feature_extractor is not None:
        _feature_extractor.close()
    _config = None
    _victim_model = None
    _victim_device = None
    _feature_extractor = None
    _mlp_detector = None
    _scaler = None
    _load_warnings_emitted.clear()
    _events_emitted.clear()


def is_architecture_supported(model_type: str | None) -> bool:
    if not model_type:
        return False
    return resolve_model_type(model_type) == "resnet18"


def _load_config() -> dict[str, Any] | None:
    global _config
    if _config is not None:
        return _config

    if not _CONFIG_PATH.is_file():
        _warn_once("config_missing", f"Poisoning detector config missing: {_CONFIG_PATH}")
        _emit_poisoning_event(
            "poisoning.detector_failure",
            "Poisoning detector config missing",
            f"Expected config at {_CONFIG_PATH.name}.",
            {"path": str(_CONFIG_PATH)},
        )
        return None

    try:
        with open(_CONFIG_PATH, encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("detector_config.json must contain a JSON object")
        _config = loaded
        return _config
    except Exception as exc:
        _warn_once("config_corrupt", f"Failed to load poisoning detector config: {exc}")
        _emit_poisoning_event(
            "poisoning.detector_failure",
            "Poisoning detector config load failure",
            str(exc),
            {"path": str(_CONFIG_PATH)},
        )
        return None


def _resolve_mlp_path() -> Path | None:
    for name in _MLP_CANDIDATES:
        candidate = _MODELS_DIR / name
        if candidate.is_file():
            return candidate
    return None


def _load_mlp_detector() -> Any | None:
    global _mlp_detector
    if _mlp_detector is not None:
        return _mlp_detector

    path = _resolve_mlp_path()
    if path is None:
        _warn_once("mlp_missing", "Poisoning MLP artifact missing (poisoning_mlp.pkl / detector_mlp.pkl)")
        _emit_poisoning_event(
            "poisoning.detector_failure",
            "Poisoning MLP artifact missing",
            "Expected poisoning_mlp.pkl or detector_mlp.pkl in security_models.",
        )
        return None

    try:
        detector = joblib.load(path)
        _mlp_detector = detector
        return detector
    except Exception as exc:
        _warn_once("mlp_corrupt", f"Failed to load poisoning MLP: {exc}")
        _emit_poisoning_event(
            "poisoning.detector_failure",
            "Poisoning MLP load failure",
            str(exc),
            {"artifact": path.name},
        )
        return None


def _load_scaler() -> Any | None:
    global _scaler
    if _scaler is not None:
        return _scaler

    path = _MODELS_DIR / _SCALER_NAME
    if not path.is_file():
        _warn_once("scaler_missing", f"Poisoning scaler missing: {path}")
        _emit_poisoning_event(
            "poisoning.detector_failure",
            "Poisoning scaler missing",
            f"Expected {_SCALER_NAME} in security_models.",
        )
        return None

    try:
        scaler = joblib.load(path)
        _scaler = scaler
        return scaler
    except Exception as exc:
        _warn_once("scaler_corrupt", f"Failed to load poisoning scaler: {exc}")
        _emit_poisoning_event(
            "poisoning.detector_failure",
            "Poisoning scaler load failure",
            str(exc),
            {"artifact": path.name},
        )
        return None


def _torch_load_state(path: Path, device: torch.device) -> dict[str, Any] | None:
    try:
        try:
            state = torch.load(path, map_location=device, weights_only=True)
        except TypeError:
            state = torch.load(path, map_location=device)
    except Exception:
        try:
            state = torch.load(path, map_location="cpu", weights_only=False)
        except Exception:
            return None
    return state if isinstance(state, dict) else None


def _load_victim_model(device: torch.device) -> nn.Module | None:
    global _victim_model, _victim_device, _feature_extractor

    if _victim_model is not None and _victim_device == device:
        return _victim_model

    config = _load_config()
    if config is None:
        return None

    victim_name = str(config.get("victim_model", "attacked_model_multi_attack.pth"))
    victim_path = _MODELS_DIR / victim_name
    if not victim_path.is_file():
        _warn_once("victim_missing", f"Poisoning victim model missing: {victim_path}")
        _emit_poisoning_event(
            "poisoning.detector_failure",
            "Poisoning victim model missing",
            f"Expected victim checkpoint {victim_name}.",
        )
        return None

    try:
        model = models.resnet18(weights=None)
        model.fc = nn.Linear(512, 1000)
        state = _torch_load_state(victim_path, device)
        if state is None:
            raise RuntimeError("checkpoint could not be deserialized")

        state_dict = state.get("model_state_dict") or state.get("state_dict") or state
        model.load_state_dict(state_dict, strict=True)
        model.to(device)
        model.eval()

        if _feature_extractor is not None:
            _feature_extractor.close()
        layer_names = tuple(str(x) for x in config.get("layers", ["layer2", "layer3", "avgpool"]))
        _feature_extractor = ResNet18MultilayerFeatureExtractor(model, layers=layer_names)

        _victim_model = model
        _victim_device = device
        return model
    except Exception as exc:
        _warn_once("victim_corrupt", f"Failed to load poisoning victim model: {exc}")
        _emit_poisoning_event(
            "poisoning.detector_failure",
            "Poisoning victim model load failure",
            str(exc),
            {"artifact": victim_name},
        )
        return None


def _normalize(x: torch.Tensor) -> torch.Tensor:
    mean = torch.tensor(_IMAGENET_MEAN, device=x.device, dtype=x.dtype).view(1, 3, 1, 1)
    std = torch.tensor(_IMAGENET_STD, device=x.device, dtype=x.dtype).view(1, 3, 1, 1)
    return (x - mean) / std


def _build_preprocess(input_size: int) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
        ]
    )


def _load_image_tensor(image_source: str | Path | torch.Tensor, input_size: int) -> torch.Tensor:
    if isinstance(image_source, torch.Tensor):
        tensor = image_source.detach()
        if tensor.dim() == 3:
            tensor = tensor.unsqueeze(0)
        return tensor.float()

    with Image.open(image_source) as img:
        rgb = img.convert("RGB")
        return _build_preprocess(input_size)(rgb).unsqueeze(0)


def _severity_from_probability(probability: float, threshold: float) -> str:
    if probability >= threshold:
        return "HIGH"
    if probability >= max(threshold - 0.17, 0.5):
        return "MEDIUM"
    return "LOW"


def _poison_class_index(detector: Any, config: dict[str, Any]) -> int:
    classes = [str(c).lower() for c in config.get("classes", ["clean", "poisoned"])]
    if "poisoned" in classes:
        return classes.index("poisoned")
    if hasattr(detector, "classes_") and len(detector.classes_) > 1:
        return int(np.where(detector.classes_ == 1)[0][0])
    return 1


def _validate_dimensions(
    embeddings: torch.Tensor,
    augmented: np.ndarray,
    config: dict[str, Any],
    scaler: Any,
) -> None:
    expected_emb = int(config.get("embedding_dimension_before_augmentation", 896))
    expected_aug = int(config.get("embedding_dimension_after_augmentation", 899))
    if embeddings.shape[1] != expected_emb:
        raise ValueError(
            f"Embedding dimension mismatch: expected {expected_emb}, got {embeddings.shape[1]}"
        )
    if hasattr(scaler, "n_features_in_") and scaler.n_features_in_ != expected_emb:
        raise ValueError(
            f"Scaler dimension mismatch: expected {expected_emb}, scaler has {scaler.n_features_in_}"
        )
    if augmented.shape[1] != expected_aug:
        raise ValueError(
            f"Augmented feature dimension mismatch: expected {expected_aug}, got {augmented.shape[1]}"
        )


@torch.no_grad()
def _extract_batch_features(
    batch_tensor: torch.Tensor,
    device: torch.device,
    config: dict[str, Any],
) -> tuple[torch.Tensor, torch.Tensor]:
    if _load_victim_model(device) is None or _feature_extractor is None:
        raise RuntimeError("Poisoning victim model unavailable")

    x = batch_tensor.to(device=device, dtype=torch.float32)
    if x.max() > 1.5:
        x = x / 255.0
    x = x.clamp(0.0, 1.0)
    x_norm = _normalize(x)
    return _feature_extractor.forward(x_norm)


def _augment_features(embeddings: torch.Tensor, logits: torch.Tensor) -> np.ndarray:
    probs = F.softmax(logits, dim=1)
    max_confidence = probs.max(dim=1, keepdim=True).values
    entropy = -(probs * (probs + 1e-9).log()).sum(dim=1, keepdim=True)
    l2_norm = embeddings.norm(p=2, dim=1, keepdim=True)
    augmented = torch.cat([embeddings, l2_norm, max_confidence, entropy], dim=1)
    return augmented.cpu().numpy()


def _unavailable_result(reason: str, model_type: str | None = None) -> dict[str, Any]:
    return {
        "poisoning": False,
        "poisoning_flag": False,
        "poisoning_available": False,
        "poisoning_probability": None,
        "poisoning_score": None,
        "poisoning_severity": "UNAVAILABLE",
        "poisoning_status": reason,
        "poisoning_detector": None,
        "poisoning_embedding_source": "ResNet18 Multi-Layer",
        "poisoning_reasons": [reason],
    }


def _available_result(
    probability: float,
    threshold: float,
    config: dict[str, Any],
    batch_size: int,
) -> dict[str, Any]:
    flagged = probability >= threshold
    severity = _severity_from_probability(probability, threshold)
    status = (
        "Potential poisoned sample detected"
        if flagged
        else "No poisoning indicators above threshold"
    )
    reasons: list[str] = []
    if flagged:
        reasons.append(f"poison probability {probability:.1%} exceeds threshold {threshold:.1%}")

    return {
        "poisoning": flagged,
        "poisoning_flag": flagged,
        "poisoning_available": True,
        "poisoning_probability": round(probability, 4),
        "poisoning_score": round(probability, 4),
        "poisoning_severity": severity,
        "poisoning_status": status,
        "poisoning_detector": str(config.get("detector_type", "MLP")),
        "poisoning_embedding_source": "ResNet18 Multi-Layer",
        "poisoning_reasons": reasons,
        "poisoning_threshold": threshold,
        "poisoning_batch_size": batch_size,
    }


def detector_runtime_status() -> dict[str, Any]:
    config = _load_config()
    mlp_path = _resolve_mlp_path()
    scaler_path = _MODELS_DIR / _SCALER_NAME
    victim_name = str((config or {}).get("victim_model", "attacked_model_multi_attack.pth"))
    victim_path = _MODELS_DIR / victim_name

    artifacts_ok = all(
        [
            config is not None,
            mlp_path is not None and mlp_path.is_file(),
            scaler_path.is_file(),
            victim_path.is_file(),
        ]
    )
    device = _resolve_device()
    runtime_ok = (
        artifacts_ok
        and _load_victim_model(device) is not None
        and _load_mlp_detector() is not None
        and _load_scaler() is not None
    )

    return {
        "available": runtime_ok,
        "artifacts_present": artifacts_ok,
        "detector_type": (config or {}).get("detector_type", "MLP"),
        "victim_model": victim_name,
        "mlp_artifact": mlp_path.name if mlp_path else None,
    }


@torch.no_grad()
def evaluate_poisoning_batch(
    image_sources: list[str | Path | torch.Tensor],
    *,
    model_type: str | None = None,
    scan_mode: str = "inference",
) -> list[dict[str, Any]]:
    if not image_sources:
        return []

    if scan_mode == "inference" and not is_architecture_supported(model_type):
        reason = (
            "Poisoning detection unavailable: detector currently supports "
            "ResNet18 embedding extraction only."
        )
        _emit_poisoning_event(
            "poisoning.unsupported_architecture",
            "Poisoning detection unsupported for active model",
            reason,
            {"model_type": model_type},
            once=True,
        )
        return [_unavailable_result(reason, model_type) for _ in image_sources]

    config = _load_config()
    detector = _load_mlp_detector()
    scaler = _load_scaler()
    if config is None or detector is None or scaler is None:
        reason = "Poisoning detection unavailable: detector artifacts failed to load."
        return [_unavailable_result(reason, model_type) for _ in image_sources]

    device = _resolve_device()
    if _load_victim_model(device) is None:
        reason = "Poisoning detection unavailable: victim model failed to load."
        return [_unavailable_result(reason, model_type) for _ in image_sources]

    input_size = int(config.get("input_size", 128))
    batch_size = max(1, int(config.get("batch_size", 32)))
    threshold = float(config.get("threshold", 0.67))
    poison_idx = _poison_class_index(detector, config)

    tensors = [_load_image_tensor(source, input_size) for source in image_sources]
    results: list[dict[str, Any]] = []

    try:
        for start in range(0, len(tensors), batch_size):
            batch = torch.cat(tensors[start : start + batch_size], dim=0)
            logits, embeddings = _extract_batch_features(batch, device, config)
            scaled = scaler.transform(embeddings.cpu().numpy())
            scaled_tensor = torch.from_numpy(scaled).to(device=device, dtype=torch.float32)
            augmented = _augment_features(scaled_tensor, logits)
            _validate_dimensions(embeddings, augmented, config, scaler)

            probabilities = detector.predict_proba(augmented)
            for row_idx in range(probabilities.shape[0]):
                poison_prob = float(probabilities[row_idx, poison_idx])
                item = _available_result(poison_prob, threshold, config, batch_size)
                results.append(item)
    except ValueError as exc:
        message = str(exc)
        event_type = (
            "poisoning.embedding_mismatch"
            if "Embedding dimension" in message
            else "poisoning.dimension_mismatch"
        )
        _emit_poisoning_event(event_type, "Poisoning feature pipeline mismatch", message, {"model_type": model_type})
        reason = f"Poisoning detection unavailable: {message}"
        return [_unavailable_result(reason, model_type) for _ in image_sources]
    except Exception as exc:
        _emit_poisoning_event(
            "poisoning.detector_failure",
            "Poisoning inference failure",
            str(exc),
            {"model_type": model_type},
        )
        reason = f"Poisoning detection unavailable: inference failed ({exc})."
        return [_unavailable_result(reason, model_type) for _ in image_sources]

    return results


def evaluate_poisoning(
    image_source: str | Path | torch.Tensor,
    *,
    model_type: str | None = None,
    scan_mode: str = "inference",
) -> dict[str, Any]:
    batch = evaluate_poisoning_batch([image_source], model_type=model_type, scan_mode=scan_mode)
    return batch[0] if batch else _unavailable_result("Poisoning detection unavailable: empty input.")


def evaluate_runtime_poison_suspicion(
    image_source: str | Path | torch.Tensor,
) -> dict[str, Any]:
    """
    Lightweight optional runtime suspicion signal for inference.
    Uses the fixed victim-model detector and is not the primary poisoning defense.
    """
    result = evaluate_poisoning(image_source, scan_mode="runtime_optional")
    available = bool(result.get("poisoning_available"))
    probability = result.get("poisoning_probability")
    severity = result.get("poisoning_severity", "UNAVAILABLE")
    flagged = bool(result.get("poisoning_flag")) if available else False

    return {
        "runtime_poison_suspicion": flagged,
        "runtime_poison_probability": probability,
        "runtime_poison_severity": severity if available else "UNAVAILABLE",
        "runtime_poison_status": (
            "Runtime suspicion analysis unavailable"
            if not available
            else (
                "Potential runtime poisoning suspicion"
                if flagged
                else "No runtime poisoning suspicion above threshold"
            )
        ),
        "runtime_poison_available": available,
    }


def merge_runtime_poison_suspicion(result: dict[str, Any], suspicion: dict[str, Any]) -> None:
    result.update(suspicion)
    if suspicion.get("runtime_poison_suspicion") and suspicion.get("runtime_poison_status"):
        issues = list(result.get("issues") or [])
        message = str(suspicion["runtime_poison_status"])
        if message not in issues:
            issues.append(message)
        result["issues"] = issues


def merge_poisoning_into_detection(detection: dict[str, Any], poison_info: dict[str, Any]) -> None:
    detection.update(poison_info)

    reasons = poison_info.get("poisoning_reasons") or []
    if reasons:
        issues = list(detection.get("issues") or [])
        for reason in reasons:
            if reason not in issues:
                issues.append(reason)
        detection["issues"] = issues

    if poison_info.get("poisoning_flag"):
        verdict = detection.get("verdict", "reliable")
        if verdict == "reliable":
            detection["verdict"] = "uncertain"
        elif verdict == "uncertain":
            detection["verdict"] = "suspicious"
