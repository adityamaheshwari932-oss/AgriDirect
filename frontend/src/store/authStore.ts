/**
 * Lightweight, framework-agnostic authentication store with React 18 integration.
 * Manages authentication lifecycle, token persistence, and session restoration.
 */

import { useSyncExternalStore } from "react";
import { authApi, AuthApi } from "../api/auth";
import { ApiError } from "../api/errors";
import { tokenStorage, TokenStorage } from "../api/tokenStorage";
import type {
  BuyerRegisterRequest,
  FarmerRegisterRequest,
  LoginRequest,
  TransporterRegisterRequest,
  User,
} from "../types";

export type AuthStatus =
  | "uninitialized"
  | "restoring"
  | "authenticated"
  | "unauthenticated";

export interface AuthState {
  status: AuthStatus;
  user: User | null;
  error: string | null;
}

export class AuthStore {
  private state: AuthState = {
    status: "uninitialized",
    user: null,
    error: null,
  };

  private listeners = new Set<() => void>();
  private restorationPromise: Promise<User | null> | null = null;
  private api: AuthApi;
  private storage: TokenStorage;

  constructor(api: AuthApi = authApi, storage: TokenStorage = tokenStorage) {
    this.api = api;
    this.storage = storage;
  }

  public getState = (): AuthState => {
    return this.state;
  };

  public subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  private setState(partial: Partial<AuthState>): void {
    this.state = { ...this.state, ...partial };
    this.listeners.forEach((listener) => listener());
  }

  /**
   * Log in with user credentials and establish an authenticated session.
   */
  public async login(credentials: LoginRequest): Promise<User> {
    this.setState({ error: null });
    try {
      const response = await this.api.login(credentials);
      this.storage.setToken(response.access_token);
      this.setState({
        status: "authenticated",
        user: response.user,
        error: null,
      });
      return response.user;
    } catch (err: unknown) {
      const message = err instanceof ApiError ? err.message : "Failed to log in";
      this.setState({
        status: "unauthenticated",
        user: null,
        error: message,
      });
      throw err;
    }
  }

  /**
   * Register a farmer account.
   * Note: Registration creates the user and profile on the server but does not
   * automatically log the user in. The authentication state remains unchanged.
   */
  public async registerFarmer(payload: FarmerRegisterRequest): Promise<User> {
    return this.api.registerFarmer(payload);
  }

  /**
   * Register a commercial buyer account.
   * Note: Registration creates the user and profile on the server but does not
   * automatically log the user in. The authentication state remains unchanged.
   */
  public async registerBuyer(payload: BuyerRegisterRequest): Promise<User> {
    return this.api.registerBuyer(payload);
  }

  /**
   * Register a transportation service provider account.
   * Note: Registration creates the user and profile on the server but does not
   * automatically log the user in. The authentication state remains unchanged.
   */
  public async registerTransporter(payload: TransporterRegisterRequest): Promise<User> {
    return this.api.registerTransporter(payload);
  }

  /**
   * Restore user session from stored credentials if present.
   * Protects against duplicate concurrent restoration requests.
   */
  public async restoreSession(): Promise<User | null> {
    // If a session restoration is already in progress, return the active promise
    if (this.restorationPromise) {
      return this.restorationPromise;
    }

    const token = this.storage.getToken();
    if (!token) {
      this.setState({
        status: "unauthenticated",
        user: null,
        error: null,
      });
      return null;
    }

    this.setState({ status: "restoring", error: null });

    this.restorationPromise = (async () => {
      try {
        const user = await this.api.getCurrentUser();
        this.setState({
          status: "authenticated",
          user,
          error: null,
        });
        return user;
      } catch (err: unknown) {
        if (err instanceof ApiError && err.isUnauthorized) {
          // Token is definitively invalid or expired on backend
          this.storage.clearToken();
          this.setState({
            status: "unauthenticated",
            user: null,
            error: "Session expired. Please log in again.",
          });
        } else {
          // Network error or unexpected server issue: do not silently destroy token
          const message =
            err instanceof ApiError
              ? err.message
              : "Unable to restore session due to a network error";
          this.setState({
            status: "unauthenticated",
            user: null,
            error: message,
          });
        }
        return null;
      } finally {
        this.restorationPromise = null;
      }
    })();

    return this.restorationPromise;
  }

  /**
   * Explicitly invalidate the active session and clear all authentication state.
   */
  public logout(): void {
    this.storage.clearToken();
    this.setState({
      status: "unauthenticated",
      user: null,
      error: null,
    });
  }

  /**
   * Update the cached active user in memory (e.g. following a profile edit).
   */
  public setUser(user: User): void {
    this.setState({ user });
  }

  /**
   * Re-fetch the current active user profile from the backend.
   */
  public async refreshUser(): Promise<User> {
    const user = await this.api.getCurrentUser();
    this.setState({ user });
    return user;
  }

  /**
   * Reset store state for testing isolation.
   */
  public reset(): void {
    this.storage.clearToken();
    this.restorationPromise = null;
    this.state = {
      status: "uninitialized",
      user: null,
      error: null,
    };
    this.listeners.forEach((listener) => listener());
  }
}

export const authStore = new AuthStore();

const authActions = {
  login: (credentials: LoginRequest) => authStore.login(credentials),
  registerFarmer: (payload: FarmerRegisterRequest) => authStore.registerFarmer(payload),
  registerBuyer: (payload: BuyerRegisterRequest) => authStore.registerBuyer(payload),
  registerTransporter: (payload: TransporterRegisterRequest) => authStore.registerTransporter(payload),
  restoreSession: () => authStore.restoreSession(),
  logout: () => authStore.logout(),
  setUser: (user: User) => authStore.setUser(user),
  refreshUser: () => authStore.refreshUser(),
};

/**
 * Custom React hook subscribing to the global authentication store via useSyncExternalStore.
 */
export function useAuth(): AuthState & {
  login: (credentials: LoginRequest) => Promise<User>;
  registerFarmer: (payload: FarmerRegisterRequest) => Promise<User>;
  registerBuyer: (payload: BuyerRegisterRequest) => Promise<User>;
  registerTransporter: (payload: TransporterRegisterRequest) => Promise<User>;
  restoreSession: () => Promise<User | null>;
  logout: () => void;
  setUser: (user: User) => void;
  refreshUser: () => Promise<User>;
} {
  const state = useSyncExternalStore(authStore.subscribe, authStore.getState);

  return {
    ...state,
    ...authActions,
  };
}
