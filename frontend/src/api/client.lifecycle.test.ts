import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiClient } from "./client";
import { ApiError } from "./errors";
import { AUTH_EVENTS, type ForbiddenEventDetail, type UnauthorizedEventDetail } from "./events";
import { InMemoryTokenStorage, tokenStorage } from "./tokenStorage";

describe("ApiClient Lifecycle, Centralized Auth & Error Handling", () => {
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

  describe("401 Unauthorized handling", () => {
    it("clears stored token and dispatches agridirect:unauthorized window event on 401", async () => {
      inMemoryStorage.setToken("expired-access-token-123");
      const eventListener = vi.fn();
      window.addEventListener(AUTH_EVENTS.UNAUTHORIZED, eventListener);

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Could not validate credentials" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        })
      );

      try {
        await client.get("/users/me");
        expect.unreachable();
      } catch (err) {
        const apiError = err as ApiError;
        expect(apiError.status).toBe(401);
        expect(apiError.isUnauthorized).toBe(true);

        // Token must be invalidated in client storage immediately
        expect(tokenStorage.getToken()).toBeNull();

        // Decoupled event must be dispatched to trigger global auth state transition
        expect(eventListener).toHaveBeenCalledTimes(1);
        const customEvent = eventListener.mock.calls[0][0] as CustomEvent<UnauthorizedEventDetail>;
        expect(customEvent.detail.status).toBe(401);
        expect(customEvent.detail.url).toContain("/api/v1/users/me");
        expect(customEvent.detail.message).toBe("Could not validate credentials");
      } finally {
        window.removeEventListener(AUTH_EVENTS.UNAUTHORIZED, eventListener);
      }
    });

    it("does NOT attempt to call an un-supported refresh endpoint on 401", async () => {
      inMemoryStorage.setToken("token-xyz");

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Token expired" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        })
      );

      await expect(client.get("/listings/my")).rejects.toThrow("Token expired");

      // Exactly 1 fetch call: no secondary /auth/refresh attempt
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).not.toHaveBeenCalledWith(
        expect.stringContaining("/refresh"),
        expect.anything()
      );
    });
  });

  describe("403 Forbidden and Account Status handling", () => {
    it("dispatches agridirect:forbidden with isAccountSuspendedOrRestricted flag for account status errors", async () => {
      inMemoryStorage.setToken("valid-token");
      const forbiddenListener = vi.fn();
      window.addEventListener(AUTH_EVENTS.FORBIDDEN, forbiddenListener);

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Account is suspended or restricted" }), {
          status: 403,
          headers: { "Content-Type": "application/json" },
        })
      );

      try {
        await client.post("/listings", { title: "Organic Apples" });
        expect.unreachable();
      } catch (err) {
        const apiError = err as ApiError;
        expect(apiError.status).toBe(403);
        expect(apiError.isForbidden).toBe(true);
        expect(apiError.isAccountSuspendedOrRestricted).toBe(true);
        expect(apiError.isVerificationRequired).toBe(false);

        // Crucial invariant: 403 does NOT wipe authentication token
        expect(tokenStorage.getToken()).toBe("valid-token");

        expect(forbiddenListener).toHaveBeenCalledTimes(1);
        const customEvent = forbiddenListener.mock.calls[0][0] as CustomEvent<ForbiddenEventDetail>;
        expect(customEvent.detail.isAccountSuspendedOrRestricted).toBe(true);
      } finally {
        window.removeEventListener(AUTH_EVENTS.FORBIDDEN, forbiddenListener);
      }
    });

    it("correctly flags verification required 403 errors", async () => {
      inMemoryStorage.setToken("valid-token");
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Operation requires a verified farmer account" }), {
          status: 403,
          headers: { "Content-Type": "application/json" },
        })
      );

      try {
        await client.post("/listings", {});
        expect.unreachable();
      } catch (err) {
        const apiError = err as ApiError;
        expect(apiError.isVerificationRequired).toBe(true);
        expect(apiError.isRoleForbidden).toBe(true);
        expect(apiError.isAccountSuspendedOrRestricted).toBe(false);
      }
    });

    it("correctly flags role permission 403 errors without logging user out", async () => {
      inMemoryStorage.setToken("valid-token");
      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Operation requires administrator privileges" }), {
          status: 403,
          headers: { "Content-Type": "application/json" },
        })
      );

      try {
        await client.get("/admin/users");
        expect.unreachable();
      } catch (err) {
        const apiError = err as ApiError;
        expect(apiError.isRoleForbidden).toBe(true);
        expect(tokenStorage.getToken()).toBe("valid-token");
      }
    });
  });

  describe("Abort and Network errors", () => {
    it("handles request abortion gracefully and tags error as aborted", async () => {
      const abortError = new DOMException("The user aborted a request.", "AbortError");
      mockFetch.mockRejectedValueOnce(abortError);

      try {
        await client.get("/long-operation");
        expect.unreachable();
      } catch (err) {
        const apiError = err as ApiError;
        expect(apiError.status).toBe(0);
        expect(apiError.isAborted).toBe(true);
        expect(apiError.message).toContain("aborted");
      }
    });

    it("handles non-JSON error response from proxy or gateway gracefully", async () => {
      mockFetch.mockResolvedValueOnce(
        new Response("<html><body>502 Bad Gateway</body></html>", {
          status: 502,
          headers: { "Content-Type": "text/html" },
        })
      );

      try {
        await client.get("/analytics");
        expect.unreachable();
      } catch (err) {
        const apiError = err as ApiError;
        expect(apiError.status).toBe(502);
        expect(apiError.isServerError).toBe(true);
        expect(apiError.message).toContain("502 Bad Gateway");
      }
    });
  });

  describe("Multipart / FormData handling", () => {
    it("does not manually set Content-Type header when body is FormData", async () => {
      const formData = new FormData();
      formData.append("file", new Blob(["test-document"], { type: "text/plain" }), "test.txt");

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "doc-1" }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        })
      );

      await client.post("/verification/documents", formData);

      const requestInit = mockFetch.mock.calls[0][1];
      const headers = requestInit.headers as Headers;

      // Crucial: Content-Type must not be 'application/json' because fetch must auto-set multipart boundary
      expect(headers.get("Content-Type")).toBeNull();
      expect(requestInit.body).toBe(formData);
    });
  });

  describe("Binary blob download handling", () => {
    it("successfully downloads blob and parses filename from content-disposition header", async () => {
      mockFetch.mockResolvedValueOnce(
        new Response(new Blob(["mock-pdf-bytes"], { type: "application/pdf" }), {
          status: 200,
          headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="land_record_verified.pdf"',
          },
        })
      );

      const result = await client.downloadBlob("/verification/documents/doc-1/download");

      expect(result.filename).toBe("land_record_verified.pdf");
      expect(result.mimeType).toBe("application/pdf");
      expect(result.blob).toBeInstanceOf(Blob);
      expect(result.blob.size).toBeGreaterThan(0);
    });

    it("triggers 401 unauthorized handling during binary download failure", async () => {
      const unauthorizedListener = vi.fn();
      window.addEventListener(AUTH_EVENTS.UNAUTHORIZED, unauthorizedListener);

      mockFetch.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Token invalid" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        })
      );

      try {
        await client.downloadBlob("/secure-file");
        expect.unreachable();
      } catch (err) {
        const apiError = err as ApiError;
        expect(apiError.status).toBe(401);
        expect(unauthorizedListener).toHaveBeenCalledTimes(1);
      } finally {
        window.removeEventListener(AUTH_EVENTS.UNAUTHORIZED, unauthorizedListener);
      }
    });
  });
});
