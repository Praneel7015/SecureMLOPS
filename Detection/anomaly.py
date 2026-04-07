import torch

def calculate_entropy(probs):
    return -torch.sum(probs * torch.log(probs + 1e-10))

def evaluate_anomaly(probs):
    probs = probs.squeeze(0)
    sorted_probs, _ = torch.sort(probs, descending=True)

    top1 = sorted_probs[0].item()
    top2 = sorted_probs[1].item()
    margin = top1 - top2
    entropy = calculate_entropy(probs).item()
    normalized_entropy = entropy / torch.log(torch.tensor(float(probs.numel()))).item()

    low_confidence = top1 < 0.55
    very_uncertain = normalized_entropy > 0.72
    ambiguous = margin < 0.20

    score = 0
    if low_confidence:
        score += 1
    if very_uncertain:
        score += 1
    if ambiguous:
        score += 1

    return {
        "flag": score >= 2,
        "score": score,
        "top1_confidence": top1,
        "top2_confidence": top2,
        "margin": margin,
        "entropy": entropy,
        "normalized_entropy": normalized_entropy,
        "reasons": [
            reason
            for reason, active in (
                ("low top-1 confidence", low_confidence),
                ("high prediction uncertainty", very_uncertain),
                ("small gap between top predictions", ambiguous),
            )
            if active
        ],
    }

def is_anomalous(probs, confidence=None):
    return evaluate_anomaly(probs)["flag"]
