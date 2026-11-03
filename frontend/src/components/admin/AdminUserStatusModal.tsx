import React, { useState } from "react";
import { X, ShieldAlert, Loader2, AlertCircle, AlertTriangle } from "lucide-react";
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
      setErrorMessage("Self-modification forbidden: You cannot modify your own administrator account status.");
      return;
    }

    if (!isValidReason) {
      setErrorMessage("A valid explanation of at least 10 non-whitespace characters is mandatory.");
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
      toastSuccess(`Account status updated to '${accountStatus}'.`, "Status Updated");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update user account status.";
      setErrorMessage(msg);
      toastError(msg, "Moderation Error");
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
                Moderate User Account Status
              </h2>
              <p className="text-[11px] text-muted-foreground">
                Target User: <span className="font-semibold text-foreground">{user.email}</span>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            aria-label="Close dialog"
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
                <strong className="block font-semibold">Self-Modification Guard</strong>
                <span>
                  You cannot modify your own administrator account status. Platform governance rules require another administrator to execute status modifications.
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
              <span className="text-[10px] text-muted-foreground block">Display Name</span>
              <span className="font-medium text-foreground">{user.display_name}</span>
            </div>
            <div>
              <span className="text-[10px] text-muted-foreground block text-right">Current Status</span>
              <span className="font-bold uppercase text-foreground text-right block">
                {user.account_status}
              </span>
            </div>
          </div>

          {/* Target Status Selection */}
          <div className="space-y-1.5">
            <label htmlFor="target-account-status" className="block text-xs font-bold text-foreground">
              New Account Status
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
              <option value="active">Active (Full platform access)</option>
              <option value="restricted">Restricted (Read-only catalog access)</option>
              <option value="suspended">Suspended (Temporary operational disablement)</option>
              <option value="blocked">Blocked (Permanent ban from platform)</option>
            </select>
          </div>

          {/* Mandatory Reason */}
          <div className="space-y-1.5">
            <label htmlFor="status-change-reason" className="block text-xs font-bold text-foreground">
              Administrative Rationale / Reason <span className="text-destructive">*</span>
            </label>
            <textarea
              id="status-change-reason"
              rows={4}
              value={reason}
              disabled={isSubmitting || isSelf}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Provide a factual administrative explanation for this status change (minimum 10 characters)..."
              className="w-full p-3 text-xs rounded-xl border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 resize-none"
            />
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Min 10 characters</span>
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
                <span>Confirm Consequential Moderation</span>
              </div>
              <p>
                You are about to transition this user to <strong>{accountStatus}</strong>. This will revoke operational capabilities. Click "Confirm & Apply" to proceed.
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
              Cancel
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
              <span>{confirmStep ? "Confirm & Apply" : "Update Account Status"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

