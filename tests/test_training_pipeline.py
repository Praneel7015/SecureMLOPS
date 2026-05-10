from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from training import config
from training.progress_tracker import get_job, init_job
from training.registry import list_models, save_dataset_metadata
from training.trainer import run_training_job


def _write_image(path: Path) -> None:
    img = Image.new("RGB", (8, 8), color=(0, 120, 200))
    img.save(path, format="PNG")


def _setup_training_paths(tmp_path: Path, monkeypatch):
    state_dir = tmp_path / "state"
    models_dir = tmp_path / "models"
    datasets_dir = tmp_path / "datasets"

    monkeypatch.setattr(config, "TRAINING_STATE_DIR", state_dir, raising=False)
    monkeypatch.setattr(config, "TRAINED_MODELS_DIR", models_dir, raising=False)
    monkeypatch.setattr(config, "DATASETS_DIR", datasets_dir, raising=False)
    monkeypatch.setattr(config, "JOB_REGISTRY_PATH", state_dir / "jobs.json", raising=False)
    monkeypatch.setattr(config, "MODEL_REGISTRY_PATH", state_dir / "models.json", raising=False)
    monkeypatch.setattr(config, "DATASET_REGISTRY_PATH", state_dir / "datasets.json", raising=False)

    from training import progress_tracker, registry, exporter

    monkeypatch.setattr(progress_tracker, "JOB_REGISTRY_PATH", config.JOB_REGISTRY_PATH, raising=False)
    monkeypatch.setattr(registry, "MODEL_REGISTRY_PATH", config.MODEL_REGISTRY_PATH, raising=False)
    monkeypatch.setattr(registry, "DATASET_REGISTRY_PATH", config.DATASET_REGISTRY_PATH, raising=False)
    monkeypatch.setattr(exporter, "TRAINED_MODELS_DIR", config.TRAINED_MODELS_DIR, raising=False)

    config.ensure_training_dirs()


def test_training_pipeline_executes(tmp_path: Path, monkeypatch):
    _setup_training_paths(tmp_path, monkeypatch)

    dataset_root = tmp_path / "dataset" / "dataset"
    class_a = dataset_root / "cat"
    class_b = dataset_root / "dog"
    class_a.mkdir(parents=True, exist_ok=True)
    class_b.mkdir(parents=True, exist_ok=True)

    _write_image(class_a / "cat1.png")
    _write_image(class_b / "dog1.png")

    dataset_id = "dataset-1"
    save_dataset_metadata(dataset_id, {
        "dataset_dir": str(dataset_root),
        "class_names": ["cat", "dog"],
        "image_count": 2,
        "source_name": "test.zip",
    })

    job_id = "job-1"
    config_payload = {
        "model_type": "resnet18",
        "epochs": 1,
        "batch_size": 1,
        "learning_rate": 0.001,
        "freeze_backbone": True,
        "seed": 42,
    }
    init_job(job_id, dataset_id, config_payload)

    run_training_job(job_id, str(dataset_root), config_payload)

    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job.get("model_id")

    models = list_models()
    assert models
    assert Path(models[0]["file_path"]).exists()
