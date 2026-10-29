/**
 * Token storage abstraction for JWT access tokens.
 *
 * Security Context:
 * - The backend currently issues a short-to-medium lived access token without a refresh token endpoint.
 * - Storing tokens in client-accessible storage (localStorage or sessionStorage) carries XSS exposure risks.
 * - InMemoryTokenStorage isolates tokens completely from persistent web storage but loses state on page reload.
 * - SessionTokenStorage retains the token across page reloads within the same browser tab, but clears on tab close.
 */

export interface TokenStorage {
  getToken(): string | null;
  setToken(token: string): void;
  clearToken(): void;
}

/**
 * Pure in-memory token storage.
 * Completely inaccessible from web storage APIs (localStorage / sessionStorage).
 * Session does not survive a page refresh.
 */
export class InMemoryTokenStorage implements TokenStorage {
  private token: string | null = null;

  getToken(): string | null {
    return this.token;
  }

  setToken(token: string): void {
    this.token = token;
  }

  clearToken(): void {
    this.token = null;
  }
}

/**
 * Browser tab-scoped session storage.
 * Retains access token across page refreshes within the same browser tab,
 * automatically clearing when the tab/window is closed.
 * Falls back gracefully to in-memory storage if sessionStorage is inaccessible.
 */
export class SessionTokenStorage implements TokenStorage {
  private readonly storageKey: string;
  private fallbackMemory: InMemoryTokenStorage;

  constructor(storageKey = "agridirect_access_token") {
    this.storageKey = storageKey;
    this.fallbackMemory = new InMemoryTokenStorage();
  }

  private isAvailable(): boolean {
    try {
      return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";
    } catch {
      return false;
    }
  }

  getToken(): string | null {
    if (!this.isAvailable()) {
      return this.fallbackMemory.getToken();
    }
    try {
      return window.sessionStorage.getItem(this.storageKey);
    } catch {
      return this.fallbackMemory.getToken();
    }
  }

  setToken(token: string): void {
    if (!this.isAvailable()) {
      this.fallbackMemory.setToken(token);
      return;
    }
    try {
      window.sessionStorage.setItem(this.storageKey, token);
    } catch {
      this.fallbackMemory.setToken(token);
    }
  }

  clearToken(): void {
    if (!this.isAvailable()) {
      this.fallbackMemory.clearToken();
      return;
    }
    try {
      window.sessionStorage.removeItem(this.storageKey);
    } catch {
      this.fallbackMemory.clearToken();
    }
  }
}

// Global active token storage instance
let activeStorage: TokenStorage = new SessionTokenStorage();

export const tokenStorage = {
  getToken: (): string | null => activeStorage.getToken(),
  setToken: (token: string): void => activeStorage.setToken(token),
  clearToken: (): void => activeStorage.clearToken(),
  setProvider: (provider: TokenStorage): void => {
    activeStorage = provider;
  },
};
