/**
 * Normalized API error class representing HTTP and network errors.
 */

import type { ValidationErrorItem } from "../types/api";

export class ApiError extends Error {
  public readonly status: number;
  public readonly detail?: string | ValidationErrorItem[];
  public readonly isNetworkError: boolean;

  constructor(status: number, message: string, detail?: string | ValidationErrorItem[]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.isNetworkError = status === 0;

    // Restore prototype chain for instanceof checks across compilation targets
    Object.setPrototypeOf(this, ApiError.prototype);
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isValidationError(): boolean {
    return this.status === 422;
  }

  get isRateLimited(): boolean {
    return this.status === 429;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }

  get isAborted(): boolean {
    return this.message.toLowerCase().includes("abort");
  }

  private get detailText(): string {
    if (typeof this.detail === "string") {
      return this.detail.toLowerCase();
    }
    return this.message.toLowerCase();
  }

  /**
   * Distinguishes account status restriction/suspension from ordinary permission denials.
   */
  get isAccountSuspendedOrRestricted(): boolean {
    if (!this.isForbidden) return false;
    const text = this.detailText;
    return (
      text.includes("suspended") ||
      text.includes("restricted") ||
      text.includes("blocked") ||
      text.includes("account_restricted") ||
      text.includes("account_suspended") ||
      text.includes("account_blocked")
    );
  }

  get isAccountInactive(): boolean {
    if (!this.isForbidden) return false;
    return this.detailText.includes("inactive");
  }

  get isVerificationRequired(): boolean {
    if (!this.isForbidden) return false;
    const text = this.detailText;
    return text.includes("requires a verified") || text.includes("verification");
  }

  get isRoleForbidden(): boolean {
    if (!this.isForbidden) return false;
    const text = this.detailText;
    return (
      text.includes("farmer account") ||
      text.includes("buyer account") ||
      text.includes("administrator privileges")
    );
  }

  /**
   * Helper to format validation errors into a field -> message[] dictionary.
   */
  get fieldErrors(): Record<string, string[]> {
    const errors: Record<string, string[]> = {};
    if (!Array.isArray(this.detail)) {
      return errors;
    }

    for (const item of this.detail) {
      if (item && item.loc && item.msg) {
        // Pydantic format: loc: ["body", "field_name"] -> "field_name"
        const fieldKey = item.loc[item.loc.length - 1]?.toString() || "general";
        if (!errors[fieldKey]) {
          errors[fieldKey] = [];
        }
        errors[fieldKey].push(item.msg);
      }
    }
    return errors;
  }
}
