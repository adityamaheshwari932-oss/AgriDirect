/**
 * Internationalization (i18n) domain types for AgriDirect.
 * Supports English and all 22 constitutionally Scheduled Indian Languages.
 */

export type TextDirection = "ltr" | "rtl";

export type LanguageCode =
  | "en"
  | "hi"
  | "mr"
  | "gu"
  | "bn"
  | "ta"
  | "te"
  | "kn"
  | "pa"
  | "ml"
  | "as"
  | "or"
  | "sa"
  | "ne"
  | "kok"
  | "mai"
  | "doi"
  | "brx"
  | "mni"
  | "sat"
  | "sd"
  | "ur"
  | "ks";

export interface Language {
  /** ISO 639-1 / 639-2 language code */
  code: LanguageCode;
  /** Language name rendered in its own native script (e.g. 'हिन्दी', 'मराठी', 'سنڌي') */
  name: string;
  /** Common English name of the language (e.g. 'Hindi', 'Marathi', 'Sindhi') */
  englishName: string;
  /** ISO 15924 four-letter script identifier (e.g. 'Deva', 'Beng', 'Arab', 'Olck') */
  script: string;
  /** Direction of the written script ('ltr' or 'rtl') */
  dir: TextDirection;
  /** Standard BCP 47 locale tag (e.g. 'hi-IN', 'ur-IN') */
  locale: string;
}
