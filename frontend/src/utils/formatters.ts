/**
 * Centralized, locale-aware formatting utilities for AgriDirect.
 * Seamlessly interfaces with the active i18n language and BCP 47 locale metadata.
 */

import i18n, { getLanguage, type LanguageCode } from "../i18n";

/**
 * Resolves the appropriate BCP 47 locale string.
 * Defaults to the active i18n language's locale, or falls back to 'en-IN'.
 */
export function getActiveLocale(overrideLocale?: string): string {
  if (overrideLocale) return overrideLocale;
  const currentLang = (i18n.language || "en") as LanguageCode;
  const langConfig = getLanguage(currentLang);
  return langConfig?.locale || "en-IN";
}

/**
 * Helper to determine if a string argument represents an ISO currency code vs a locale code.
 */
function isCurrencyCode(str: string): boolean {
  // ISO 4217 currency codes are exactly 3 letters without hyphens or underscores
  return /^[A-Za-z]{3}$/.test(str) && !str.includes("-") && !str.includes("_");
}

/**
 * Formats a monetary amount using the active locale and currency.
 * Defaults to INR currency. Does NOT perform currency conversion.
 *
 * Examples:
 *   formatCurrency(150000) => "₹1,50,000" (or locale equivalent)
 *   formatCurrency(150000, { minimumFractionDigits: 2 }) => "₹1,50,000.00"
 *   formatCurrency(150000, "INR", "hi-IN") => "₹1,50,000"
 *   formatCurrency(150000, "hi-IN") => "₹1,50,000"
 */
export function formatCurrency(
  amount: number | string | null | undefined,
  currencyOrLocaleOrOptions?: string | Intl.NumberFormatOptions,
  localeOrOptions?: string | Intl.NumberFormatOptions,
  options?: Intl.NumberFormatOptions
): string {
  if (amount === null || amount === undefined || amount === "") {
    return "₹0";
  }

  const numericVal = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(numericVal) || !isFinite(numericVal)) {
    // If not a number, preserve currency prefix fallback for backwards compatibility
    const fallbackCurrency =
      typeof currencyOrLocaleOrOptions === "string" && isCurrencyCode(currencyOrLocaleOrOptions)
        ? currencyOrLocaleOrOptions.toUpperCase()
        : "INR";
    return `${fallbackCurrency} 0`;
  }

  let currency = "INR";
  let locale: string | undefined;
  let opts: Intl.NumberFormatOptions | undefined;

  // Polymorphic argument parsing
  if (typeof currencyOrLocaleOrOptions === "string") {
    if (isCurrencyCode(currencyOrLocaleOrOptions)) {
      currency = currencyOrLocaleOrOptions.toUpperCase();
      if (typeof localeOrOptions === "string") {
        locale = localeOrOptions;
        opts = options;
      } else if (typeof localeOrOptions === "object") {
        opts = localeOrOptions;
      }
    } else {
      // 2nd arg is a locale like "hi-IN" or "mr"
      locale = currencyOrLocaleOrOptions;
      if (typeof localeOrOptions === "object") {
        opts = localeOrOptions;
      }
    }
  } else if (typeof currencyOrLocaleOrOptions === "object") {
    opts = currencyOrLocaleOrOptions;
  }

  const defaultOptions: Intl.NumberFormatOptions = {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
    ...opts,
  };

  try {
    const loc = getActiveLocale(locale);
    return new Intl.NumberFormat(loc, defaultOptions).format(numericVal);
  } catch {
    // Fallback if locale or currency code is unsupported
    return `₹${Number(numericVal).toLocaleString()}`;
  }
}

/**
 * Formats a raw number according to the active locale grouping rules (e.g. lakhs/crores in en-IN).
 *
 * Example: formatNumber(2500000) => "25,00,00" (or Devanagari numerals in mr-IN)
 */
export function formatNumber(
  value: number | string | null | undefined,
  localeOrOptions?: string | Intl.NumberFormatOptions,
  options?: Intl.NumberFormatOptions
): string {
  if (value === null || value === undefined || value === "") return "0";
  const numericVal = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(numericVal) || !isFinite(numericVal)) return "0";

  const locale = typeof localeOrOptions === "string" ? localeOrOptions : undefined;
  const opts = typeof localeOrOptions === "object" ? localeOrOptions : options;

  try {
    const loc = getActiveLocale(locale);
    return new Intl.NumberFormat(loc, opts).format(numericVal);
  } catch {
    return Number(numericVal).toLocaleString();
  }
}

/**
 * Formats a date string, timestamp, or Date object according to the active locale.
 *
 * Example: formatDate("2026-04-12T10:00:00Z") => "12 Apr 2026"
 */
export function formatDate(
  date: string | number | Date | null | undefined,
  localeOrOptions?: string | Intl.DateTimeFormatOptions,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "";
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d.getTime())) return "";

  const locale = typeof localeOrOptions === "string" ? localeOrOptions : undefined;
  const opts = typeof localeOrOptions === "object" ? localeOrOptions : options;

  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
    ...opts,
  };

  try {
    const loc = getActiveLocale(locale);
    return new Intl.DateTimeFormat(loc, defaultOptions).format(d);
  } catch {
    return d.toLocaleDateString();
  }
}

/**
 * Formats time-only display according to the active locale.
 *
 * Example: formatTime("2026-04-12T10:30:00Z") => "4:00 PM" (or locale equivalent)
 */
export function formatTime(
  date: string | number | Date | null | undefined,
  localeOrOptions?: string | Intl.DateTimeFormatOptions,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "";
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d.getTime())) return "";

  const locale = typeof localeOrOptions === "string" ? localeOrOptions : undefined;
  const opts = typeof localeOrOptions === "object" ? localeOrOptions : options;

  const defaultOptions: Intl.DateTimeFormatOptions = {
    hour: "numeric",
    minute: "2-digit",
    ...opts,
  };

  try {
    const loc = getActiveLocale(locale);
    return new Intl.DateTimeFormat(loc, defaultOptions).format(d);
  } catch {
    return d.toLocaleTimeString();
  }
}

/**
 * Formats a date with time according to the active locale.
 *
 * Example: formatDateTime("2026-04-12T10:30:00Z") => "12 Apr 2026, 4:00 PM"
 */
export function formatDateTime(
  date: string | number | Date | null | undefined,
  localeOrOptions?: string | Intl.DateTimeFormatOptions,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "";
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d.getTime())) return "";

  const locale = typeof localeOrOptions === "string" ? localeOrOptions : undefined;
  const opts = typeof localeOrOptions === "object" ? localeOrOptions : options;

  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    ...opts,
  };

  try {
    const loc = getActiveLocale(locale);
    return new Intl.DateTimeFormat(loc, defaultOptions).format(d);
  } catch {
    return d.toLocaleString();
  }
}
