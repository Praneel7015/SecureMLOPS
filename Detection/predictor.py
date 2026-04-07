import torch
import torch.nn.functional as F

from torchvision.models import EfficientNet_B0_Weights

weights = EfficientNet_B0_Weights.DEFAULT

# This gives you labels automatically
labels = weights.meta["categories"]

def predict(model, input_tensor):
    with torch.no_grad():
        output = model(input_tensor)
        probs = F.softmax(output, dim=1)

        confidence, predicted = torch.max(probs, 1)
        top_probs, top_indices = torch.topk(probs, k=5, dim=1)

    top5 = [
        {
            "label": labels[index.item()],
            "confidence": prob.item(),
        }
        for prob, index in zip(top_probs[0], top_indices[0])
    ]

    return {
        "class": predicted.item(), #class index(0-999) from the ImageNet dataset
        "label": labels[predicted.item()],#human readable class name
        "confidence": confidence.item(), #Probability assigned to the predicted class
        "probs": probs,
        "top5": top5,
    }
