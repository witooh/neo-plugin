/**
 * Global setup: wait for the service /health to be ready before the suite runs.
 *
 * This suite seeds nothing. The skeleton has no tables, no upstream, and no
 * domain endpoint: only GET /health, so there is no fixture to seed and
 * nothing to tear down. The `neoschema` schema is created by the compose
 * postgres-init one-shot for when neo adds the first migration.
 */
import * as dotenv from "dotenv";
import * as path from "path";

dotenv.config({ path: path.resolve(__dirname, ".env.test") });

const MAX_RETRIES = 30;
const RETRY_INTERVAL_MS = 2_000;

export default async function globalSetup(): Promise<void> {
  const baseUrl = process.env.API_BASE_URL ?? "http://localhost:8080";
  await waitForHealth(baseUrl);
}

async function waitForHealth(baseUrl: string): Promise<void> {
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      const res = await fetch(`${baseUrl}/health`);
      if (res.ok) return;
    } catch (err) {
      if (attempt === MAX_RETRIES) {
        throw new Error(
          `API at ${baseUrl} is not reachable after ${MAX_RETRIES} attempts: ${
            err instanceof Error ? err.message : String(err)
          }`,
        );
      }
    }
    await sleep(RETRY_INTERVAL_MS);
  }
  throw new Error(`API at ${baseUrl} did not become healthy in time`);
}

async function sleep(ms: number): Promise<void> {
  const { promise, resolve } = Promise.withResolvers<void>();
  setTimeout(resolve, ms);
  return promise;
}
