"""
Adversarial scoring uses a FIXED Food-101 ResNet50 victim shipped with the detector.

The unified detector (adv_model.pt) was trained on logits + 2048-d embeddings + stats
from that specific victim. Feeding it features from arbitrary user-trained models shifts
every distribution the MLP saw at train time, so softmax calibration and per-class
thresholds stop matching reality.

Normal classification may still use the user-uploaded model elsewhere; this module
always runs the bundled victim for adversarial analysis only.

Perturbation guard (||delta|| vs clean) from kaggle_test.py applies when a clean
reference exists; ``is_adversarial(model, image)`` only receives one tensor, so guard
is omitted here—single-image parity follows ``mode_clean`` / ``detect()`` on that tensor.

If checkpoints are missing or inference fails, we fail open.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any, List

import numpy as np
import torch
import torch.nn as nn
from PIL import Image as PILImage
import torchvision.models as models
import torchvision.transforms.functional as TF
from torchvision.transforms.functional import gaussian_blur

# ImageNet normalization (must match detector training / Kaggle script).
_IMAGENET_MEAN: List[float] = [0.485, 0.456, 0.406]
_IMAGENET_STD: List[float] = [0.229, 0.224, 0.225]

_EXPECTED_FEAT_DIM = 2048
_EXPECTED_LOGIT_DIM = 101
PIX_STAT_DIM = 9
NUM_CLASSES_DET = 4
COMBINED_DIM = _EXPECTED_FEAT_DIM + _EXPECTED_LOGIT_DIM + 3 + PIX_STAT_DIM + 1  # 2162

FINAL_CLEAN = 0
FINAL_LINF_ADV = 1
FINAL_L2_ADV = 2
FINAL_NOISE = 3

# Calibrated per-class gates (Kaggle patch v2). Plain argmax ignores these and breaks L∞/L2/Noise.
DEFAULT_THRESHOLDS = np.array([0.40, 0.123, 0.139, 0.85], dtype=np.float64)
LOW_CONF_ADV_FLOOR = 0.01

_DETECTOR_CLASS_NAMES = ["Clean", "L∞ Adversarial", "L2 Adversarial", "Noise"]
_ADV_REASONS = {
    1: "detected L∞ adversarial characteristics",
    2: "detected L2 adversarial characteristics",
    3: "detected perturbation/noise attack characteristics",
}

# Post-calibration gates: calibrated class is not always a hard "attack" (Noise is broad).
MIN_ADV_CONF = 0.25
NOISE_ADV_CONF = 0.85

SUSPICIOUS_NOISE_REASON = (
    "noise-like or ambiguous perturbation statistics (not scored as definitive adversarial)"
)

_ADV_CKPT = Path(__file__).resolve().parent / "security_models" / "adv_model.pt"
_VICTIM_CKPT = Path(__file__).resolve().parent / "security_models" / "victim_resnet50.pt"

_adv_detector: nn.Module | None = None
_adv_detector_device: torch.device | None = None
_internal_victim_model: nn.Module | None = None
_internal_victim_device: torch.device | None = None


class VictimResNet50(nn.Module):
    """Kaggle / training victim: ResNet50 trunk + 101-way head, returns (logits, feats)."""

    def __init__(self, num_classes: int = 101) -> None:
        super().__init__()
        bb = models.resnet50(weights=None)
        self.features = nn.Sequential(*list(bb.children())[:-1])
        self.classifier = nn.Linear(2048, num_classes)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        feats = self.features(x).flatten(1)
        logits = self.classifier(feats)
        return logits, feats


class UnifiedDetector(nn.Module):
    """
    4-class MLP trained on combined features (2162-d):
    backbone feats (2048) + logits (101) + model_stats (3) +
    pixel_stats (9) + smoothed_margin (1).
    """

    def __init__(
        self,
        feat_dim: int = 2048,
        logit_dim: int = 101,
        stat_dim: int = 3,
        pix_dim: int = PIX_STAT_DIM,
        margin_dim: int = 1,
        num_classes: int = NUM_CLASSES_DET,
    ) -> None:
        super().__init__()
        self.feat_branch = nn.Sequential(
            nn.Linear(feat_dim, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
        )
        stat_in = logit_dim + stat_dim + pix_dim + margin_dim
        self.logit_branch = nn.Sequential(
            nn.Linear(stat_in, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
        )
        self.head = nn.Sequential(
            nn.Linear(256 + 64, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )
        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, combined: torch.Tensor) -> torch.Tensor:
        fb = self.feat_branch(combined[:, :2048])
        lb = self.logit_branch(combined[:, 2048:])
        return self.head(torch.cat([fb, lb], dim=1))


@torch.no_grad()
def _kaggle_eval_spatial_preprocess(raw: torch.Tensor) -> torch.Tensor:
    """
    Match kaggle_test ``EVAL_TF``: Resize(256), CenterCrop(224), on [0,1] BCHW tensors.
    Alignment matters for pixel_stats and for weights trained on 224 crops.
    """
    if raw.dim() == 3:
        raw = raw.unsqueeze(0)
    try:
        x = TF.resize(raw, 256, antialias=True)
    except TypeError:
        x = TF.resize(raw, 256)
    return TF.center_crop(x, [224, 224])


def _norm(x: torch.Tensor, mean: List[float], std: List[float]) -> torch.Tensor:
    m = torch.tensor(mean, device=x.device, dtype=x.dtype).view(1, 3, 1, 1)
    s = torch.tensor(std, device=x.device, dtype=x.dtype).view(1, 3, 1, 1)
    return (x - m) / s


@torch.no_grad()
def _model_stats(logits: torch.Tensor) -> torch.Tensor:
    """(B,3): max_prob, entropy, top2_margin — same as Kaggle."""
    probs = logits.softmax(1)
    max_prob = probs.max(1, keepdim=True).values
    entropy = -(probs * (probs + 1e-9).log()).sum(1, keepdim=True)
    top2 = probs.topk(2, dim=1).values
    margin = (top2[:, 0] - top2[:, 1]).unsqueeze(1)
    return torch.cat([max_prob, entropy, margin], dim=1)


def add_jpeg_compression(x: torch.Tensor, quality: int = 30) -> torch.Tensor:
    out: list[torch.Tensor] = []
    for img in x.detach().cpu():
        pil = TF.to_pil_image(img.clamp(0.0, 1.0))
        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        out.append(TF.to_tensor(PILImage.open(buf)))
    return torch.stack(out, dim=0).to(device=x.device, dtype=x.dtype)


@torch.no_grad()
def _pixel_stats(x: torch.Tensor) -> torch.Tensor:
    """(B,9) pixel-space features on raw [0,1] tensors — matches Kaggle."""
    blurred = gaussian_blur(x, kernel_size=5, sigma=1.0)
    hf = x - blurred
    hf_energy = hf.pow(2).mean([1, 2, 3])
    hf_max = hf.abs().amax([1, 2, 3])
    hf_std = hf.std([1, 2, 3])
    patch_var = x.unfold(2, 8, 4).unfold(3, 8, 4).var(dim=(-1, -2)).mean([1, 2, 3])
    grad_x = (x[:, :, :, 1:] - x[:, :, :, :-1]).pow(2).mean([1, 2, 3])
    grad_y = (x[:, :, 1:, :] - x[:, :, :-1, :]).pow(2).mean([1, 2, 3])
    x_jpeg = add_jpeg_compression(x, quality=75)
    x_blur = gaussian_blur(x, kernel_size=3, sigma=0.5)
    jpeg_dist = (x - x_jpeg).pow(2).mean([1, 2, 3])
    blur_dist = (x - x_blur).pow(2).mean([1, 2, 3])
    linf_norm = x.amax([1, 2, 3])
    return torch.stack(
        [hf_energy, hf_max, hf_std, patch_var, grad_x, grad_y, jpeg_dist, blur_dist, linf_norm],
        dim=1,
    )


def _forward_logits(victim: nn.Module, x_norm: torch.Tensor) -> torch.Tensor:
    out = victim(x_norm)
    return out[0] if isinstance(out, (tuple, list)) else out


@torch.no_grad()
def _smoothed_margin(
    victim: nn.Module,
    x: torch.Tensor,
    mean: List[float],
    std: List[float],
    n: int = 8,
    sigma: float = 0.05,
) -> torch.Tensor:
    margins: list[torch.Tensor] = []
    for _ in range(n):
        noisy = (x + torch.randn_like(x) * sigma).clamp(0.0, 1.0)
        logits = _forward_logits(victim, _norm(noisy, mean, std))
        top2 = logits.topk(2, dim=1).values
        margins.append((top2[:, 0] - top2[:, 1]).unsqueeze(1))
    return torch.stack(margins, dim=0).mean(0)


def _make_combined(
    feats: torch.Tensor,
    logits: torch.Tensor,
    model_stats: torch.Tensor,
    pixel_stats: torch.Tensor,
    smoothed_margin: torch.Tensor,
) -> torch.Tensor:
    return torch.cat([feats, logits, model_stats, pixel_stats, smoothed_margin], dim=1)


def _calibrated_predict_class(
    probs: torch.Tensor,
    threshold_vec: torch.Tensor,
    low_conf_floor: float,
) -> int:
    """Same threshold / tie-break / low-conf behavior as ``detect()`` in kaggle_test.txt."""
    if probs.dim() == 2:
        row = probs[0]
    else:
        row = probs
    fires = row >= threshold_vec
    n_f = int(fires.sum().item())
    pred_argmax = int(row.argmax().item())

    if n_f == 1:
        return int(fires.nonzero(as_tuple=False)[0, 0].item())
    if n_f > 1:
        if fires[FINAL_L2_ADV] and fires[FINAL_NOISE]:
            return FINAL_L2_ADV
        masked = row.clone()
        masked[~fires] = -1.0
        return int(masked.argmax().item())
    if row[FINAL_LINF_ADV] > low_conf_floor:
        return FINAL_LINF_ADV
    if row[FINAL_L2_ADV] > low_conf_floor:
        return FINAL_L2_ADV
    return pred_argmax


def _final_adversarial_flags(pred: int, confidence: float) -> tuple[bool, bool]:
    """
    Security layer after calibrated class selection.

    L∞ / L2 heads target structured attacks; require modest softmax confidence before
    treating a prediction as a true positive (reduces spurious flips).

    Noise is deliberately broad (compression, blur, benign odd stats) and often
    co-fires with L2 in feature space—it must not be treated like a geometric attack
    unless probability mass is overwhelmingly on Noise.
    """
    suspicious = False
    if pred == FINAL_LINF_ADV:
        is_adv = confidence > MIN_ADV_CONF
    elif pred == FINAL_L2_ADV:
        is_adv = confidence > MIN_ADV_CONF
    elif pred == FINAL_NOISE:
        is_adv = confidence > NOISE_ADV_CONF
        suspicious = not is_adv
    else:
        is_adv = False
    return is_adv, suspicious


def _reasons_for_security_decision(pred: int, is_adv: bool, suspicious: bool) -> list[str]:
    if is_adv and pred != FINAL_CLEAN:
        return [_ADV_REASONS[pred]]
    if suspicious:
        return [SUSPICIOUS_NOISE_REASON]
    return []


def _legacy_probe_stubs() -> dict[str, Any]:
    return {
        "fgsm": {"confidence_drop": 0.0, "prediction_changed": False, "flag": False},
        "transform": {"unstable_transforms": [], "largest_conf_drop": 0.0, "flag": False},
    }


def _fallback() -> dict[str, Any]:
    return {
        "flag": False,
        "suspicious": False,
        "reasons": ["adversarial detection unavailable"],
        **_legacy_probe_stubs(),
    }


@torch.no_grad()
def _victim_logits_and_feats(victim: nn.Module, x_norm: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """For tuple-return victims or last-Linear hook fallback (non-internal models)."""
    last_linear: nn.Linear | None = None
    for mod in victim.modules():
        if isinstance(mod, nn.Linear):
            last_linear = mod

    feats_capture: list[torch.Tensor] = []

    def _pre_hook(_m: nn.Module, inputs: tuple[torch.Tensor, ...]) -> None:
        feats_capture.append(inputs[0])

    hook_handle = (
        last_linear.register_forward_pre_hook(_pre_hook) if last_linear is not None else None
    )
    try:
        out = victim(x_norm)
    finally:
        if hook_handle is not None:
            hook_handle.remove()

    if isinstance(out, tuple) and len(out) == 2:
        return out[0], out[1]
    if isinstance(out, (tuple, list)):
        raise RuntimeError("victim returned a sequence but not (logits, feats)")
    if last_linear is None or not feats_capture:
        raise RuntimeError("victim has no Linear layer; cannot extract features")
    return out, feats_capture[0]


def _resolve_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _torch_load_state(path: Path, device: torch.device) -> dict[str, Any] | None:
    try:
        try:
            state = torch.load(path, map_location=device, weights_only=True)
        except TypeError:
            state = torch.load(path, map_location=device)
    except Exception:
        try:
            state = torch.load(path, map_location=device, weights_only=False)
        except Exception:
            return None
    return state if isinstance(state, dict) else None


def _load_internal_victim(device: torch.device) -> VictimResNet50 | None:
    """Lazy-load bundled ResNet50 checkpoint (single global cache per device)."""
    global _internal_victim_model, _internal_victim_device

    if _internal_victim_model is not None and _internal_victim_device == device:
        return _internal_victim_model  # type: ignore[return-value]

    if not _VICTIM_CKPT.is_file():
        return None

    try:
        v = VictimResNet50()
        state = _torch_load_state(_VICTIM_CKPT, device)
        if state is None:
            return None
        v.load_state_dict(state, strict=True)
        v.to(device)
        v.eval()
    except Exception:
        return None

    _internal_victim_model = v
    _internal_victim_device = device
    return v


def _load_adversarial_detector(device: torch.device) -> UnifiedDetector | None:
    global _adv_detector, _adv_detector_device

    if _adv_detector is not None and _adv_detector_device == device:
        return _adv_detector  # type: ignore[return-value]

    if not _ADV_CKPT.is_file():
        return None

    try:
        det = UnifiedDetector()
        state = _torch_load_state(_ADV_CKPT, device)
        if state is None:
            return None
        det.load_state_dict(state, strict=True)
        det.to(device)
        det.eval()
    except Exception:
        return None

    _adv_detector = det
    _adv_detector_device = device
    return det


@torch.no_grad()
def is_adversarial(model: nn.Module, image: torch.Tensor) -> dict[str, Any]:
    """
    Run detector on features from the **internal** ResNet50 victim only.
    ``model`` is kept for API compatibility but is not used for this path.
    """
    _ = model

    device = _resolve_device()
    victim = _load_internal_victim(device)
    det = _load_adversarial_detector(device)
    if victim is None or det is None:
        return _fallback()

    try:
        if image.dim() == 3:
            image = image.unsqueeze(0)
        raw_in = image.to(device=device, dtype=torch.float32).clamp(0.0, 1.0)
        raw = _kaggle_eval_spatial_preprocess(raw_in)

        x_norm = _norm(raw, _IMAGENET_MEAN, _IMAGENET_STD)
        logits, feats = victim(x_norm)
        if logits.shape[-1] != _EXPECTED_LOGIT_DIM or feats.shape[-1] != _EXPECTED_FEAT_DIM:
            return _fallback()

        ms = _model_stats(logits)
        ps = _pixel_stats(raw)
        sm = _smoothed_margin(victim, raw, _IMAGENET_MEAN, _IMAGENET_STD, n=8, sigma=0.05)

        combined = _make_combined(feats.float(), logits.float(), ms, ps, sm).float()
        if combined.shape[1] != COMBINED_DIM:
            return _fallback()

        logits_det = det(combined)
        probs = logits_det.softmax(1)
        thr = torch.tensor(DEFAULT_THRESHOLDS, device=device, dtype=probs.dtype)
        pred = _calibrated_predict_class(probs, thr, LOW_CONF_ADV_FLOOR)
        confidence = float(probs[0, pred].item())

        is_adv, suspicious = _final_adversarial_flags(pred, confidence)
        reasons = _reasons_for_security_decision(pred, is_adv, suspicious)

        return {
            "flag": is_adv,
            "suspicious": suspicious,
            "predicted_class": pred,
            "class_name": _DETECTOR_CLASS_NAMES[pred],
            "confidence": confidence,
            "reasons": reasons,
            **_legacy_probe_stubs(),
        }
    except Exception:
        return _fallback()
