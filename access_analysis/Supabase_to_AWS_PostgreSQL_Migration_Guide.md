# Supabase → AWS PostgreSQL (RDS) Migration Guide
### SecureMLOPS Access Analysis Project

---

## Overview

Your project's database logic is cleanly isolated inside **`access_analysis/db.py`**. The Supabase SDK is used there exclusively via a lazy client that wraps three operations:

| Function | What it does |
|---|---|
| `insert_log(...)` | Appends one row per request to `security_logs` |
| `fetch_historical_avg(user_id)` | Computes `AVG(access_risk)` for a user |
| `fetch_recent_logs(user_id, limit)` | Fetches last N rows for session reconstruction |

The rest of the app (`analyser.py`, `app.py`, etc.) only calls these three functions — so **you only need to rewrite `db.py`** and update a few config/env vars. Nothing else touches the database.

---

## What You Need to Change — File by File

### 1. `requirements.txt`

**Remove** the Supabase SDK. **Add** `psycopg2` (the standard PostgreSQL driver for Python).

```diff
- supabase>=2.0.0
+ psycopg2-binary>=2.9.9
```

> Use `psycopg2-binary` for local development (no compilation needed). For production deployments, use `psycopg2` (compiled against your system's libpq) for better performance.

---

### 2. `access_analysis/config.py`

Replace the three Supabase config lines at the bottom with AWS RDS connection parameters.

**Remove these lines:**
```python
# ── Supabase (set these via environment variables) ───────────────────────────
SUPABASE_URL = None        # overridden by env var SUPABASE_URL
SUPABASE_KEY = None        # overridden by env var SUPABASE_ANON_KEY
SUPABASE_TABLE = "security_logs"
```

**Replace with:**
```python
# ── AWS PostgreSQL / RDS (set these via environment variables) ────────────────
DB_HOST     = None         # overridden by env var DB_HOST     (your RDS endpoint)
DB_PORT     = 5432         # overridden by env var DB_PORT
DB_NAME     = None         # overridden by env var DB_NAME
DB_USER     = None         # overridden by env var DB_USER
DB_PASSWORD = None         # overridden by env var DB_PASSWORD
DB_TABLE    = "security_logs"
```

---

### 3. `access_analysis/db.py` — Full Rewrite

This is the only file that needs significant rewriting. Replace the entire file content with the following:

```python
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
    port     = int(os.environ.get("DB_PORT", cfg.DB_PORT))
    dbname   = os.environ.get("DB_NAME")     or cfg.DB_NAME
    user     = os.environ.get("DB_USER")     or cfg.DB_USER
    password = os.environ.get("DB_PASSWORD") or cfg.DB_PASSWORD

    if not all([host, dbname, user, password]):
        logger.warning("AWS DB env vars not set – DB persistence disabled.")
        return None

    try:
        from psycopg2 import pool as pg_pool  # type: ignore
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
```

---

### 4. `.env` File (Create this — never commit it)

Create a `.env` file in the project root:

```env
DB_HOST=mydb.abc123xyz.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=securemlops
DB_USER=secureml_user
DB_PASSWORD=your-strong-password-here
```

`.env` is already in your `.gitignore` — so it is safe and will not be committed.

To load it at runtime, add this to `main.py` or `app.py` at the very top:

```python
from dotenv import load_dotenv
load_dotenv()
```

And add `python-dotenv` to `requirements.txt`:
```
python-dotenv>=1.0.0
```

---

## Step-by-Step AWS Setup

### Step 1 — Create an RDS PostgreSQL Instance

1. Go to **AWS Console → RDS → Create database**
2. Choose:
   - Engine: **PostgreSQL** (latest stable, e.g. 16.x)
   - Template: **Free tier** (for dev) or **Production**
   - DB instance identifier: `securemlops-db`
   - Master username: `secureml_user`
   - Master password: *(generate a strong one)*
3. Under **Connectivity**:
   - VPC: choose the same VPC as your app server (or default VPC for local dev)
   - Public access: **Yes** for local dev, **No** for production (use a bastion or VPC peering instead)
4. Under **Additional configuration**:
   - Initial database name: `securemlops`
5. Click **Create database** — takes ~5 minutes.

After creation, note the **Endpoint** (looks like `securemlops-db.abc123.us-east-1.rds.amazonaws.com`) — this is your `DB_HOST`.

---

### Step 2 — Configure the Security Group

Your RDS instance has a Security Group that acts as a firewall.

1. Go to your RDS instance → **Connectivity & security** → click the Security Group link.
2. Add an **Inbound rule**:
   - Type: **PostgreSQL**
   - Port: **5432**
   - Source: Your app server's IP (or Security Group ID if on EC2/ECS) — **not `0.0.0.0/0`** in production.

---

### Step 3 — Create the Table (Run Once)

Connect to your RDS instance using `psql` (or any PostgreSQL GUI like DBeaver/pgAdmin):

```bash
psql -h your-rds-endpoint.rds.amazonaws.com -U secureml_user -d securemlops
```

Then run the schema (same SQL as Supabase — it's standard PostgreSQL):

```sql
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
```

> This is identical to your existing `supabase_scheme` file — no changes to the schema needed.

---

### Step 4 — Migrate Existing Data (Optional)

If you want to carry over existing rows from Supabase:

**Export from Supabase:**
```bash
# In Supabase dashboard → Table Editor → security_logs → Export as CSV
# OR using psql against Supabase's connection string:
psql "postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres" \
  -c "\COPY security_logs TO 'security_logs_export.csv' CSV HEADER"
```

**Import into AWS RDS:**
```bash
psql -h your-rds-endpoint.rds.amazonaws.com -U secureml_user -d securemlops \
  -c "\COPY security_logs (user_id, timestamp, access_risk, final_risk, decision, reason, request_type, response_status, input_hash) FROM 'security_logs_export.csv' CSV HEADER"
```

> The `id` column (BIGSERIAL) is excluded — AWS RDS will auto-generate new IDs.

---

### Step 5 — Install Dependencies

```bash
pip install psycopg2-binary python-dotenv
```

Or update your venv:
```bash
pip install -r requirements.txt
```

---

### Step 6 — Test the Connection

Quick connection test before starting the full app:

```python
# test_db.py (run from project root)
from dotenv import load_dotenv
load_dotenv()

from access_analysis import db

# Test insert
ok = db.insert_log(
    user_id="test_user",
    access_risk=0.1,
    final_risk=0.1,
    decision="ALLOW",
    reason="connection test",
    request_type="test",
    response_status="200",
    input_hash="abc123",
)
print("Insert OK:", ok)

# Test fetch
avg = db.fetch_historical_avg("test_user")
print("Historical avg:", avg)

logs = db.fetch_recent_logs("test_user", limit=5)
print("Recent logs:", logs)
```

Run it:
```bash
python test_db.py
```

Expected output:
```
Insert OK: True
Historical avg: None   # None because < 3 rows (BASELINE_MIN_ROWS)
Recent logs: [{'timestamp': ..., 'input_hash': 'abc123'}]
```

---

## Summary of All Changed Files

| File | What changes |
|---|---|
| `requirements.txt` | Remove `supabase>=2.0.0`, add `psycopg2-binary>=2.9.9`, add `python-dotenv>=1.0.0` |
| `access_analysis/config.py` | Replace 3 Supabase config lines with 6 DB config lines |
| `access_analysis/db.py` | Full rewrite — replace Supabase client with psycopg2 connection pool |
| `.env` (new file) | Add RDS credentials as environment variables |
| `main.py` or `app.py` | Add `from dotenv import load_dotenv; load_dotenv()` at the top |

**Files that do NOT need any changes:**

- `access_analysis/analyser.py` — calls `db.insert_log`, `db.fetch_historical_avg`, `db.fetch_recent_logs` — same function signatures, no change.
- `access_analysis/session_store.py` — no DB calls.
- `access_analysis/risk_engine.py` — no DB calls.
- `app.py` — no direct DB calls.
- All other files — untouched.

---

## Production Checklist

- [ ] RDS instance created in same VPC as your app server
- [ ] Security Group allows port 5432 from app only (not `0.0.0.0/0`)
- [ ] SSL enforced (`sslmode="require"` is already set in the new `db.py`)
- [ ] `.env` file is in `.gitignore` (already is in your project)
- [ ] Credentials stored in AWS Secrets Manager (recommended for production instead of `.env`)
- [ ] Automated RDS backups enabled (set retention to 7+ days in RDS settings)
- [ ] Delete `access_analysis/supabase_scheme` file or rename it to `postgres_schema.sql` for clarity
