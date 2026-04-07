import torch
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# FGSM ATTACK
# ---------------------------------------------------------------------------

def fgsm_attack(image, epsilon, gradient):
    sign_grad = gradient.sign()
    perturbed = image + epsilon * sign_grad
    return torch.clamp(perturbed, 0, 1)


# ---------------------------------------------------------------------------
# FGSM SENSITIVITY CHECK
# ---------------------------------------------------------------------------
# FIX: The original code used `pred1 != pred2 OR confidence_drop > 0.20`.
# That OR is the root cause of false positives — a clean, slightly-uncertain
# image often shifts prediction under any perturbation.
# NEW logic: BOTH prediction change AND a large confidence drop must occur.
# This means the model must be simultaneously unstable AND lose significant
# confidence on its own prediction — a much stronger adversarial signal.
# ---------------------------------------------------------------------------

def detect_fgsm_attack(model, image):
    img = image.clone().detach().requires_grad_(True)

    output = model(img)
    pred_idx = output.argmax(dim=1)

    criterion = nn.CrossEntropyLoss()
    loss = criterion(output, pred_idx)
    model.zero_grad()
    loss.backward()
    gradient = img.grad.data

    perturbed = fgsm_attack(img, 0.01, gradient)

    with torch.no_grad():
        output2 = model(perturbed)

    probs1 = F.softmax(output.detach(), dim=1)
    probs2 = F.softmax(output2, dim=1)

    pred1 = pred_idx.item()
    pred2 = output2.argmax(dim=1).item()
    confidence_drop = probs1[0, pred1].item() - probs2[0, pred1].item()
    prediction_changed = pred1 != pred2

    # Both must be true — prediction flip alone or small drop alone is NOT enough
    significant_drop = confidence_drop > 0.30   # raised from 0.20
    flag = prediction_changed and significant_drop

    return {
        "prediction_changed": prediction_changed,
        "confidence_drop": confidence_drop,
        "flag": flag,
    }


# ---------------------------------------------------------------------------
# TRANSFORM STABILITY CHECK
# ---------------------------------------------------------------------------
# FIX: Original used `len(unstable) >= 2 OR conf_drop > 0.25`.
# A normal complex scene image can easily fail one transform by chance.
# NEW: Per-transform instability requires BOTH prediction flip AND >0.20 drop,
# and the overall flag requires BOTH 2+ unstable transforms AND large drop.
# ---------------------------------------------------------------------------

def transform_check(model, image):
    transforms_to_test = {
        "horizontal_flip": transforms.RandomHorizontalFlip(p=1.0),
        "center_crop": transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
        ]),
    }

    with torch.no_grad():
        baseline_output = model(image)
    baseline_probs = F.softmax(baseline_output, dim=1)
    baseline_pred = baseline_output.argmax(dim=1).item()
    baseline_conf = baseline_probs[0, baseline_pred].item()

    unstable_transforms = []
    largest_conf_drop = 0.0

    for name, transform in transforms_to_test.items():
        transformed_img = transform(image.squeeze(0)).unsqueeze(0)
        with torch.no_grad():
            transformed_output = model(transformed_img)
        transformed_probs = F.softmax(transformed_output, dim=1)
        transformed_pred = transformed_output.argmax(dim=1).item()
        transformed_conf = transformed_probs[0, baseline_pred].item()
        conf_drop = baseline_conf - transformed_conf

        largest_conf_drop = max(largest_conf_drop, conf_drop)
        # Per-transform: require BOTH conditions
        if transformed_pred != baseline_pred and conf_drop > 0.20:
            unstable_transforms.append(name)

    return {
        "unstable_transforms": unstable_transforms,
        "largest_conf_drop": largest_conf_drop,
        # Require BOTH 2+ unstable transforms AND large overall drop
        "flag": len(unstable_transforms) >= 2 and largest_conf_drop > 0.30,
    }


# ---------------------------------------------------------------------------
# FINAL ADVERSARIAL DECISION
# ---------------------------------------------------------------------------
# FIX: Changed `fgsm_flag OR transform_flag` to `fgsm_flag AND transform_flag`.
# Genuine adversarial examples will trip BOTH checks.
# Clean but uncertain images will only trip one (if any), so they won't flag.
# ---------------------------------------------------------------------------

def is_adversarial(model, image):
    fgsm_result = detect_fgsm_attack(model, image.clone().detach())
    transform_result = transform_check(model, image.clone().detach())

    reasons = []
    if fgsm_result["flag"]:
        reasons.append("prediction is fragile to FGSM perturbation")
    if transform_result["flag"]:
        reasons.append("prediction is unstable under image transforms")

    return {
        # AND not OR: both probes must independently flag for adversarial verdict
        "flag": fgsm_result["flag"] and transform_result["flag"],
        "fgsm": fgsm_result,
        "transform": transform_result,
        "reasons": reasons,
    }
