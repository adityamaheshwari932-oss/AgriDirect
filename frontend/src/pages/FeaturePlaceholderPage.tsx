import React from "react";
import { Link } from "react-router-dom";
import { Construction, ArrowLeft, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { PageContainer } from "../components/layout/PageContainer";

interface FeaturePlaceholderPageProps {
  title: string;
  description: string;
  stageBadge?: string;
  icon?: LucideIcon;
  returnTo?: string;
  returnLabel?: string;
}

export const FeaturePlaceholderPage: React.FC<FeaturePlaceholderPageProps> = ({
  title,
  description,
  stageBadge,
  icon: Icon = Construction,
  returnTo = "/dashboard",
  returnLabel,
}) => {
  const { t } = useTranslation(["common"]);

  const displayBadge = stageBadge || t("common:under_development", "Under Development");
  const displayReturnLabel = returnLabel || t("common:return_to_dashboard", "Return to Dashboard");

  return (
    <div className="flex-1 py-8">
      <PageContainer size="default">
        <div className="bg-card p-8 rounded-xl border border-border shadow-xs space-y-6 text-center">
          <div className="mx-auto w-14 h-14 rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <Icon className="w-7 h-7" aria-hidden="true" />
          </div>

          <div className="space-y-2">
            <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-primary-900 border border-border">
              {displayBadge}
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{title}</h1>
            <p className="text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
              {description}
            </p>
          </div>

          <div className="p-4 bg-secondary/50 rounded-lg text-xs text-muted-foreground max-w-lg mx-auto leading-relaxed border border-border">
            {t(
              "common:module_roadmap_notice",
              "This module is part of the planned AgriDirect implementation roadmap. Production business workflows and API endpoints for this feature will be integrated in subsequent development stages."
            )}
          </div>

          <div className="pt-2">
            <Link
              to={returnTo}
              className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:text-primary-800 transition-colors"
            >
              <ArrowLeft className="w-4 h-4 rtl:rotate-180" />
              <span>{displayReturnLabel}</span>
            </Link>
          </div>
        </div>
      </PageContainer>
    </div>
  );
};

