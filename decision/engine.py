"""
Risk decision engine.

FIX 1 — API inconsistency:
  The original engine required ml_result as a positional arg, but app.py was
  calling decide_risk(suspicious=False, adversarial=False, integrity_ok=False, ...)
  for error cases (rate-limit, validation fail, integrity fail). Those calls
  had no ml_result and passed kwargs the function didn't accept → TypeError.

  Solution: make ml_result optional, accept **kwargs to absorb legacy params,
  and handle each error path before touching ml_result.

FIX 2 — Missing risk_level:
  The original returned {"action": ..., "risk": 0.71, "breakdown": ...}.
  app.py used decision["risk_level"] which didn't exist → KeyError.
  Now returns a "risk_level" string (LOW / MEDIUM / HIGH / CRITICAL) and a
  "status" string so app.py doesn't need its own action-to-status mapping.
"""

from decision.risk_scoring import compute_total_risk


def decide_risk(
    ml_result=None,
    rate_limited=False,
    auth_failed=False,
    integrity_ok=True,
    validation_error=None,
    **kwargs,   # absorb legacy kwargs like suspicious=, adversarial=, etc.
) -> dict:
    # ── Error paths (no ML inference) ────────────────────────────────────────
    if not integrity_ok:
        return _build("BLOCK", 1.0, {})

    if rate_limited:
        return _build("BLOCK", 1.0, {})

    if validation_error or ml_result is None:
        return _build("BLOCK", 0.85, {})

    # ── Normal path: ML result present ───────────────────────────────────────
    risk_data = compute_total_risk(ml_result, rate_limited, auth_failed)
    total_risk = risk_data["total_risk"]

    if total_risk <= 0.30:
        action = "ALLOW"
    elif total_risk <= 0.55:
        action = "MONITOR"
    elif total_risk <= 0.75:
        action = "ALERT"
    else:
        action = "BLOCK"

    return _build(action, total_risk, risk_data["breakdown"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _risk_level(risk: float) -> str:
    if risk <= 0.30:
        return "LOW"
    elif risk <= 0.55:
        return "MEDIUM"
    elif risk <= 0.75:
        return "HIGH"
    return "CRITICAL"


_STATUS = {
    "ALLOW":   "allowed",
    "MONITOR": "allowed_with_warning",
    "ALERT":   "allowed_with_warning",
    "BLOCK":   "blocked",
}


def _build(action: str, risk: float, breakdown: dict) -> dict:
    return {
        "action":     action,
        "risk":       risk,
        "risk_level": _risk_level(risk),
        "status":     _STATUS[action],
        "breakdown":  breakdown,
    }
