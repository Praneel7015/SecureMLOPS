from io import BytesIO
from pathlib import Path

from PIL import Image

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def validate_image_upload(uploaded_file, max_bytes):
    if uploaded_file is None or not uploaded_file.filename:
        return False, "Please upload an image file."

    filename = uploaded_file.filename.lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return False, "Only JPG, JPEG, and PNG files are allowed."

    file_bytes = uploaded_file.read()
    uploaded_file.stream.seek(0)

    if len(file_bytes) == 0:
        return False, "Uploaded file is empty."

    if len(file_bytes) > max_bytes:
        return False, "File exceeds the maximum size of 5 MB."

    try:
        image = Image.open(BytesIO(file_bytes))
        image.verify()
    except Exception:
        return False, "Uploaded image is corrupted or unreadable."

    return True, "Valid image."


def validate_image_path(image_path, max_bytes):
    path = Path(image_path)
    if not path.exists() or not path.is_file():
        return False, "Selected sample image does not exist."

    filename = path.name.lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return False, "Only JPG, JPEG, and PNG files are allowed."

    file_bytes = path.read_bytes()
    if len(file_bytes) == 0:
        return False, "Selected sample image is empty."

    if len(file_bytes) > max_bytes:
        return False, "Selected sample image exceeds the maximum size of 5 MB."

    try:
        image = Image.open(BytesIO(file_bytes))
        image.verify()
    except Exception:
        return False, "Selected sample image is corrupted or unreadable."

    return True, "Valid image."
