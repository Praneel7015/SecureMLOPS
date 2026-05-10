from PIL import Image
from torchvision import transforms
from torchvision.models import EfficientNet_B0_Weights

# Standard ImageNet preprocessing extracted directly from the model weights
transform = EfficientNet_B0_Weights.DEFAULT.transforms()


def build_transform(image_size: int):
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
    ])


def preprocess_image(image_file):
    return preprocess_image_with_size(image_file, image_size=224)


def preprocess_image_with_size(image_file, image_size: int):
    try:
        img = Image.open(image_file).convert("RGB")
        img = build_transform(image_size)(img)
        return img.unsqueeze(0)  # add batch dimension
    except Exception:
        raise ValueError("Invalid image input")