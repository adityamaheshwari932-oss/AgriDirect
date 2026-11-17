import React, { useState, useRef, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Globe, Check, Search, X, ChevronDown } from "lucide-react";
import {
  SUPPORTED_LANGUAGES,
  getLanguage,
  type LanguageCode,
  type Language,
} from "../../i18n";
import { setLanguage } from "../../i18n";

export interface LanguageSelectorProps {
  /** Visual variant: 'header' for top navigation, 'compact' for mobile/sub-bars */
  variant?: "header" | "compact";
  /** Optional custom CSS classes for the container */
  className?: string;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  variant = "header",
  className = "",
}) => {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const currentLangCode = (i18n.language || "en") as LanguageCode;
  const currentLanguage = getLanguage(currentLangCode);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Focus search input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
    } else {
      setSearchQuery("");
    }
  }, [isOpen]);

  // Keyboard navigation: Escape key closes the dropdown
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  const filteredLanguages = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return SUPPORTED_LANGUAGES;
    return SUPPORTED_LANGUAGES.filter(
      (lang) =>
        lang.name.toLowerCase().includes(q) ||
        lang.englishName.toLowerCase().includes(q) ||
        lang.code.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  const handleSelectLanguage = async (code: LanguageCode) => {
    await setLanguage(code);
    setIsOpen(false);
  };

  return (
    <div
      ref={containerRef}
      className={`relative inline-block text-start ${className}`}
      onKeyDown={handleKeyDown}
    >
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-label="Language selector. Current language: "
        className={`inline-flex items-center gap-2 rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-primary ${
          variant === "header"
            ? "px-3 py-1.5 text-xs font-semibold bg-secondary/80 hover:bg-secondary text-foreground border border-border shadow-xs"
            : "px-2.5 py-1 text-[11px] font-medium bg-card hover:bg-secondary text-foreground border border-border"
        }`}
      >
        <Globe className="w-3.5 h-3.5 text-primary shrink-0" aria-hidden="true" />
        <span className="truncate max-w-[120px] sm:max-w-none font-medium">
          {currentLanguage.name}
        </span>
        <span className="text-[10px] text-muted-foreground hidden sm:inline">
          ({currentLanguage.englishName})
        </span>
        <ChevronDown
          className={`w-3 h-3 text-muted-foreground transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        />
      </button>

      {/* Popover Dropdown Panel */}
      {isOpen && (
        <div
          role="dialog"
          aria-label="Language selection options"
          className="absolute end-0 mt-2 w-80 sm:w-96 rounded-2xl bg-card border border-border shadow-2xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150 text-foreground"
        >
          {/* Header */}
          <div className="p-3.5 border-b border-border bg-secondary/40">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h3 className="text-xs font-bold text-foreground">
                  Select Language / भाषा चुनें
                </h3>
                <p className="text-[10px] text-muted-foreground">
                  23 Constitutionally Recognized Languages
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                aria-label="Close language selector"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>

            {/* Search Input */}
            <div className="relative">
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search language / भाषा खोजें..."
                className="w-full rounded-xl border border-border bg-card ps-8 pe-7 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label="Search language"
              />
              <Search
                className="w-3.5 h-3.5 text-muted-foreground absolute start-2.5 top-2.5"
                aria-hidden="true"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute end-2 top-2 text-muted-foreground hover:text-foreground p-0.5"
                  aria-label="Clear search"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          {/* Languages Grid/List */}
          <div className="max-h-72 overflow-y-auto p-2 divide-y divide-border/40">
            {filteredLanguages.length === 0 ? (
              <div className="py-6 text-center text-xs text-muted-foreground">
                No matching language found / कोई भाषा नहीं मिली
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
                {filteredLanguages.map((lang: Language) => {
                  const isSelected = lang.code === currentLangCode;
                  return (
                    <button
                      key={lang.code}
                      type="button"
                      onClick={() => void handleSelectLanguage(lang.code)}
                      className={`w-full text-start p-2 rounded-xl transition-all flex items-center justify-between group ${
                        isSelected
                          ? "bg-primary/10 border border-primary/30 text-primary font-bold shadow-xs"
                          : "hover:bg-secondary text-foreground border border-transparent"
                      }`}
                    >
                      <div className="min-w-0 pe-2">
                        {/* Native Display Name (NEVER translated to English) */}
                        <div
                          className="text-sm font-semibold truncate leading-tight"
                          dir={lang.dir}
                        >
                          {lang.name}
                        </div>
                        {/* English Subtitle */}
                        <div className="text-[10px] text-muted-foreground group-hover:text-foreground/80 transition-colors">
                          {lang.englishName}
                          {lang.dir === "rtl" && (
                            <span className="ms-1 px-1 py-0.2 rounded bg-amber-500/10 text-amber-700 text-[9px] font-mono">
                              RTL
                            </span>
                          )}
                        </div>
                      </div>

                      {isSelected && (
                        <Check
                          className="w-4 h-4 text-primary shrink-0 ms-1"
                          aria-hidden="true"
                        />
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer Persistence Notice */}
          <div className="px-3 py-2 border-t border-border bg-secondary/30 text-[10px] text-muted-foreground flex items-center justify-between">
            <span>AgriDirect Multilingual Registry</span>
            <span className="font-mono text-[9px] text-emerald-700 font-semibold">
              Saved automatically
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
