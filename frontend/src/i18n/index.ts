import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import {
  DEFAULT_LANGUAGE,
  LANGUAGE_STORAGE_KEY,
  getInitialLanguage,
  getLanguage,
  isValidLanguageCode,
} from "./languages";
import type { LanguageCode } from "./types";

import en from "./locales/en";
import hi from "./locales/hi";
import mr from "./locales/mr";
import gu from "./locales/gu";
import bn from "./locales/bn";
import ta from "./locales/ta";
import te from "./locales/te";
import kn from "./locales/kn";
import pa from "./locales/pa";
import ml from "./locales/ml";
import as from "./locales/as";
import or from "./locales/or";
import sa from "./locales/sa";
import ne from "./locales/ne";
import kok from "./locales/kok";
import mai from "./locales/mai";
import doi from "./locales/doi";
import brx from "./locales/brx";
import mni from "./locales/mni";
import sat from "./locales/sat";
import sd from "./locales/sd";
import ur from "./locales/ur";
import ks from "./locales/ks";

export const NAMESPACES = [
  "common",
  "auth",
  "profile",
  "verification",
  "marketplace",
  "requirements",
  "dashboard",
  "offers",
  "orders",
  "inventory",
  "delivery",
  "messaging",
  "payments",
  "disputes",
  "reviews",
  "notifications",
  "reports",
  "analytics",
  "admin",
  "errors",
  "validation",
] as const;

export type TranslationNamespace = (typeof NAMESPACES)[number];

export const resources = {
  en,
  hi,
  mr,
  gu,
  bn,
  ta,
  te,
  kn,
  pa,
  ml,
  as,
  or,
  sa,
  ne,
  kok,
  mai,
  doi,
  brx,
  mni,
  sat,
  sd,
  ur,
  ks,
};

export const enResources = en;

/**
 * Synchronizes HTML document attributes (`lang` and `dir`) and persists
 * the chosen language code in LocalStorage.
 */
export function syncDocumentAttributes(code: string): void {
  if (typeof document === "undefined") return;

  const validCode: LanguageCode = isValidLanguageCode(code) ? code : DEFAULT_LANGUAGE;
  const langConfig = getLanguage(validCode);

  document.documentElement.lang = validCode;
  document.documentElement.dir = langConfig.dir;

  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, validCode);
    }
  } catch {
    // Ignore LocalStorage security/quota errors in restricted contexts
  }
}

const initialLanguage = getInitialLanguage();

// Initialize i18next instance exactly once
void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage,
  fallbackLng: DEFAULT_LANGUAGE,
  defaultNS: "common",
  ns: NAMESPACES as unknown as string[],
  interpolation: {
    escapeValue: false, // React already escapes values safely
  },
  react: {
    useSuspense: false, // Synchronous fallback to prevent suspense hydration flashes
  },
});

// Keep document attributes synchronized on language change
i18n.on("languageChanged", (lng: string) => {
  syncDocumentAttributes(lng);
});

// Initial attribute synchronization for the current document
if (typeof document !== "undefined") {
  syncDocumentAttributes(initialLanguage);
}

/**
 * Programmatically switches the active UI language across the entire application,
 * updates the document's `lang` and `dir` attributes, and persists the preference.
 */
export async function setLanguage(code: LanguageCode): Promise<void> {
  const targetCode = isValidLanguageCode(code) ? code : DEFAULT_LANGUAGE;
  await i18n.changeLanguage(targetCode);
  syncDocumentAttributes(targetCode);
}

export default i18n;
export * from "./types";
export * from "./languages";
