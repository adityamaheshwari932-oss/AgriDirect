import type { Language, LanguageCode } from "./types";

export const LANGUAGE_STORAGE_KEY = "agridirect_language";
export const DEFAULT_LANGUAGE: LanguageCode = "en";

/**
 * Central registry of supported languages:
 * English + all 22 constitutionally Scheduled Indian Languages (Eighth Schedule).
 *
 * NOTE: The `name` property is ALWAYS written in its native script so that
 * speakers of that language can immediately identify it in the selector,
 * regardless of the currently active UI language.
 */
export const SUPPORTED_LANGUAGES: readonly Language[] = [
  {
    code: "en",
    name: "English",
    englishName: "English",
    script: "Latn",
    dir: "ltr",
    locale: "en-IN",
  },
  {
    code: "hi",
    name: "हिन्दी",
    englishName: "Hindi",
    script: "Deva",
    dir: "ltr",
    locale: "hi-IN",
  },
  {
    code: "mr",
    name: "मराठी",
    englishName: "Marathi",
    script: "Deva",
    dir: "ltr",
    locale: "mr-IN",
  },
  {
    code: "gu",
    name: "ગુજરાતી",
    englishName: "Gujarati",
    script: "Gujr",
    dir: "ltr",
    locale: "gu-IN",
  },
  {
    code: "bn",
    name: "বাংলা",
    englishName: "Bengali",
    script: "Beng",
    dir: "ltr",
    locale: "bn-IN",
  },
  {
    code: "ta",
    name: "தமிழ்",
    englishName: "Tamil",
    script: "Taml",
    dir: "ltr",
    locale: "ta-IN",
  },
  {
    code: "te",
    name: "తెలుగు",
    englishName: "Telugu",
    script: "Telu",
    dir: "ltr",
    locale: "te-IN",
  },
  {
    code: "kn",
    name: "ಕನ್ನಡ",
    englishName: "Kannada",
    script: "Knda",
    dir: "ltr",
    locale: "kn-IN",
  },
  {
    code: "pa",
    name: "ਪੰਜਾਬੀ",
    englishName: "Punjabi",
    script: "Guru",
    dir: "ltr",
    locale: "pa-IN",
  },
  {
    code: "ml",
    name: "മലയാളം",
    englishName: "Malayalam",
    script: "Mlym",
    dir: "ltr",
    locale: "ml-IN",
  },
  {
    code: "as",
    name: "অসমীয়া",
    englishName: "Assamese",
    script: "Beng",
    dir: "ltr",
    locale: "as-IN",
  },
  {
    code: "or",
    name: "ଓଡ଼ିଆ",
    englishName: "Odia",
    script: "Orya",
    dir: "ltr",
    locale: "or-IN",
  },
  {
    code: "sa",
    name: "संस्कृतम्",
    englishName: "Sanskrit",
    script: "Deva",
    dir: "ltr",
    locale: "sa-IN",
  },
  {
    code: "ne",
    name: "नेपाली",
    englishName: "Nepali",
    script: "Deva",
    dir: "ltr",
    locale: "ne-IN",
  },
  {
    code: "kok",
    name: "कोंकणी",
    englishName: "Konkani",
    script: "Deva",
    dir: "ltr",
    locale: "kok-IN",
  },
  {
    code: "mai",
    name: "मैथिली",
    englishName: "Maithili",
    script: "Deva",
    dir: "ltr",
    locale: "mai-IN",
  },
  {
    code: "doi",
    name: "डोगरी",
    englishName: "Dogri",
    script: "Deva",
    dir: "ltr",
    locale: "doi-IN",
  },
  {
    code: "brx",
    name: "बड़ो",
    englishName: "Bodo",
    script: "Deva",
    dir: "ltr",
    locale: "brx-IN",
  },
  {
    code: "mni",
    name: "ꯃꯩꯇꯩꯂꯣꯟ",
    englishName: "Manipuri",
    script: "Mtei",
    dir: "ltr",
    locale: "mni-IN",
  },
  {
    code: "sat",
    name: "ᱥᱟᱱᱛᱟᱲᱤ",
    englishName: "Santali",
    script: "Olck",
    dir: "ltr",
    locale: "sat-IN",
  },
  {
    code: "sd",
    name: "سنڌي",
    englishName: "Sindhi",
    script: "Arab",
    dir: "rtl",
    locale: "sd-IN",
  },
  {
    code: "ur",
    name: "اُردُو",
    englishName: "Urdu",
    script: "Arab",
    dir: "rtl",
    locale: "ur-IN",
  },
  {
    code: "ks",
    name: "کٲشُر",
    englishName: "Kashmiri",
    script: "Arab",
    dir: "rtl",
    locale: "ks-IN",
  },
];

const LANGUAGE_CODE_SET = new Set<string>(SUPPORTED_LANGUAGES.map((l) => l.code));

const LANGUAGE_MAP = new Map<LanguageCode, Language>(
  SUPPORTED_LANGUAGES.map((l) => [l.code, l])
);

/**
 * Checks whether a given string is a supported LanguageCode.
 */
export function isValidLanguageCode(code: string | null | undefined): code is LanguageCode {
  if (!code) return false;
  return LANGUAGE_CODE_SET.has(code);
}

/**
 * Retrieves full language metadata by its language code.
 */
export function getLanguage(code: string | null | undefined): Language {
  if (isValidLanguageCode(code)) {
    const lang = LANGUAGE_MAP.get(code);
    if (lang) return lang;
  }
  return LANGUAGE_MAP.get(DEFAULT_LANGUAGE)!;
}

/**
 * Reads and validates the user's saved language preference from LocalStorage.
 * Falls back safely to DEFAULT_LANGUAGE ('en') if invalid or missing.
 */
export function getInitialLanguage(): LanguageCode {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
      if (isValidLanguageCode(stored)) {
        return stored;
      }
    }
  } catch {
    // LocalStorage might be disabled or restricted in private browsing
  }
  return DEFAULT_LANGUAGE;
}

/**
 * Determines whether a given language code (or document language) requires RTL direction.
 */
export function isRTL(code?: string | null): boolean {
  const target = code || (typeof document !== "undefined" ? document.documentElement.lang : DEFAULT_LANGUAGE);
  return getLanguage(target).dir === "rtl";
}
