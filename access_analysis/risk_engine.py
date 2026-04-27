"""
access_analysis/risk_engine.py
────────────────────────────────
Computes the three behavioural risk signals and combines them into a final
access_risk score, adjusted by a historical baseline fetched from Supabase.

Signal definitions
──────────────────
frequency_risk
    How many requests has the user made in the last SESSION_TIME_WINDOW_SEC?
    Linearly interpolated between FREQ_LOW_THRESHOLD (risk=0) and
    FREQ_HIGH_THRESHOLD (risk=1).

timing_risk
    How irregular are the inter-request intervals?
    Measured via the Coefficient of Variation (std / mean).  A perfectly
    regular bot has CoV ≈ 0 (LOW), a human is moderately variable, and an
    erratic bot is highly variable (HIGH).  CoV is normalised to [0, 1].

repetition_risk
    What fraction of the recent input window is dominated by a single hash?
    If one hash appears in ≥ REPETITION_DOMINANT_THRESHOLD fraction of slots,
    risk = 1.0.

Baseline adjustment
───────────────────
  deviation = session_risk − historical_avg
  if deviation > 0:
      final = session_risk + BASELINE_ALPHA * deviation
  else:
      final = session_risk           # never penalise below-average behaviour

Why this matters: a user whose normal baseline is 0.5 spiking to 0.8 is far
more suspicious than a user whose baseline is already 0.75.
"""

import math
import time
from collections import Counter
from typing import Optional

import access_analysis.config as cfg

# ── Individual signal computers ───────────────────────────────────────────────

def compute_frequency_risk(timestamps: list[float]) -> float:
    """
    Count requests in the last SESSION_TIME_WINDOW_SEC seconds.
    Returns a value in [0, 1].
    """
    now = time.time()
    cutoff = now - cfg.SESSION_TIME_WINDOW_SEC
    recent_count = sum(1 for ts in timestamps if ts >= cutoff)

    low  = cfg.FREQ_LOW_THRESHOLD
    high = cfg.FREQ_HIGH_THRESHOLD

    if recent_count <= low:
        return 0.0
    if recent_count >= high:
        return 1.0
    return (recent_count - low) / (high - low)


def compute_timing_risk(timestamps: list[float]) -> float:
    """
    Coefficient of Variation of inter-request intervals, normalised to [0,1].
    Returns 0.0 when fewer than 2 timestamps are available.
    """
    if len(timestamps) < 2:
        return 0.0

    sorted_ts = sorted(timestamps)
    gaps = [sorted_ts[i + 1] - sorted_ts[i] for i in range(len(sorted_ts) - 1)]

    mean_gap = sum(gaps) / len(gaps)
    if mean_gap == 0:
        return 1.0   # identical timestamps → likely a bot replay

    variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
    std_gap  = math.sqrt(variance)
    cv       = std_gap / mean_gap

    return min(cv / cfg.TIMING_CV_MAX, 1.0)


def compute_repetition_risk(inputs: list[str]) -> float:
    """
    Fraction of the window occupied by the most common input hash.
    Returns 0.0 when the window is empty.
    """
    if not inputs:
        return 0.0

    counts  = Counter(inputs)
    top_frac = counts.most_common(1)[0][1] / len(inputs)
    threshold = cfg.REPETITION_DOMINANT_THRESHOLD

    if top_frac >= threshold:
        return 1.0
    return top_frac / threshold   # smooth ramp below threshold


# ── Combined session risk ──────────────────────────────────────────────────────

def compute_session_risk(
    timestamps: list[float],
    inputs: list[str],
) -> dict:
    """
    Return a breakdown dict containing each signal and the weighted sum.
    """
    freq  = compute_frequency_risk(timestamps)
    timing = compute_timing_risk(timestamps)
    rep   = compute_repetition_risk(inputs)

    session_risk = (
        cfg.WEIGHT_FREQUENCY  * freq
        + cfg.WEIGHT_TIMING   * timing
        + cfg.WEIGHT_REPETITION * rep
    )
    session_risk = round(min(session_risk, 1.0), 4)

    return {
        "frequency_risk":  round(freq,   4),
        "timing_risk":     round(timing, 4),
        "repetition_risk": round(rep,    4),
        "session_risk":    session_risk,
    }


# ── Baseline-adjusted final risk ──────────────────────────────────────────────

def apply_baseline(session_risk: float, historical_avg: Optional[float]) -> float:
    """
    If we have a historical average, amplify any upward deviation.
    Returns the final access_risk in [0, 1].
    """
    if historical_avg is None:
        return session_risk

    deviation = session_risk - historical_avg

    if deviation > 0:
        final = session_risk + cfg.BASELINE_ALPHA * deviation
    else:
        final = session_risk

    return round(min(final, 1.0), 4)


# ── Decision engine ────────────────────────────────────────────────────────────

def make_decision(access_risk: float, breakdown: dict) -> tuple[str, str]:
    """
    Returns (decision, reason) based on thresholds in config.

    decision : "ALLOW" | "MONITOR" | "BLOCK"
    reason   : human-readable explanation string
    """
    freq  = breakdown["frequency_risk"]
    timing = breakdown["timing_risk"]
    rep   = breakdown["repetition_risk"]

    # Pick the dominant signal for the reason string
    dominant = max(
        [("frequency", freq), ("timing", timing), ("repetition", rep)],
        key=lambda x: x[1],
    )

    _LABELS = {
        "frequency":  "High request frequency detected",
        "timing":     "Irregular request timing pattern detected",
        "repetition": "High input repetition detected",
    }

    if access_risk <= cfg.RISK_LOW_MAX:
        decision = "ALLOW"
        reason   = "Access pattern within normal bounds"
    elif access_risk <= cfg.RISK_MEDIUM_MAX:
        decision = "MONITOR"
        reason   = f"Elevated access risk — {_LABELS[dominant[0]].lower()}"
    else:
        decision = "BLOCK"
        reason   = _LABELS[dominant[0]]

    return decision, reason
