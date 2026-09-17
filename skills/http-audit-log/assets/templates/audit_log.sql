-- name: InsertAuditLog :exec
INSERT INTO audit_log (
    request_id,
    http_method,
    route,
    status,
    http_status,
    response_code,
    failure_reason,
    metadata,
    raw_request,
    raw_response,
    duration_ms,
    created_at
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
);
