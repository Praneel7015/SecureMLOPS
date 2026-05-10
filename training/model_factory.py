from __future__ import annotations

import os
from typing import Any

import torch
from torchvision import models

from training.config import SUPPORTED_MODELS


def resolve_model_type(model_type: str) -> str:
    key = model_type.strip().lower()
    if key in {"efficientnet", "efficientnet_b0"}:
        return "efficientnet-b0"
    if key in {"mobilenet_v3", "mobilenet-v3", "mobilenetv3", "mobilenet_v3_large"}:
        return "mobilenetv3"
    return key


def build_model(model_type: str, num_classes: int, freeze_backbone: bool = False) -> torch.nn.Module:
    resolved = resolve_model_type(model_type)
    if resolved not in SUPPORTED_MODELS:
        raise ValueError("Unsupported model type")

    def _weights(weights):
        return None if os.environ.get("SKIP_TORCHVISION_WEIGHTS") == "1" else weights

    if resolved == "resnet18":
        weights = _weights(models.ResNet18_Weights.DEFAULT)
        model = models.resnet18(weights=weights)
        in_features = model.fc.in_features
        model.fc = torch.nn.Linear(in_features, num_classes)
        backbone_params = [p for name, p in model.named_parameters() if not name.startswith("fc")]
    elif resolved == "efficientnet-b0":
        weights = _weights(models.EfficientNet_B0_Weights.DEFAULT)
        model = models.efficientnet_b0(weights=weights)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = torch.nn.Linear(in_features, num_classes)
        backbone_params = [p for name, p in model.named_parameters() if not name.startswith("classifier")]
    else:
        weights = _weights(models.MobileNet_V3_Large_Weights.DEFAULT)
        model = models.mobilenet_v3_large(weights=weights)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = torch.nn.Linear(in_features, num_classes)
        backbone_params = [p for name, p in model.named_parameters() if not name.startswith("classifier")]

    if freeze_backbone:
        for param in backbone_params:
            param.requires_grad = False

    return model


def load_model_from_checkpoint(checkpoint: dict[str, Any], device: torch.device) -> tuple[torch.nn.Module, dict[str, Any]]:
    model_type = resolve_model_type(str(checkpoint["model_type"]))
    model = build_model(model_type, checkpoint["num_classes"], freeze_backbone=False)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.to(device)
    model.eval()
    return model, {
        "model_type": model_type,
        "class_names": checkpoint["class_names"],
        "image_size": checkpoint["image_size"],
        "num_classes": checkpoint["num_classes"],
        "created_at": checkpoint.get("created_at"),
    }
