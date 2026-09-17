/**
 * Per-suite Jest setup: load .env.test and expose a shared Playwright
 * APIRequestContext as `globalThis.apiContext`.
 */
import * as dotenv from "dotenv";
import * as path from "path";
import { request, APIRequestContext } from "@playwright/test";

dotenv.config({ path: path.resolve(__dirname, ".env.test") });

declare global {
  // eslint-disable-next-line no-var
  var apiContext: APIRequestContext;
}

beforeAll(async () => {
  globalThis.apiContext = await request.newContext({
    baseURL: process.env.API_BASE_URL ?? "http://localhost:8080",
  });
});

afterAll(async () => {
  await globalThis.apiContext?.dispose();
});
