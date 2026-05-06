"""
access_analysis/analyser.py
─────────────────────────────
Public entry point for the Access Analysis module.

analyse_request() is the single function called from app.py.
It orchestrates:

  1. Session lookup / reconstruction
  2. Record the current request
  3. Compute behavioural risk signals
  4. Fetch historical baseline from Supabase
  5. Apply baseline adjustment
  6. Make ALLOW / MONITOR / BLOCK decision
  7. Persist the log row to RDS

Returns a dict that app.py can merge into its result payload.
"""

import hashlib
import logging
import time
from typing import Optional

from access_analysis import config as cfg
from access_analysis import db, session_store
from access_analysis.risk_engine import (
    apply_baseline,
    compute_session_risk,
    make_decision,
)

logger = logging.getLogger("secureml.access")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_input(raw: str) -> str:
    """SHA-256 of the input string, hex-encoded."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reconstruct_if_needed(user_id: str) -> None:
    """
    If the in-memory session is missing, pull the last N rows from Supabase
    and rebuild timestamps + input-hashes.
    """
    if session_store.get_session(user_id) is not None:
        return   # session is present – nothing to do

    logger.info("Session missing for user=%s – attempting DB reconstruction", user_id)
    rows = db.fetch_recent_logs(user_id, limit=cfg.SESSION_TIMESTAMP_WINDOW)

    if not rows:
        logger.info("No DB history for user=%s – starting blank session", user_id)
        session_store.init_session(user_id)
        return

    timestamps = []
    inputs     = []
    for row in rows:
        try:
            ts = _parse_iso_timestamp(row["timestamp"])
            timestamps.append(ts)
        except Exception:
            pass
        if row.get("input_hash"):
            inputs.append(row["input_hash"])

    session_store.reconstruct_session(user_id, timestamps, inputs)
    logger.info(
        "Reconstructed session for user=%s from %d DB rows", user_id, len(rows)
    )


def _parse_iso_timestamp(iso: str) -> float:
    """Convert ISO-8601 string → Unix epoch float (UTC)."""
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.replace(tzinfo=timezone.utc).timestamp()


# ── Public API ─────────────────────────────────────────────────────────────────

def analyse_request(
    user_id: str,
    input_identifier: str,          # filename, selected_sample, or raw input key
    request_type: str = "inference",
    response_status: str = "200",
) -> dict:
    """
    Run the full Access Analysis pipeline for a single request.

    Parameters
    ----------
    user_id           : authenticated username
    input_identifier  : something that uniquely identifies the input
                        (filename / sample name / form field value)
    request_type      : "inference" | "training" | etc.
    response_status   : HTTP status code string, set after the fact if needed

    Returns
    -------
    dict with keys:
        access_risk     float in [0,1]
        final_risk      float in [0,1]   (baseline-adjusted)
        decision        "ALLOW" | "MONITOR" | "BLOCK"
        reason          str
        breakdown       dict of sub-scores
        historical_avg  float | None
        allowed         bool
    """
    now       = time.time()
    inp_hash  = _hash_input(input_identifier)

    # 1. Ensure session exists (reconstruct from DB if worker restarted)
    _reconstruct_if_needed(user_id)

    # 2. Record this request in the session
    session_store.record_request(user_id, now, inp_hash)

    # 3. Read session data for analysis
    session   = session_store.get_session(user_id)
    timestamps = list(session["timestamps"])
    inputs     = list(session["inputs"])

    # 4. Compute behavioural risk signals
    breakdown = compute_session_risk(timestamps, inputs)
    session_risk = breakdown["session_risk"]

    # 5. Fetch historical baseline (non-blocking – returns None if unavailable)
    historical_avg: Optional[float] = db.fetch_historical_avg(user_id)

    # 6. Apply baseline adjustment
    final_risk = apply_baseline(session_risk, historical_avg)

    # 7. Decision
    decision, reason = make_decision(final_risk, breakdown)

    result = {
        "access_risk":    session_risk,
        "final_risk":     final_risk,
        "decision":       decision,
        "reason":         reason,
        "breakdown":      breakdown,
        "historical_avg": historical_avg,
        "allowed":        decision != "BLOCK",
    }

    logger.info(
        "ACCESS user=%s decision=%s access_risk=%.3f final_risk=%.3f "
        "freq=%.3f timing=%.3f rep=%.3f hist_avg=%s",
        user_id, decision, session_risk, final_risk,
        breakdown["frequency_risk"],
        breakdown["timing_risk"],
        breakdown["repetition_risk"],
        f"{historical_avg:.3f}" if historical_avg is not None else "None",
    )

    # 8. Persist to Supabase (best-effort, never raises)
    try:
        db.insert_log(
            user_id         = user_id,
            access_risk     = session_risk,
            final_risk      = final_risk,
            decision        = decision,
            reason          = reason,
            request_type    = request_type,
            response_status = response_status,
            input_hash      = inp_hash,
        )
    except Exception as exc:
        logger.error("DB log failed (non-fatal): %s", exc)

    return result
