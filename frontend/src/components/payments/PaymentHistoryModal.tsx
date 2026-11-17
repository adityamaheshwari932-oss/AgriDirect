import React, { useCallback, useEffect, useState } from "react";
import {
  X,
  CreditCard,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Download,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { paymentsApi } from "../../api/payments";
import type { PaymentComplaint, PaymentRecord } from "../../types/payments";
import { formatDate, formatNumber } from "../../utils/formatters";
import { PaymentComplaintModal } from "./PaymentComplaintModal";

interface PaymentHistoryModalProps {
  isOpen: boolean;
  orderId: string;
  orderNumber: string;
  isFarmer: boolean;
  onClose: () => void;
  onPaymentUpdated?: () => void;
}

export const PaymentHistoryModal: React.FC<PaymentHistoryModalProps> = ({
  isOpen,
  orderId,
  orderNumber,
  isFarmer,
  onClose,
  onPaymentUpdated,
}) => {
  const { t } = useTranslation(["payments", "common", "errors"]);
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Acknowledging payment state
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);

  // Dispute modal state
  const [disputePayment, setDisputePayment] = useState<PaymentRecord | null>(null);

  const loadPayments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await paymentsApi.listOrderPayments(orderId);
      setPayments(res.items || []);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("payments:history.load_failed", "Failed to load payment records.");
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [orderId, t]);

  useEffect(() => {
    if (isOpen) {
      void loadPayments();
      setActionSuccess(null);
    }
  }, [isOpen, loadPayments]);

  if (!isOpen) return null;

  const handleAcknowledge = async (paymentId: string) => {
    setAcknowledgingId(paymentId);
    setError(null);
    setActionSuccess(null);
    try {
      await paymentsApi.acknowledgePayment(paymentId);
      setActionSuccess(
        t(
          "payments:history.ack_success",
          "Payment receipt confirmed and marked acknowledged."
        )
      );
      await loadPayments();
      if (onPaymentUpdated) onPaymentUpdated();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("payments:history.ack_failed", "Failed to acknowledge payment.");
      setError(msg);
    } finally {
      setAcknowledgingId(null);
    }
  };

  const handleDisputeSuccess = (complaint: PaymentComplaint) => {
    setActionSuccess(
      t(
        "payments:history.dispute_success",
        "Payment claim disputed successfully (Complaint #{{id}}).",
        { id: complaint.id.slice(0, 8) }
      )
    );
    void loadPayments();
    if (onPaymentUpdated) onPaymentUpdated();
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "acknowledged":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-700">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" aria-hidden="true" />
            {t("payments:status.acknowledged", "Acknowledged")}
          </span>
        );
      case "disputed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-destructive/10 text-destructive">
            <AlertTriangle className="w-3 h-3 text-destructive" aria-hidden="true" />
            {t("payments:status.disputed", "Disputed")}
          </span>
        );
      case "recorded":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700">
            <Clock className="w-3 h-3 text-amber-600" aria-hidden="true" />
            {t("payments:status.pending_ack", "Pending Ack")}
          </span>
        );
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-payment-history-title"
    >
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-primary" aria-hidden="true" />
            <div>
              <h2 id="modal-payment-history-title" className="text-base font-bold text-foreground">
                {t("payments:history.title", "Payment Records Ledger")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {t("payments:history.order_ref", "Order Reference: {{orderNumber}}", {
                  orderNumber,
                })}
              </p>
            </div>
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

        {/* Content */}
        <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
          {actionSuccess && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" aria-hidden="true" />
              <span>{actionSuccess}</span>
            </div>
          )}
          {error && (
            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden="true" />
              <span className="text-xs text-muted-foreground">
                {t("payments:history.loading", "Loading payment records...")}
              </span>
            </div>
          ) : payments.length === 0 ? (
            <div className="py-12 text-center text-xs text-muted-foreground">
              {t(
                "payments:history.empty",
                "No off-platform payment claims have been logged against this order yet."
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {payments.map((p) => (
                <div
                  key={p.id}
                  className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition-colors space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-foreground">
                        ₹{formatNumber(Number(p.amount), { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-md bg-secondary text-foreground uppercase font-semibold">
                        {p.payment_method.replace("_", " ")}
                      </span>
                    </div>
                    {getStatusBadge(p.status)}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs text-muted-foreground">
                    <div>
                      <span className="block text-[11px]">{t("payments:payment_date_label", "Payment Date")}</span>
                      <span className="font-medium text-foreground">{formatDate(p.payment_date)}</span>
                    </div>
                    <div>
                      <span className="block text-[11px]">{t("payments:history.reference_utr", "Reference / UTR")}</span>
                      <span className="font-medium text-foreground font-mono">
                        {p.reference_number || "—"}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[11px]">{t("payments:history.receipt_proof", "Receipt Proof")}</span>
                      {p.has_proof ? (
                        <a
                          href={paymentsApi.getProofUrl(p.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:underline font-semibold"
                        >
                          <Download className="w-3 h-3" aria-hidden="true" />
                          <span>{t("payments:history.view_proof", "View Proof")}</span>
                        </a>
                      ) : (
                        <span className="text-muted-foreground">
                          {t("payments:history.none_attached", "None attached")}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions on this record */}
                  <div className="pt-2 border-t border-border flex items-center justify-end gap-2">
                    {/* Dispute button for either participant if not already disputed */}
                    {p.status !== "disputed" && (
                      <button
                        type="button"
                        onClick={() => setDisputePayment(p)}
                        className="px-3 py-1.5 rounded-lg border border-destructive/30 text-destructive hover:bg-destructive/10 text-xs font-semibold transition-colors"
                      >
                        {t("payments:history.btn_dispute", "Dispute Claim")}
                      </button>
                    )}

                    {/* Farmer Acknowledge button */}
                    {isFarmer && p.status === "recorded" && (
                      <button
                        type="button"
                        disabled={acknowledgingId === p.id}
                        onClick={() => handleAcknowledge(p.id)}
                        className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-bold transition-colors flex items-center gap-1.5 disabled:opacity-50"
                      >
                        {acknowledgingId === p.id ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
                            <span>{t("payments:history.confirming", "Confirming...")}</span>
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                            <span>{t("payments:history.btn_acknowledge", "Acknowledge Receipt")}</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border flex items-center justify-end bg-secondary/20">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
          >
            {t("common:actions.close", "Close")}
          </button>
        </div>
      </div>

      {/* Nested Dispute Complaint Modal */}
      {disputePayment && (
        <PaymentComplaintModal
          isOpen={Boolean(disputePayment)}
          paymentId={disputePayment.id}
          paymentAmount={disputePayment.amount}
          orderNumber={orderNumber}
          onClose={() => setDisputePayment(null)}
          onSuccess={handleDisputeSuccess}
        />
      )}
    </div>
  );
};

