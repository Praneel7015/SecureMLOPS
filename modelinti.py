
from utils.file_hash import sha256_for_file
from pathlib import Path

files = ["Detection/model_loader.py", "Detection/predictor.py"]
BASE_DIR = Path(".").resolve()

for f in files:
    path = BASE_DIR / f
    print(f"{f}: {sha256_for_file(path)}")