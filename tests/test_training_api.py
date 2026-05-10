import json
import zipfile
from pathlib import Path
import sys

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as flask_app


def _write_image(path: Path) -> None:
    img = Image.new("RGB", (8, 8), color=(50, 80, 120))
    img.save(path, format="PNG")


def _build_dataset(tmp_path: Path) -> Path:
    payload_root = tmp_path / "payload"
    dataset_root = payload_root / "dataset"
    class_dir = dataset_root / "cat"
    class_dir.mkdir(parents=True, exist_ok=True)
    _write_image(class_dir / "cat1.png")
    (dataset_root / "classes.json").write_text(json.dumps({"classes": ["cat"]}))
    return payload_root


def _zip_dataset(root: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for item in root.rglob("*"):
            zip_file.write(item, item.relative_to(root))


@pytest.fixture
def client(tmp_path, monkeypatch):
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user"] = "person1"
        monkeypatch.setattr(flask_app, "DATASET_UPLOAD_DIR", tmp_path / "datasets", raising=False)
        monkeypatch.setattr(flask_app, "MODEL_UPLOAD_DIR", tmp_path / "models", raising=False)
        flask_app.DATASET_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        flask_app.MODEL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        from training import config as training_config
        from training import registry
        state_dir = tmp_path / "state"
        monkeypatch.setattr(training_config, "TRAINING_STATE_DIR", state_dir, raising=False)
        monkeypatch.setattr(training_config, "JOB_REGISTRY_PATH", state_dir / "jobs.json", raising=False)
        monkeypatch.setattr(training_config, "MODEL_REGISTRY_PATH", state_dir / "models.json", raising=False)
        monkeypatch.setattr(training_config, "DATASET_REGISTRY_PATH", state_dir / "datasets.json", raising=False)
        monkeypatch.setattr(registry, "MODEL_REGISTRY_PATH", training_config.MODEL_REGISTRY_PATH, raising=False)
        monkeypatch.setattr(registry, "DATASET_REGISTRY_PATH", training_config.DATASET_REGISTRY_PATH, raising=False)
        training_config.ensure_training_dirs()

        yield client


def test_dataset_upload_and_list(client, tmp_path):
    payload_root = _build_dataset(tmp_path)
    zip_path = tmp_path / "dataset.zip"
    _zip_dataset(payload_root, zip_path)

    with zip_path.open("rb") as handle:
        response = client.post(
            "/api/training/datasets",
            data={"dataset": (handle, "dataset.zip")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"]
    dataset_id = payload["dataset"]["dataset_id"]

    list_response = client.get("/api/training/datasets")
    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert any(item["dataset_id"] == dataset_id for item in list_payload["datasets"])


def test_training_start_endpoint(client, monkeypatch):
    from training.registry import save_dataset_metadata

    dataset = save_dataset_metadata(
        "dataset-id",
        {
            "dataset_dir": str(Path(flask_app.DATASET_UPLOAD_DIR) / "dataset"),
            "class_names": ["cat"],
            "image_count": 1,
            "source_name": "dataset.zip",
        },
    )
    dataset_dir = Path(dataset["dataset_dir"])
    dataset_dir.mkdir(parents=True, exist_ok=True)

    dummy_job = {
        "job_id": "job-id",
        "dataset_id": dataset["dataset_id"],
        "status": "queued",
        "epochs": 1,
        "current_epoch": 0,
        "progress": 0.0,
    }

    monkeypatch.setattr(flask_app, "submit_training_job", lambda *_args, **_kwargs: dummy_job)
    monkeypatch.setattr(
        flask_app.rate_limiter,
        "check",
        lambda *_args, **_kwargs: {"allowed": True, "message": "Request allowed."},
    )

    response = client.post(
        "/api/training/start",
        json={
            "dataset_id": dataset["dataset_id"],
            "model_type": "resnet18",
            "epochs": 1,
            "batch_size": 1,
            "learning_rate": 0.001,
            "freeze_backbone": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"]
    assert payload["job"]["job_id"] == "job-id"
