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