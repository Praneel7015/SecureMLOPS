# import torch
# from torchvision.utils import save_image

# noise = torch.rand(3, 224, 224)
# save_image(noise, "images/noise.jpg") -- randome noise

import torch
from torchvision import transforms
from PIL import Image
from torchvision.utils import save_image

# Step 1: Load image
# image = Image.open("images/cat.jpg").convert("RGB")
image = Image.open("images/guarddog.jpg").convert("RGB")

# Step 2: Convert to tensor
transform = transforms.ToTensor()
image_tensor = transform(image)

# Step 3: Add batch dimension (VERY IMPORTANT)
image_tensor = image_tensor.unsqueeze(0)

# Step 4: Add noise
def add_noise(image, epsilon=0.05):
    noise = torch.randn_like(image) * epsilon
    noisy_image = image + noise
    return torch.clamp(noisy_image, 0, 1)

noisy = add_noise(image_tensor)

# Step 5: Remove batch dimension before saving
noisy = noisy.squeeze(0)

# Step 6: Save image
# save_image(noisy, "images/noisycat.jpg")
save_image(noisy, "images/noisydog.jpg")