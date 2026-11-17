import React from "react";
import { useTranslation } from "react-i18next";
import { ShieldAlert, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

interface ForbiddenStateProps {
  title?: string;
  message?: string;
  returnTo?: string;
  returnLabel?: string;
  className?: string;
}

export const ForbiddenState: React.FC<ForbiddenStateProps> = ({
  title,
  message,
  returnTo = "/dashboard",
  returnLabel,
  className = "",
}) => {
  const { t } = useTranslation("errors");
  const displayTitle = title ?? t("forbidden_title", "Access Restricted");
  const displayMessage =
    message ??
    t(
      "forbidden_message",
      "You do not have sufficient permissions to access this feature or perform this operation."
    );
  const displayReturnLabel = returnLabel ?? t("return_to_dashboard", "Return to Dashboard");

  return (
    <div
      role="alert"
      className={`flex-1 flex flex-col items-center justify-center p-8 text-center min-h-[240px] rounded-lg border border-amber-500/20 bg-amber-500/5 ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-600 mb-3">
        <ShieldAlert className="w-6 h-6" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-semibold text-foreground tracking-tight">{displayTitle}</h3>
      <p className="text-xs text-muted-foreground mt-1 max-w-md leading-relaxed">{displayMessage}</p>
      <div className="mt-4">
        <Link
          to={returnTo}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary-700 transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
        >
          <ArrowLeft className="w-3.5 h-3.5 rtl:rotate-180" aria-hidden="true" />
          <span>{displayReturnLabel}</span>
        </Link>
      </div>
    </div>
  );
};

