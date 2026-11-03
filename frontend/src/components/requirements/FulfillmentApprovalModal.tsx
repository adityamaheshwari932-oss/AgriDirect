import React, { useState } from "react";
import {
  X,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  Info,
  ShieldCheck,
} from "lucide-react";
import { ordersApi } from "../../api/orders";
import type { FulfillmentApproval } from "../../types/orders";

interface FulfillmentApprovalModalProps {
  isOpen: boolean;
  approval: FulfillmentApproval | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const FulfillmentApprovalModal: React.FC<FulfillmentApprovalModalProps> = ({
  isOpen,
  approval,
  onClose,
  onSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<"approve" | "reject">("approve");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Approve fields
  const [useCustomQty, setUseCustomQty] = useState(false);
  const [customQuantity, setCustomQuantity] = useState<number | "">("");
  const [closeRequirement, setCloseRequirement] = useState(false);

  // Reject fields
  const [rejectReason, setRejectReason] = useState("");

  if (!isOpen || !approval) return null;

  const handleApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    let approvedQty: number | undefined = undefined;
    if (useCustomQty) {
      const num = Number(customQuantity);
      if (isNaN(num) || num <= 0) {
        setError("Please enter a valid approved quantity greater than 0.");
        return;
      }
      if (num > Number(approval.proposed_quantity)) {
        setError(`Approved quantity cannot exceed the proposed quantity of ${approval.proposed_quantity}.`);
        return;
      }
      approvedQty = num;
    }

    setIsSubmitting(true);
    try {
      await ordersApi.approveFulfillment(approval.id, {
        approved_quantity: approvedQty,
        close_requirement: closeRequirement,
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to approve requirement fulfillment.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    setIsSubmitting(true);
    try {
      await ordersApi.rejectFulfillment(approval.id, {
        reason: rejectReason.trim() || undefined,
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reject requirement fulfillment.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-fulfillment-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div>
            <h2 id="modal-fulfillment-title" className="text-lg font-bold text-foreground flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-primary" aria-hidden="true" />
              <span>Review Demand Fulfillment</span>
            </h2>
            <p className="text-xs text-muted-foreground">
              Authorize requirement remaining demand deduction for farmer-accepted supply
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {error && (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold">Review Error</p>
                <p className="text-xs">{error}</p>
              </div>
            </div>
          )}

          {/* Proposal Summary Card */}
          <div className="p-4 rounded-xl bg-secondary/40 border border-border space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-muted-foreground block text-[11px]">Proposed Volume</span>
                <span className="text-base font-bold text-primary">
                  {approval.proposed_quantity} units
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Current Status</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-700 capitalize">
                  {approval.status}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Requirement ID</span>
                <span className="font-mono text-muted-foreground truncate block">
                  {approval.requirement_id}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Commercial Order ID</span>
                <span className="font-mono text-muted-foreground truncate block">
                  {approval.order_id}
                </span>
              </div>
            </div>
          </div>

          {/* Action Tabs */}
          <div className="flex rounded-xl bg-secondary p-1 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setActiveTab("approve")}
              className={`flex-1 py-2 rounded-lg transition-all ${
                activeTab === "approve"
                  ? "bg-card text-foreground shadow-xs font-bold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Approve Deduction
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("reject")}
              className={`flex-1 py-2 rounded-lg transition-all ${
                activeTab === "reject"
                  ? "bg-card text-destructive shadow-xs font-bold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Reject Deduction
            </button>
          </div>

          {activeTab === "approve" ? (
            <form onSubmit={handleApprove} className="space-y-4">
              <div className="space-y-3">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                  Deduction Volume Strategy
                </label>

                <div className="space-y-2">
                  <label className="flex items-center gap-2.5 p-3 rounded-xl border border-border bg-card cursor-pointer hover:border-primary/50 text-xs">
                    <input
                      type="radio"
                      name="qty_strategy"
                      checked={!useCustomQty}
                      onChange={() => setUseCustomQty(false)}
                      className="text-primary focus:ring-primary h-4 w-4"
                    />
                    <div>
                      <span className="font-semibold text-foreground">
                        Full Proposed Quantity ({approval.proposed_quantity} units)
                      </span>
                      <p className="text-[11px] text-muted-foreground">
                        Deducts the entire order volume from the requirement remaining demand.
                      </p>
                    </div>
                  </label>

                  <label className="flex items-start gap-2.5 p-3 rounded-xl border border-border bg-card cursor-pointer hover:border-primary/50 text-xs">
                    <input
                      type="radio"
                      name="qty_strategy"
                      checked={useCustomQty}
                      onChange={() => setUseCustomQty(true)}
                      className="text-primary focus:ring-primary h-4 w-4 mt-0.5"
                    />
                    <div className="flex-1 space-y-2">
                      <span className="font-semibold text-foreground">
                        Custom Partial Deduction
                      </span>
                      {useCustomQty && (
                        <input
                          type="number"
                          step="0.001"
                          min="0.001"
                          max={Number(approval.proposed_quantity)}
                          value={customQuantity}
                          onChange={(e) =>
                            setCustomQuantity(
                              e.target.value === "" ? "" : parseFloat(e.target.value)
                            )
                          }
                          placeholder={`Enter amount (max ${approval.proposed_quantity})`}
                          className="w-full rounded-lg border border-border bg-secondary/50 px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
                          required
                        />
                      )}
                    </div>
                  </label>
                </div>
              </div>

              <div className="pt-1">
                <label className="flex items-center gap-2 cursor-pointer text-xs">
                  <input
                    type="checkbox"
                    checked={closeRequirement}
                    onChange={(e) => setCloseRequirement(e.target.checked)}
                    className="rounded border-border text-primary focus:ring-primary h-4 w-4"
                  />
                  <span className="font-semibold text-foreground">
                    Close requirement upon approval (mark as completely fulfilled)
                  </span>
                </label>
              </div>

              <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-700 text-xs flex items-start gap-2">
                <Info className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-[11px] leading-relaxed">
                  Approving decrements the requirement&apos;s remaining demand without modifying the
                  commercial order quantity or pricing.
                </p>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-border">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                      <span>Approving...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                      <span>Confirm Approval</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleReject} className="space-y-4">
              <div className="space-y-1.5">
                <label
                  htmlFor="reject-reason-input"
                  className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
                >
                  Reason for Rejection (Optional)
                </label>
                <textarea
                  id="reject-reason-input"
                  rows={3}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Explain why this order should not decrement open requirement demand..."
                  maxLength={500}
                  className="w-full rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-700 text-xs flex items-start gap-2">
                <Info className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-[11px] leading-relaxed">
                  Rejecting demand deduction preserves your open requirement demand so other farmers
                  can fulfill it. The underlying commercial order will continue normally.
                </p>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3 border-t border-border">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                      <span>Rejecting...</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4" aria-hidden="true" />
                      <span>Reject Demand Deduction</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

