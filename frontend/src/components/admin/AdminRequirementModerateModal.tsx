import React, { useEffect, useState } from "react";
import { X, ClipboardList, Loader2, AlertCircle, AlertTriangle } from "lucide-react";
import { adminApi } from "../../api/admin";
import type { AdminCatalogAction, AdminRequirementSummary } from "../../types/admin";
import { useToast } from "../ui/toast";

interface AdminRequirementModerateModalProps {
  requirement: AdminRequirementSummary | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const AdminRequirementModerateModal: React.FC<AdminRequirementModerateModalProps> = ({
  requirement,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { success: toastSuccess, error: toastError } = useToast();

  const [action, setAction] = useState<AdminCatalogAction>("close");
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmStep, setConfirmStep] = useState(false);

  useEffect(() => {
    if (requirement) {
      setAction(requirement.is_deleted ? "restore" : "close");
      setReason("");
      setErrorMessage(null);
      setConfirmStep(false);
    }
  }, [requirement, isOpen]);

  if (!isOpen || !requirement) return null;

  const isValidReason = reason.trim().length >= 10 && reason.trim().length <= 1000;
  const isConsequential = action === "close" || action === "remove";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isValidReason) {
      setErrorMessage("Administrative justification must be at least 10 non-whitespace characters.");
      return;
    }

    if (isConsequential && !confirmStep) {
      setConfirmStep(true);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await adminApi.moderateRequirement(requirement.id, {
        action,
        reason: reason.trim(),
      });
      toastSuccess(`Requirement action '${action}' applied successfully.`, "Requirement Moderated");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to apply moderation action to requirement.";
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
      aria-labelledby="modal-requirement-moderate-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2.5">
            <ClipboardList className="w-5 h-5 text-primary" aria-hidden="true" />
            <div>
              <h2 id="modal-requirement-moderate-title" className="text-base font-bold text-foreground">
                Moderate Buyer Requirement
              </h2>
              <p className="text-[11px] text-muted-foreground">
                Procurement Demand Catalog Action
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
          {errorMessage && (
            <div
              role="alert"
              className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Requirement Summary Card */}
          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-bold text-foreground text-sm">{requirement.product_name}</span>
              <span className="font-medium text-muted-foreground">
                {requirement.required_quantity} {requirement.unit}
              </span>
            </div>
            <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1">
              <span>Buyer: <strong>{requirement.buyer_name}</strong></span>
              <span>Remaining: <strong>{requirement.remaining_quantity} {requirement.unit}</strong></span>
              <span>Status: <strong className="uppercase">{requirement.status}</strong></span>
              {requirement.is_deleted && <span className="text-destructive font-bold">(Soft-Deleted)</span>}
            </div>
          </div>

          {/* Moderation Action */}
          <div className="space-y-1.5">
            <label htmlFor="requirement-moderate-action" className="block text-xs font-bold text-foreground">
              Moderation Action
            </label>
            <select
              id="requirement-moderate-action"
              value={action}
              disabled={isSubmitting}
              onChange={(e) => {
                setAction(e.target.value as AdminCatalogAction);
                setConfirmStep(false);
              }}
              className="w-full px-3 py-2 text-xs rounded-xl border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            >
              <option value="close">Close Requirement (Mark status as closed)</option>
              <option value="remove">Remove Requirement (Soft-delete from marketplace)</option>
              <option value="restore">Restore Requirement (Un-delete / reopen requirement)</option>
            </select>
          </div>

          {/* Mandatory Reason */}
          <div className="space-y-1.5">
            <label htmlFor="requirement-moderate-reason" className="block text-xs font-bold text-foreground">
              Administrative Justification <span className="text-destructive">*</span>
            </label>
            <textarea
              id="requirement-moderate-reason"
              rows={4}
              value={reason}
              disabled={isSubmitting}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Provide a mandatory administrative reason for this requirement moderation (minimum 10 characters)..."
              className="w-full p-3 text-xs rounded-xl border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 resize-none"
            />
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Min 10 characters</span>
              <span className={reason.trim().length < 10 ? "text-amber-600 font-medium" : "text-muted-foreground"}>
                {reason.trim().length} / 1000
              </span>
            </div>
          </div>

          {/* Confirmation Prompt */}
          {confirmStep && (
            <div
              role="alert"
              className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 text-xs space-y-1"
            >
              <div className="flex items-center gap-1.5 font-bold">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>Confirm Requirement Moderation</span>
              </div>
              <p>
                You are about to execute action <strong>{action}</strong> on requirement "{requirement.product_name}". Click "Confirm & Apply" to enforce this decision.
              </p>
            </div>
          )}

          {/* Footer */}
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
              disabled={isSubmitting || !isValidReason}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{confirmStep ? "Confirm & Apply" : "Apply Moderation"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

