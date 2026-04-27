"""
access_analysis/db.py
──────────────────────
Supabase (PostgreSQL) persistence layer for the Access Analysis module.

Responsibilities
────────────────
1. Insert a new security_log row for every request  (append-only, never UPDATE)
2. Fetch the historical average access_risk for a user  (baseline calculation)
3. Fetch the last N log rows to reconstruct a lost in-memory session

The module lazy-initialises the Supabase client on first use so the app still
boots if the env vars are missing (it just won't persist).

Required environment variables
───────────────────────────────
  SUPABASE_URL       – e.g. https://xyzxyz.supabase.co
  SUPABASE_ANON_KEY  – the project's anon/public JWT

Supabase table schema  (run once in the SQL editor)
────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS security_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         TEXT        NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    access_risk     FLOAT       NOT NULL,
    final_risk      FLOAT       NOT NULL,
    decision        TEXT        NOT NULL,
    reason          TEXT        NOT NULL,
    request_type    TEXT        NOT NULL DEFAULT 'inference',
    response_status TEXT        NOT NULL,
    input_hash      TEXT        NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_security_logs_user_id
    ON security_logs (user_id);
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import access_analysis.config as cfg

logger = logging.getLogger("secureml.access.db")

# ── Lazy Supabase client ───────────────────────────────────────────────────────

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    url = os.environ.get("SUPABASE_URL") or cfg.SUPABASE_URL
    key = os.environ.get("SUPABASE_ANON_KEY") or cfg.SUPABASE_KEY

    if not url or not key:
        logger.warning("Supabase env vars not set – DB persistence disabled.")
        return None

    try:
        from supabase import create_client  # type: ignore
        _client = create_client(url, key)
        logger.info("Supabase client initialised (url=%s)", url)
        return _client
    except ImportError:
        logger.error("supabase-py not installed.  Run: pip install supabase")
        return None
    except Exception as exc:
        logger.error("Supabase init failed: %s", exc)
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def insert_log(
    user_id: str,
    access_risk: float,
    final_risk: float,
    decision: str,
    reason: str,
    request_type: str,
    response_status: str,
    input_hash: str,
) -> bool:
    """
    Append a new row to security_logs.
    Returns True on success, False on failure.
    Never raises – the calling code must not crash if DB is unavailable.
    """
    client = _get_client()
    if client is None:
        return False

    row = {
        "user_id":         user_id,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "access_risk":     round(access_risk, 4),
        "final_risk":      round(final_risk, 4),
        "decision":        decision,
        "reason":          reason,
        "request_type":    request_type,
        "response_status": response_status,
        "input_hash":      input_hash,
    }

    try:
        client.table(cfg.SUPABASE_TABLE).insert(row).execute()
        logger.debug("DB insert OK user=%s decision=%s", user_id, decision)
        return True
    except Exception as exc:
        logger.error("DB insert failed user=%s: %s", user_id, exc)
        return False


def fetch_historical_avg(user_id: str) -> Optional[float]:
    """
    SELECT AVG(access_risk) FROM security_logs WHERE user_id = ?

    Returns the float average, or None if the user has fewer than
    BASELINE_MIN_ROWS rows (not enough history to be meaningful).
    """
    client = _get_client()
    if client is None:
        return None

    try:
        resp = (
            client.table(cfg.SUPABASE_TABLE)
            .select("access_risk")
            .eq("user_id", user_id)
            .execute()
        )
        rows = resp.data or []
        if len(rows) < cfg.BASELINE_MIN_ROWS:
            return None
        values = [r["access_risk"] for r in rows if r.get("access_risk") is not None]
        return sum(values) / len(values) if values else None
    except Exception as exc:
        logger.error("fetch_historical_avg failed user=%s: %s", user_id, exc)
        return None


def fetch_recent_logs(user_id: str, limit: int) -> list[dict]:
    """
    Fetch the *limit* most-recent rows for *user_id*.
    Returns a (possibly empty) list of dicts.
    Used for session reconstruction after a worker restart.
    """
    client = _get_client()
    if client is None:
        return []

    try:
        resp = (
            client.table(cfg.SUPABASE_TABLE)
            .select("timestamp, input_hash")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("fetch_recent_logs failed user=%s: %s", user_id, exc)
        return []
