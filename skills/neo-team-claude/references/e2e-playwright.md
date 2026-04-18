---
name: e2e-playwright
description: >
  Reference guide for QA agent to generate E2E API test code using Playwright APIRequestContext + Jest + TypeScript.
  Covers project bootstrapping, shared helpers, precondition patterns, and test file templates.
  Read this BEFORE writing any E2E test code.
---

# E2E Playwright API Testing Guide

This reference tells you **how** to generate E2E test code for API-only testing. It complements the test case document (which defines **what** to test) by providing the project structure, code templates, and patterns you need to produce executable tests.

**Technology stack:** Playwright `APIRequestContext` as HTTP client, Jest as test runner, TypeScript in strict mode.

**Prerequisite:** A test case document (following [`test-case-document.md`](test-case-document.md) template) must exist before you write any E2E code. The test case document defines TC-IDs, expected behavior, and Workflow Chains — you translate those into code.

## E2E Path Resolution (CRITICAL)

Do NOT assume a hardcoded E2E path. Resolve the E2E project root using this chain — stop at the first match:

1. **Read the project's `CLAUDE.md` / `AGENTS.md`** — look for e2e path convention, test directory config, or any project-specific test structure definition
2. **If not found** — ask the Orchestrator to clarify with the user where the E2E project should live
3. **If user does not specify** — fallback to `tests/e2e/` as default

Store the resolved path and use it consistently throughout bootstrapping, test generation, and test execution. In this document, `{e2e-root}` refers to the resolved path (e.g., `tests/e2e/`, `e2e/`, `test/e2e/`, etc.).

## E2E Project Structure

The E2E project lives at `{e2e-root}` in the project root as a **standalone project** with its own `package.json`. Feature test folders mirror `docs/design/{feature}/` names exactly.

```
{e2e-root}/
├── package.json                    ← standalone dependencies
├── tsconfig.json                   ← strict mode, ES2020+
├── jest.config.ts                  ← Jest configuration
├── jest.setup.ts                   ← global Playwright APIRequestContext setup
│
├── helpers/                        ← shared utilities (all features use these)
│   ├── api-client.ts               ← typed HTTP wrapper around APIRequestContext
│   ├── precondition.ts             ← abstract base class for feature preconditions
│   └── fixture-loader.ts           ← load JSON fixtures / execute SQL seeds
│
├── {feature}/                      ← mirrors docs/design/{feature}/ name
│   ├── __fixtures__/               ← per-feature test data (optional)
│   │   ├── data.json               ← JSON fixture data
│   │   └── seed.sql                ← SQL seed script (optional)
│   ├── {feature}.precondition.ts   ← setup/teardown for this feature
│   └── {feature}.e2e.ts            ← test file with TC-ID-prefixed cases
│
└── {feature-2}/
    └── (same structure)
```

**Naming rules:**
- Feature folder name = exact match of `docs/design/{feature}/` folder name
- Test file: `{feature}.e2e.ts`
- Precondition file: `{feature}.precondition.ts`
- Fixtures folder: `__fixtures__/` inside each feature folder

## Bootstrapping (First-time Setup)

If `{e2e-root}` does not exist in the project root, create the entire skeleton before writing any test code. Run `cd {e2e-root} && npm install` after creating all files.

### package.json

```json
{
  "name": "e2e-tests",
  "private": true,
  "scripts": {
    "test": "jest",
    "test:feature": "jest --testPathPattern"
  },
  "devDependencies": {
    "jest": "^29.7.0",
    "ts-jest": "^29.2.0",
    "@types/jest": "^29.5.0",
    "playwright": "^1.48.0",
    "typescript": "^5.6.0"
  }
}
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "strict": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "outDir": "./dist",
    "rootDir": ".",
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
```

### jest.config.ts

```typescript
import type { Config } from 'jest';

const config: Config = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: ['**/*.e2e.ts'],
  setupFilesAfterEnv: ['./jest.setup.ts'],
  testTimeout: 30000,
};

export default config;
```

### jest.setup.ts

```typescript
import { request, APIRequestContext } from 'playwright';

let apiContext: APIRequestContext;

beforeAll(async () => {
  apiContext = await request.newContext({
    baseURL: process.env.API_BASE_URL || 'http://localhost:3000',
    extraHTTPHeaders: {
      'Content-Type': 'application/json',
      ...(process.env.API_AUTH_TOKEN
        ? { Authorization: `Bearer ${process.env.API_AUTH_TOKEN}` }
        : {}),
    },
  });

  // Make available globally for all test files
  (globalThis as any).__API_CONTEXT__ = apiContext;
});

afterAll(async () => {
  await apiContext?.dispose();
});
```

## Shared Helpers

### helpers/api-client.ts

Typed wrapper around Playwright's `APIRequestContext`. Every test file and precondition uses this instead of calling Playwright directly.

```typescript
import { APIRequestContext } from 'playwright';

export interface ApiResponse<T = any> {
  status: number;
  body: T;
  headers: Record<string, string>;
}

export class ApiClient {
  private request: APIRequestContext;

  constructor(requestContext?: APIRequestContext) {
    this.request = requestContext || (globalThis as any).__API_CONTEXT__;
  }

  async get<T = any>(path: string): Promise<ApiResponse<T>> {
    const res = await this.request.get(path);
    return {
      status: res.status(),
      body: (await res.json()) as T,
      headers: res.headers(),
    };
  }

  async post<T = any>(path: string, data?: object): Promise<ApiResponse<T>> {
    const res = await this.request.post(path, { data });
    return {
      status: res.status(),
      body: (await res.json()) as T,
      headers: res.headers(),
    };
  }

  // put, patch follow same pattern as post (accept path + data)
  // delete follows same pattern as get (path only)
  async put<T = any>(path: string, data?: object): Promise<ApiResponse<T>> { /* same as post */ }
  async patch<T = any>(path: string, data?: object): Promise<ApiResponse<T>> { /* same as post */ }
  async delete<T = any>(path: string): Promise<ApiResponse<T>> { /* same as get */ }
}
```

### helpers/precondition.ts

Abstract base class for feature preconditions. Each feature extends this to define its own setup/teardown workflow.

```typescript
import { ApiClient } from './api-client';

export abstract class Precondition {
  protected context: Record<string, any> = {};

  /**
   * Run prerequisite API calls in order.
   * Use capture() to store IDs/refs from responses.
   */
  abstract setup(client: ApiClient): Promise<void>;

  /**
   * Clean up created data in reverse order.
   * Always attempt cleanup even if some deletes fail.
   */
  abstract teardown(client: ApiClient): Promise<void>;

  /** Return all captured values for test cases to use. */
  getContext(): Record<string, any> {
    return { ...this.context };
  }

  /** Store a value from a response for use in later steps or test cases. */
  protected capture(key: string, value: any): void {
    this.context[key] = value;
  }
}
```

### helpers/fixture-loader.ts

Utilities for loading test data from fixture files.

```typescript
import * as fs from 'fs';
import * as path from 'path';

/**
 * Load a JSON fixture file relative to the calling feature's __fixtures__/ folder.
 * @param fixturePath - path relative to {e2e-root} (e.g., 'loan-approval/__fixtures__/data.json')
 */
export function loadJson<T = any>(fixturePath: string): T {
  const fullPath = path.resolve(__dirname, '..', fixturePath);
  const content = fs.readFileSync(fullPath, 'utf-8');
  return JSON.parse(content) as T;
}

/**
 * Read a SQL seed file and return its content as a string.
 * The caller is responsible for executing it against the database.
 * @param fixturePath - path relative to {e2e-root} (e.g., 'loan-approval/__fixtures__/seed.sql')
 */
export function readSqlSeed(fixturePath: string): string {
  const fullPath = path.resolve(__dirname, '..', fixturePath);
  return fs.readFileSync(fullPath, 'utf-8');
}
```

## Precondition Pattern

When a feature requires calling other APIs before its test cases can run (documented as a **Workflow Chain** in the test case document), create a `{feature}.precondition.ts` that implements those steps.

The precondition's `setup()` method must follow the exact step order from the Workflow Chain table. Each step calls an API, captures the response value, and makes it available to subsequent steps and test cases.

### Example: Savings Account Precondition

Based on a Workflow Chain that requires creating a product (TC-001) and opening an account (TC-002) before testing transactions:

```typescript
import { Precondition } from '../helpers/precondition';
import { ApiClient } from '../helpers/api-client';

export class SavingsAccountPrecondition extends Precondition {
  async setup(client: ApiClient): Promise<void> {
    // Step 1: Create product (maps to Workflow Chain step 1)
    const product = await client.post('/v1/products', {
      name: 'Savings Account',
      denomination: 'THB',
    });
    this.capture('productId', product.body.id);

    // Step 2: Open account (maps to Workflow Chain step 2)
    const account = await client.post('/v1/accounts', {
      product_id: this.context.productId,
      denomination: 'THB',
      customer_id: 'CUST-001',
    });
    this.capture('accountId', account.body.account_id);
  }

  async teardown(client: ApiClient): Promise<void> {
    // Reverse order: delete account first, then product
    try {
      if (this.context.accountId) {
        await client.delete(`/v1/accounts/${this.context.accountId}`);
      }
    } catch { /* log but continue cleanup */ }

    try {
      if (this.context.productId) {
        await client.delete(`/v1/products/${this.context.productId}`);
      }
    } catch { /* log but continue cleanup */ }
  }
}
```

### When No Precondition Is Needed

If a feature's test cases have no Workflow Chain (all preconditions are "None"), skip creating a precondition file. The test file's `beforeAll` can directly set up simple state or use fixture data.

## Test File Pattern

Each feature has one test file: `{feature}.e2e.ts`. The file structure maps directly to the test case document:
- `describe()` blocks = Test Suites from the document
- `it()` blocks = individual Test Cases, prefixed with TC-ID

### Example: Savings Account E2E Test

```typescript
import { ApiClient } from '../helpers/api-client';
import { SavingsAccountPrecondition } from './savings-account.precondition';

describe('Savings Account', () => {
  let client: ApiClient;
  const precondition = new SavingsAccountPrecondition();

  beforeAll(async () => {
    client = new ApiClient();
    await precondition.setup(client);
  });

  afterAll(async () => {
    await precondition.teardown(client);
  });

  // --- Test Suite 2: Transaction Validation ---
  // (Suite 1 steps are handled by precondition)

  describe('Transaction Validation', () => {
    it('TC-003: should accept credit in primary denomination', async () => {
      const { accountId } = precondition.getContext();

      const res = await client.post(`/v1/accounts/${accountId}/transactions`, {
        type: 'CREDIT',
        amount: 1000,
        denomination: 'THB',
      });

      expect(res.status).toBe(200);
      expect(res.body.status).toBe('ACCEPTED');
      expect(res.body.denomination).toBe('THB');
    });

    it('TC-004: should reject credit in non-primary denomination', async () => {
      const { accountId } = precondition.getContext();

      const res = await client.post(`/v1/accounts/${accountId}/transactions`, {
        type: 'CREDIT',
        amount: 100,
        denomination: 'USD',
      });

      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Invalid denomination');
    });
  });
});
```

### Test File Rules

1. **TC-ID prefix is mandatory** — every `it()` must start with the TC-ID from the test case document: `it('TC-001: ...')`
2. **One test file per feature** — all test suites for a feature go in the same `.e2e.ts` file
3. **Precondition test cases become setup** — if TC-001 and TC-002 are preconditions for TC-003+, they belong in `precondition.ts` setup, not as `it()` blocks (they are implicitly validated when setup succeeds)
4. **Assertion standards** — follow the Test Case Quality Rules from [`qa.md`](qa.md) (exact HTTP status codes, error body assertions, no duplicate scenarios)

## Running Tests

```bash
# Run all E2E tests
cd {e2e-root} && npm test

# Run tests for a specific feature
cd {e2e-root} && npm test -- --testPathPattern=savings-account

# With custom API URL
cd {e2e-root} && API_BASE_URL=https://staging.example.com npm test
```

**Environment variables:**
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | No | `http://localhost:3000` | Base URL of the API under test |
| `API_AUTH_TOKEN` | No | (none) | Bearer token for authenticated endpoints |

If the project's `CLAUDE.md` defines different env vars or test commands, follow project conventions instead.

## Pre-submission Checklist

Before reporting E2E test results, verify:

- [ ] Every TC-ID from the test case document has a corresponding `it()` block in the `.e2e.ts` file
- [ ] Precondition `setup()` covers every step from the Workflow Chain table in the test case document
- [ ] Precondition `teardown()` cleans up in reverse order
- [ ] `cd {e2e-root} && npm test` runs successfully (or failures are documented in the execution report)
- [ ] No hardcoded URLs or tokens — all use environment variables
- [ ] Feature folder name matches `docs/design/{feature}/` exactly
- [ ] Test assertions use exact HTTP status codes from the API contract
- [ ] Error test cases assert error body structure (not just status code)
