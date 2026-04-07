from PIL import Image
from torchvision.models import EfficientNet_B0_Weights

# Standard ImageNet preprocessing extracted directly from the model weights
transform = EfficientNet_B0_Weights.DEFAULT.transforms()

def preprocess_image(image_file):
    try:
        img = Image.open(image_file).convert("RGB")
        img = transform(img)
        return img.unsqueeze(0)  # add batch dimension
    except Exception as e:
        raise ValueError("Invalid image input")