/**
 * Centralized API client using the native Fetch API.
 * Handles base URLs, header injection, Bearer authentication, standardized error parsing,
 * and centralized event dispatching for 401 and 403 status responses.
 */

import { ApiError } from "./errors";
import { dispatchForbidden, dispatchUnauthorized } from "./events";
import { tokenStorage } from "./tokenStorage";
import type { ApiErrorResponse, ValidationErrorItem } from "../types/api";

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  skipAuth?: boolean;
}

export class ApiClient {
  private readonly baseUrl: string;

  constructor(baseUrl?: string) {
    // Relative /api/v1 default routes through Vite development proxy or reverse proxy in production
    this.baseUrl = baseUrl || (import.meta.env?.VITE_API_BASE_URL as string) || "/api/v1";
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  public async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const url = path.startsWith("http://") || path.startsWith("https://")
      ? path
      : `${this.baseUrl}${path.startsWith("/") ? "" : "/"}${path}`;

    const headers = new Headers(options.headers);

    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }

    const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

    // Do NOT set Content-Type for FormData; browser must generate boundary automatically
    if (options.body !== undefined && !isFormData && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    if (!options.skipAuth) {
      const token = tokenStorage.getToken();
      if (token && !headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${token}`);
      }
    }

    const body = options.body !== undefined
      ? isFormData
        ? (options.body as BodyInit)
        : JSON.stringify(options.body)
      : undefined;

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
        body,
      });
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new ApiError(0, "Request was aborted");
      }
      if (err instanceof Error && err.name === "AbortError") {
        throw new ApiError(0, "Request was aborted");
      }
      const msg = err instanceof Error ? err.message : "Unable to reach server";
      throw new ApiError(0, `Network error: ${msg}`);
    }

    // Handle 204 No Content or responses with explicitly zero content-length
    if (response.status === 204 || response.headers.get("content-length") === "0") {
      if (response.ok) {
        return undefined as unknown as T;
      }
      throw new ApiError(response.status, `Request failed with status ${response.status}`);
    }

    const contentType = response.headers.get("content-type");
    const isJson = contentType !== null && contentType.includes("application/json");

    let data: unknown = null;
    if (isJson) {
      try {
        data = await response.json();
      } catch {
        data = null;
      }
    } else {
      try {
        data = await response.text();
      } catch {
        data = null;
      }
    }

    if (!response.ok) {
      let detail: string | ValidationErrorItem[] | undefined;
      let message = `Request failed with status ${response.status}`;

      if (data && typeof data === "object" && "detail" in data) {
        const errorPayload = data as ApiErrorResponse;
        detail = errorPayload.detail;
        if (typeof detail === "string") {
          message = detail;
        } else if (Array.isArray(detail) && detail.length > 0) {
          message = detail[0].msg || message;
        }
      } else if (typeof data === "string" && data.trim()) {
        message = data;
      }

      const apiError = new ApiError(response.status, message, detail);

      // Centralized 401 Unauthorized handling: clear token and dispatch decoupled event
      if (response.status === 401) {
        tokenStorage.clearToken();
        dispatchUnauthorized({
          status: 401,
          url,
          message,
        });
      }

      // Centralized 403 Forbidden handling: dispatch decoupled event with categorization
      if (response.status === 403) {
        dispatchForbidden({
          status: 403,
          url,
          message,
          detail,
          isAccountSuspendedOrRestricted: apiError.isAccountSuspendedOrRestricted,
          isVerificationRequired: apiError.isVerificationRequired,
          isRoleForbidden: apiError.isRoleForbidden,
        });
      }

      throw apiError;
    }

    return data as T;
  }

  public get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "GET" });
  }

  public post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "POST", body });
  }

  public patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "PATCH", body });
  }

  public put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "PUT", body });
  }

  public delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "DELETE" });
  }

  /**
   * Downloads a binary response (e.g. PDF or image file) as a Blob without JSON parsing.
   * Authenticates using the Bearer token and wraps HTTP errors in standard ApiError.
   */
  public async downloadBlob(
    path: string,
    options?: RequestOptions
  ): Promise<{ blob: Blob; filename?: string; mimeType: string }> {
    const url = path.startsWith("http://") || path.startsWith("https://")
      ? path
      : `${this.baseUrl}${path.startsWith("/") ? "" : "/"}${path}`;

    const headers = new Headers(options?.headers);

    if (!options?.skipAuth) {
      const token = tokenStorage.getToken();
      if (token && !headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${token}`);
      }
    }

    const { body: _ignoredBody, skipAuth: _ignoredAuth, ...fetchInit } = options || {};

    let response: Response;
    try {
      response = await fetch(url, {
        ...fetchInit,
        method: options?.method || "GET",
        headers,
      });
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new ApiError(0, "Request was aborted");
      }
      if (err instanceof Error && err.name === "AbortError") {
        throw new ApiError(0, "Request was aborted");
      }
      const msg = err instanceof Error ? err.message : "Unable to reach server";
      throw new ApiError(0, `Network error: ${msg}`);
    }

    if (!response.ok) {
      const contentType = response.headers.get("content-type");
      let message = `Download failed with status ${response.status}`;
      let detail: string | ValidationErrorItem[] | undefined;

      if (contentType && contentType.includes("application/json")) {
        try {
          const data = (await response.json()) as ApiErrorResponse;
          detail = data.detail;
          if (typeof detail === "string") {
            message = detail;
          } else if (Array.isArray(detail) && detail.length > 0) {
            message = detail[0].msg || message;
          }
        } catch {
          // ignore parsing error
        }
      } else {
        try {
          const text = await response.text();
          if (text.trim()) {
            message = text;
          }
        } catch {
          // ignore text error
        }
      }

      const apiError = new ApiError(response.status, message, detail);

      if (response.status === 401) {
        tokenStorage.clearToken();
        dispatchUnauthorized({
          status: 401,
          url,
          message,
        });
      }

      if (response.status === 403) {
        dispatchForbidden({
          status: 403,
          url,
          message,
          detail,
          isAccountSuspendedOrRestricted: apiError.isAccountSuspendedOrRestricted,
          isVerificationRequired: apiError.isVerificationRequired,
          isRoleForbidden: apiError.isRoleForbidden,
        });
      }

      throw apiError;
    }

    let filename: string | undefined;
    const disposition = response.headers.get("content-disposition");
    if (disposition) {
      const match = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i);
      if (match && match[1]) {
        filename = decodeURIComponent(match[1].trim());
      }
    }

    const mimeType = response.headers.get("content-type") || "application/octet-stream";
    const blob = await response.blob();

    return { blob, filename, mimeType };
  }
}

export const apiClient = new ApiClient();
