import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { LanguageSelector } from "./LanguageSelector";
import { setLanguage } from "../../i18n";

describe("LanguageSelector Component", () => {
  beforeEach(async () => {
    localStorage.clear();
    await setLanguage("en");
  });

  it("renders trigger button displaying the active language name and globe icon", () => {
    render(<LanguageSelector />);

    const button = screen.getByRole("button", { name: /Language selector/i });
    expect(button).toBeInTheDocument();
    expect(screen.getByText("English")).toBeInTheDocument();
  });

  it("opens the dropdown dialog and displays all 23 languages on click", () => {
    render(<LanguageSelector />);

    const button = screen.getByRole("button", { name: /Language selector/i });
    fireEvent.click(button);

    // Dialog title
    expect(screen.getByText(/Select Language \/ भाषा चुनें/i)).toBeInTheDocument();

    // Check prominent native scripts are displayed
    expect(screen.getByText("हिन्दी")).toBeInTheDocument();
    expect(screen.getByText("मराठी")).toBeInTheDocument();
    expect(screen.getByText("ગુજરાતી")).toBeInTheDocument();
    expect(screen.getByText("বাংলা")).toBeInTheDocument();
    expect(screen.getByText("தமிழ்")).toBeInTheDocument();
    expect(screen.getByText("తెలుగు")).toBeInTheDocument();
    expect(screen.getByText("ಕನ್ನಡ")).toBeInTheDocument();
    expect(screen.getByText("ਪੰਜਾਬੀ")).toBeInTheDocument();
    expect(screen.getByText("മലയാളം")).toBeInTheDocument();
    expect(screen.getByText("অসমীয়া")).toBeInTheDocument();
    expect(screen.getByText("ଓଡ଼ିଆ")).toBeInTheDocument();
    expect(screen.getByText("संस्कृतम्")).toBeInTheDocument();
    expect(screen.getByText("नेपाली")).toBeInTheDocument();
    expect(screen.getByText("कोंकणी")).toBeInTheDocument();
    expect(screen.getByText("मैथिली")).toBeInTheDocument();
    expect(screen.getByText("डोगरी")).toBeInTheDocument();
    expect(screen.getByText("बड़ो")).toBeInTheDocument();
    expect(screen.getByText("ꯃꯩꯇꯩꯂꯣꯟ")).toBeInTheDocument();
    expect(screen.getByText("ᱥᱟᱱᱛᱟᱲᱤ")).toBeInTheDocument();
    expect(screen.getByText("سنڌي")).toBeInTheDocument();
    expect(screen.getByText("اُردُو")).toBeInTheDocument();
    expect(screen.getByText("کٲشُر")).toBeInTheDocument();
  });

  it("filters language options when typing in the search box", () => {
    render(<LanguageSelector />);

    fireEvent.click(screen.getByRole("button", { name: /Language selector/i }));

    const searchInput = screen.getByPlaceholderText(/Search language \/ भाषा खोजें.../i);

    // Search by English name
    fireEvent.change(searchInput, { target: { value: "Marathi" } });
    expect(screen.getByText("मराठी")).toBeInTheDocument();
    expect(screen.queryByText("ગુજરાતી")).not.toBeInTheDocument();

    // Search by Native script
    fireEvent.change(searchInput, { target: { value: "தமிழ்" } });
    expect(screen.getByText("தமிழ்")).toBeInTheDocument();
    expect(screen.queryByText("मराठी")).not.toBeInTheDocument();

    // Search with no results
    fireEvent.change(searchInput, { target: { value: "nonexistentlanguage" } });
    expect(screen.getByText(/No matching language found/i)).toBeInTheDocument();
  });

  it("shows RTL badge for Urdu, Sindhi, and Kashmiri", () => {
    render(<LanguageSelector />);

    fireEvent.click(screen.getByRole("button", { name: /Language selector/i }));

    const rtlBadges = screen.getAllByText("RTL");
    expect(rtlBadges.length).toBe(3);
  });

  it("switches active language when a language option is clicked and closes dropdown", async () => {
    render(<LanguageSelector />);

    fireEvent.click(screen.getByRole("button", { name: /Language selector/i }));

    // Click on Hindi option
    const hindiOption = screen.getByText("हिन्दी");
    fireEvent.click(hindiOption);

    await waitFor(() => {
      // Dropdown dialog should close
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      // Document lang and dir should be updated
      expect(document.documentElement.lang).toBe("hi");
      expect(document.documentElement.dir).toBe("ltr");
    });
  });

  it("closes dialog on Escape key press", () => {
    render(<LanguageSelector />);

    fireEvent.click(screen.getByRole("button", { name: /Language selector/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes dialog on close button click", () => {
    render(<LanguageSelector />);

    fireEvent.click(screen.getByRole("button", { name: /Language selector/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    const closeButton = screen.getByLabelText(/Close language selector/i);
    fireEvent.click(closeButton);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
