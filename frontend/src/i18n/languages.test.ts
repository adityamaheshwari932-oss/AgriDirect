import { describe, it, expect, beforeEach } from "vitest";
import {
  SUPPORTED_LANGUAGES,
  DEFAULT_LANGUAGE,
  LANGUAGE_STORAGE_KEY,
  getLanguage,
  isValidLanguageCode,
  getInitialLanguage,
} from "./languages";
import type { LanguageCode } from "./types";

describe("i18n Language Registry — All 23 Constitutional Languages", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("registers exactly 23 languages (English + 22 Scheduled Indian Languages)", () => {
    expect(SUPPORTED_LANGUAGES).toHaveLength(23);
  });

  it("ensures all language codes are unique", () => {
    const codes = SUPPORTED_LANGUAGES.map((l) => l.code);
    const uniqueCodes = new Set(codes);
    expect(uniqueCodes.size).toBe(23);
  });

  it("ensures all native names, English names, scripts, and locales are populated", () => {
    for (const lang of SUPPORTED_LANGUAGES) {
      expect(lang.code).toBeTruthy();
      expect(lang.name.trim().length).toBeGreaterThan(0);
      expect(lang.englishName.trim().length).toBeGreaterThan(0);
      expect(lang.script.trim().length).toBe(4); // ISO 15924 script codes are 4 letters
      expect(lang.locale).toMatch(/^[a-z]{2,3}-[A-Z]{2}$/);
    }
  });

  it("contains all 22 Eighth Schedule languages plus English", () => {
    const expectedCodes: LanguageCode[] = [
      "en",
      "hi",
      "mr",
      "gu",
      "bn",
      "ta",
      "te",
      "kn",
      "pa",
      "ml",
      "as",
      "or",
      "sa",
      "ne",
      "kok",
      "mai",
      "doi",
      "brx",
      "mni",
      "sat",
      "sd",
      "ur",
      "ks",
    ];

    const registeredCodes = SUPPORTED_LANGUAGES.map((l) => l.code);
    for (const expected of expectedCodes) {
      expect(registeredCodes).toContain(expected);
    }
  });

  it("correctly assigns RTL text direction to Urdu, Sindhi, and Kashmiri", () => {
    const rtlCodes: LanguageCode[] = ["ur", "sd", "ks"];

    for (const code of rtlCodes) {
      const lang = getLanguage(code);
      expect(lang.dir).toBe("rtl");
      expect(lang.script).toBe("Arab");
    }
  });

  it("correctly assigns LTR text direction to the remaining 20 languages", () => {
    const ltrLanguages = SUPPORTED_LANGUAGES.filter(
      (l) => !["ur", "sd", "ks"].includes(l.code)
    );

    expect(ltrLanguages).toHaveLength(20);
    for (const lang of ltrLanguages) {
      expect(lang.dir).toBe("ltr");
    }
  });

  it("validates language codes using isValidLanguageCode()", () => {
    expect(isValidLanguageCode("en")).toBe(true);
    expect(isValidLanguageCode("hi")).toBe(true);
    expect(isValidLanguageCode("mr")).toBe(true);
    expect(isValidLanguageCode("ur")).toBe(true);
    expect(isValidLanguageCode("fr")).toBe(false);
    expect(isValidLanguageCode("de")).toBe(false);
    expect(isValidLanguageCode("")).toBe(false);
    expect(isValidLanguageCode(null)).toBe(false);
    expect(isValidLanguageCode(undefined)).toBe(false);
  });

  it("retrieves language metadata using getLanguage() or falls back to English", () => {
    const hindi = getLanguage("hi");
    expect(hindi.code).toBe("hi");
    expect(hindi.name).toBe("हिन्दी");
    expect(hindi.englishName).toBe("Hindi");

    const fallback = getLanguage("nonexistent-code");
    expect(fallback.code).toBe(DEFAULT_LANGUAGE);
    expect(fallback.name).toBe("English");
  });

  it("reads and restores initial language from LocalStorage", () => {
    expect(getInitialLanguage()).toBe("en");

    localStorage.setItem(LANGUAGE_STORAGE_KEY, "mr");
    expect(getInitialLanguage()).toBe("mr");

    // Invalid code in localStorage falls back to English
    localStorage.setItem(LANGUAGE_STORAGE_KEY, "invalid-lang");
    expect(getInitialLanguage()).toBe("en");
  });
});
