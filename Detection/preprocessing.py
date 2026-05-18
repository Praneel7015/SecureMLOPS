from PIL import Image
from torchvision import transforms

from training.dataset_loader import build_eval_transforms


def build_transform(image_size: int) -> transforms.Compose:
    return build_eval_transforms(image_size)


def preprocess_image(image_file):
    return preprocess_image_with_size(image_file, image_size=224)


def preprocess_image_with_size(image_file, image_size: int):
    try:
        img = Image.open(image_file).convert("RGB")
        img = build_transform(image_size)(img)
        return img.unsqueeze(0)  # add batch dimension
    except Exception:
        raise ValueError("Invalid image input")