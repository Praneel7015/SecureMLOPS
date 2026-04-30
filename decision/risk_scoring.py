"""
Risk scoring recalibration.

Original problem: fine-grained signals (entropy, conf_drop, margin) had weights
so high they would push a perfectly normal image to MEDIUM/HIGH risk even when
neither the anomaly nor adversarial flags were set.

Example (original weights, normal image, 70% confidence):
    adversarial = False → 0
    anomaly     = False → 0
    entropy ≈ 0.35      → 0.20 * 0.35 = 0.07
    conf_drop ≈ 0.12    → 0.20 * 0.12 = 0.024
    margin ≈ 0.50       → 0.10 * 0.50 = 0.05
    anomaly_score = 0   → 0
    input_risk ≈ 0.14
    total_risk  ≈ 0.14 + 0.3 * (0.14/3) = 0.154  →  "LOW" only by margin

With the OLD thresholds for anomaly/adversarial being too loose, the flags
would often be set, pushing input_risk to 0.6–0.8.

NEW approach:
  - Fine-grained signals are minor adjustments only (halved weights)
  - The major penalty (adversarial/anomaly base) only fires when those flags
    are actually warranted after the tightened detection thresholds
"""


def compute_input_risk(ml_result: dict) -> float:
    risk = 0.0

    # Primary binary signals — these dominate
    if ml_result["adversarial"]:
        risk += 0.45
    if ml_result["anomaly"]:
        risk += 0.20

    # Fine-grained adjustments — reduced from original 0.20 to 0.10 each
    anomaly_score = ml_result["anomaly_score"] / 3.0
    entropy = ml_result["normalized_entropy"]
    margin = ml_result["margin"]
    conf_drop = ml_result["fgsm_confidence_drop"]

    risk += 0.10 * anomaly_score          # was 0.20
    risk += 0.10 * entropy                # was 0.20
    risk += 0.05 * (1.0 - margin)        # was 0.10
    risk += 0.10 * conf_drop             # was 0.20

    return min(risk, 1.0)


def compute_traffic_risk(rate_limited: bool) -> float:
    return 1.0 if rate_limited else 0.0


def compute_access_risk(auth_failed_or_score) -> float:
    """
        Accept either:
        • bool  – legacy API (True → 1.0, False → 0.0)
        • float – pre-computed access_risk from access_analysis module
        """
    if isinstance(auth_failed_or_score, bool):
        return 1.0 if auth_failed_or_score else 0.0
    return float(auth_failed_or_score)




def compute_total_risk(ml_result: dict, rate_limited: bool, auth_failed=False,access_risk:float|None=None,) -> dict:
    input_risk = compute_input_risk(ml_result)
    traffic_risk = compute_traffic_risk(rate_limited)
    
    if access_risk is not None:
        acc_risk = compute_access_risk(access_risk)
    else:
        acc_risk = compute_access_risk(auth_failed)

    max_risk = max(input_risk, traffic_risk, acc_risk)
    mean_risk = (input_risk + traffic_risk + acc_risk) / 3.0
    lambda_factor = 0.3

    total_risk = min(max_risk + lambda_factor * mean_risk, 1.0)

    return {
        "total_risk": round(total_risk, 3),
        "breakdown": {
            "input_risk": round(input_risk, 3),
            "traffic_risk": round(traffic_risk, 3),
            "access_risk": round(acc_risk, 3),
        },
    }
