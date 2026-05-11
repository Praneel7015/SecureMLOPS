# Secure MLOps Platform

SecureMLOPS is a modular Flask + React platform for secure image inference **and** model training. It combines a hardened security pipeline (authentication, rate limiting, integrity verification, anomaly/adversarial detection, access analysis, and risk scoring) with a production-style training workflow that supports dataset validation, background training jobs, and model registry management.

## Core Features

- Secure image inference with full security pipeline visibility
- Optional custom model uploads validated before inference
- Dataset ZIP validation with ZIP Slip protection
- Background training jobs with live progress polling
- Model registry with downloadable checkpoints
- Detailed audit logs and risk decisions

## Architecture Overview

Backend modules are separated by responsibility:

- `app.py`: Flask routes + security pipeline integration
- `Detection/`: inference, preprocessing, anomaly/adversarial checks
- `training/`: dataset validation, model factory, trainer, job manager, exporters
- `access_analysis/`: behavioral risk scoring and persistence

Frontend structure mirrors the backend workflow:

- **Dashboard**: overview of datasets, jobs, and models
- **Inference**: upload image + optional model, view pipeline output
- **Training**: upload dataset, configure jobs, track progress, download models

## Dataset ZIP Format

```
dataset.zip
└── dataset/
        ├── cat/
        ├── dog/
        └── classes.json
```

`classes.json` must match the folder names:

```json
{
    "classes": ["cat", "dog"]
}
```

Supported image formats: `.jpg`, `.jpeg`, `.png`.

Example ZIP layout: see `examples/dataset/README.md`.

## Supported Training Models

- ResNet18
- EfficientNet-B0
- MobileNetV3 (large)

Each checkpoint includes:

```json
{
    "model_state_dict": "...",
    "class_names": ["cat", "dog"],
    "model_type": "resnet18",
    "image_size": 224,
    "num_classes": 2,
    "metrics": {"final_val_accuracy": 0.92},
    "created_at": "2026-05-08T12:00:00Z"
}
```

## Setup

### Backend

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend

```powershell
Set-Location -LiteralPath .\frontend
npm install
Set-Location -LiteralPath ..
```

## Running the App

### Option A: Flask serves the built React app

```powershell
Set-Location -LiteralPath .\frontend
npm run build
Set-Location -LiteralPath ..
python app.py
```

Open: `http://127.0.0.1:5000`

### Option B: React dev server + Flask API

Terminal 1:

```powershell
python app.py
```

Terminal 2:

```powershell
Set-Location -LiteralPath .\frontend
npm run dev
```

Dev URL: `http://127.0.0.1:5173`

## Example Training Flow

1. Upload `dataset.zip` in the Training tab.
2. Choose model type, epochs, batch size, and learning rate.
3. Start training; progress updates via polling.
4. Download the exported `.pt` checkpoint from the Model Registry.

## Example Inference Flow

1. Upload an image (or select a sample).
2. Optionally upload a trained `.pt` checkpoint.
3. Review security pipeline results, prediction, and risk decision.

## Security Validation Notes

- ZIP extraction uses safe path checks to prevent ZIP Slip.
- `classes.json` must match dataset folder names.
- Uploaded checkpoints are validated before loading and must include required metadata.
- Only ResNet18, EfficientNet-B0, and MobileNetV3 checkpoints are accepted.

## Tests

```powershell
pytest
```

## Additional Docs

- `steps.md` - End-to-end command checklist for setup, run, and validation.
- `summary.md` - High-level project summary and architecture notes.

## Project Structure

```text
miniproject/
├── app.py                     # Flask web application
├── main.py                    # Simple script runner for local batch testing
├── images/                    # Default sample images
├── uploads/                   # User-uploaded or selected sample copies
├── templates/
│   └── index.html             # Main UI template
├── static/
│   └── style.css              # UI styling
├── Detection/
│   ├── model_loader.py
│   ├── preprocessing.py
│   ├── predictor.py
│   ├── anomaly.py
│   ├── adversarial.py
│   └── ml_pipeline.py
├── decision/
│   └── engine.py              # Final allow/warn/block decision logic
├── integrity/
│   └── checker.py             # Integrity verification
├── validation/
│   └── image_validator.py     # Upload and image checks
├── rate_limit/
│   └── service.py             # Request throttling
├── auth/
│   ├── auth_service.py
│   └── users.json             # Stored user credentials
├── config/
│   └── integrity.json         # Protected file hashes + model fingerprint
└── utils/
    ├── file_hash.py
    ├── model_fingerprint.py
    └── logging_setup.py
```

## Tech Stack

- Python 3.11+
- Flask
- PyTorch
- Torchvision
- Pillow
- Werkzeug

-postgres 16.13
## First-Time Setup (Backend + React Frontend)

### 1. Clone and open the project

```powershell
git clone https://github.com/Praneel7015/SecureMLOPS.git
Set-Location -LiteralPath .\SecureMLOPS
```

### 2. Create and activate Python virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

```powershell
pip install -r requirements.txt
```

### 4. Install React frontend dependencies (`frontend` folder)

`.env` File

Create a `.env` file in the project root:

```env
DB_HOST=mydb.abc123xyz.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=securemlops
DB_USER=secureml_user
DB_PASSWORD=your-strong-password-here
```

### Connect to RDS

Connect to your RDS instance using `psql` (or any PostgreSQL GUI like DBeaver/pgAdmin):

```bash
psql -h your-rds-endpoint.rds.amazonaws.com -U secureml_user -d securemlops
```
Frontend
```bash
Set-Location -LiteralPath .\frontend
npm install
Set-Location -LiteralPath ..

```

## Running The Project

### Option A (recommended): Flask serves built React app on `:5000`

Build the React app first:

```powershell
Set-Location -LiteralPath .\frontend
npm run dev
Set-Location -LiteralPath ..
```

Run Flask:

```powershell
python app.py
```

Open in browser:

```text
http://127.0.0.1:5000
```

### Option B: React hot-reload development mode

Terminal 1 (backend):

```powershell
Set-Location -LiteralPath <path-to-cloned-repo>\SecureMLOPS
python app.py
```

Terminal 2 (frontend dev server):

```powershell
Set-Location -LiteralPath <path-to-cloned-repo>\SecureMLOPS\frontend
npm run dev
```

Open frontend dev URL:

```text
http://127.0.0.1:5173
```

The Vite dev server is configured to proxy backend API calls to Flask on `127.0.0.1:5000`.

### Run the simple batch script

This processes all images inside the `images/` folder and prints the raw detection result.

```powershell
python main.py
```

## Login Credentials

The current app uses the following users from `auth/users.json`:

- `person1` / `secure123`
- `person2` / `secure123`

## How The Integrity Check Works

The integrity layer verifies two things:

- Protected source files listed in `config/integrity.json`
- The fingerprint of the initialized EfficientNet-B0 model weights

This means the app is not only checking whether key code files changed, but also whether the loaded model weights still match the expected fingerprint.

## Sample Workflow

1. Log in to the system.
2. Select a default image from the gallery or upload your own.
3. Run the security pipeline.
4. Review the staged pipeline cards.
5. Check the final risk verdict and prediction output.

## Notes

- Uploaded files are stored in the `uploads/` directory.
- Sample images come from the `images/` directory.
- Security logs are written to `logs/security.log`.
- If the integrity check fails, the system blocks the request before inference proceeds.

## Future Improvements

- Add unit tests for the security pipeline
- Add admin tools for regenerating integrity fingerprints safely
- Add per-stage timing metrics in the UI
- Add Docker support

## License

Add your preferred license here if needed.
