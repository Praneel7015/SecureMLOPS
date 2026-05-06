# Secure ML Inference System

This project is a secure machine learning inference application built around an image classification pipeline. It combines a pretrained EfficientNet-B0 model with multiple security checks so the system does not blindly return predictions for unsafe or suspicious inputs.

The app includes a Flask-based dashboard that shows the full staged pipeline visually, from authentication to the final risk decision. Users can choose default images from the local `images/` directory or upload their own image and then see exactly how the system processed the request.

## What The Project Does

The system runs an image through these stages:

1. Authentication
2. Rate limiting
3. Input validation
4. Preprocessing
5. Model integrity verification
6. Initial AI prediction
7. Anomaly detection
8. Adversarial detection
9. Risk decision engine

Depending on the security signals, the request is either:

- `allowed`
- `allowed_with_warning`
- `blocked`

## Main Features

- Secure image upload flow with file validation
- Built-in sample image gallery from the `images/` folder
- EfficientNet-B0 image classification using torchvision pretrained weights
- Statistical anomaly detection based on confidence, entropy, and prediction margin
- Adversarial detection using FGSM sensitivity and transform stability checks
- Rate limiting for repeated requests
- File and model-weight integrity verification
- Audit-style staged pipeline output in the web UI
- Security event logging

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

## First-Time Setup (Backend + React Frontend)

### 1. Clone and open the project

```powershell
git clone https://github.com/Praneel7015/SecureMLOPS.git
Set-Location -LiteralPath .\SecureMLOPS
```

### 2. Create and activate Python virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

```powershell
pip install -r requirements.txt
```

### 4. Install React frontend dependencies (`frontend` folder)

```powershell

pip install flask torch torchvision pillow werkzeug psycopg2-binary python-dotenv
```
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
npm run build
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
