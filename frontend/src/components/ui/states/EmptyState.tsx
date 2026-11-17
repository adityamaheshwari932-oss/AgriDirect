import React from "react";
import { Inbox } from "lucide-react";
import { useTranslation } from "react-i18next";

interface EmptyStateProps {
  icon?: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  actionLabel,
  onAction,
  className = "",
}) => {
  const { t } = useTranslation("common");
  const resolvedTitle = title || t("labels.no_results");

  return (
    <div
      className={`flex-1 flex flex-col items-center justify-center p-8 text-center min-h-[220px] rounded-lg border border-dashed border-border bg-card/50 ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center text-muted-foreground mb-3">
        <Icon className="w-6 h-6" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-semibold text-foreground tracking-tight">{resolvedTitle}</h3>
      {description && (
        <p className="text-xs text-muted-foreground mt-1 max-w-sm leading-relaxed">
          {description}
        </p>
      )}
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 inline-flex items-center justify-center px-3.5 py-1.5 rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary-700 transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};
