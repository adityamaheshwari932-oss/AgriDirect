import { describe, it, expect, beforeEach, afterEach } from "vitest";
import i18n, { setLanguage, syncDocumentAttributes } from "./index";
import { LANGUAGE_STORAGE_KEY } from "./languages";

describe("i18n Initialization and Dynamic Language Switching", () => {
  beforeEach(async () => {
    localStorage.clear();
    await setLanguage("en");
  });

  afterEach(async () => {
    await setLanguage("en");
  });

  it("initializes with English as the fallback and active language", () => {
    expect(i18n.isInitialized).toBe(true);
    expect(i18n.language).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");
  });

  it("translates baseline keys from common.json", () => {
    expect(i18n.t("app.name")).toBe("AgriDirect");
    expect(i18n.t("actions.submit")).toBe("Submit");
    expect(i18n.t("status.verified")).toBe("Verified");
  });

  it("switches language dynamically and updates document lang and dir attributes for LTR languages", async () => {
    await setLanguage("hi");
    expect(i18n.language).toBe("hi");
    expect(document.documentElement.lang).toBe("hi");
    expect(document.documentElement.dir).toBe("ltr");
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("hi");

    await setLanguage("bn");
    expect(i18n.language).toBe("bn");
    expect(document.documentElement.lang).toBe("bn");
    expect(document.documentElement.dir).toBe("ltr");
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("bn");
  });

  it("updates document dir attribute to 'rtl' when switching to Urdu, Sindhi, or Kashmiri", async () => {
    await setLanguage("ur");
    expect(i18n.language).toBe("ur");
    expect(document.documentElement.lang).toBe("ur");
    expect(document.documentElement.dir).toBe("rtl");
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("ur");

    await setLanguage("sd");
    expect(i18n.language).toBe("sd");
    expect(document.documentElement.lang).toBe("sd");
    expect(document.documentElement.dir).toBe("rtl");

    await setLanguage("ks");
    expect(i18n.language).toBe("ks");
    expect(document.documentElement.lang).toBe("ks");
    expect(document.documentElement.dir).toBe("rtl");
  });

  it("safely resets document dir back to 'ltr' when switching back from RTL to an LTR language", async () => {
    await setLanguage("ur");
    expect(document.documentElement.dir).toBe("rtl");

    await setLanguage("en");
    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");
  });

  it("falls back to English when an invalid language code is passed to setLanguage()", async () => {
    // @ts-expect-error testing invalid runtime code
    await setLanguage("xyz-invalid");
    expect(i18n.language).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");
  });

  it("syncDocumentAttributes updates DOM and localStorage properly", () => {
    syncDocumentAttributes("mr");
    expect(document.documentElement.lang).toBe("mr");
    expect(document.documentElement.dir).toBe("ltr");
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("mr");

    syncDocumentAttributes("ur");
    expect(document.documentElement.lang).toBe("ur");
    expect(document.documentElement.dir).toBe("rtl");
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("ur");
  });

  it("loads and resolves keys across all 21 translation namespaces", () => {
    expect(i18n.t("common:actions.save")).toBe("Save");
    expect(i18n.t("auth:login.title")).toBe("Welcome Back to AgriDirect");
    expect(i18n.t("profile:title")).toBe("Account & Commercial Profile");
    expect(i18n.t("verification:title")).toBe("Identity & Operational Verification");
    expect(i18n.t("marketplace:title")).toBe("Agricultural Commodities Marketplace");
    expect(i18n.t("requirements:title")).toBe("Buyer Sourcing Requirements");
    expect(i18n.t("dashboard:farmer.portal_title")).toBe("Agricultural Producer Portal");
    expect(i18n.t("offers:title")).toBe("Trade Offers & Negotiations");
    expect(i18n.t("orders:title")).toBe("Commercial Orders Ledger");
    expect(i18n.t("inventory:title")).toBe("Produce Inventory Ledger");
    expect(i18n.t("delivery:arrange_title")).toBe("Schedule Lot Dispatch & Logistics");
    expect(i18n.t("messaging:title")).toBe("Trade Communications");
    expect(i18n.t("payments:title")).toBe("Off-Platform Direct Bank Settlement");
    expect(i18n.t("disputes:title")).toBe("Payment & Contract Disputes");
    expect(i18n.t("reviews:title")).toBe("Counterparty Trade Reviews");
    expect(i18n.t("notifications:title")).toBe("Notifications & Alerts");
    expect(i18n.t("reports:title")).toBe("Safety & Integrity Reporting");
    expect(i18n.t("analytics:title")).toBe("Market Analytics & Price Trends");
    expect(i18n.t("admin:portal_title")).toBe("Platform Governance & Compliance Portal");
    expect(i18n.t("errors:generic")).toContain("unexpected error");
    expect(i18n.t("validation:required")).toBe("This field is required");
  });

  it("performs interpolation and pluralization accurately", () => {
    // Interpolation
    const interpolated = i18n.t("orders:slip.subtitle", { orderNumber: "ORD-9999" });
    expect(interpolated).toBe("Official bilateral B2B trade documentation for Order ORD-9999");

    // Pluralization
    const singular = i18n.t("notifications:unread_count", { count: 1 });
    expect(singular).toBe("1 unread notification");

    const plural = i18n.t("notifications:unread_count", { count: 5 });
    expect(plural).toBe("5 unread notifications");
  });

  it("handles missing translation keys by falling back to key or default", () => {
    const missing = i18n.t("common:nonexistent.key");
    expect(missing).toBe("nonexistent.key");
  });
});
