/**
 * Typed HTTP wrapper around Playwright's APIRequestContext.
 * Domain fixtures and envelope types land here when neo adds the first endpoint.
 */
import type { APIRequestContext, APIResponse } from "@playwright/test";

export interface ApiResponse<T = unknown> {
  status: number;
  body: T;
  raw: APIResponse;
}

export class ApiClient {
  constructor(private readonly ctx: APIRequestContext) {}

  async get<T = unknown>(
    path: string,
    options?: { params?: Record<string, string>; headers?: Record<string, string> },
  ): Promise<ApiResponse<T>> {
    const res = await this.ctx.get(path, {
      params: options?.params,
      headers: options?.headers,
    });
    return this.toResponse<T>(res);
  }

  async post<T = unknown>(
    path: string,
    options?: { data?: unknown; headers?: Record<string, string> },
  ): Promise<ApiResponse<T>> {
    const res = await this.ctx.post(path, {
      data: options?.data as never,
      headers: options?.headers,
    });
    return this.toResponse<T>(res);
  }

  private async toResponse<T>(raw: APIResponse): Promise<ApiResponse<T>> {
    const status = raw.status();
    const contentType = raw.headers()["content-type"] ?? "";
    let body: T;
    if (status === 204) {
      body = null as unknown as T;
    } else if (contentType.includes("application/json")) {
      body = (await raw.json()) as T;
    } else {
      const text = await raw.text();
      body = (text || null) as unknown as T;
    }
    return { status, body, raw };
  }
}
