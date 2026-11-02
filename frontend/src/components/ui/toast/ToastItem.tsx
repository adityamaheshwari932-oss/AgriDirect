import React from "react";
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from "lucide-react";

export type ToastVariant = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  title?: string;
  message: string;
  variant: ToastVariant;
  duration?: number;
}

interface ToastItemProps {
  toast: Toast;
  onDismiss: (id: string) => void;
}

const VARIANT_CONFIG: Record<
  ToastVariant,
  {
    icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
    containerClass: string;
    iconClass: string;
    titleClass: string;
    role: "alert" | "status";
    ariaLive: "assertive" | "polite";
  }
> = {
  success: {
    icon: CheckCircle2,
    containerClass: "bg-card border-emerald-500/30 text-card-foreground shadow-md",
    iconClass: "text-emerald-600 bg-emerald-50",
    titleClass: "text-emerald-950 font-semibold",
    role: "status",
    ariaLive: "polite",
  },
  error: {
    icon: AlertCircle,
    containerClass: "bg-card border-destructive/40 text-card-foreground shadow-md",
    iconClass: "text-destructive bg-destructive/10",
    titleClass: "text-destructive font-semibold",
    role: "alert",
    ariaLive: "assertive",
  },
  warning: {
    icon: AlertTriangle,
    containerClass: "bg-card border-amber-500/40 text-card-foreground shadow-md",
    iconClass: "text-amber-600 bg-amber-50",
    titleClass: "text-amber-950 font-semibold",
    role: "alert",
    ariaLive: "assertive",
  },
  info: {
    icon: Info,
    containerClass: "bg-card border-blue-500/30 text-card-foreground shadow-md",
    iconClass: "text-blue-600 bg-blue-50",
    titleClass: "text-blue-950 font-semibold",
    role: "status",
    ariaLive: "polite",
  },
};

export const ToastItem: React.FC<ToastItemProps> = ({ toast, onDismiss }) => {
  const config = VARIANT_CONFIG[toast.variant] || VARIANT_CONFIG.info;
  const Icon = config.icon;

  return (
    <div
      role={config.role}
      aria-live={config.ariaLive}
      className={`pointer-events-auto flex items-start gap-3 p-4 rounded-lg border transition-all duration-200 ${config.containerClass}`}
      data-testid={`toast-${toast.variant}`}
    >
      <div className={`p-1 rounded-md shrink-0 ${config.iconClass}`}>
        <Icon className="w-4 h-4" aria-hidden="true" />
      </div>

      <div className="flex-1 min-w-0 pt-0.5">
        {toast.title && (
          <h4 className={`text-xs ${config.titleClass} mb-0.5 leading-tight`}>{toast.title}</h4>
        )}
        <p className="text-xs text-muted-foreground leading-relaxed break-words">{toast.message}</p>
      </div>

      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        className="shrink-0 p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
        aria-label="Dismiss notification"
      >
        <X className="w-3.5 h-3.5" aria-hidden="true" />
      </button>
    </div>
  );
};

