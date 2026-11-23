import React, { useState } from "react";
import { X, ShieldAlert, Loader2, AlertCircle, AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { adminApi } from "../../api/admin";
import type { AdminAccountStatus, AdminUserSummary } from "../../types/admin";
import { useToast } from "../ui/toast";

interface AdminUserStatusModalProps {
  user: AdminUserSummary | null;
  isOpen: boolean;
  currentAdminId?: string;
  onClose: () => void;
  onSuccess: () => void;
}

export const AdminUserStatusModal: React.FC<AdminUserStatusModalProps> = ({
  user,
  isOpen,
  currentAdminId,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["admin", "common", "errors"]);
  const { success: toastSuccess, error: toastError } = useToast();

  const [accountStatus, setAccountStatus] = useState<AdminAccountStatus>("active");
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmStep, setConfirmStep] = useState(false);

  // Sync initial status when modal opens
  React.useEffect(() => {
    if (user) {
      const current = user.account_status as AdminAccountStatus;
      setAccountStatus(current === "active" ? "restricted" : current);
      setReason("");
      setErrorMessage(null);
      setConfirmStep(false);
    }
  }, [user, isOpen]);

  if (!isOpen || !user) return null;

  const isSelf = Boolean(currentAdminId && currentAdminId === user.id);
  const isConsequential = accountStatus === "suspended" || accountStatus === "blocked";
  const isValidReason = reason.trim().length >= 10 && reason.trim().length <= 1000;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isSelf) {
      setErrorMessage(
        t(
          "admin:self_mod_error",
          "Self-modification forbidden: You cannot modify your own administrator account status."
        )
      );
      return;
    }

    if (!isValidReason) {
      setErrorMessage(
        t("admin:reason_min_length", "A valid explanation of at least 10 non-whitespace characters is mandatory.")
      );
      return;
    }

    if (isConsequential && !confirmStep) {
      setConfirmStep(true);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await adminApi.updateUserStatus(user.id, {
        account_status: accountStatus,
        reason: reason.trim(),
      });
      toastSuccess(
        t("admin:toast_status_updated", `Account status updated to '${accountStatus}'.`, { status: accountStatus }),
        t("admin:status_updated_title", "Status Updated")
      );
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("admin:status_update_failed", "Failed to update user account status.");
      setErrorMessage(msg);
      toastError(msg, t("admin:moderation_error", "Moderation Error"));
      setConfirmStep(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-user-status-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-amber-600" aria-hidden="true" />
            <div>
              <h2 id="modal-user-status-title" className="text-base font-bold text-foreground">
                {t("admin:moderate_user_status_title", "Moderate User Account Status")}
              </h2>
              <p className="text-[11px] text-muted-foreground">
                {t("admin:target_user_label", `Target User: ${user.email}`, { email: user.email })}
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
          {/* Self-modification Guard Warning */}
          {isSelf && (
            <div
              role="alert"
              className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-start gap-2.5"
            >
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-semibold">
                  {t("admin:self_mod_guard_title", "Self-Modification Guard")}
                </strong>
                <span>
                  {t(
                    "admin:self_mod_guard_desc",
                    "You cannot modify your own administrator account status. Platform governance rules require another administrator to execute status modifications."
                  )}
                </span>
              </div>
            </div>
          )}

          {errorMessage && (
            <div
              role="alert"
              className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* User Current Info Card */}
          <div className="p-3 rounded-lg bg-secondary/30 border border-border text-xs flex items-center justify-between">
            <div>
              <span className="text-[10px] text-muted-foreground block">{t("admin:display_name", "Display Name")}</span>
              <span className="font-medium text-foreground">{user.display_name}</span>
            </div>
            <div>
              <span className="text-[10px] text-muted-foreground block text-end">{t("admin:current_status", "Current Status")}</span>
              <span className="font-bold uppercase text-foreground text-end block">
                {user.account_status}
              </span>
            </div>
          </div>

          {/* Target Status Selection */}
          <div className="space-y-1.5">
            <label htmlFor="target-account-status" className="block text-xs font-bold text-foreground">
              {t("admin:new_account_status_label", "New Account Status")}
            </label>
            <select
              id="target-account-status"
              value={accountStatus}
              disabled={isSubmitting || isSelf}
              onChange={(e) => {
                setAccountStatus(e.target.value as AdminAccountStatus);
                setConfirmStep(false);
              }}
              className="w-full px-3 py-2 text-xs rounded-xl border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            >
              <option value="active">{t("admin:status_opt_active", "Active (Full platform access)")}</option>
              <option value="restricted">{t("admin:status_opt_restricted", "Restricted (Read-only catalog access)")}</option>
              <option value="suspended">{t("admin:status_opt_suspended", "Suspended (Temporary operational disablement)")}</option>
              <option value="blocked">{t("admin:status_opt_blocked", "Blocked (Permanent ban from platform)")}</option>
            </select>
          </div>

          {/* Mandatory Reason */}
          <div className="space-y-1.5">
            <label htmlFor="status-change-reason" className="block text-xs font-bold text-foreground">
              {t("admin:reason_label", "Administrative Rationale / Reason")} <span className="text-destructive">*</span>
            </label>
            <textarea
              id="status-change-reason"
              rows={4}
              value={reason}
              disabled={isSubmitting || isSelf}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t(
                "admin:status_reason_placeholder",
                "Provide a factual administrative explanation for this status change (minimum 10 characters)..."
              )}
              className="w-full p-3 text-xs rounded-xl border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 resize-none"
            />
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>{t("admin:min_10_chars", "Min 10 characters")}</span>
              <span className={reason.trim().length < 10 ? "text-amber-600 font-medium" : "text-muted-foreground"}>
                {reason.trim().length} / 1000
              </span>
            </div>
          </div>

          {/* Consequential Action Confirmation Prompt */}
          {confirmStep && (
            <div
              role="alert"
              className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 text-xs space-y-1.5"
            >
              <div className="flex items-center gap-1.5 font-bold">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>{t("admin:confirm_consequential_moderation", "Confirm Consequential Moderation")}</span>
              </div>
              <p>
                {t(
                  "admin:consequential_moderation_desc",
                  `You are about to transition this user to ${accountStatus}. This will revoke operational capabilities. Click "Confirm & Apply" to proceed.`,
                  { status: accountStatus }
                )}
              </p>
            </div>
          )}

          {/* Footer actions */}
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
              disabled={isSubmitting || isSelf || !isValidReason}
              className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold shadow-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                isConsequential
                  ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  : "bg-primary text-primary-foreground hover:bg-primary/90"
              }`}
            >
              {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>
                {confirmStep
                  ? t("admin:confirm_and_apply", "Confirm & Apply")
                  : t("admin:update_account_status", "Update Account Status")}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

