import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClient } from "./client";
import { ApiError } from "./errors";
import { InMemoryTokenStorage, tokenStorage } from "./tokenStorage";

describe("ApiClient", () => {
  let mockFetch: ReturnType<typeof vi.fn>;
  let inMemoryStorage: InMemoryTokenStorage;
  let client: ApiClient;

  beforeEach(() => {
    inMemoryStorage = new InMemoryTokenStorage();
    tokenStorage.setProvider(inMemoryStorage);

    mockFetch = vi.fn();
    vi.stubGlobal("fetch", mockFetch);

    client = new ApiClient("/api/v1");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    tokenStorage.clearToken();
  });

  it("constructs correct request URL with relative base prefix", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const result = await client.get<{ status: string }>("/health");

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/health",
      expect.objectContaining({
        method: "GET",
      })
    );
    expect(result).toEqual({ status: "ok" });
  });

  it("sets JSON request headers and serializes body", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "123" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const payload = { email: "user@example.com", name: "User" };
    await client.post("/test-post", payload);

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/test-post",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
        headers: expect.any(Headers),
      })
    );

    const headers = mockFetch.mock.calls[0][1].headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("Accept")).toBe("application/json");
  });

  it("injects Bearer token into Authorization header when token is stored", async () => {
    inMemoryStorage.setToken("mock-jwt-token-xyz");

    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "user-1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    await client.get("/users/me");

    const headers = mockFetch.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer mock-jwt-token-xyz");
  });

  it("omits Authorization header when skipAuth is true", async () => {
    inMemoryStorage.setToken("mock-jwt-token-xyz");

    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: "new-token" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    await client.post("/auth/login", { email: "a@b.com" }, { skipAuth: true });

    const headers = mockFetch.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBeNull();
  });

  it("handles successful 204 No Content response gracefully", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(null, {
        status: 204,
      })
    );

    const result = await client.delete("/items/1");
    expect(result).toBeUndefined();
  });

  it("handles 401 Unauthorized structured error", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Invalid email or password" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      })
    );

    try {
      await client.post("/auth/login", {});
      expect.unreachable();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(401);
      expect(apiErr.message).toBe("Invalid email or password");
      expect(apiErr.isUnauthorized).toBe(true);
    }
  });

  it("handles 422 validation error with Pydantic detail format", async () => {
    const pydanticError = {
      detail: [
        {
          loc: ["body", "password"],
          msg: "Password must not be blank",
          type: "value_error",
        },
        {
          loc: ["body", "email"],
          msg: "value is not a valid email address",
          type: "value_error",
        },
      ],
    };

    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(pydanticError), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      })
    );

    try {
      await client.post("/auth/register/farmer", {});
      expect.unreachable();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(422);
      expect(apiErr.isValidationError).toBe(true);
      expect(apiErr.message).toBe("Password must not be blank");
      expect(apiErr.fieldErrors.password).toContain("Password must not be blank");
      expect(apiErr.fieldErrors.email).toContain("value is not a valid email address");
    }
  });

  it("handles network failures and converts to ApiError with status 0", async () => {
    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    try {
      await client.get("/users/me");
      expect.unreachable();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(0);
      expect(apiErr.isNetworkError).toBe(true);
      expect(apiErr.message).toContain("Network error");
    }
  });

  it("does not leak secrets, passwords, or tokens in error message", async () => {
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Authentication failed" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      })
    );

    try {
      await client.post("/auth/login", {
        email: "farmer@example.com",
        password: "SecretPassword123!",
      });
      expect.unreachable();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      expect(apiErr.message).not.toContain("SecretPassword123!");
      expect(JSON.stringify(apiErr)).not.toContain("SecretPassword123!");
    }
  });
});
