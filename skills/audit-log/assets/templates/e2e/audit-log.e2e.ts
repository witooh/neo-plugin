/**
 * E2E — per-request HTTP audit log.
 *
 * Portable SUCCESS is GET /health (MR 196 used POST /v1/accounts). Set SCHEMA
 * from Step 0. FAILED must hit a REGISTERED 4xx route — unmatched 404 has
 * empty FullPath(). If ApiClient has no get(), use globalThis.apiContext.get.
 *
 * Title: `[<CARD> - AC-NNN] …` when a work record has ACs; else `[audit] …`.
 */
import { ApiClient, DbHelper } from "@helpers/index";

const SCHEMA = "__SCHEMA__"; // e.g. "account" — must match Step 0

describe("Audit log", () => {
  let api: ApiClient;
  let db: DbHelper;

  beforeAll(async () => {
    api = new ApiClient(globalThis.apiContext);
    db = new DbHelper();
    await db.connect();
  });

  afterAll(async () => {
    await db.disconnect();
  });

  it("[audit] GET /health writes an audit_log row with status SUCCESS", async () => {
    const since = new Date();

    const { status } = await api.get("/health");
    expect(status).toBe(200);

    const audit = await db.query(
      `SELECT http_method, route, status, http_status, duration_ms
         FROM ${SCHEMA}.audit_log
        WHERE http_method = $1 AND route = $2 AND status = $3 AND created_at >= $4
        ORDER BY created_at DESC
        LIMIT 1`,
      ["GET", "/health", "SUCCESS", since.toISOString()],
    );
    expect(audit.rowCount).toBe(1);
    expect(Number(audit.rows[0].http_status)).toBe(200);
    expect(Number(audit.rows[0].duration_ms)).toBeGreaterThanOrEqual(0);
  });

  it("[audit] a rejected request on a registered route writes status FAILED and the 4xx http_status", async () => {
    const since = new Date();
    // Registered-route 4xx only (validation reject, missing field). Not GET /no-such-route.
    const failMethod = "POST";
    const failPath = "/v1/REPLACE_ME";
    const failRoute = "/v1/REPLACE_ME"; // gin FullPath() pattern
    const failBody = {};

    const { status } = await api.post(failPath, failBody);
    expect(status).toBeGreaterThanOrEqual(400);

    const audit = await db.query(
      `SELECT status, http_status
         FROM ${SCHEMA}.audit_log
        WHERE http_method = $1 AND route = $2 AND status = $3 AND created_at >= $4
        ORDER BY created_at DESC
        LIMIT 1`,
      [failMethod, failRoute, "FAILED", since.toISOString()],
    );
    expect(audit.rowCount).toBe(1);
    expect(Number(audit.rows[0].http_status)).toBe(status);
  });
});
