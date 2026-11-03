import React, { useState } from "react";
import { X, AlertTriangle, Loader2 } from "lucide-react";
import { ordersApi } from "../../api/orders";
import type { OrderDetail } from "../../types/orders";

interface OrderCancelModalProps {
  isOpen: boolean;
  order: OrderDetail | null;
  onClose: () => void;
  onSuccess: (updatedOrder: OrderDetail) => void;
}

export const OrderCancelModal: React.FC<OrderCancelModalProps> = ({
  isOpen,
  order,
  onClose,
  onSuccess,
}) => {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !order) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmed = reason.trim();
    if (!trimmed) {
      setError("A cancellation reason is required for audited commercial records.");
      return;
    }

    setIsSubmitting(true);
    try {
      const updated = await ordersApi.cancelOrder(order.id, { reason: trimmed });
      onSuccess(updated);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to cancel order.";
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
      aria-labelledby="modal-order-cancel-title"
    >
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-destructive/10">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-destructive" aria-hidden="true" />
            <h2 id="modal-order-cancel-title" className="text-base font-bold text-foreground">
              Cancel Commercial Order
            </h2>
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

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs">
              {error}
            </div>
          )}

          <div className="text-xs text-muted-foreground space-y-2">
            <p>
              Are you sure you want to cancel Order{" "}
              <strong className="text-foreground">{order.order_number}</strong>?
            </p>
            <div className="p-3 rounded-lg bg-secondary/50 border border-border space-y-1">
              <span className="font-semibold text-foreground block">Audited Restitution:</span>
              <p className="text-[11px] leading-relaxed">
                Cancelling this order will atomically restitute reserved inventory back to the farmer&apos;s
                available stock and reverse any applied buyer requirement demand deductions.
              </p>
            </div>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="cancel-order-reason"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
            >
              Cancellation Reason <span className="text-destructive">*</span>
            </label>
            <textarea
              id="cancel-order-reason"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Provide a clear commercial justification (e.g., severe transport disruption, harvest loss)..."
              maxLength={500}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
              required
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
            >
              Keep Order Active
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>Cancelling...</span>
                </>
              ) : (
                <span>Confirm Cancellation</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

