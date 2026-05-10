from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATASETS_DIR = BASE_DIR / "training_datasets"
TRAINING_STATE_DIR = BASE_DIR / "training_state"
TRAINED_MODELS_DIR = BASE_DIR / "trained_models"

JOB_REGISTRY_PATH = TRAINING_STATE_DIR / "jobs.json"
MODEL_REGISTRY_PATH = TRAINING_STATE_DIR / "models.json"
DATASET_REGISTRY_PATH = TRAINING_STATE_DIR / "datasets.json"

MAX_DATASET_UPLOAD_BYTES = 600 * 1024 * 1024
MAX_MODEL_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_IMAGE_COUNT = 20000
MAX_IMAGE_SIDE = 4096
MAX_EPOCHS = 50
MAX_BATCH_SIZE = 256
MIN_BATCH_SIZE = 1
MIN_LEARNING_RATE = 1e-6
MAX_LEARNING_RATE = 1e-1
DEFAULT_RANDOM_SEED = 42
DEFAULT_VALIDATION_SPLIT = 0.2

MAX_CONCURRENT_TRAINING = 1
MAX_QUEUED_JOBS = 3

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

SUPPORTED_MODELS = {
    "resnet18": {"label": "ResNet18", "image_size": 224},
    "efficientnet-b0": {"label": "EfficientNet-B0", "image_size": 224},
    "mobilenetv3": {"label": "MobileNetV3", "image_size": 224},
}


def ensure_training_dirs() -> None:
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    TRAINING_STATE_DIR.mkdir(parents=True, exist_ok=True)
    TRAINED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
