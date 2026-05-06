"""
access_analysis/db.py
──────────────────────
AWS PostgreSQL (RDS) persistence layer for the Access Analysis module.

Responsibilities
────────────────
1. Insert a new security_log row for every request  (append-only, never UPDATE)
2. Fetch the historical average access_risk for a user  (baseline calculation)
3. Fetch the last N log rows to reconstruct a lost in-memory session

The module lazy-initialises a connection pool on first use so the app still
boots if env vars are missing (it just won't persist).

Required environment variables
───────────────────────────────
  DB_HOST      – RDS endpoint, e.g. mydb.abc123xyz.us-east-1.rds.amazonaws.com
  DB_PORT      – default 5432
  DB_NAME      – your database name
  DB_USER      – your database username
  DB_PASSWORD  – your database password

PostgreSQL table schema  (run once on your RDS instance)
────────────────────────────────────────────────────────
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

# ── Lazy connection pool ───────────────────────────────────────────────────────

_pool = None


def _get_pool():
    global _pool
    if _pool is not None:
        return _pool

    host     = os.environ.get("DB_HOST")     or cfg.DB_HOST
    dbname   = os.environ.get("DB_NAME")     or cfg.DB_NAME
    user     = os.environ.get("DB_USER")     or cfg.DB_USER
    password = os.environ.get("DB_PASSWORD") or cfg.DB_PASSWORD

    if not all([host, dbname, user, password]):
        logger.warning("AWS DB env vars not set – DB persistence disabled.")
        return None

    try:
        from psycopg2 import pool as pg_pool  # type: ignore
        raw_port = os.environ.get("DB_PORT")
        try:
            port = int(raw_port) if raw_port else int(cfg.DB_PORT)
        except (TypeError, ValueError):
            logger.warning(
                "Invalid DB_PORT=%r; falling back to default port %s.",
                raw_port,
                cfg.DB_PORT,
            )
            port = int(cfg.DB_PORT)
        _pool = pg_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            sslmode="require",          # RDS enforces SSL by default
            connect_timeout=5,
        )
        logger.info("PostgreSQL connection pool initialised (host=%s)", host)
        return _pool
    except ImportError:
        logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
        return None
    except Exception as exc:
        logger.error("DB pool init failed: %s", exc)
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
    pool = _get_pool()
    if pool is None:
        return False

    sql = f"""
        INSERT INTO {cfg.DB_TABLE}
            (user_id, timestamp, access_risk, final_risk, decision,
             reason, request_type, response_status, input_hash)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        user_id,
        datetime.now(timezone.utc),
        round(access_risk, 4),
        round(final_risk, 4),
        decision,
        reason,
        request_type,
        response_status,
        input_hash,
    )

    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor() as cur:
            cur.execute(sql, values)
        conn.commit()
        logger.debug("DB insert OK user=%s decision=%s", user_id, decision)
        return True
    except Exception as exc:
        if conn:
            conn.rollback()
        logger.error("DB insert failed user=%s: %s", user_id, exc)
        return False
    finally:
        if conn:
            pool.putconn(conn)


def fetch_historical_avg(user_id: str) -> Optional[float]:
    """
    SELECT AVG(access_risk) FROM security_logs WHERE user_id = ?

    Returns the float average, or None if the user has fewer than
    BASELINE_MIN_ROWS rows (not enough history to be meaningful).
    """
    pool = _get_pool()
    if pool is None:
        return None

    sql = f"""
        SELECT access_risk
        FROM   {cfg.DB_TABLE}
        WHERE  user_id = %s
    """

    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            rows = cur.fetchall()

        if len(rows) < cfg.BASELINE_MIN_ROWS:
            return None

        values = [r[0] for r in rows if r[0] is not None]
        return sum(values) / len(values) if values else None
    except Exception as exc:
        logger.error("fetch_historical_avg failed user=%s: %s", user_id, exc)
        return None
    finally:
        if conn:
            pool.putconn(conn)


def fetch_recent_logs(user_id: str, limit: int) -> list[dict]:
    """
    Fetch the *limit* most-recent rows for *user_id*.
    Returns a (possibly empty) list of dicts.
    Used for session reconstruction after a worker restart.
    """
    pool = _get_pool()
    if pool is None:
        return []

    sql = f"""
        SELECT timestamp, input_hash
        FROM   {cfg.DB_TABLE}
        WHERE  user_id = %s
        ORDER  BY timestamp DESC
        LIMIT  %s
    """

    conn = None
    try:
        conn = pool.getconn()
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, limit))
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]

        return [dict(zip(colnames, row)) for row in rows]
    except Exception as exc:
        logger.error("fetch_recent_logs failed user=%s: %s", user_id, exc)
        return []
    finally:
        if conn:
            pool.putconn(conn)
