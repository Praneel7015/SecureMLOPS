"""SQLite persistence layer for normalized security events."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "training_state" / "security_events.db"

_lock = threading.Lock()
_db_path: Path = DEFAULT_DB_PATH


def configure_db_path(path: Path | str) -> None:
    global _db_path
    _db_path = Path(path)


def _connect() -> sqlite3.Connection:
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_db_path), timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_event_store(db_path: Path | str | None = None) -> None:
    if db_path is not None:
        configure_db_path(db_path)
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS security_events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_events_event_type ON security_events(event_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_events_source ON security_events(source)"
            )
            conn.commit()
        finally:
            conn.close()


def _serialize_metadata(metadata: dict[str, Any] | None) -> str:
    return json.dumps(metadata or {}, sort_keys=True, default=str)


def _deserialize_row(row: sqlite3.Row) -> dict[str, Any]:
    metadata = {}
    try:
        metadata = json.loads(row["metadata_json"] or "{}")
    except Exception:
        metadata = {}
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "severity": row["severity"],
        "event_type": row["event_type"],
        "source": row["source"],
        "title": row["title"],
        "description": row["description"],
        "metadata": metadata,
    }


def insert_event(event: dict[str, Any]) -> None:
    init_event_store()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO security_events
                    (id, timestamp, severity, event_type, source, title, description, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["timestamp"],
                    event["severity"],
                    event["event_type"],
                    event["source"],
                    event["title"],
                    event.get("description") or event["title"],
                    _serialize_metadata(event.get("metadata")),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def fetch_events_raw(
    *,
    where_clause: str = "",
    params: tuple[Any, ...] = (),
    order: str = "DESC",
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    init_event_store()
    order_dir = "DESC" if order.upper() == "DESC" else "ASC"
    sql = f"SELECT * FROM security_events {where_clause} ORDER BY timestamp {order_dir}, id {order_dir}"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params = (*params, limit, offset)

    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [_deserialize_row(row) for row in rows]
        finally:
            conn.close()


def count_events_raw(where_clause: str = "", params: tuple[Any, ...] = ()) -> int:
    init_event_store()
    sql = f"SELECT COUNT(*) AS cnt FROM security_events {where_clause}"
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(sql, params).fetchone()
            return int(row["cnt"]) if row else 0
        finally:
            conn.close()


def fetch_event_by_id(event_id: str) -> dict[str, Any] | None:
    init_event_store()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT * FROM security_events WHERE id = ?", (event_id,)).fetchone()
            return _deserialize_row(row) if row else None
        finally:
            conn.close()


def execute_scalar(query: str, params: tuple[Any, ...] = ()) -> Any:
    init_event_store()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(query, params).fetchone()
            if row is None:
                return None
            return row[0] if len(row.keys()) == 1 else dict(row)
        finally:
            conn.close()
