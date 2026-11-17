import React, { useState } from "react";
import { X, DollarSign, Calendar, Upload, AlertCircle, Loader2, FileCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { paymentsApi } from "../../api/payments";
import type { PaymentMethod, PaymentRecord, PaymentRecordCreatePayload } from "../../types/payments";
import { formatNumber } from "../../utils/formatters";

interface PaymentRecordModalProps {
  isOpen: boolean;
  orderId: string;
  orderNumber: string;
  maxPayableAmount?: string | number | null;
  onClose: () => void;
  onSuccess: (payment: PaymentRecord) => void;
}

export const PaymentRecordModal: React.FC<PaymentRecordModalProps> = ({
  isOpen,
  orderId,
  orderNumber,
  maxPayableAmount,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["payments", "common", "validation", "errors"]);
  const [amount, setAmount] = useState<string>("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("upi");
  const [paymentDate, setPaymentDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [referenceNumber, setReferenceNumber] = useState<string>("");
  const [proofFile, setProofFile] = useState<File | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > 10 * 1024 * 1024) {
        setError(
          t(
            "payments:record.file_too_large",
            "Payment receipt proof file must not exceed 10 MB."
          )
        );
        return;
      }
      setProofFile(file);
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      setError(
        t(
          "payments:record.amount_invalid",
          "Please enter a valid positive payment amount."
        )
      );
      return;
    }

    if (!paymentDate) {
      setError(
        t(
          "payments:record.date_required",
          "Please select the date the off-platform transfer took place."
        )
      );
      return;
    }

    const payload: PaymentRecordCreatePayload = {
      amount: numAmount.toFixed(2),
      payment_method: paymentMethod,
      payment_date: paymentDate,
      reference_number: referenceNumber.trim() ? referenceNumber.trim() : null,
      proof_file: proofFile,
    };

    setIsSubmitting(true);
    try {
      const created = await paymentsApi.recordPayment(orderId, payload);
      onSuccess(created);
      onClose();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("payments:record.failed", "Failed to record payment.");
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
      aria-labelledby="modal-payment-record-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-primary-50/50">
          <div className="flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-primary" aria-hidden="true" />
            <h2 id="modal-payment-record-title" className="text-base font-bold text-foreground">
              {t("payments:record.title", "Record Off-Platform Payment")}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label={t("common:actions.close", "Close dialog")}
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
              {t("payments:order_ref", "Order")}:{" "}
              <strong className="text-foreground">{orderNumber}</strong>
            </p>
            {maxPayableAmount !== undefined && maxPayableAmount !== null && (
              <p className="text-[11px]">
                {t(
                  "payments:record.max_headroom_label",
                  "Maximum allowable payable headroom:"
                )}{" "}
                <span className="font-bold text-foreground">
                  ₹{formatNumber(Number(maxPayableAmount), { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </p>
            )}
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              {t(
                "payments:record.disclaimer",
                "AgriDirect does not process or hold payments. Enter the details of the direct payment (e.g. UPI, NEFT/RTGS, cash) transferred to the producer."
              )}
            </p>
          </div>

          {/* Amount */}
          <div className="space-y-1.5">
            <label
              htmlFor="payment-amount-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
            >
              {t("payments:amount_label", "Payment Amount (INR)")}{" "}
              <span className="text-destructive">*</span>
            </label>
            <div className="relative">
              <span className="absolute start-3.5 top-2.5 text-xs font-bold text-muted-foreground">₹</span>
              <input
                id="payment-amount-input"
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="w-full rounded-xl border border-border bg-card ps-8 pe-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
                required
              />
            </div>
          </div>

          {/* Payment Method */}
          <div className="space-y-1.5">
            <label
              htmlFor="payment-method-select"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
            >
              {t("payments:method_label", "Payment Method")}{" "}
              <span className="text-destructive">*</span>
            </label>
            <select
              id="payment-method-select"
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
              required
            >
              <option value="upi">
                {t(
                  "payments:record.method_upi_desc",
                  "UPI (GPay / PhonePe / Paytm / BHIM)"
                )}
              </option>
              <option value="bank_transfer">
                {t(
                  "payments:record.method_bank_desc",
                  "Direct Bank Transfer (NEFT / RTGS / IMPS)"
                )}
              </option>
              <option value="cash">
                {t(
                  "payments:record.method_cash_desc",
                  "Cash on Farm Gate / Delivery Handover"
                )}
              </option>
              <option value="other">
                {t("payments:record.method_other_desc", "Other Agreed Settlement")}
              </option>
            </select>
          </div>

          {/* Payment Date */}
          <div className="space-y-1.5">
            <label
              htmlFor="payment-date-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"
            >
              <Calendar className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
              <span>{t("payments:payment_date_label", "Payment Date")}</span>{" "}
              <span className="text-destructive">*</span>
            </label>
            <input
              id="payment-date-input"
              type="date"
              value={paymentDate}
              onChange={(e) => setPaymentDate(e.target.value)}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
              required
            />
          </div>

          {/* Reference / UTR Number */}
          <div className="space-y-1.5">
            <label
              htmlFor="payment-ref-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
            >
              {t(
                "payments:reference_number_label",
                "Transaction Reference / UTR Number (Optional)"
              )}
            </label>
            <input
              id="payment-ref-input"
              type="text"
              value={referenceNumber}
              onChange={(e) => setReferenceNumber(e.target.value)}
              placeholder={t(
                "payments:reference_placeholder",
                "e.g., UPI Ref 324159876543, Bank UTR SBIN0001234"
              )}
              maxLength={128}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
            />
          </div>

          {/* Proof Upload */}
          <div className="space-y-1.5">
            <label
              htmlFor="payment-proof-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"
            >
              <Upload className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
              <span>
                {t(
                  "payments:proof_file_label",
                  "Attach Receipt Proof (Optional, Max 10MB)"
                )}
              </span>
            </label>
            <div className="flex items-center gap-2">
              <input
                id="payment-proof-input"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp"
                onChange={handleFileChange}
                className="text-xs text-muted-foreground file:me-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-border file:text-xs file:font-semibold file:bg-secondary file:text-foreground hover:file:bg-secondary/80 cursor-pointer"
              />
              {proofFile && (
                <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 font-medium">
                  <FileCheck className="w-3.5 h-3.5" aria-hidden="true" />
                  {proofFile.name}
                </span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="pt-3 flex items-center justify-end gap-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
            >
              {t("common:actions.cancel", "Cancel")}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>{t("payments:record.recording", "Recording...")}</span>
                </>
              ) : (
                <span>{t("payments:record_payment_button", "Record Payment")}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

