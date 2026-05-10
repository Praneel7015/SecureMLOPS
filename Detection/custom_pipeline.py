from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F

from Detection.adversarial import is_adversarial
from Detection.anomaly import evaluate_anomaly
from Detection.preprocessing import preprocess_image_with_size


def process_custom_image(
    image_file: str,
    model: torch.nn.Module,
    class_names: list[str],
    image_size: int,
    device: torch.device,
) -> dict[str, Any]:
    input_tensor = preprocess_image_with_size(image_file, image_size)
    input_tensor = input_tensor.to(device)

    with torch.no_grad():
        output = model(input_tensor)
        probs = F.softmax(output, dim=1)

        confidence, predicted = torch.max(probs, 1)
        top_probs, top_indices = torch.topk(probs, k=min(5, probs.shape[1]), dim=1)

    top5 = [
        {
            "label": class_names[index.item()],
            "confidence": prob.item(),
        }
        for prob, index in zip(top_probs[0], top_indices[0])
    ]

    anomaly_result = evaluate_anomaly(probs)
    adv_result = is_adversarial(model, input_tensor)

    issues = []
    issues.extend(anomaly_result["reasons"])
    issues.extend(adv_result["reasons"])

    transform_unstable = bool(adv_result["transform"]["unstable_transforms"])

    if anomaly_result["flag"] and adv_result["flag"]:
        verdict = "suspicious"
    elif transform_unstable:
        verdict = "suspicious"
    elif anomaly_result["flag"] or adv_result["flag"]:
        verdict = "uncertain"
    else:
        verdict = "reliable"

    return {
        "prediction": predicted.item(),
        "label": class_names[predicted.item()],
        "confidence": confidence.item(),
        "top5": top5,
        "anomaly": anomaly_result["flag"],
        "adversarial": adv_result["flag"],
        "verdict": verdict,
        "anomaly_score": anomaly_result["score"],
        "top1_confidence": anomaly_result["top1_confidence"],
        "top2_confidence": anomaly_result["top2_confidence"],
        "margin": anomaly_result["margin"],
        "entropy": anomaly_result["entropy"],
        "normalized_entropy": anomaly_result["normalized_entropy"],
        "fgsm_confidence_drop": adv_result["fgsm"]["confidence_drop"],
        "transform_confidence_drop": adv_result["transform"]["largest_conf_drop"],
        "transform_instability": adv_result["transform"]["unstable_transforms"],
        "issues": issues,
    }
