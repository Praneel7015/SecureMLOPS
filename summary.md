# SecureMLOPS Summary

SecureMLOPS is a modular Flask + React platform that combines secure image inference with a production-style training workflow. It provides a multi-stage security pipeline for inference requests while supporting dataset validation, background training jobs, and a model registry with downloadable checkpoints.

## Highlights

- **Secure inference** with authentication, rate limiting, integrity checks, access analysis, anomaly/adversarial detection, and risk scoring.
- **Training workflow** with ZIP dataset validation, background job execution, live progress polling, and a model registry.
- **Custom model inference** with safe checkpoint validation and dynamic architecture reconstruction.
- **Production-ready structure** with dedicated modules for validation, training, exports, and persistence.

## Architecture Overview

### Backend (Flask)

- `app.py` hosts API routes for inference and training, enforcing security checks.
- `Detection/` handles preprocessing, prediction, anomaly and adversarial detection.
- `training/` provides dataset validation, model factory, trainer, job manager, exporter, and registries.
- `access_analysis/` tracks behavioral risk scoring with optional PostgreSQL persistence.

### Frontend (React)

- **Dashboard**: summary of datasets, training jobs, and registry state.
- **Inference**: image upload, optional model upload, pipeline results, risk status.
- **Training**: dataset upload, configuration controls, live progress, metrics charts, downloads.

## Security & Safety

- ZIP extraction uses path traversal protection.
- Dataset format enforced via `classes.json` and folder checks.
- Checkpoints validated for required metadata and supported architectures.
- Training jobs run in background threads to avoid blocking Flask requests.

## Persistence

- Training jobs, datasets, and model registry metadata are stored in JSON registries under `training_state/`.
- Model artifacts are stored under `trained_models/`.

## Supported Models

- ResNet18
- EfficientNet-B0
- MobileNetV3 (Large)

## How to Run

See `steps.md` for the full end-to-end command list.
