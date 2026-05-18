from __future__ import annotations
from pathlib import Path

import pytest
import torch
import torch.nn as nn

import Detection.adversarial as adv


_FIXTURE_IMAGE = (1, 3, 32, 32)

ADV_CKPT_PATH = Path(__file__).resolve().parent.parent / "Detection" / "security_models" / "adv_model.pt"
VICTIM_CKPT_PATH = Path(__file__).resolve().parent.parent / "Detection" / "security_models" / "victim_resnet50.pt"

requires_adv_ckpt = pytest.mark.skipif(
    not ADV_CKPT_PATH.is_file(),
    reason="Detection/security_models/adv_model.pt not found",
)

requires_full_adversarial_pipeline = pytest.mark.skipif(
    not ADV_CKPT_PATH.is_file() or not VICTIM_CKPT_PATH.is_file(),
    reason="adv_model.pt and/or victim_resnet50.pt missing",
)


@pytest.fixture(autouse=True)
def reset_adversarial_caches() -> None:
    adv._adv_detector = None
    adv._adv_detector_device = None
    adv._internal_victim_model = None
    adv._internal_victim_device = None
    yield
    adv._adv_detector = None
    adv._adv_detector_device = None
    adv._internal_victim_model = None
    adv._internal_victim_device = None


class DummyVictim(nn.Module):
    """Unused by is_adversarial(); kept for _victim_logits_and_feats unit tests."""

    def __init__(self) -> None:
        super().__init__()
        self._w = nn.Parameter(torch.zeros(1))

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        b = x.size(0)
        dev, dt = x.device, x.dtype
        logits = torch.zeros(b, adv._EXPECTED_LOGIT_DIM, device=dev, dtype=dt)
        feats = torch.zeros(b, adv._EXPECTED_FEAT_DIM, device=dev, dtype=dt)
        logits[:, 0] = 3.0
        return logits, feats


class ArbitraryExternalModel(nn.Module):
    """Different from internal ResNet50 — ``is_adversarial`` must ignore it."""

    def __init__(self) -> None:
        super().__init__()
        self._w = nn.Parameter(torch.randn(1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x.mean(dim=(1, 2, 3), keepdim=True)


def _assert_minimal_adversarial_keys(result: dict) -> None:
    assert "flag" in result
    assert "reasons" in result
    assert "suspicious" in result
    assert isinstance(result["flag"], bool)
    assert isinstance(result["suspicious"], bool)
    assert isinstance(result["reasons"], list)


@requires_adv_ckpt
def test_adv_checkpoint_loads_into_unified_detector() -> None:
    det = adv.UnifiedDetector()
    try:
        state = torch.load(ADV_CKPT_PATH, map_location="cpu", weights_only=True)
    except TypeError:
        state = torch.load(ADV_CKPT_PATH, map_location="cpu")
    det.load_state_dict(state, strict=True)
    det.eval()
    x = torch.randn(1, adv.COMBINED_DIM)
    out = det(x)
    assert out.shape == (1, adv.NUM_CLASSES_DET)


@requires_adv_ckpt
def test_detector_initializes_with_expected_input_dim() -> None:
    det = adv.UnifiedDetector()
    assert det(torch.randn(2, adv.COMBINED_DIM)).shape == (2, adv.NUM_CLASSES_DET)


def test_resolve_device_returns_torch_device() -> None:
    d = adv._resolve_device()
    assert isinstance(d, torch.device)


@requires_adv_ckpt
def test_combined_feature_tensor_shape_matches_training() -> None:
    raw = torch.rand(*_FIXTURE_IMAGE)
    logits = torch.randn(1, adv._EXPECTED_LOGIT_DIM)
    feats = torch.randn(1, adv._EXPECTED_FEAT_DIM)
    ms = adv._model_stats(logits)
    ps = adv._pixel_stats(raw)
    sm = torch.zeros(1, 1)
    combined = adv._make_combined(feats, logits, ms, ps, sm)
    assert combined.shape == (1, adv.COMBINED_DIM)


@requires_full_adversarial_pipeline
def test_is_adversarial_valid_tensor_runs_end_to_end() -> None:
    image = torch.rand(*_FIXTURE_IMAGE)
    result = adv.is_adversarial(DummyVictim(), image)
    _assert_minimal_adversarial_keys(result)
    assert "predicted_class" in result
    assert "class_name" in result
    assert "confidence" in result
    pred = result["predicted_class"]
    exp_flag, exp_susp = adv._final_adversarial_flags(pred, result["confidence"])
    assert result["flag"] == exp_flag
    assert result["suspicious"] == exp_susp


@requires_full_adversarial_pipeline
def test_binary_flag_matches_security_layer() -> None:
    image = torch.rand(1, 3, 64, 64)
    result = adv.is_adversarial(DummyVictim(), image)
    exp_flag, exp_susp = adv._final_adversarial_flags(
        result["predicted_class"], result["confidence"]
    )
    assert result["flag"] == exp_flag
    assert result["suspicious"] == exp_susp


@requires_full_adversarial_pipeline
def test_kaggle_preprocess_makes_small_images_valid() -> None:
    """4×4 input is expanded/cropped to 224 like Kaggle EVAL_TF."""
    image = torch.rand(1, 3, 4, 4)
    result = adv.is_adversarial(DummyVictim(), image)
    _assert_minimal_adversarial_keys(result)
    assert result["reasons"] != ["adversarial detection unavailable"]


@requires_full_adversarial_pipeline
def test_external_classifier_does_not_change_detector_output() -> None:
    image = torch.rand(1, 3, 48, 48)
    r1 = adv.is_adversarial(DummyVictim(), image)
    r2 = adv.is_adversarial(ArbitraryExternalModel(), image)
    assert r1["predicted_class"] == r2["predicted_class"]
    assert r1["flag"] == r2["flag"]
    assert r1["suspicious"] == r2["suspicious"]
    assert abs(r1["confidence"] - r2["confidence"]) < 1e-4


def test_missing_detector_checkpoint_returns_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(adv, "_ADV_CKPT", tmp_path / "missing_adv_model.pt")
    image = torch.rand(1, 3, 32, 32)
    result = adv.is_adversarial(DummyVictim(), image)
    _assert_minimal_adversarial_keys(result)
    assert result["flag"] is False
    assert result["suspicious"] is False


@requires_adv_ckpt
def test_missing_internal_victim_checkpoint_returns_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(adv, "_VICTIM_CKPT", tmp_path / "missing_victim.pt")
    image = torch.rand(1, 3, 32, 32)
    result = adv.is_adversarial(DummyVictim(), image)
    assert result["flag"] is False
    assert result["suspicious"] is False
    assert result["reasons"] == ["adversarial detection unavailable"]


@requires_full_adversarial_pipeline
def test_internal_victim_loads_and_is_resnet_wrapper() -> None:
    v = adv._load_internal_victim(torch.device("cpu"))
    assert v is not None
    assert isinstance(v, adv.VictimResNet50)


@requires_full_adversarial_pipeline
def test_cpu_pipeline_runs_without_crash() -> None:
    image = torch.rand(1, 3, 48, 48)
    result = adv.is_adversarial(DummyVictim(), image)
    _assert_minimal_adversarial_keys(result)
    assert result["predicted_class"] in range(adv.NUM_CLASSES_DET)


@requires_full_adversarial_pipeline
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_cuda_internal_models_run() -> None:
    device = torch.device("cuda")
    adv._load_internal_victim(device)
    adv._load_adversarial_detector(device)
    image = torch.rand(1, 3, 32, 32)
    result = adv.is_adversarial(ArbitraryExternalModel().cuda(), image.cuda())
    _assert_minimal_adversarial_keys(result)
    assert "predicted_class" in result


@requires_full_adversarial_pipeline
def test_repeated_inference_caches_both_checkpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    loads: list[int] = []
    real_load = torch.load

    def counting_load(*args, **kwargs):  # type: ignore[no-untyped-def]
        loads.append(1)
        return real_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", counting_load)
    img = torch.rand(1, 3, 40, 40)
    adv.is_adversarial(DummyVictim(), img)
    assert len(loads) == 2
    adv.is_adversarial(DummyVictim(), img)
    assert len(loads) == 2


def test_victim_tuple_forward_integrates_with_feature_pipeline() -> None:
    victim = DummyVictim()
    raw = torch.rand(1, 3, 56, 56)
    x_norm = adv._norm(raw, adv._IMAGENET_MEAN, adv._IMAGENET_STD)
    logits, feats = adv._victim_logits_and_feats(victim, x_norm)
    assert logits.shape == (1, adv._EXPECTED_LOGIT_DIM)
    assert feats.shape == (1, adv._EXPECTED_FEAT_DIM)


@requires_adv_ckpt
@torch.no_grad()
def test_loaded_detector_output_shape_on_combined_features() -> None:
    det = adv._load_adversarial_detector(torch.device("cpu"))
    assert det is not None
    combined = torch.randn(3, adv.COMBINED_DIM)
    out = det(combined)
    assert out.shape == (3, adv.NUM_CLASSES_DET)


def test_kaggle_spatial_preprocess_output_shape() -> None:
    x = torch.rand(1, 3, 17, 91)
    y = adv._kaggle_eval_spatial_preprocess(x)
    assert y.shape == (1, 3, 224, 224)


def _kaggle_detect_pred_reference(
    probs: torch.Tensor,
    thresholds: list[float],
    low_conf_floor: float,
) -> int:
    thr = torch.tensor(thresholds, dtype=probs.dtype)
    fires = probs >= thr
    n_f = fires.sum(1)
    preds = probs.argmax(1).clone()
    b = 0
    nf = int(n_f[b].item())
    if nf == 1:
        preds[b] = fires[b].nonzero(as_tuple=False)[0, 0]
    elif nf > 1:
        if fires[b, adv.FINAL_L2_ADV] and fires[b, adv.FINAL_NOISE]:
            preds[b] = adv.FINAL_L2_ADV
        else:
            masked = probs[b].clone()
            masked[~fires[b]] = -1.0
            preds[b] = masked.argmax()
    else:
        if probs[b, adv.FINAL_LINF_ADV] > low_conf_floor:
            preds[b] = adv.FINAL_LINF_ADV
        elif probs[b, adv.FINAL_L2_ADV] > low_conf_floor:
            preds[b] = adv.FINAL_L2_ADV
    return int(preds[b].item())


@pytest.fixture
def default_thr_cpu() -> torch.Tensor:
    return torch.tensor(adv.DEFAULT_THRESHOLDS, dtype=torch.float32)


def test_calibrated_predict_single_fire(default_thr_cpu: torch.Tensor) -> None:
    probs = torch.tensor([[0.30, 0.20, 0.05, 0.05]])
    assert adv._calibrated_predict_class(probs, default_thr_cpu, 0.01) == adv.FINAL_LINF_ADV


def test_calibrated_l2_beats_noise_when_both_fire(default_thr_cpu: torch.Tensor) -> None:
    probs = torch.tensor([[0.10, 0.05, 0.20, 0.70]])
    assert adv._calibrated_predict_class(probs, default_thr_cpu, 0.01) == adv.FINAL_L2_ADV


def test_calibrated_multi_fire_highest_firing_prob_wins(default_thr_cpu: torch.Tensor) -> None:
    probs = torch.tensor([[0.50, 0.15, 0.05, 0.05]])
    assert adv._calibrated_predict_class(probs, default_thr_cpu, 0.01) == adv.FINAL_CLEAN


def test_calibrated_low_conf_linf_when_none_fire(default_thr_cpu: torch.Tensor) -> None:
    probs = torch.tensor([[0.35, 0.05, 0.08, 0.10]])
    assert adv._calibrated_predict_class(probs, default_thr_cpu, 0.01) == adv.FINAL_LINF_ADV


def test_calibrated_low_conf_l2_when_linf_below_floor(default_thr_cpu: torch.Tensor) -> None:
    probs = torch.tensor([[0.35, 0.005, 0.02, 0.10]])
    assert adv._calibrated_predict_class(probs, default_thr_cpu, 0.01) == adv.FINAL_L2_ADV


def test_calibrated_falls_back_to_argmax_clean_when_no_fire_no_weak_signal(default_thr_cpu: torch.Tensor) -> None:
    probs = torch.tensor([[0.35, 0.005, 0.005, 0.10]])
    assert adv._calibrated_predict_class(probs, default_thr_cpu, 0.01) == adv.FINAL_CLEAN


def test_calibrated_matches_kaggle_detect_reference(default_thr_cpu: torch.Tensor) -> None:
    thr_list = [float(x) for x in adv.DEFAULT_THRESHOLDS]
    floor = adv.LOW_CONF_ADV_FLOOR
    samples = [
        torch.tensor([[0.30, 0.20, 0.05, 0.05]]),
        torch.tensor([[0.10, 0.05, 0.20, 0.70]]),
        torch.tensor([[0.50, 0.15, 0.05, 0.05]]),
        torch.tensor([[0.35, 0.05, 0.08, 0.10]]),
        torch.tensor([[0.35, 0.005, 0.02, 0.10]]),
        torch.tensor([[0.2, 0.12, 0.14, 0.66]]),
    ]
    for pr in samples:
        a = adv._calibrated_predict_class(pr.clone(), default_thr_cpu, floor)
        b = _kaggle_detect_pred_reference(pr.clone(), thr_list, floor)
        assert a == b


def test_final_flags_linf_and_l2_require_min_conf() -> None:
    f, s = adv._final_adversarial_flags(adv.FINAL_LINF_ADV, adv.MIN_ADV_CONF + 0.01)
    assert f is True and s is False
    f, s = adv._final_adversarial_flags(adv.FINAL_LINF_ADV, adv.MIN_ADV_CONF - 0.01)
    assert f is False and s is False
    f, s = adv._final_adversarial_flags(adv.FINAL_L2_ADV, adv.MIN_ADV_CONF + 0.01)
    assert f is True and s is False


def test_final_flags_noise_strong_vs_weak() -> None:
    f, s = adv._final_adversarial_flags(adv.FINAL_NOISE, adv.NOISE_ADV_CONF + 0.01)
    assert f is True and s is False
    f, s = adv._final_adversarial_flags(adv.FINAL_NOISE, adv.NOISE_ADV_CONF - 0.01)
    assert f is False and s is True


def test_final_flags_clean() -> None:
    f, s = adv._final_adversarial_flags(adv.FINAL_CLEAN, 0.99)
    assert f is False and s is False


def test_reasons_for_security_decision_noise_suspicious() -> None:
    r = adv._reasons_for_security_decision(adv.FINAL_NOISE, is_adv=False, suspicious=True)
    assert r == [adv.SUSPICIOUS_NOISE_REASON]


def test_reasons_for_security_decision_linf_adv() -> None:
    r = adv._reasons_for_security_decision(adv.FINAL_LINF_ADV, is_adv=True, suspicious=False)
    assert r == [adv._ADV_REASONS[adv.FINAL_LINF_ADV]]
