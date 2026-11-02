/**
 * Decoupled event constants and dispatchers for API client and auth store communication.
 * Prevents circular dependencies between the API client and state management modules.
 */

export const AUTH_EVENTS = {
  UNAUTHORIZED: "agridirect:unauthorized",
  FORBIDDEN: "agridirect:forbidden",
} as const;

export interface UnauthorizedEventDetail {
  status: 401;
  url: string;
  message: string;
}

export interface ForbiddenEventDetail {
  status: 403;
  url: string;
  message: string;
  detail?: unknown;
  isAccountSuspendedOrRestricted?: boolean;
  isVerificationRequired?: boolean;
  isRoleForbidden?: boolean;
}

export function dispatchUnauthorized(detail: UnauthorizedEventDetail): void {
  if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
    window.dispatchEvent(
      new CustomEvent<UnauthorizedEventDetail>(AUTH_EVENTS.UNAUTHORIZED, { detail })
    );
  }
}

export function dispatchForbidden(detail: ForbiddenEventDetail): void {
  if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
    window.dispatchEvent(
      new CustomEvent<ForbiddenEventDetail>(AUTH_EVENTS.FORBIDDEN, { detail })
    );
  }
}

