import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { X, ShieldAlert, Loader2, AlertCircle, Clock, CheckCircle2, FileText, User, ShoppingBag } from "lucide-react";
import { reportsApi } from "../../api/reports";
import { formatDate } from "../../utils/formatters";
import type { ReportItem, ReportStatus } from "../../types/reports";

interface ReportDetailModalProps {
  reportId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ReportDetailModal: React.FC<ReportDetailModalProps> = ({
  reportId,
  isOpen,
  onClose,
}) => {
  const { t, i18n } = useTranslation(["reports", "common"]);
  const [report, setReport] = useState<ReportItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const CATEGORY_LABELS: Record<string, string> = {
    payment: t("reports:cat_create_payment", "Payment Settlement Issue"),
    quantity_mismatch: t("reports:cat_create_quantity", "Quantity Mismatch"),
    quality_issue: t("reports:cat_create_quality", "Quality / Grading Misrepresentation"),
    fraud: t("reports:cat_create_fraud", "Fraudulent Activity"),
    harassment: t("reports:cat_create_harassment", "Harassment or Abusive Behavior"),
    other: t("reports:cat_create_other", "Other Safety Concern"),
  };

  useEffect(() => {
    if (!isOpen || !reportId) {
      setReport(null);
      setError(null);
      return;
    }

    let isMounted = true;
    const fetchReport = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await reportsApi.getReport(reportId);
        if (isMounted) {
          setReport(data);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg =
            err instanceof Error
              ? err.message
              : t("reports:error_load_detail", "Failed to load report details.");
          setError(msg);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void fetchReport();

    return () => {
      isMounted = false;
    };
  }, [isOpen, reportId, t]);

  if (!isOpen || !reportId) return null;

  const renderStatusBadge = (status: ReportStatus | string) => {
    switch (status) {
      case "open":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-700 border border-amber-500/20">
            <Clock className="w-3 h-3 text-amber-600" aria-hidden="true" />
            {t("reports:status_open", "Open Intake")}
          </span>
        );
      case "under_review":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-700 border border-blue-500/20">
            <Clock className="w-3 h-3 text-blue-600" aria-hidden="true" />
            {t("reports:status_under_review", "Under Investigation")}
          </span>
        );
      case "action_taken":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" aria-hidden="true" />
            {t("reports:status_action_taken", "Action Taken")}
          </span>
        );
      case "dismissed":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-muted-foreground border border-border">
            {t("reports:status_dismissed", "Dismissed")}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-foreground capitalize">
            {status}
          </span>
        );
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-report-detail-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-destructive" aria-hidden="true" />
            <div>
              <h2 id="modal-report-detail-title" className="text-base font-bold text-foreground">
                {t("reports:detail_modal_title", "Report Details")}
              </h2>
              <p className="text-[11px] text-muted-foreground">
                {t("reports:detail_modal_subtitle", "Platform Safety & Conduct Record")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label={t("common:actions.close_dialog", "Close dialog")}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-10 space-y-2">
              <Loader2 className="w-6 h-6 text-primary animate-spin" />
              <p className="text-xs text-muted-foreground">
                {t("reports:loading_detail", "Loading report details...")}
              </p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          ) : report ? (
            <>
              {/* Status and Category Summary */}
              <div className="flex items-center justify-between gap-2 p-3.5 rounded-xl bg-secondary/30 border border-border">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-0.5">
                    {t("reports:th_category", "Category")}
                  </span>
                  <span className="text-xs font-bold text-foreground">
                    {CATEGORY_LABELS[report.category] || report.category}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-0.5 text-end">
                    {t("reports:review_status", "Review Status")}
                  </span>
                  <div>{renderStatusBadge(report.status)}</div>
                </div>
              </div>

              {/* Related Reference Metadata */}
              {(report.reported_user_id || report.listing_id) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {report.reported_user_id && (
                    <div className="p-2.5 rounded-lg border border-border bg-card flex items-center gap-2">
                      <User className="w-4 h-4 text-primary shrink-0" />
                      <div className="truncate">
                        <span className="text-[10px] text-muted-foreground block">
                          {t("reports:reported_user", "Reported User")}
                        </span>
                        <span className="font-mono text-[11px] font-medium text-foreground truncate block">
                          {report.reported_user_id}
                        </span>
                      </div>
                    </div>
                  )}
                  {report.listing_id && (
                    <div className="p-2.5 rounded-lg border border-border bg-card flex items-center gap-2">
                      <ShoppingBag className="w-4 h-4 text-primary shrink-0" />
                      <div className="truncate">
                        <span className="text-[10px] text-muted-foreground block">
                          {t("reports:subject_listing", "Subject Listing")}
                        </span>
                        <span className="font-mono text-[11px] font-medium text-foreground truncate block">
                          {report.listing_id}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Description */}
              <div className="space-y-1.5">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" />
                  {t("reports:your_narrative", "Your Narrative")}
                </span>
                <div className="p-3.5 rounded-xl bg-card border border-border text-xs leading-relaxed text-foreground whitespace-pre-wrap break-words">
                  {report.description}
                </div>
              </div>

              {/* Moderator / Admin Resolution Notes */}
              <div className="space-y-1.5">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-primary" />
                  {t("reports:moderator_resolution", "Platform Moderator Resolution")}
                </span>
                {report.admin_notes ? (
                  <div className="p-3.5 rounded-xl bg-primary-50/40 border border-primary/20 text-xs text-foreground leading-relaxed">
                    <p className="font-semibold text-primary mb-1">
                      {t("reports:official_finding", "Official Finding & Action:")}
                    </p>
                    <p className="whitespace-pre-wrap">{report.admin_notes}</p>
                  </div>
                ) : (
                  <div className="p-3.5 rounded-xl bg-secondary/30 border border-border text-xs text-muted-foreground italic">
                    {t(
                      "reports:moderator_in_progress",
                      "Moderator investigation in progress. Resolution notes will appear here once reviewed."
                    )}
                  </div>
                )}
              </div>

              {/* Timestamps */}
              <div className="pt-2 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
                <span>
                  {t("reports:filed_on", "Filed: {{date}}", {
                    date: formatDate(report.created_at, i18n.language),
                  })}
                </span>
                <span>
                  {t("reports:last_updated_on", "Last Updated: {{date}}", {
                    date: formatDate(report.updated_at, i18n.language),
                  })}
                </span>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border flex justify-end bg-secondary/20">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition-colors"
          >
            {t("common:actions.close", "Close")}
          </button>
        </div>
      </div>
    </div>
  );
};
