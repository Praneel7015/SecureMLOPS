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

## Setup

### 1. Clone the repository

```powershell
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

If you have a `requirements.txt`, install with:

```powershell
pip install -r requirements.txt
```

If not, install the main packages manually:

```powershell
pip install flask torch torchvision pillow werkzeug
```

##
```
export SUPABASE_URL=your_supabase_apiurl
export SUPABASE_ANON_KEY=your_anon_key_here
```
## Running The Project

### Run the Flask web app

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

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

- Add a `requirements.txt`
- Add unit tests for the security pipeline
- Add admin tools for regenerating integrity fingerprints safely
- Add per-stage timing metrics in the UI
- Add Docker support

## License

Add your preferred license here if needed.
