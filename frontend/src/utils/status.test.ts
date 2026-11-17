import { describe, it, expect } from "vitest";
import {
  VERIFICATION_STATUS_CONFIG,
  ACCOUNT_STATUS_CONFIG,
  getLocalizedVerificationStatus,
  getLocalizedAccountStatus,
  getDocumentTypeLabel,
} from "./status";

describe("Status Configuration & Localization Helpers", () => {
  it("preserves static default values for backwards compatibility", () => {
    expect(VERIFICATION_STATUS_CONFIG.verified.label).toBe("Verified");
    expect(VERIFICATION_STATUS_CONFIG.unverified.label).toBe("Not Verified");
    expect(ACCOUNT_STATUS_CONFIG.active.label).toBe("Active");
    expect(ACCOUNT_STATUS_CONFIG.suspended.label).toBe("Suspended");
  });

  it("returns localized verification presentation using translation function", () => {
    const mockT = (key: string) => {
      if (key === "common:status.verified") return "सत्यापित";
      if (key === "verification:status_verified_desc") return "खाते सत्यापित झाले आहे";
      return key;
    };

    const localized = getLocalizedVerificationStatus("verified", mockT);
    expect(localized.label).toBe("सत्यापित");
    expect(localized.description).toBe("खाते सत्यापित झाले आहे");
    expect(localized.badgeClass).toContain("bg-emerald-50");
  });

  it("safely falls back when no translation function is provided", () => {
    const direct = getLocalizedVerificationStatus("verified");
    expect(direct.label).toBe("Verified");
  });

  it("returns localized account status", () => {
    const mockT = (key: string) => {
      if (key === "common:status.active") return "सक्रिय";
      return key;
    };

    const localized = getLocalizedAccountStatus("active", mockT);
    expect(localized.label).toBe("सक्रिय");
    expect(localized.badgeClass).toContain("bg-emerald-50");
  });

  it("returns document type labels and fallbacks", () => {
    expect(getDocumentTypeLabel("land_ownership")).toBe("Land Ownership Record / Title");
    expect(getDocumentTypeLabel("gstin_certificate")).toBe("GSTIN Registration Certificate");
    expect(getDocumentTypeLabel("unknown_doc")).toBe("Unknown Doc");
  });
});
