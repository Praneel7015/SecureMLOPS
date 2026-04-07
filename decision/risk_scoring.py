def compute_input_risk(ml_result):
    risk = 0.0

    # Base signals
    if ml_result["adversarial"]:
        risk += 0.5

    if ml_result["anomaly"]:
        risk += 0.3

    # Fine-grained signals
    anomaly_score = ml_result["anomaly_score"] / 3.0
    entropy = ml_result["normalized_entropy"]
    margin = ml_result["margin"]
    conf_drop = ml_result["fgsm_confidence_drop"]

    risk += 0.2 * anomaly_score
    risk += 0.2 * entropy
    risk += 0.1 * (1 - margin)
    risk += 0.2 * conf_drop

    return min(risk, 1.0)


def compute_traffic_risk(rate_limited):
    return 1.0 if rate_limited else 0.0


def compute_access_risk(auth_failed):
    return 1.0 if auth_failed else 0.0


def compute_total_risk(ml_result, rate_limited, auth_failed):
    input_risk = compute_input_risk(ml_result)
    traffic_risk = compute_traffic_risk(rate_limited)
    access_risk = compute_access_risk(auth_failed)

    max_risk = max(input_risk, traffic_risk, access_risk)

    mean_risk = (input_risk + traffic_risk + access_risk) / 3
    lambda_factor = 0.3

    total_risk = min(max_risk + lambda_factor * mean_risk, 1.0)

    return {
        "total_risk": round(total_risk, 3),
        "breakdown": {
            "input_risk": input_risk,
            "traffic_risk": traffic_risk,
            "access_risk": access_risk
        }
    }