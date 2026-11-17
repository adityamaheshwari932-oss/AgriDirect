import React from "react";
import { useTranslation } from "react-i18next";
import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title,
  message,
  onRetry,
  className = "",
}) => {
  const { t } = useTranslation(["errors", "common"]);
  const displayTitle = title ?? t("errors:load_failed", "Unable to load data");

  return (
    <div
      role="alert"
      className={`flex-1 flex flex-col items-center justify-center p-8 text-center min-h-[220px] rounded-lg border border-destructive/20 bg-destructive/5 ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center text-destructive mb-3">
        <AlertCircle className="w-6 h-6" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-semibold text-foreground tracking-tight">{displayTitle}</h3>
      <p className="text-xs text-muted-foreground mt-1 max-w-sm leading-relaxed">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-medium bg-secondary text-foreground hover:bg-secondary/80 border border-border transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
          <span>{t("errors:try_again", "Try Again")}</span>
        </button>
      )}
    </div>
  );
};

