from decision.risk_scoring import compute_total_risk

def decide_risk(ml_result, rate_limited=False, auth_failed=False):
    
    risk_data = compute_total_risk(ml_result, rate_limited, auth_failed)
    total_risk = risk_data["total_risk"]

    # Step 5: Risk → Action mapping
    if total_risk <= 0.3:
        action = "ALLOW"
    elif total_risk <= 0.6:
        action = "MONITOR"
    elif total_risk <= 0.8:
        action = "ALERT"
    else:
        action = "BLOCK"

    return {
        "action": action,
        "risk": total_risk,
        "breakdown": risk_data["breakdown"]
    }