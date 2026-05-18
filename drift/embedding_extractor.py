from __future__ import annotations

from typing import Dict
from weakref import WeakKeyDictionary

import torch
import torch.nn.functional as F

from training.model_factory import resolve_model_type

_FEATURE_CACHE: "WeakKeyDictionary[torch.nn.Module, torch.nn.Module]" = WeakKeyDictionary()


def _build_feature_extractor(model: torch.nn.Module, model_type: str) -> torch.nn.Module:
    resolved = resolve_model_type(model_type)
    if resolved == "resnet18":
        return torch.nn.Sequential(*list(model.children())[:-1])
    if resolved == "efficientnet-b0":
        return torch.nn.Sequential(model.features, model.avgpool)
    if resolved == "mobilenetv3":
        return torch.nn.Sequential(model.features, model.avgpool)
    return torch.nn.Sequential(*list(model.children())[:-1])


def get_feature_extractor(model: torch.nn.Module, model_type: str) -> torch.nn.Module:
    extractor = _FEATURE_CACHE.get(model)
    if extractor is None:
        extractor = _build_feature_extractor(model, model_type)
        extractor.eval()
        _FEATURE_CACHE[model] = extractor
    return extractor


def extract_embedding(
    model: torch.nn.Module,
    model_type: str,
    input_tensor: torch.Tensor,
    device: torch.device,
) -> list[float]:
    extractor = get_feature_extractor(model, model_type).to(device)
    with torch.no_grad():
        features = extractor(input_tensor.to(device))
        flat = features.view(features.size(0), -1)
    normalized = F.normalize(flat, p=2, dim=1)
    return normalized.squeeze(0).cpu().tolist()
