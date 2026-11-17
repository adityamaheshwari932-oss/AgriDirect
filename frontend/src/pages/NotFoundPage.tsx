import React from "react";
import { Link } from "react-router-dom";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { useTranslation } from "react-i18next";
import { PageContainer } from "../components/layout/PageContainer";

export const NotFoundPage: React.FC = () => {
  const { t } = useTranslation(["common"]);

  return (
    <div className="flex-1 flex items-center justify-center py-16 px-4">
      <PageContainer size="sm" className="text-center space-y-6">
        <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mx-auto text-muted-foreground">
          <AlertCircle className="w-8 h-8" aria-hidden="true" />
        </div>
        <div className="space-y-2">
          <h1 className="text-3xl font-extrabold text-foreground tracking-tight">
            {t("common:not_found_title", "404 — Page Not Found")}
          </h1>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            {t("common:not_found_description", "The page you requested does not exist or may have been moved.")}
          </p>
        </div>
        <div>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <ArrowLeft className="w-4 h-4 rtl:rotate-180" />
            <span>{t("common:return_to_marketplace", "Return to Marketplace Overview")}</span>
          </Link>
        </div>
      </PageContainer>
    </div>
  );
};

