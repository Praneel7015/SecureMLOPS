import json
from pathlib import Path

from werkzeug.security import check_password_hash

USER_DB = Path(__file__).resolve().parent / "users.json"


def authenticate_user(username, password):
    if not username or not password:
        return False, "Username and password are required."

    users = json.loads(USER_DB.read_text(encoding="utf-8"))
    user_record = users.get(username)

    if not user_record:
        return False, "Unknown user."

    if not check_password_hash(user_record["password_hash"], password):
        return False, "Invalid password."

    return True, "Authenticated"
