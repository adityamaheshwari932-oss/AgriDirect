import React, { useState } from "react";
import { X, CheckCircle2, AlertCircle, Loader2, PackageCheck } from "lucide-react";
import { ordersApi } from "../../api/orders";
import type { DeliveryAcknowledgePayload, OrderDetail } from "../../types/orders";

interface DeliveryAcknowledgeModalProps {
  isOpen: boolean;
  order: OrderDetail | null;
  onClose: () => void;
  onSuccess: (updated: OrderDetail) => void;
}

export const DeliveryAcknowledgeModal: React.FC<DeliveryAcknowledgeModalProps> = ({
  isOpen,
  order,
  onClose,
  onSuccess,
}) => {
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !order) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const payload: DeliveryAcknowledgePayload = {
      notes: notes.trim() ? notes.trim() : null,
    };

    setIsSubmitting(true);
    try {
      const updated = await ordersApi.acknowledgeDelivery(order.id, payload);
      onSuccess(updated);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to acknowledge delivery receipt.";
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
      aria-labelledby="modal-delivery-ack-title"
    >
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-emerald-500/10">
          <div className="flex items-center gap-2">
            <PackageCheck className="w-5 h-5 text-emerald-600" aria-hidden="true" />
            <h2 id="modal-delivery-ack-title" className="text-base font-bold text-foreground">
              Acknowledge Delivery & Complete Order
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
            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          <div className="text-xs text-muted-foreground space-y-2">
            <p>
              Confirming receipt for Order <strong className="text-foreground">{order.order_number}</strong>.
            </p>
            <div className="p-3 rounded-xl bg-secondary/50 border border-border space-y-1">
              <span className="font-semibold text-foreground block">Binding Finalization:</span>
              <p className="text-[11px] leading-relaxed">
                By acknowledging physical receipt of the produce, this trade transaction will be permanently marked as{" "}
                <strong className="text-foreground">Completed</strong> and all line items will transition to fulfilled.
              </p>
            </div>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="delivery-ack-notes"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
            >
              Inspection Notes / Verification Remarks (Optional)
            </label>
            <textarea
              id="delivery-ack-notes"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g., Goods inspected at farm gate, weights match weighbridge receipt..."
              maxLength={1000}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
            />
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
              className="px-5 py-2 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>Finalizing...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                  <span>Acknowledge & Complete</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

