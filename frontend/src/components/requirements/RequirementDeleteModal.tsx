import React from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import type { BuyerRequirementDetail } from "../../types";

interface RequirementDeleteModalProps {
  isOpen: boolean;
  requirement: BuyerRequirementDetail | null;
  isDeleting: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export const RequirementDeleteModal: React.FC<RequirementDeleteModalProps> = ({
  isOpen,
  requirement,
  isDeleting,
  onClose,
  onConfirm,
}) => {
  if (!isOpen || !requirement) return null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-delete-req-title"
    >
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl p-6 space-y-4 animate-in fade-in zoom-in-95 duration-200">
        <div className="w-12 h-12 rounded-xl bg-destructive/10 text-destructive flex items-center justify-center mx-auto">
          <AlertTriangle className="w-6 h-6" aria-hidden="true" />
        </div>

        <div className="text-center space-y-1">
          <h2 id="modal-delete-req-title" className="text-lg font-bold text-foreground">
            Remove Procurement Requirement
          </h2>
          <p className="text-xs text-muted-foreground">
            Are you sure you want to remove &quot;{requirement.title}&quot;?
          </p>
        </div>

        <p className="text-xs text-muted-foreground bg-secondary/50 p-3 rounded-xl border border-border leading-relaxed">
          The requirement will be soft-deleted and transitioned to closed status. It will no longer appear
          on the public demand discovery board. Existing negotiation records or confirmed orders referencing
          this procurement demand will remain intact.
        </p>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs font-semibold transition-colors shadow-xs disabled:opacity-50"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                <span>Removing...</span>
              </>
            ) : (
              <span>Confirm Removal</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

