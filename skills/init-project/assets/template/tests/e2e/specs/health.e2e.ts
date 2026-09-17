/**
 * E2E: Health probe.
 * Endpoint: GET /health  (internal/delivery/http/router/router.go) → 200 {"status":"ok"}
 * No AC card: authored from the endpoint under test (no-AC mode).
 */
import { ApiClient } from "@helpers/index";

describe("GET /health: liveness probe", () => {
  let api: ApiClient;

  beforeAll(() => {
    api = new ApiClient(globalThis.apiContext);
  });

  it("[neo-service] GET /health → 200 {status:ok}", async () => {
    const { status, body } = await api.get("/health");
    expect(status).toBe(200);
    expect(body).toEqual({ status: "ok" });
  });
});
