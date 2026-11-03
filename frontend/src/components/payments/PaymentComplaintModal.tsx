import React, { useState } from "react";
import { X, AlertTriangle, Upload, AlertCircle, Loader2, FileCheck } from "lucide-react";
import { paymentsApi } from "../../api/payments";
import type { PaymentComplaint, PaymentComplaintCreatePayload } from "../../types/payments";

interface PaymentComplaintModalProps {
  isOpen: boolean;
  paymentId: string | null;
  paymentAmount: string;
  orderNumber: string;
  onClose: () => void;
  onSuccess: (complaint: PaymentComplaint) => void;
}

export const PaymentComplaintModal: React.FC<PaymentComplaintModalProps> = ({
  isOpen,
  paymentId,
  paymentAmount,
  orderNumber,
  onClose,
  onSuccess,
}) => {
  const [reason, setReason] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !paymentId) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > 10 * 1024 * 1024) {
        setError("Evidence document must not exceed 10 MB.");
        return;
      }
      setEvidenceFile(file);
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmed = reason.trim();
    if (trimmed.length < 5) {
      setError("Please provide a detailed dispute narrative (at least 5 characters).");
      return;
    }

    const payload: PaymentComplaintCreatePayload = {
      complaint_reason: trimmed,
      evidence_file: evidenceFile,
    };

    setIsSubmitting(true);
    try {
      const complaint = await paymentsApi.filePaymentComplaint(paymentId, payload);
      onSuccess(complaint);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to file payment dispute.";
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
      aria-labelledby="modal-payment-complaint-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-destructive/10">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-destructive" aria-hidden="true" />
            <h2 id="modal-payment-complaint-title" className="text-base font-bold text-foreground">
              Dispute Payment Claim
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

          <div className="p-3 rounded-xl bg-secondary/50 border border-border text-xs text-muted-foreground space-y-1">
            <p>
              Order: <strong className="text-foreground">{orderNumber}</strong> | Claimed Amount:{" "}
              <strong className="text-foreground">₹{paymentAmount}</strong>
            </p>
            <p className="text-[11px] leading-relaxed">
              Filing a dispute transitions the payment record to{" "}
              <span className="font-bold text-destructive">Disputed</span> and alerts the counterparty.
              The claim is queued for administrative mediation and evidence verification.
            </p>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="complaint-reason-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
            >
              Factual Ground for Dispute <span className="text-destructive">*</span>
            </label>
            <textarea
              id="complaint-reason-input"
              rows={4}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="State the exact discrepancy (e.g. funds not received in bank account, incorrect amount, duplicate receipt)..."
              minLength={5}
              maxLength={2000}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
              required
            />
          </div>

          {/* Evidence Upload */}
          <div className="space-y-1.5">
            <label
              htmlFor="complaint-evidence-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"
            >
              <Upload className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
              <span>Attach Bank Statement / Evidence (Optional, Max 10MB)</span>
            </label>
            <div className="flex items-center gap-2">
              <input
                id="complaint-evidence-input"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx"
                onChange={handleFileChange}
                className="text-xs text-muted-foreground file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-border file:text-xs file:font-semibold file:bg-secondary file:text-foreground hover:file:bg-secondary/80 cursor-pointer"
              />
              {evidenceFile && (
                <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 font-medium">
                  <FileCheck className="w-3.5 h-3.5" aria-hidden="true" />
                  {evidenceFile.name}
                </span>
              )}
            </div>
          </div>

          <div className="pt-3 flex items-center justify-end gap-3 border-t border-border">
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
                  <span>Submitting Dispute...</span>
                </>
              ) : (
                <span>Submit Formal Dispute</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

