import logging
import os

from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0


logger = logging.getLogger("secureml.access.model")

_model = None
_loaded_with_pretrained_weights = False

def load_model():
    global _model, _loaded_with_pretrained_weights
    if _model is None:
        use_pretrained_weights = os.environ.get("SKIP_TORCHVISION_WEIGHTS") != "1"
        weights = EfficientNet_B0_Weights.DEFAULT if use_pretrained_weights else None
        try:
            _model = efficientnet_b0(weights=weights)
            _loaded_with_pretrained_weights = weights is not None
        except Exception as exc:
            logger.warning("Falling back to EfficientNet-B0 without pretrained weights: %s", exc)
            _model = efficientnet_b0(weights=None)
            _loaded_with_pretrained_weights = False
        _model.eval()
    return _model


def loaded_with_pretrained_weights() -> bool:
    return _loaded_with_pretrained_weights
