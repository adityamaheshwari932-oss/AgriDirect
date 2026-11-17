import React from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Sprout } from "lucide-react";
import { PageContainer } from "./PageContainer";

export const PublicFooter: React.FC = () => {
  const { t } = useTranslation("common");

  return (
    <footer className="border-t border-border bg-card py-10 text-muted-foreground transition-colors">
      <PageContainer>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground">
                <Sprout className="w-5 h-5" aria-hidden="true" />
              </div>
              <span className="text-base font-bold text-foreground">
                {t("app.name", "AgriDirect")}
              </span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-md">
              {t(
                "footer.about",
                "A transparent B2B agricultural marketplace connecting verified farmers directly with commercial buyers, wholesale procurers, and food enterprises without intermediaries."
              )}
            </p>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">
              {t("footer.marketplace", "Marketplace")}
            </h4>
            <ul className="text-sm space-y-2">
              <li>
                <Link to="/" className="hover:text-foreground transition-colors">
                  {t("nav.overview", "Overview")}
                </Link>
              </li>
              <li>
                <Link to="/register/farmer" className="hover:text-foreground transition-colors">
                  {t("footer.farmer_registration", "Farmer Registration")}
                </Link>
              </li>
              <li>
                <Link to="/register/buyer" className="hover:text-foreground transition-colors">
                  {t("footer.buyer_registration", "Commercial Buyer Registration")}
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">
              {t("footer.account", "Account")}
            </h4>
            <ul className="text-sm space-y-2">
              <li>
                <Link to="/login" className="hover:text-foreground transition-colors">
                  {t("nav.sign_in", "Sign In")}
                </Link>
              </li>
              <li>
                <Link to="/register" className="hover:text-foreground transition-colors">
                  {t("footer.choose_role", "Choose Role")}
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-border pt-6 text-xs text-center text-muted-foreground space-y-2">
          <p>
            {t("footer.copyright", "© {{year}} AgriDirect Marketplace. All rights reserved.", {
              year: new Date().getFullYear(),
            })}
          </p>
          <p className="text-[11px] text-muted-foreground/80 max-w-2xl mx-auto leading-relaxed">
            {t(
              "footer.disclaimer",
              "AgriDirect facilitates direct commercial trade. It does not own produce, process financial payments, or manage logistics."
            )}
          </p>
        </div>
      </PageContainer>
    </footer>
  );
};
