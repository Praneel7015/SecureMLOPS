"""
access_analysis/session_store.py
─────────────────────────────────
In-memory rolling-window session store.

Stores, per user:
  • recent_timestamps : deque[float]   – epoch seconds of the last N requests
  • recent_inputs     : deque[str]     – hashes of the last M inputs

The store is a plain module-level dict – one process, one dict, no external
dependency. In a multi-worker/serverless deployment, cross-worker persistence
is handled by PostgreSQL/RDS (see db.py), while within a single worker the
dict provides zero-latency reads/writes.
"""

from collections import deque
from typing import Dict

from access_analysis.config import SESSION_TIMESTAMP_WINDOW, SESSION_INPUT_WINDOW

# ── Internal store ────────────────────────────────────────────────────────────

_store: Dict[str, dict] = {}


# ── Public API ────────────────────────────────────────────────────────────────

def get_session(user_id: str) -> dict | None:
    """Return the session dict for *user_id*, or None if absent."""
    return _store.get(user_id)


def init_session(user_id: str) -> dict:
    """Create a blank session for *user_id* and return it."""
    session = {
        "timestamps": deque(maxlen=SESSION_TIMESTAMP_WINDOW),
        "inputs":     deque(maxlen=SESSION_INPUT_WINDOW),
    }
    _store[user_id] = session
    return session


def get_or_create_session(user_id: str) -> dict:
    """Return existing session or create a new blank one."""
    return _store.get(user_id) or init_session(user_id)


def record_request(user_id: str, timestamp: float, input_hash: str) -> None:
    """Append a new timestamp and input_hash to the user's session."""
    session = get_or_create_session(user_id)
    session["timestamps"].append(timestamp)
    session["inputs"].append(input_hash)


def reconstruct_session(user_id: str, timestamps: list[float], inputs: list[str]) -> dict:
    """
    Rebuild the in-memory session from historical DB rows.
    Called when the worker has no session for this user (e.g. after a restart).
    """
    session = init_session(user_id)
    for ts in timestamps[-SESSION_TIMESTAMP_WINDOW:]:
        session["timestamps"].append(ts)
    for inp in inputs[-SESSION_INPUT_WINDOW:]:
        session["inputs"].append(inp)
    return session


def clear_session(user_id: str) -> None:
    """Remove session (useful in tests)."""
    _store.pop(user_id, None)
