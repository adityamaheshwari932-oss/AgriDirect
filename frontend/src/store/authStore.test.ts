import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthStore } from "./authStore";
import { AuthApi } from "../api/auth";
import { ApiError } from "../api/errors";
import { InMemoryTokenStorage } from "../api/tokenStorage";
import type {
  BuyerRegisterRequest,
  FarmerRegisterRequest,
  LoginRequest,
  TokenResponse,
  User,
} from "../types";

describe("AuthStore", () => {
  let mockStorage: InMemoryTokenStorage;
  let mockApi: AuthApi;
  let store: AuthStore;

  const mockUser: User = {
    id: "user-123",
    email: "test@example.com",
    role: "farmer",
    verification_status: "unverified",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
  };

  beforeEach(() => {
    mockStorage = new InMemoryTokenStorage();
    mockApi = {
      login: vi.fn(),
      registerFarmer: vi.fn(),
      registerBuyer: vi.fn(),
      getCurrentUser: vi.fn(),
    } as unknown as AuthApi;

    store = new AuthStore(mockApi, mockStorage);
  });

  it("starts in uninitialized state with null user and null error", () => {
    const state = store.getState();
    expect(state.status).toBe("uninitialized");
    expect(state.user).toBeNull();
    expect(state.error).toBeNull();
  });

  it("authenticates and stores token on successful login", async () => {
    const tokenResponse: TokenResponse = {
      access_token: "valid-jwt-token",
      token_type: "bearer",
      user: mockUser,
    };
    vi.mocked(mockApi.login).mockResolvedValueOnce(tokenResponse);

    const credentials: LoginRequest = { email: "test@example.com", password: "Password123!" };
    const user = await store.login(credentials);

    expect(user).toEqual(mockUser);
    expect(mockStorage.getToken()).toBe("valid-jwt-token");

    const state = store.getState();
    expect(state.status).toBe("authenticated");
    expect(state.user).toEqual(mockUser);
    expect(state.error).toBeNull();
  });

  it("does not authenticate user on failed login and records error", async () => {
    vi.mocked(mockApi.login).mockRejectedValueOnce(
      new ApiError(401, "Invalid email or password")
    );

    const credentials: LoginRequest = { email: "test@example.com", password: "WrongPassword" };

    await expect(store.login(credentials)).rejects.toThrow("Invalid email or password");

    expect(mockStorage.getToken()).toBeNull();
    const state = store.getState();
    expect(state.status).toBe("unauthenticated");
    expect(state.user).toBeNull();
    expect(state.error).toBe("Invalid email or password");
  });

  it("farmer registration does not automatically log in or change auth state", async () => {
    vi.mocked(mockApi.registerFarmer).mockResolvedValueOnce(mockUser);

    const payload: FarmerRegisterRequest = {
      email: "newfarmer@example.com",
      password: "Password123!",
      full_name: "New Farmer",
    };

    const result = await store.registerFarmer(payload);

    expect(result).toEqual(mockUser);
    expect(mockStorage.getToken()).toBeNull();
    expect(store.getState().status).toBe("uninitialized");
    expect(store.getState().user).toBeNull();
  });

  it("buyer registration does not automatically log in or change auth state", async () => {
    vi.mocked(mockApi.registerBuyer).mockResolvedValueOnce(mockUser);

    const payload: BuyerRegisterRequest = {
      email: "newbuyer@example.com",
      password: "Password123!",
      business_name: "Buyer Co",
    };

    const result = await store.registerBuyer(payload);

    expect(result).toEqual(mockUser);
    expect(mockStorage.getToken()).toBeNull();
    expect(store.getState().status).toBe("uninitialized");
    expect(store.getState().user).toBeNull();
  });

  it("restoreSession transitions to unauthenticated when no token is stored", async () => {
    const user = await store.restoreSession();

    expect(user).toBeNull();
    expect(store.getState().status).toBe("unauthenticated");
    expect(store.getState().user).toBeNull();
  });

  it("restoreSession restores user when valid token is stored", async () => {
    mockStorage.setToken("existing-valid-token");
    vi.mocked(mockApi.getCurrentUser).mockResolvedValueOnce(mockUser);

    const user = await store.restoreSession();

    expect(user).toEqual(mockUser);
    expect(store.getState().status).toBe("authenticated");
    expect(store.getState().user).toEqual(mockUser);
    expect(store.getState().error).toBeNull();
  });

  it("restoreSession clears token and sets unauthenticated on 401 response", async () => {
    mockStorage.setToken("expired-token");
    vi.mocked(mockApi.getCurrentUser).mockRejectedValueOnce(
      new ApiError(401, "Could not validate credentials")
    );

    const user = await store.restoreSession();

    expect(user).toBeNull();
    expect(mockStorage.getToken()).toBeNull(); // Token cleared on definitive 401
    expect(store.getState().status).toBe("unauthenticated");
    expect(store.getState().user).toBeNull();
    expect(store.getState().error).toBe("Session expired. Please log in again.");
  });

  it("restoreSession preserves token on temporary network error", async () => {
    mockStorage.setToken("saved-token");
    vi.mocked(mockApi.getCurrentUser).mockRejectedValueOnce(
      new ApiError(0, "Network error: Failed to fetch")
    );

    const user = await store.restoreSession();

    expect(user).toBeNull();
    expect(mockStorage.getToken()).toBe("saved-token"); // Token NOT cleared on network error
    expect(store.getState().status).toBe("unauthenticated");
    expect(store.getState().error).toContain("Network error");
  });

  it("prevents concurrent duplicate session restoration requests", async () => {
    mockStorage.setToken("valid-token");

    let resolvePromise!: (u: User) => void;
    const pendingPromise = new Promise<User>((resolve) => {
      resolvePromise = resolve;
    });

    vi.mocked(mockApi.getCurrentUser).mockReturnValueOnce(pendingPromise);

    // Call restoreSession twice concurrently
    const promise1 = store.restoreSession();
    const promise2 = store.restoreSession();

    // Verify only one API call was dispatched
    expect(mockApi.getCurrentUser).toHaveBeenCalledTimes(1);

    resolvePromise(mockUser);

    const [res1, res2] = await Promise.all([promise1, promise2]);
    expect(res1).toEqual(mockUser);
    expect(res2).toEqual(mockUser);
    expect(store.getState().status).toBe("authenticated");
  });

  it("explicit logout clears token and resets user state", () => {
    mockStorage.setToken("active-token");
    store["state"] = {
      status: "authenticated",
      user: mockUser,
      error: null,
    };

    store.logout();

    expect(mockStorage.getToken()).toBeNull();
    const state = store.getState();
    expect(state.status).toBe("unauthenticated");
    expect(state.user).toBeNull();
    expect(state.error).toBeNull();
  });

  it("notifies subscribers when state changes and supports unsubscribing", () => {
    const listener = vi.fn();
    const unsubscribe = store.subscribe(listener);

    store.logout();
    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
    store.logout();
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("updates cached user via setUser", () => {
    const updatedUser: User = { ...mockUser, email: "updated@example.com" };
    store.setUser(updatedUser);

    expect(store.getState().user).toEqual(updatedUser);
  });

  it("refreshes user profile via refreshUser", async () => {
    const refreshedUser: User = { ...mockUser, phone_number: "+15559876543" };
    vi.mocked(mockApi.getCurrentUser).mockResolvedValueOnce(refreshedUser);

    const result = await store.refreshUser();

    expect(result).toEqual(refreshedUser);
    expect(store.getState().user).toEqual(refreshedUser);
  });
});
