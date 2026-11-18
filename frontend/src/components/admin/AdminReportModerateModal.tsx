import React, { useEffect, useState } from "react";
import { X, ShieldAlert, Loader2, AlertCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { adminApi } from "../../api/admin";
import type { ReportItem, ReportStatus } from "../../types/reports";
import { useToast } from "../ui/toast";

interface AdminReportModerateModalProps {
  report: ReportItem | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const AdminReportModerateModal: React.FC<AdminReportModerateModalProps> = ({
  report,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["admin", "reports", "common", "errors"]);
  const { success: toastSuccess, error: toastError } = useToast();

  const [status, setStatus] = useState<ReportStatus>("under_review");
  const [adminNotes, setAdminNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (report) {
      setStatus(
        report.status === "open"
          ? "under_review"
          : (report.status as ReportStatus)
      );
      setAdminNotes(report.admin_notes || "");
      setErrorMessage(null);
    }
  }, [report, isOpen]);

  if (!isOpen || !report) return null;

  const isValidNotes = adminNotes.trim().length >= 5 && adminNotes.trim().length <= 2000;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isValidNotes) {
      setErrorMessage(
        t(
          "admin:report_notes_min_length",
          "Administrative investigation notes must be between 5 and 2000 characters."
        )
      );
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await adminApi.moderateReport(report.id, {
        status,
        admin_notes: adminNotes.trim(),
      });
      toastSuccess(
        t("admin:toast_report_marked", `Report marked as '${status}'.`, { status }),
        t("admin:report_moderated_title", "Report Moderated")
      );
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("admin:moderate_report_failed", "Failed to moderate report.");
      setErrorMessage(msg);
      toastError(msg, t("admin:moderation_error", "Moderation Error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-report-moderate-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-primary" aria-hidden="true" />
            <div>
              <h2 id="modal-report-moderate-title" className="text-base font-bold text-foreground">
                {t("admin:moderate_safety_report_title", "Moderate Safety Report")}
              </h2>
              <p className="text-[11px] text-muted-foreground">
                {t("admin:record_findings_subtitle", "Record Findings & Enforcement Decision")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            aria-label={t("common:close_dialog", "Close dialog")}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMessage && (
            <div
              role="alert"
              className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Report Summary Card */}
          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-bold text-foreground capitalize">
                {t("admin:category_label", "Category")}: {report.category}
              </span>
              <span className="font-semibold text-muted-foreground capitalize">
                {t("admin:current_label", "Current")}: {report.status}
              </span>
            </div>
            <p className="text-muted-foreground italic line-clamp-3">"{report.description}"</p>
          </div>

          {/* Resolution Status */}
          <div className="space-y-1.5">
            <label htmlFor="report-target-status" className="block text-xs font-bold text-foreground">
              {t("admin:moderation_status_label", "Moderation Status")}
            </label>
            <select
              id="report-target-status"
              value={status}
              disabled={isSubmitting}
              onChange={(e) => setStatus(e.target.value as ReportStatus)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            >
              <option value="under_review">
                {t("admin:report_opt_under_review", "Under Review (Investigation in progress)")}
              </option>
              <option value="action_taken">
                {t("admin:report_opt_action_taken", "Action Taken (Enforcement action applied)")}
              </option>
              <option value="dismissed">
                {t("admin:report_opt_dismissed", "Dismissed (No violation found / grievance closed)")}
              </option>
            </select>
          </div>

          {/* Mandatory Admin Notes */}
          <div className="space-y-1.5">
            <label htmlFor="report-admin-notes" className="block text-xs font-bold text-foreground">
              {t("admin:admin_findings_notes_label", "Administrative Findings & Notes")} <span className="text-destructive">*</span>
            </label>
            <textarea
              id="report-admin-notes"
              rows={4}
              value={adminNotes}
              disabled={isSubmitting}
              onChange={(e) => setAdminNotes(e.target.value)}
              placeholder={t(
                "admin:report_notes_placeholder",
                "Record investigation findings, evidence checked, and justification for this status..."
              )}
              className="w-full p-3 text-xs rounded-xl border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 resize-none"
            />
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>{t("admin:min_5_chars", "Min 5 characters")}</span>
              <span className={adminNotes.trim().length < 5 ? "text-amber-600 font-medium" : "text-muted-foreground"}>
                {adminNotes.trim().length} / 2000
              </span>
            </div>
          </div>

          {/* Footer */}
          <div className="pt-2 border-t border-border flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl bg-secondary text-foreground hover:bg-secondary/80 text-xs font-semibold border border-border transition-colors disabled:opacity-50"
            >
              {t("common:cancel", "Cancel")}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !isValidNotes}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{t("admin:save_resolution_btn", "Save Resolution")}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

