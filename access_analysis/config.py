"""
access_analysis/config.py
─────────────────────────
All tuneable parameters for the Access Analysis module.
"""

# ── Session rolling window ────────────────────────────────────────────────────
SESSION_TIMESTAMP_WINDOW = 20        # max recent timestamps kept per user
SESSION_INPUT_WINDOW      = 10       # max recent input-hashes kept per user
SESSION_TIME_WINDOW_SEC   = 300      # look-back window for frequency (5 min)

# ── Risk weights  (must sum to 1.0) ─────────────────────────────────────────
WEIGHT_FREQUENCY  = 0.40
WEIGHT_TIMING     = 0.30
WEIGHT_REPETITION = 0.30

# ── Frequency risk thresholds ────────────────────────────────────────────────
FREQ_LOW_THRESHOLD  = 5    # ≤ this → risk 0
FREQ_HIGH_THRESHOLD = 20   # ≥ this → risk 1

# ── Timing risk: coefficient of variation cap ────────────────────────────────
TIMING_CV_MAX = 2.0        # CoV above this is capped at risk 1.0

# ── Repetition risk ──────────────────────────────────────────────────────────
REPETITION_DOMINANT_THRESHOLD = 0.70   # dominant-input fraction → risk 1.0

# ── Historical baseline ───────────────────────────────────────────────────────
BASELINE_ALPHA   = 0.25    # upward deviation amplifier
BASELINE_MIN_ROWS = 3      # minimum rows needed before baseline is applied

# ── Decision thresholds ──────────────────────────────────────────────────────
RISK_LOW_MAX    = 0.35     # ≤ → LOW  → ALLOW
RISK_MEDIUM_MAX = 0.65     # ≤ → MEDIUM → MONITOR

# ── AWS PostgreSQL / RDS (set these via environment variables) ────────────────
DB_HOST     = None         # overridden by env var DB_HOST     (your RDS endpoint)
DB_PORT     = 5432         # overridden by env var DB_PORT
DB_NAME     = None         # overridden by env var DB_NAME
DB_USER     = None         # overridden by env var DB_USER
DB_PASSWORD = None         # overridden by env var DB_PASSWORD
DB_TABLE    = "security_logs"
