import { describe, it, expect, beforeEach } from "vitest";
import {
  formatCurrency,
  formatNumber,
  formatDate,
  formatTime,
  formatDateTime,
  getActiveLocale,
} from "./formatters";
import { setLanguage } from "../i18n";

describe("Locale-Aware Formatting Utilities", () => {
  beforeEach(async () => {
    await setLanguage("en");
  });

  describe("Locale Resolution", () => {
    it("resolves the active BCP 47 locale from i18n", async () => {
      expect(getActiveLocale()).toBe("en-IN");

      await setLanguage("hi");
      expect(getActiveLocale()).toBe("hi-IN");

      await setLanguage("mr");
      expect(getActiveLocale()).toBe("mr-IN");

      await setLanguage("gu");
      expect(getActiveLocale()).toBe("gu-IN");

      await setLanguage("bn");
      expect(getActiveLocale()).toBe("bn-IN");

      await setLanguage("ta");
      expect(getActiveLocale()).toBe("ta-IN");

      await setLanguage("te");
      expect(getActiveLocale()).toBe("te-IN");

      await setLanguage("kn");
      expect(getActiveLocale()).toBe("kn-IN");

      await setLanguage("pa");
      expect(getActiveLocale()).toBe("pa-IN");

      await setLanguage("ml");
      expect(getActiveLocale()).toBe("ml-IN");
    });

    it("respects override locale when explicitly passed", () => {
      expect(getActiveLocale("mr-IN")).toBe("mr-IN");
      expect(getActiveLocale("ta-IN")).toBe("ta-IN");
    });
  });

  describe("Number Formatting", () => {
    it("formats small integers and zeros", () => {
      expect(formatNumber(0)).toBe("0");
      expect(formatNumber(5)).toBe("5");
      expect(formatNumber(100)).toBe("100");
    });

    it("formats decimals and respects fraction digit options", () => {
      expect(formatNumber(12.345, { maximumFractionDigits: 2 })).toBe("12.35");
      expect(formatNumber(12.3, { minimumFractionDigits: 2 })).toBe("12.30");
    });

    it("formats large numbers using Indian numbering grouping", () => {
      // 1 Lakh (1,00,000)
      const lakh = formatNumber(100000);
      expect(lakh).toBe("1,00,000");

      // 10 Crores (10,00,00,000)
      const crore = formatNumber(100000000);
      expect(crore).toBe("10,00,00,000");
    });

    it("handles negative numbers", () => {
      const negative = formatNumber(-25000);
      expect(negative).toBe("-25,000");
    });

    it("safely handles null, undefined, empty, and invalid inputs", () => {
      expect(formatNumber(null)).toBe("0");
      expect(formatNumber(undefined)).toBe("0");
      expect(formatNumber("")).toBe("0");
      expect(formatNumber("invalid")).toBe("0");
      expect(formatNumber(NaN)).toBe("0");
      expect(formatNumber(Infinity)).toBe("0");
    });
  });

  describe("Currency Formatting", () => {
    it("formats INR currency with Indian grouping and symbol without conversion", () => {
      const formatted = formatCurrency(50000);
      expect(formatted).toContain("50,000");
      expect(formatted).toContain("₹");

      const zeroFormatted = formatCurrency(0);
      expect(zeroFormatted).toContain("0");

      const crore = formatCurrency(18500000);
      expect(crore).toContain("1,85,00,000");
    });

    it("supports configurable decimal precision", () => {
      const withDecimals = formatCurrency(1850000, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      expect(withDecimals).toContain("18,50,000.00");
    });

    it("handles negative currency values", () => {
      const neg = formatCurrency(-5000);
      expect(neg).toContain("5,000");
      expect(neg).toContain("-");
    });

    it("safely handles invalid inputs and provides safe backwards-compatible fallbacks", () => {
      expect(formatCurrency(null)).toBe("₹0");
      expect(formatCurrency(undefined)).toBe("₹0");
      expect(formatCurrency("")).toBe("₹0");
      expect(formatCurrency("not-a-number")).toBe("INR 0");
      expect(formatCurrency(NaN)).toBe("INR 0");
    });

    it("supports polymorphic arguments (amount, locale) and (amount, currency, locale)", () => {
      const inHindi = formatCurrency(100000, "hi-IN");
      expect(inHindi).toContain("1,00,000");

      const inMarathi = formatCurrency(100000, "INR", "mr-IN");
      expect(inMarathi).toBeTruthy();
    });
  });

  describe("Date Formatting", () => {
    it("formats ISO date strings, timestamps, and Date objects", () => {
      const isoStr = "2026-04-15T10:30:00Z";
      const formattedDate = formatDate(isoStr);
      expect(formattedDate).toBeTruthy();
      expect(formattedDate).toContain("2026");

      const d = new Date(isoStr);
      expect(formatDate(d)).toBe(formattedDate);
      expect(formatDate(d.getTime())).toBe(formattedDate);
    });

    it("formats date-only strings", () => {
      const dateOnly = formatDate("2026-11-20");
      expect(dateOnly).toBeTruthy();
      expect(dateOnly).toContain("2026");
    });

    it("safely handles null, undefined, empty, and invalid dates", () => {
      expect(formatDate(null)).toBe("");
      expect(formatDate(undefined)).toBe("");
      expect(formatDate("")).toBe("");
      expect(formatDate("invalid-date")).toBe("");
    });
  });

  describe("Time Formatting", () => {
    it("formats morning, afternoon, and midnight timestamps", () => {
      const morning = formatTime("2026-04-15T04:30:00Z");
      expect(morning).toBeTruthy();

      const afternoon = formatTime("2026-04-15T10:00:00Z");
      expect(afternoon).toBeTruthy();

      const midnight = formatTime("2026-04-15T00:00:00Z");
      expect(midnight).toBeTruthy();
    });

    it("safely handles null, undefined, and invalid time values", () => {
      expect(formatTime(null)).toBe("");
      expect(formatTime(undefined)).toBe("");
      expect(formatTime("")).toBe("");
      expect(formatTime("invalid-time")).toBe("");
    });
  });

  describe("Date-Time Combined Formatting", () => {
    it("formats combined date and time", () => {
      const isoStr = "2026-04-15T10:30:00Z";
      const formatted = formatDateTime(isoStr);
      expect(formatted).toBeTruthy();
      expect(formatted).toContain("2026");
    });

    it("safely handles null, undefined, and invalid date-times", () => {
      expect(formatDateTime(null)).toBe("");
      expect(formatDateTime(undefined)).toBe("");
      expect(formatDateTime("")).toBe("");
      expect(formatDateTime("invalid-datetime")).toBe("");
    });
  });

  describe("Language Switching Dynamics Across Indian Languages", () => {
    const amount = 2500000;

    it("switches number and currency formatting between all 10 active languages", async () => {
      // English
      await setLanguage("en");
      expect(formatNumber(amount)).toBe("25,00,000");
      expect(formatCurrency(amount)).toContain("25,00,000");

      // Hindi
      await setLanguage("hi");
      expect(formatNumber(amount)).toBe("25,00,000");
      expect(formatCurrency(amount)).toContain("25,00,000");

      // Marathi (Devanagari numerals)
      await setLanguage("mr");
      expect(formatNumber(amount)).toBe("२५,००,०००");

      // Gujarati
      await setLanguage("gu");
      expect(formatNumber(amount)).toBe("25,00,000");

      // Bengali (Bengali numerals)
      await setLanguage("bn");
      expect(formatNumber(amount)).toBe("২৫,০০,০০০");

      // Tamil
      await setLanguage("ta");
      expect(formatNumber(amount)).toBe("25,00,000");

      // Telugu
      await setLanguage("te");
      expect(formatNumber(amount)).toBe("25,00,000");

      // Kannada
      await setLanguage("kn");
      expect(formatNumber(amount)).toBeTruthy();

      // Punjabi
      await setLanguage("pa");
      expect(formatNumber(amount)).toBe("25,00,000");

      // Malayalam
      await setLanguage("ml");
      expect(formatNumber(amount)).toBeTruthy();
    });
  });
});
