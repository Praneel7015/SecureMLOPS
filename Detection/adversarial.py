import torch
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F

# FGSM ATTACK
def fgsm_attack(image, epsilon, gradient):
    sign_grad = gradient.sign()
    perturbed = image + epsilon * sign_grad
    return torch.clamp(perturbed, 0, 1)

# DETECTION USING FGSM
def detect_fgsm_attack(model, image):
    image.requires_grad = True

    output = model(image)
    pred_idx = output.argmax(dim=1)
    
    # Maximize the loss of the predicted class to create an adversarial example
    criterion = nn.CrossEntropyLoss()
    loss = criterion(output, pred_idx)

    model.zero_grad()
    loss.backward()

    gradient = image.grad.data

    perturbed = fgsm_attack(image, 0.01, gradient)

    output2 = model(perturbed)
    probs1 = F.softmax(output, dim=1)
    probs2 = F.softmax(output2, dim=1)

    pred1 = pred_idx.item()
    pred2 = output2.argmax(dim=1).item()
    confidence_drop = probs1[0, pred1].item() - probs2[0, pred1].item()

    return {
        "prediction_changed": pred1 != pred2,
        "confidence_drop": confidence_drop,
        "flag": pred1 != pred2 or confidence_drop > 0.20,
    }

# TRANSFORMATION CHECK
def transform_check(model, image):
    transforms_to_test = {
        "horizontal_flip": transforms.RandomHorizontalFlip(p=1.0),
        "center_crop": transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
        ]),
    }

    baseline_output = model(image)
    baseline_probs = F.softmax(baseline_output, dim=1)
    baseline_pred = baseline_output.argmax(dim=1).item()
    baseline_conf = baseline_probs[0, baseline_pred].item()

    unstable_transforms = []
    largest_conf_drop = 0.0

    for name, transform in transforms_to_test.items():
        transformed_img = transform(image.squeeze(0)).unsqueeze(0)
        transformed_output = model(transformed_img)
        transformed_probs = F.softmax(transformed_output, dim=1)
        transformed_pred = transformed_output.argmax(dim=1).item()
        transformed_conf = transformed_probs[0, baseline_pred].item()
        conf_drop = baseline_conf - transformed_conf

        largest_conf_drop = max(largest_conf_drop, conf_drop)
        if transformed_pred != baseline_pred or conf_drop > 0.15:
            unstable_transforms.append(name)

    return {
        "unstable_transforms": unstable_transforms,
        "largest_conf_drop": largest_conf_drop,
        "flag": len(unstable_transforms) >= 2 or largest_conf_drop > 0.25,
    }

# FINAL ADVERSARIAL DECISION
def is_adversarial(model, image):
    fgsm_result = detect_fgsm_attack(model, image.clone().detach())
    transform_result = transform_check(model, image.clone().detach())

    reasons = []
    if fgsm_result["flag"]:
        reasons.append("prediction is fragile to FGSM perturbation")
    if transform_result["flag"]:
        reasons.append("prediction is unstable under image transforms")

    return {
        "flag": fgsm_result["flag"] or transform_result["flag"],
        "fgsm": fgsm_result,
        "transform": transform_result,
        "reasons": reasons,
    }
