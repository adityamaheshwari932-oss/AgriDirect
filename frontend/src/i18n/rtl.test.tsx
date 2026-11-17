import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { isRTL, LANGUAGE_STORAGE_KEY } from "./languages";
import { setLanguage, syncDocumentAttributes } from "./index";
import { LanguageSelector } from "../components/ui/LanguageSelector";
import { MessageBubble } from "../components/chat/MessageBubble";
import { NegotiationHistoryTimeline } from "../components/offers/NegotiationHistoryTimeline";
import { ForbiddenState } from "../components/ui/states/ForbiddenState";
import { NotFoundPage } from "../pages/NotFoundPage";
import { ToastContainer } from "../components/ui/toast/ToastContainer";

describe("Stage 4: Complete Right-to-Left (RTL) Layout & Direction Support", () => {
  beforeEach(async () => {
    localStorage.clear();
    await setLanguage("en");
  });

  afterEach(async () => {
    await setLanguage("en");
  });

  describe("Direction Helper Function: isRTL()", () => {
    it("identifies Urdu (ur), Sindhi (sd), and Kashmiri (ks) as RTL", () => {
      expect(isRTL("ur")).toBe(true);
      expect(isRTL("sd")).toBe(true);
      expect(isRTL("ks")).toBe(true);
    });

    it("identifies English and all 19 other constitutional Indic languages as LTR", () => {
      const ltrCodes = [
        "en", "hi", "mr", "gu", "bn", "ta", "te", "kn", "pa", "ml",
        "as", "or", "sa", "ne", "kok", "mai", "doi", "brx", "mni", "sat",
      ];
      for (const code of ltrCodes) {
        expect(isRTL(code)).toBe(false);
      }
    });

    it("falls back to document language direction when called without arguments", () => {
      document.documentElement.lang = "ur";
      expect(isRTL()).toBe(true);

      document.documentElement.lang = "en";
      expect(isRTL()).toBe(false);
    });

    it("gracefully falls back to false (LTR) for invalid or null language codes", () => {
      expect(isRTL(null)).toBe(false);
      expect(isRTL(undefined)).toBe(false);
      expect(isRTL("invalid_code_xyz")).toBe(false);
    });
  });

  describe("Document Attribute Synchronization: syncDocumentAttributes()", () => {
    it("sets document dir='rtl' for RTL languages", () => {
      syncDocumentAttributes("ur");
      expect(document.documentElement.lang).toBe("ur");
      expect(document.documentElement.dir).toBe("rtl");

      syncDocumentAttributes("sd");
      expect(document.documentElement.lang).toBe("sd");
      expect(document.documentElement.dir).toBe("rtl");

      syncDocumentAttributes("ks");
      expect(document.documentElement.lang).toBe("ks");
      expect(document.documentElement.dir).toBe("rtl");
    });

    it("restores document dir='ltr' when switching back to LTR languages", () => {
      syncDocumentAttributes("ur");
      expect(document.documentElement.dir).toBe("rtl");

      syncDocumentAttributes("en");
      expect(document.documentElement.lang).toBe("en");
      expect(document.documentElement.dir).toBe("ltr");

      syncDocumentAttributes("hi");
      expect(document.documentElement.lang).toBe("hi");
      expect(document.documentElement.dir).toBe("ltr");
    });

    it("persists language selection in localStorage", () => {
      syncDocumentAttributes("ur");
      expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("ur");

      syncDocumentAttributes("en");
      expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("en");
    });

    it("falls back to default language 'en' and dir 'ltr' on invalid inputs", () => {
      syncDocumentAttributes("unknown-garbage");
      expect(document.documentElement.lang).toBe("en");
      expect(document.documentElement.dir).toBe("ltr");
    });
  });

  describe("Dynamic Language Switching: setLanguage()", () => {
    it("dynamically switches to Urdu, sets RTL, and switches back to English", async () => {
      await setLanguage("ur");
      expect(document.documentElement.dir).toBe("rtl");
      expect(document.documentElement.lang).toBe("ur");

      await setLanguage("en");
      expect(document.documentElement.dir).toBe("ltr");
      expect(document.documentElement.lang).toBe("en");
    });

    it("switching between different RTL languages preserves dir='rtl' seamlessly", async () => {
      await setLanguage("ur");
      expect(document.documentElement.dir).toBe("rtl");
      expect(document.documentElement.lang).toBe("ur");

      await setLanguage("sd");
      expect(document.documentElement.dir).toBe("rtl");
      expect(document.documentElement.lang).toBe("sd");

      await setLanguage("ks");
      expect(document.documentElement.dir).toBe("rtl");
      expect(document.documentElement.lang).toBe("ks");
    });
  });

  describe("RTL Component Layout & Mirroring Verification", () => {
    it("renders LanguageSelector with direction-aware placement classes", () => {
      const { container } = render(<LanguageSelector variant="compact" />);
      const button = container.querySelector("button");
      expect(button).not.toBeNull();
      fireEvent.click(button!);

      const popover = container.querySelector(".end-0");
      expect(popover).not.toBeNull();
      const input = container.querySelector("input");
      expect(input?.className).toContain("ps-8");
      expect(input?.className).toContain("pe-7");
    });

    it("renders MessageBubble with dir='auto' and logical corner classes", () => {
      const message = {
        id: "msg-123",
        conversation_id: "conv-1",
        sender_id: "user-1",
        recipient_id: "user-2",
        message_type: "text",
        content: "سلام، میں 50 ٹن گندم خریدنا چاہتا ہوں",
        created_at: new Date().toISOString(),
        is_read: false,
      };

      const { container } = render(
        <MessageBubble message={message as any} isCurrentUser={false} />
      );

      const content = container.querySelector('[dir="auto"]');
      expect(content).not.toBeNull();
      expect(content?.textContent).toContain("سلام");

      // Verify timestamp uses bdi-isolate
      const timestamp = container.querySelector(".bdi-isolate");
      expect(timestamp).not.toBeNull();
    });

    it("renders NegotiationHistoryTimeline with logical start coordinates and rotated arrow", () => {
      const history = [
        {
          id: "off-1",
          offer_number: "OFF-101",
          status: "countered",
          sender: { name: "John Buyer", role: "buyer" },
          quantity: 100,
          unit_price: 25,
          unit: "kg",
          created_at: new Date().toISOString(),
        },
      ];

      const { container } = render(
        <NegotiationHistoryTimeline history={history as any} currentOfferId="off-1" />
      );

      // Verify logical start coordinates on timeline line
      const timelineLine = container.querySelector(".ps-6");
      expect(timelineLine).not.toBeNull();

      // Verify Countered badge icon has rtl:rotate-180
      const rotatedIcon = container.querySelector(".rtl\\:rotate-180");
      expect(rotatedIcon).not.toBeNull();
    });

    it("renders ForbiddenState with directional back arrow having rtl:rotate-180", () => {
      const { container } = render(
        <MemoryRouter>
          <ForbiddenState />
        </MemoryRouter>
      );

      const rotatedIcon = container.querySelector(".rtl\\:rotate-180");
      expect(rotatedIcon).not.toBeNull();
    });

    it("renders NotFoundPage with directional return arrow having rtl:rotate-180", () => {
      const { container } = render(
        <MemoryRouter>
          <NotFoundPage />
        </MemoryRouter>
      );

      const rotatedIcon = container.querySelector(".rtl\\:rotate-180");
      expect(rotatedIcon).not.toBeNull();
    });

    it("renders ToastContainer using logical end-4 positioning", () => {
      const dummyToast = {
        id: "t-1",
        variant: "success" as const,
        title: "Order Confirmed",
        message: "Order has been registered",
        duration: 5000,
      };

      const { container } = render(
        <ToastContainer toasts={[dummyToast]} onDismiss={() => {}} />
      );

      const toastWrapper = container.querySelector(".end-4");
      expect(toastWrapper).not.toBeNull();
    });
  });
});
