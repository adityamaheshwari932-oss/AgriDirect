import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import i18n, { setLanguage, resources, NAMESPACES } from "./index";
import { LANGUAGE_STORAGE_KEY } from "./languages";
import { formatCurrency, formatNumber } from "../utils/formatters";
import { LoginPage } from "../pages/LoginPage";
import { ProduceListingCard } from "../components/marketplace/ProduceListingCard";
import type { ProduceListingPublicSummary } from "../types/listings";

const TARGET_LANGUAGES = [
  "hi",
  "mr",
  "gu",
  "bn",
  "ta",
  "te",
  "kn",
  "pa",
  "ml",
] as const;

describe("Stage 3: 9 Indian Language Translations & Application Localization", () => {
  beforeEach(async () => {
    localStorage.clear();
    await setLanguage("en");
  });

  afterEach(async () => {
    await setLanguage("en");
  });

  describe("A. Translation Resource Registration & Parity", () => {
    it("registers all 9 Indian languages plus English in resources", () => {
      const registeredLangs = Object.keys(resources);
      expect(registeredLangs).toContain("en");
      for (const lang of TARGET_LANGUAGES) {
        expect(registeredLangs).toContain(lang);
      }
    });

    it("registers all 21 namespaces for each of the 9 Indian languages", () => {
      for (const lang of TARGET_LANGUAGES) {
        const langResources = resources[lang as keyof typeof resources] as Record<string, unknown>;
        expect(langResources).toBeDefined();

        for (const ns of NAMESPACES) {
          expect(langResources[ns]).toBeDefined();
          expect(typeof langResources[ns]).toBe("object");
        }
      }
    });

    it("verifies key structure parity between English and all 9 languages for critical namespaces", () => {
      const enCommon = resources.en.common as Record<string, Record<string, string>>;
      const enActions = Object.keys(enCommon.actions);

      for (const lang of TARGET_LANGUAGES) {
        const langCommon = (resources[lang as keyof typeof resources] as typeof resources.en).common as Record<string, Record<string, string>>;
        expect(Object.keys(langCommon.actions)).toEqual(enActions);
      }
    });
  });

  describe("B. Dynamic Language Switching & Preference Persistence", () => {
    it("switches smoothly between all 9 languages, maintaining LTR and updating document lang", async () => {
      for (const lang of TARGET_LANGUAGES) {
        await setLanguage(lang);
        expect(i18n.language).toBe(lang);
        expect(document.documentElement.lang).toBe(lang);
        expect(document.documentElement.dir).toBe("ltr");
        expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe(lang);
      }
    });

    it("persists language selection and survives simulated session reload", async () => {
      await setLanguage("mr");
      expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("mr");

      // Verify that re-reading from storage preserves preference
      const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
      expect(stored).toBe("mr");
    });
  });

  describe("C. Accurate Indic Translation Resolution", () => {
    it("resolves action submit label accurately in all 9 languages", async () => {
      const expectedSubmit: Record<(typeof TARGET_LANGUAGES)[number], string> = {
        hi: "जमा करें",
        mr: "सादर करा",
        gu: "સબમિટ કરો",
        bn: "জমা দিন",
        ta: "சமர்ப்பி",
        te: "సమర్పించు",
        kn: "ಸಲ್ಲಿಸಿ",
        pa: "ਜਮ੍ਹਾ ਕਰੋ",
        ml: "സമർപ്പിക്കുക",
      };

      for (const lang of TARGET_LANGUAGES) {
        await setLanguage(lang);
        expect(i18n.t("common:actions.submit")).toBe(expectedSubmit[lang]);
      }
    });

    it("resolves marketplace verified trade badge accurately in all 9 languages", async () => {
      const expectedBadge: Record<(typeof TARGET_LANGUAGES)[number], string> = {
        hi: "सत्यापित B2B प्रत्यक्ष व्यापार",
        mr: "सत्यापित B2B थेट व्यापार",
        gu: "ચકાસાયેલ B2B પ્રત્યક્ષ વેપાર",
        bn: "যাচাইকৃত B2B প্রত্যক্ষ বাণিজ্য",
        ta: "சரிபார்க்கப்பட்ட B2B நேரடி வர்த்தகம்",
        te: "ధృవీకరించబడిన B2B ప్రత్యక్ష వాణిజ్యం",
        kn: "ಪರಿಶೀಲಿಸಿದ B2B ನೇರ ವ್ಯಾಪಾರ",
        pa: "ਤਸਦੀਕਸ਼ੁਦਾ B2B ਸਿੱਧਾ ਵਪਾਰ",
        ml: "സ്ഥിരീകരിച്ച B2B നേരിട്ടുള്ള വ്യാപാരം",
      };

      for (const lang of TARGET_LANGUAGES) {
        await setLanguage(lang);
        expect(i18n.t("marketplace:badge_verified")).toBe(expectedBadge[lang]);
      }
    });

    it("resolves interpolation placeholders accurately in Indic translations", async () => {
      await setLanguage("hi");
      const hiSubtitle = i18n.t("orders:slip.subtitle", { orderNumber: "ORD-5555" });
      expect(hiSubtitle).toContain("ORD-5555");
      expect(hiSubtitle).toContain("B2B");

      await setLanguage("bn");
      const bnSubtitle = i18n.t("orders:slip.subtitle", { orderNumber: "ORD-7777" });
      expect(bnSubtitle).toContain("ORD-7777");

      await setLanguage("ta");
      const taSubtitle = i18n.t("orders:slip.subtitle", { orderNumber: "ORD-8888" });
      expect(taSubtitle).toContain("ORD-8888");
    });
  });

  describe("D. Indic Component Localization Rendering", () => {
    it("renders LoginPage in Marathi with translated headings and action buttons", async () => {
      await setLanguage("mr");

      render(
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      );

      // Check Marathi translated heading and submit button
      expect(screen.getByText("आपल्या खात्यात साइन इन करा")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "साइन इन करा" })).toBeInTheDocument();
      expect(screen.getByText("ईमेल पत्ता")).toBeInTheDocument();
      expect(screen.getByText("पासवर्ड")).toBeInTheDocument();
    });

    it("renders ProduceListingCard in Tamil with translated badges and volume labels", async () => {
      await setLanguage("ta");

      const mockListing: ProduceListingPublicSummary = {
        id: "listing-test-1",
        product_name: "Wheat",
        title: "Sharbati Organic Wheat",
        category_name: "Cereals",
        available_quantity: 50,
        unit: "quintal",
        price_per_unit: 2850,
        harvest_date: "2026-03-15",
        status: "active",
        location_city: "Indore",
        location_state: "MP",
        available_from: "2026-03-15",
        expires_at: "2026-04-15",
        created_at: "2026-03-01T10:00:00Z",
      };

      render(
        <MemoryRouter>
          <ProduceListingCard listing={mockListing} onViewDetails={() => {}} />
        </MemoryRouter>
      );

      // Tamil translated badge and labels
      expect(screen.getByText("பண்ணை நேரடி தொகுதி")).toBeInTheDocument();
      expect(screen.getByText("மொத்த விலை")).toBeInTheDocument();
      expect(screen.getByText("கிடைக்கும் அளவு")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /தொகுதி விவரங்களைப் பார்க்கவும்/i })).toBeInTheDocument();
    });
  });

  describe("E. Indian Numbering & Locale Currency Formatting", () => {
    it("formats Indian Rupees and numbers adhering to Indian numbering conventions", () => {
      // 1 Lakh (1,00,000)
      const formattedHi = formatCurrency(100000, "hi-IN");
      expect(formattedHi).toContain("1,00,000");

      // 25 Lakhs in Marathi native script (२५,००,०००)
      const formattedNumberMr = formatNumber(2500000, "mr-IN");
      expect(formattedNumberMr).toBe("२५,००,०००");

      // 25 Lakhs in English-Indian format
      const formattedNumberEnIn = formatNumber(2500000, "en-IN");
      expect(formattedNumberEnIn).toBe("25,00,000");
    });
  });
});
