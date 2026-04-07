from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
import torch

_model = None

def load_model():
    global _model
    if _model is None:
        _model = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
        _model.eval()
    return _model
