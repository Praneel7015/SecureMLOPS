"""
decision/risk_scoring.py  (updated)
─────────────────────────────────────
compute_access_risk() now accepts the pre-computed access_risk float from the
Access Analysis module instead of the binary auth_failed flag.

Backward compatibility is maintained: if called with the legacy bool signature
(auth_failed=True/False) the function still returns 0.0 or 1.0.
"""


def compute_input_risk(ml_result: dict) -> float:
    risk = 0.0

    if ml_result["adversarial"]:
        risk += 0.45
    if ml_result["anomaly"]:
        risk += 0.20

    anomaly_score = ml_result["anomaly_score"] / 3.0
    entropy = ml_result["normalized_entropy"]
    margin = ml_result["margin"]
    conf_drop = ml_result["fgsm_confidence_drop"]

    risk += 0.10 * anomaly_score
    risk += 0.10 * entropy
    risk += 0.05 * (1.0 - margin)
    risk += 0.10 * conf_drop

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


def compute_total_risk(
    ml_result: dict,
    rate_limited: bool,
    auth_failed=False,
    access_risk: float | None = None,
) -> dict:
    """
    Compute final risk score.

    Parameters
    ----------
    ml_result    : output of process_image()
    rate_limited : from RateLimiter
    auth_failed  : legacy bool (used when access_risk is not provided)
    access_risk  : pre-computed float from access_analysis.analyse_request()
                   If provided, overrides auth_failed.
    """
    input_risk   = compute_input_risk(ml_result)
    traffic_risk = compute_traffic_risk(rate_limited)

    if access_risk is not None:
        acc_risk = compute_access_risk(access_risk)
    else:
        acc_risk = compute_access_risk(auth_failed)

    max_risk    = max(input_risk, traffic_risk, acc_risk)
    mean_risk   = (input_risk + traffic_risk + acc_risk) / 3.0
    lambda_factor = 0.3

    total_risk = min(max_risk + lambda_factor * mean_risk, 1.0)

    return {
        "total_risk": round(total_risk, 3),
        "breakdown": {
            "input_risk":   round(input_risk,   3),
            "traffic_risk": round(traffic_risk, 3),
            "access_risk":  round(acc_risk,     3),
        },
    }
