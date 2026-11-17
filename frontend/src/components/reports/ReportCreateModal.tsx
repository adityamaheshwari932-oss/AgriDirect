import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X, ShieldAlert, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { reportsApi } from "../../api/reports";
import type { ReportCategory, ReportItem } from "../../types/reports";

interface ReportCreateModalProps {
  reportedUserId?: string;
  reportedUserName?: string;
  listingId?: string;
  listingTitle?: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (report: ReportItem) => void;
}

export const ReportCreateModal: React.FC<ReportCreateModalProps> = ({
  reportedUserId,
  reportedUserName,
  listingId,
  listingTitle,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["reports", "common", "errors", "validation"]);
  const [category, setCategory] = useState<ReportCategory>("fraud");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const REPORT_CATEGORIES: { value: ReportCategory; label: string; description: string }[] = [
    {
      value: "payment",
      label: t("reports:cat_create_payment", "Payment Settlement Issue"),
      description: t("reports:cat_desc_payment", "Payment default, unauthorized claims, or off-platform payment disputes."),
    },
    {
      value: "quantity_mismatch",
      label: t("reports:cat_create_quantity", "Quantity Mismatch"),
      description: t("reports:cat_desc_quantity", "Delivered volume differs from agreed contract quantity."),
    },
    {
      value: "quality_issue",
      label: t("reports:cat_create_quality", "Quality / Grading Misrepresentation"),
      description: t("reports:cat_desc_quality", "Produce delivered does not match agreed grade, standard, or description."),
    },
    {
      value: "fraud",
      label: t("reports:cat_create_fraud", "Fraudulent Activity"),
      description: t("reports:cat_desc_fraud", "Fake listings, forged identity, or financial fraud."),
    },
    {
      value: "harassment",
      label: t("reports:cat_create_harassment", "Harassment or Abusive Behavior"),
      description: t("reports:cat_desc_harassment", "Threatening, offensive, or unprofessional messages."),
    },
    {
      value: "other",
      label: t("reports:cat_create_other", "Other Safety Concern"),
      description: t("reports:cat_desc_other", "Any other issue that threatens marketplace integrity."),
    },
  ];

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (description.trim().length < 5) {
      setError(
        t("reports:error_desc_min", "Please provide a description of at least 5 characters.")
      );
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const report = await reportsApi.createReport({
        reported_user_id: reportedUserId || null,
        listing_id: listingId || null,
        category,
        description: description.trim(),
      });
      setIsSubmitted(true);
      if (onSuccess) onSuccess(report);
      setTimeout(() => {
        setIsSubmitted(false);
        onClose();
      }, 1500);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("reports:error_submit_failed", "Failed to file report.");
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
      <div className="relative w-full max-w-lg bg-card border border-border rounded-xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-destructive/5">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-destructive/10 flex items-center justify-center text-destructive">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-foreground">
                {t("reports:create_modal_title", "File Safety Report")}
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t(
                  "reports:create_modal_subtitle",
                  "Confidential report submitted to AgriDirect Trust & Safety."
                )}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            aria-label={t("common:actions.close", "Close")}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {isSubmitted ? (
          <div className="p-8 text-center space-y-3">
            <CheckCircle2 className="w-12 h-12 text-primary mx-auto animate-in zoom-in" />
            <h3 className="text-sm font-bold text-foreground">
              {t("reports:submitted_title", "Report Submitted")}
            </h3>
            <p className="text-xs text-muted-foreground max-w-xs mx-auto">
              {t(
                "reports:submitted_desc",
                "Thank you for keeping AgriDirect safe. Our Trust & Safety team will review the incident."
              )}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="p-3 text-xs bg-destructive/10 border border-destructive/20 text-destructive rounded-lg flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Target context banner */}
            {(reportedUserName || listingTitle) && (
              <div className="p-3 bg-secondary/30 rounded-lg border border-border text-xs space-y-1">
                {reportedUserName && (
                  <div>
                    <span className="text-muted-foreground">
                      {t("reports:reported_user_label", "Reported User:")}{" "}
                    </span>
                    <span className="font-semibold text-foreground">{reportedUserName}</span>
                  </div>
                )}
                {listingTitle && (
                  <div>
                    <span className="text-muted-foreground">
                      {t("reports:related_listing_label", "Related Listing:")}{" "}
                    </span>
                    <span className="font-semibold text-foreground">{listingTitle}</span>
                  </div>
                )}
              </div>
            )}

            {/* Category Select */}
            <div className="space-y-1">
              <label htmlFor="report_category" className="block text-xs font-medium text-foreground">
                {t("reports:violation_category_label", "Violation Category")}{" "}
                <span className="text-destructive">*</span>
              </label>
              <select
                id="report_category"
                value={category}
                onChange={(e) => setCategory(e.target.value as ReportCategory)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {REPORT_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-muted-foreground">
                {REPORT_CATEGORIES.find((c) => c.value === category)?.description}
              </p>
            </div>

            {/* Description */}
            <div className="space-y-1">
              <div className="flex justify-between items-center text-xs">
                <label htmlFor="report_description" className="font-medium text-foreground">
                  {t("reports:incident_desc_label", "Description of Incident")}{" "}
                  <span className="text-destructive">*</span>
                </label>
                <span className="text-muted-foreground text-[11px]">{description.length}/2000</span>
              </div>
              <textarea
                id="report_description"
                rows={5}
                required
                maxLength={2000}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t(
                  "reports:incident_desc_placeholder",
                  "Explain what occurred with specific dates, message excerpts, or delivery discrepancies..."
                )}
                className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* Footer Buttons */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 text-xs font-medium rounded-lg border border-border bg-background hover:bg-secondary text-foreground transition-colors"
              >
                {t("common:actions.cancel", "Cancel")}
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50 transition-colors shadow-sm"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    {t("common:status.submitting", "Submitting...")}
                  </>
                ) : (
                  <>
                    <ShieldAlert className="w-3.5 h-3.5" />
                    {t("reports:submit_report_button", "Submit Report")}
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
