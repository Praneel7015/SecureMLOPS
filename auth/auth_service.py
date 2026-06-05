"""Echelon authentication service.

Backs a simple JSON user store (auth/users.json). Supports:
  - email/password registration + login (login by email OR username/key)
  - Google OAuth account upsert (link by google_id, then email)

Records are keyed by a stable identifier (email for new accounts, legacy
username for pre-existing ones) and carry:
  password_hash | display_name | email | role | google_id | created_at
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

USER_DB = Path(__file__).resolve().parent / "users.json"
_LOCK = threading.Lock()

EMAIL_MIN = 3
PASSWORD_MIN = 8


# ── store helpers ─────────────────────────────────────────────────────────────

def _load() -> dict:
    if not USER_DB.exists():
        return {}
    try:
        return json.loads(USER_DB.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def _save(users: dict) -> None:
    USER_DB.write_text(json.dumps(users, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _find_by_email(users: dict, email: str):
    """Return (key, record) for a matching email, or (None, None)."""
    email = (email or "").strip().lower()
    if not email:
        return None, None
    for key, record in users.items():
        if str(record.get("email", "")).strip().lower() == email:
            return key, record
        if key.strip().lower() == email:
            return key, record
    return None, None


def _find_by_google_id(users: dict, google_id: str):
    for key, record in users.items():
        if record.get("google_id") and record["google_id"] == google_id:
            return key, record
    return None, None


# ── public API ────────────────────────────────────────────────────────────────

def authenticate_user(identifier, password):
    """Authenticate by username/key OR email + password."""
    if not identifier or not password:
        return False, "Email and password are required.", None

    users = _load()
    record = users.get(identifier)
    key = identifier
    if record is None:
        key, record = _find_by_email(users, identifier)

    if not record:
        return False, "We couldn't find an account with those details.", None

    stored = record.get("password_hash")
    if not stored:
        return False, "This account uses Google sign-in. Continue with Google.", None

    if not check_password_hash(stored, password):
        return False, "Incorrect password.", None

    return True, "Authenticated", key


def register_user(name, email, password):
    """Create a new email/password account. Returns (ok, message, key)."""
    name = (name or "").strip()
    email = (email or "").strip().lower()

    if not name:
        return False, "Please enter your name.", None
    if "@" not in email or len(email) < EMAIL_MIN:
        return False, "Please enter a valid email address.", None
    if len(password or "") < PASSWORD_MIN:
        return False, f"Password must be at least {PASSWORD_MIN} characters.", None

    with _LOCK:
        users = _load()
        existing_key, _ = _find_by_email(users, email)
        if existing_key is not None:
            return False, "An account with this email already exists.", None

        users[email] = {
            "password_hash": generate_password_hash(password),
            "display_name": name,
            "email": email,
            "role": "user",
            "google_id": None,
            "created_at": _now(),
        }
        _save(users)

    return True, "Account created.", email


def upsert_google_user(google_id, email, name):
    """Find or create an account for a verified Google identity. Returns key."""
    email = (email or "").strip().lower()
    name = (name or "").strip() or (email.split("@")[0] if email else "Member")

    with _LOCK:
        users = _load()

        key, record = _find_by_google_id(users, google_id)
        if record is None and email:
            key, record = _find_by_email(users, email)

        if record is not None:
            # Link / refresh Google identity on the existing record.
            record["google_id"] = google_id
            if email and not record.get("email"):
                record["email"] = email
            if name and not record.get("display_name"):
                record["display_name"] = name
            users[key] = record
            _save(users)
            return key

        new_key = email or f"google-{google_id}"
        users[new_key] = {
            "password_hash": None,
            "display_name": name,
            "email": email or None,
            "role": "user",
            "google_id": google_id,
            "created_at": _now(),
        }
        _save(users)
        return new_key


def get_user(key):
    """Return the record for a session key (or None)."""
    if not key:
        return None
    return _load().get(key)


def get_display_name(key):
    record = get_user(key)
    if not record:
        return key
    return record.get("display_name") or record.get("email") or key
