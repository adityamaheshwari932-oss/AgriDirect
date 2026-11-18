import React, { useEffect, useState } from "react";
import { X, AlertTriangle, Loader2, AlertCircle, FileText, IndianRupee } from "lucide-react";
import { useTranslation } from "react-i18next";
import { adminApi } from "../../api/admin";
import type { AdminPaymentComplaintDetail } from "../../types/admin";
import { useToast } from "../ui/toast";

interface AdminDisputeModerateModalProps {
  complaintId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const AdminDisputeModerateModal: React.FC<AdminDisputeModerateModalProps> = ({
  complaintId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["admin", "disputes", "payments", "common", "errors"]);
  const { success: toastSuccess, error: toastError } = useToast();

  const [detail, setDetail] = useState<AdminPaymentComplaintDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [status, setStatus] = useState<"under_review" | "resolved" | "dismissed">("under_review");
  const [resolutionNotes, setResolutionNotes] = useState("");

  useEffect(() => {
    if (!isOpen || !complaintId) {
      setDetail(null);
      setErrorMessage(null);
      return;
    }

    let isMounted = true;
    const fetchDetail = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const data = await adminApi.getPaymentComplaintDetail(complaintId);
        if (isMounted) {
          setDetail(data);
          const currentStatus = data.complaint.status;
          if (currentStatus === "resolved" || currentStatus === "dismissed" || currentStatus === "under_review") {
            setStatus(currentStatus);
          } else {
            setStatus("under_review");
          }
          setResolutionNotes(data.complaint.admin_resolution_notes || "");
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : t("admin:load_dispute_failed", "Failed to load payment complaint detail.");
          setErrorMessage(msg);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void fetchDetail();

    return () => {
      isMounted = false;
    };
  }, [isOpen, complaintId, t]);

  if (!isOpen || !complaintId) return null;

  const isTerminal = status === "resolved" || status === "dismissed";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isTerminal && resolutionNotes.trim().length < 5) {
      setErrorMessage(
        t(
          "admin:dispute_notes_min_length",
          "Administrative resolution notes must contain at least 5 characters for resolved or dismissed status."
        )
      );
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await adminApi.resolvePaymentComplaint(complaintId, {
        status,
        admin_resolution_notes: resolutionNotes.trim() || undefined,
      });
      toastSuccess(
        t("admin:toast_dispute_marked", `Dispute complaint marked as '${status}'.`, { status }),
        t("admin:dispute_resolved_title", "Dispute Resolved")
      );
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("admin:resolve_complaint_failed", "Failed to resolve payment complaint.");
      setErrorMessage(msg);
      toastError(msg, t("admin:resolution_error", "Resolution Error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-dispute-moderate-title"
    >
      <div className="bg-card w-full max-w-xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-5 h-5 text-amber-600" aria-hidden="true" />
            <div>
              <h2 id="modal-dispute-moderate-title" className="text-base font-bold text-foreground">
                {t("admin:dispute_modal_title", "Payment Dispute Moderation")}
              </h2>
              <p className="text-[11px] text-muted-foreground">
                {t("admin:dispute_modal_subtitle", "Off-Platform Settlement Dispute Investigation")}
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
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-2">
              <Loader2 className="w-7 h-7 text-primary animate-spin" />
              <p className="text-xs text-muted-foreground">{t("admin:loading_dispute_details", "Loading dispute details...")}</p>
            </div>
          ) : errorMessage && !detail ? (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          ) : detail ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              {errorMessage && (
                <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Order & Payment Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3.5 rounded-xl bg-secondary/30 border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                    {t("admin:associated_order", "Associated Order")}
                  </span>
                  <div className="font-bold text-foreground">{detail.order_number}</div>
                  <div className="text-[11px] text-muted-foreground">
                    {t("admin:buyer_label", "Buyer")}: <span className="font-mono text-foreground">{detail.buyer_id}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {t("admin:farmer_label", "Farmer")}: <span className="font-mono text-foreground">{detail.farmer_id}</span>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-secondary/30 border border-border space-y-1">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                    {t("admin:contested_payment", "Contested Payment Claim")}
                  </span>
                  <div className="font-bold text-foreground flex items-center gap-1">
                    <IndianRupee className="w-3.5 h-3.5" />
                    <span>{detail.payment.amount}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {t("admin:method_label", "Method")}: <span className="capitalize font-medium text-foreground">{detail.payment.payment_method}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {t("admin:date_label", "Date")}: <span className="font-medium text-foreground">{detail.payment.payment_date}</span>
                  </div>
                  {detail.payment.reference_number && (
                    <div className="text-[11px] text-muted-foreground">
                      {t("admin:ref_label", "Ref")}: <span className="font-mono text-foreground">{detail.payment.reference_number}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Factual Complaint Narrative */}
              <div className="space-y-1.5">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" />
                  {t("admin:dispute_narrative", "Dispute Complaint Narrative")}
                </span>
                <div className="p-3.5 rounded-xl bg-card border border-border text-xs leading-relaxed text-foreground whitespace-pre-wrap">
                  {detail.complaint.complaint_reason}
                </div>
                <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
                  <span>
                    {t("admin:filed_by", "Filed by")}: <span className="font-mono">{detail.complaint.complainant_user_id}</span>
                  </span>
                  <span>
                    {t("admin:has_evidence", "Has Evidence")}: {detail.complaint.has_evidence ? t("common:yes", "Yes") : t("common:no", "No")}
                  </span>
                </div>
              </div>

              {/* Non-Acknowledgement Notice */}
              <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-900 text-[11px] leading-relaxed">
                <strong>{t("admin:platform_policy_notice_prefix", "Platform Policy Notice:")}</strong>{" "}
                {t(
                  "admin:dispute_policy_notice",
                  "Administrators facilitate dispute resolution and mediation notes. Administrators do not acknowledge payment receipt on behalf of farmers."
                )}
              </div>

              {/* Status Selector */}
              <div className="space-y-1.5">
                <label htmlFor="dispute-target-status" className="block text-xs font-bold text-foreground">
                  {t("admin:dispute_status_label", "Dispute Resolution Status")}
                </label>
                <select
                  id="dispute-target-status"
                  value={status}
                  disabled={isSubmitting}
                  onChange={(e) => setStatus(e.target.value as "under_review" | "resolved" | "dismissed")}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                >
                  <option value="under_review">
                    {t("admin:dispute_opt_under_review", "Under Review (Mediation / Banking Verification in Progress)")}
                  </option>
                  <option value="resolved">
                    {t("admin:dispute_opt_resolved", "Resolved (Dispute resolved between parties)")}
                  </option>
                  <option value="dismissed">
                    {t("admin:dispute_opt_dismissed", "Dismissed (Complaint rejected or unfounded)")}
                  </option>
                </select>
              </div>

              {/* Mediation Findings Notes */}
              <div className="space-y-1.5">
                <label htmlFor="dispute-admin-notes" className="block text-xs font-bold text-foreground">
                  {t("admin:dispute_notes_label", "Administrative Mediation & Resolution Notes")}{" "}
                  {isTerminal && <span className="text-destructive">*</span>}
                </label>
                <textarea
                  id="dispute-admin-notes"
                  rows={3}
                  value={resolutionNotes}
                  disabled={isSubmitting}
                  onChange={(e) => {
                    setResolutionNotes(e.target.value);
                    if (errorMessage) setErrorMessage(null);
                  }}
                  placeholder={
                    isTerminal
                      ? t(
                          "admin:dispute_notes_placeholder_terminal",
                          "Record mandatory dispute findings and resolution terms (min 5 characters)..."
                        )
                      : t(
                          "admin:dispute_notes_placeholder",
                          "Record dispute findings, communication with counterparties, or resolution terms..."
                        )
                  }
                  className="w-full p-3 text-xs rounded-xl border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 resize-none"
                />
                {isTerminal && (
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                    <span>{t("admin:min_5_chars", "Min 5 characters")}</span>
                    <span
                      className={
                        resolutionNotes.trim().length < 5
                          ? "text-amber-600 font-medium"
                          : "text-muted-foreground"
                      }
                    >
                      {resolutionNotes.trim().length} {t("common:characters", "characters")}
                    </span>
                  </div>
                )}
              </div>

              {/* Footer Actions */}
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
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
                >
                  {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{t("admin:save_dispute_resolution", "Save Dispute Resolution")}</span>
                </button>
              </div>
            </form>
          ) : null}
        </div>
      </div>
    </div>
  );
};

