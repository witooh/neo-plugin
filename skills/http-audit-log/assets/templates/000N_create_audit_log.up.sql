BEGIN;

-- audit_log records one row per inbound HTTP API call, both SUCCESS and FAILED
-- outcomes, written by the Audit middleware after the handler chain returns and
-- before the response reaches the client. It captures the full request/response
-- lifecycle (method, route, status, response code, failure reason, searchable
-- metadata, raw request/response, duration) for observability and compliance.
CREATE TABLE IF NOT EXISTS "audit_log" (
    id              BIGSERIAL       PRIMARY KEY,
    request_id      UUID            NOT NULL UNIQUE,
    http_method     VARCHAR(10)     NOT NULL,
    route           VARCHAR(255)    NOT NULL,

    status          VARCHAR(20)     NOT NULL,
    http_status     SMALLINT        NOT NULL,
    response_code   VARCHAR(50)     NOT NULL DEFAULT '',
    failure_reason  TEXT            NOT NULL DEFAULT '',

    metadata        JSONB           NOT NULL DEFAULT '{}'::jsonb,
    raw_request     TEXT            NOT NULL DEFAULT '',
    raw_response    TEXT            NOT NULL DEFAULT '',

    duration_ms     BIGINT          NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CHECK (status IN ('SUCCESS', 'FAILED')),
    CHECK (http_status BETWEEN 100 AND 599),
    CHECK (duration_ms >= 0)
);

CREATE INDEX IF NOT EXISTS audit_log_route_created_idx
    ON audit_log(http_method, route, created_at DESC);

CREATE INDEX IF NOT EXISTS audit_log_status_created_idx
    ON audit_log(status, created_at DESC);

END;
