import React, { useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  X,
  Loader2,
  AlertCircle,
  Calendar,
  CheckCircle2,
  XCircle,
  Ban,
  ArrowRightLeft,
  Truck,
  ExternalLink,
  MessageSquare,
} from "lucide-react";
import { useAuth } from "../../store/authStore";
import { offersApi } from "../../api/offers";
import { chatApi } from "../../api/chat";
import { ApiError } from "../../api/errors";
import { ToastContext } from "../ui/toast/ToastContext";
import { NegotiationHistoryTimeline } from "./NegotiationHistoryTimeline";
import { CounterOfferModal } from "./CounterOfferModal";
import { OfferAcceptModal } from "./OfferAcceptModal";
import type {
  OfferAcceptResponse,
  OfferDetail,
  OfferHistoryResponse,
  OfferStatus,
} from "../../types/offers";

interface OfferDetailModalProps {
  offerId: string | null;
  onClose: () => void;
  onActionCompleted: () => void;
  onViewOrder?: (orderId: string) => void;
}

export const OfferDetailModal: React.FC<OfferDetailModalProps> = ({
  offerId,
  onClose,
  onActionCompleted,
  onViewOrder,
}) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useContext(ToastContext);

  const [offer, setOffer] = useState<OfferDetail | null>(null);
  const [history, setHistory] = useState<OfferHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isMessaging, setIsMessaging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sub-modals
  const [isCounterModalOpen, setIsCounterModalOpen] = useState(false);
  const [isAcceptModalOpen, setIsAcceptModalOpen] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (!offerId) {
      setOffer(null);
      setHistory(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    Promise.all([
      offersApi.getOffer(offerId),
      offersApi.getOfferHistory(offerId).catch(() => null),
    ])
      .then(([offerData, historyData]) => {
        setOffer(offerData);
        setHistory(historyData);
      })
      .catch((err) => {
        setError(err.message || "Failed to load complete offer details.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [offerId]);

  if (!offerId) return null;

  const isSender = user?.id === offer?.sender_id;
  const isRecipient = user?.id === offer?.recipient_id;
  const isPending = offer?.status === "pending";

  const handleMessageCounterparty = async () => {
    if (!offer || !user) return;
    const counterpartyId = isSender ? offer.recipient_id : offer.sender_id;
    setIsMessaging(true);
    try {
      const conv = await chatApi.createOrGetConversation({
        offer_id: offer.id,
        target_user_id: counterpartyId,
      });
      onClose();
      navigate(`/dashboard/messages?conversationId=${conv.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to open conversation.";
      setError(msg);
    } finally {
      setIsMessaging(false);
    }
  };

  const handleWithdraw = async () => {
    if (!offer) return;
    if (!window.confirm("Are you sure you want to withdraw this pending trade offer?")) {
      return;
    }

    setActionLoading(true);
    try {
      await offersApi.withdrawOffer(offer.id);
      toast?.success("Proposal successfully withdrawn.", "Offer Withdrawn");
      onActionCompleted();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        toast?.error(err.message || "Failed to withdraw offer.", "Operation Failed");
      } else {
        toast?.error("Network error while withdrawing offer.", "Error");
      }
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!offer) return;

    setActionLoading(true);
    try {
      await offersApi.rejectOffer(offer.id, { reason: rejectReason.trim() || null });
      toast?.success("Proposal rejected.", "Offer Rejected");
      onActionCompleted();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        toast?.error(err.message || "Failed to reject offer.", "Operation Failed");
      } else {
        toast?.error("Network error while rejecting offer.", "Error");
      }
    } finally {
      setActionLoading(false);
      setIsRejecting(false);
    }
  };

  const handleAcceptSuccess = (response: OfferAcceptResponse) => {
    toast?.success(
      `Offer accepted! Order #${response.order_number} has been created.`,
      "Order Created"
    );
    setIsAcceptModalOpen(false);
    onActionCompleted();
    onClose();
    if (onViewOrder && response.order_id) {
      onViewOrder(response.order_id);
    }
  };

  const handleCounterSuccess = (newOffer: OfferDetail) => {
    toast?.success(
      `Counter-offer ${newOffer.offer_number} submitted successfully.`,
      "Counter-Offer Sent"
    );
    setIsCounterModalOpen(false);
    onActionCompleted();
    onClose();
  };

  const getStatusBadge = (status: OfferStatus) => {
    switch (status) {
      case "accepted":
        return "bg-emerald-50 text-emerald-800 border-emerald-200";
      case "countered":
        return "bg-blue-50 text-blue-800 border-blue-200";
      case "rejected":
        return "bg-red-50 text-red-800 border-red-200";
      case "withdrawn":
        return "bg-amber-50 text-amber-800 border-amber-200";
      case "expired":
        return "bg-gray-100 text-gray-800 border-gray-300";
      case "pending":
      default:
        return "bg-primary/10 text-primary border-primary/20";
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-offer-detail-title"
    >
      <div className="bg-card w-full max-w-3xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div>
            <div className="flex items-center gap-2">
              <h2 id="modal-offer-detail-title" className="text-lg font-bold text-foreground">
                Offer Specifications
              </h2>
              {offer && (
                <span
                  className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider border capitalize ${getStatusBadge(
                    offer.status
                  )}`}
                >
                  {offer.status}
                </span>
              )}
            </div>
            {offer && (
              <p className="text-xs text-muted-foreground">
                Trade proposal #{offer.offer_number}
              </p>
            )}
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
        <div className="p-6 max-h-[75vh] overflow-y-auto space-y-6 text-xs">
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center text-muted-foreground gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-primary" aria-hidden="true" />
              <p className="text-sm">Retrieving negotiation proposal specifications...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold">Unable to Load Details</p>
                <p className="text-xs">{error}</p>
              </div>
            </div>
          ) : offer ? (
            <>
              {/* Counterparty & Participants Banner */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 rounded-xl border border-border bg-secondary/30">
                <div>
                  <span className="text-muted-foreground block text-[11px] uppercase tracking-wider font-semibold">
                    Proposer (Sender)
                  </span>
                  <div className="font-bold text-foreground text-sm mt-0.5">
                    {offer.sender?.name || "Participant"}
                  </div>
                  <div className="text-[11px] text-muted-foreground capitalize">
                    {offer.sender?.business_name || offer.sender?.role || "Trade User"}
                    {offer.sender?.city && ` • ${offer.sender.city}, ${offer.sender.state}`}
                  </div>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px] uppercase tracking-wider font-semibold">
                    Recipient (Counterparty)
                  </span>
                  <div className="font-bold text-foreground text-sm mt-0.5">
                    {offer.recipient?.name || "Participant"}
                  </div>
                  <div className="text-[11px] text-muted-foreground capitalize">
                    {offer.recipient?.business_name || offer.recipient?.role || "Trade User"}
                    {offer.recipient?.city && ` • ${offer.recipient.city}, ${offer.recipient.state}`}
                  </div>
                </div>
              </div>

              {/* Line Items Table */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Proposed Produce Items ({offer.items.length})
                </h3>

                <div className="rounded-xl border border-border overflow-hidden bg-card">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead className="bg-secondary/40 text-muted-foreground font-semibold uppercase tracking-wider border-b border-border">
                      <tr>
                        <th className="py-2.5 px-3">Product Name</th>
                        <th className="py-2.5 px-3">Quality</th>
                        <th className="py-2.5 px-3">Quantity</th>
                        <th className="py-2.5 px-3">Unit Price</th>
                        <th className="py-2.5 px-3 text-right">Subtotal</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {offer.items.map((item) => (
                        <tr key={item.id} className="hover:bg-secondary/20">
                          <td className="py-2.5 px-3 font-semibold text-foreground">
                            {item.product_name}
                          </td>
                          <td className="py-2.5 px-3 text-muted-foreground">
                            {item.quality_grade || "—"}
                          </td>
                          <td className="py-2.5 px-3">
                            {item.quantity} {item.unit}
                          </td>
                          <td className="py-2.5 px-3">
                            ₹{Number(item.unit_price).toLocaleString()}
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold text-foreground">
                            ₹{Number(item.subtotal).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-secondary/30 font-bold border-t border-border">
                      <tr>
                        <td colSpan={4} className="py-3 px-3 text-right text-muted-foreground uppercase text-[11px]">
                          Server-Calculated Total:
                        </td>
                        <td className="py-3 px-3 text-right text-sm text-primary">
                          ₹{Number(offer.total_amount).toLocaleString()}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Delivery Terms & Scheduling */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 rounded-xl bg-secondary/30 border border-border text-xs">
                <div>
                  <span className="text-muted-foreground block text-[11px] font-semibold uppercase flex items-center gap-1">
                    <Truck className="w-3.5 h-3.5" aria-hidden="true" />
                    Delivery Terms
                  </span>
                  <p className="mt-1 font-medium text-foreground">
                    {offer.delivery_terms || "Standard commercial transit terms apply."}
                  </p>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px] font-semibold uppercase flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" aria-hidden="true" />
                    Target Delivery Date
                  </span>
                  <p className="mt-1 font-semibold text-foreground">
                    {offer.proposed_delivery_date || "To be confirmed upon acceptance"}
                  </p>
                </div>
              </div>

              {/* Generated Order Link if Accepted */}
              {offer.status === "accepted" && offer.order_id && (
                <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <p className="font-bold text-xs">Order Finalized</p>
                      <p className="text-[11px] text-emerald-700">
                        Formal trade order generated: #{offer.order_number || offer.order_id.slice(0, 8)}
                      </p>
                    </div>
                  </div>
                  {onViewOrder && (
                    <button
                      type="button"
                      onClick={() => {
                        onClose();
                        onViewOrder(offer.order_id!);
                      }}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 transition-colors"
                    >
                      <span>View Order</span>
                      <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
                    </button>
                  )}
                </div>
              )}

              {/* Negotiation Lineage Timeline */}
              {Boolean(history?.history && history.history.length > 1) && (
                <NegotiationHistoryTimeline
                  history={history!.history}
                  currentOfferId={offer.id}
                  onSelectOffer={(newId) => {
                    offersApi.getOffer(newId).then(setOffer);
                  }}
                />
              )}

              {/* Rejection Form view if toggled */}
              {isRejecting && (
                <form
                  onSubmit={handleConfirmReject}
                  className="p-4 rounded-xl border border-destructive/30 bg-destructive/5 space-y-3"
                >
                  <div className="flex items-center gap-2 text-destructive font-bold text-xs">
                    <XCircle className="w-4 h-4" aria-hidden="true" />
                    <span>Decline Trade Proposal</span>
                  </div>
                  <textarea
                    rows={2}
                    placeholder="Provide an optional explanation for declining this proposal..."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="w-full p-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-destructive"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setIsRejecting(false)}
                      className="px-3 py-1.5 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="px-3 py-1.5 rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs font-semibold"
                    >
                      {actionLoading ? "Rejecting..." : "Confirm Rejection"}
                    </button>
                  </div>
                </form>
              )}
            </>
          ) : null}
        </div>

        {/* Action Footer */}
        <div className="px-6 py-3.5 border-t border-border flex items-center justify-between bg-secondary/20">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
            >
              Close
            </button>
            {offer && (
              <button
                type="button"
                onClick={handleMessageCounterparty}
                disabled={isMessaging}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
              >
                {isMessaging ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <MessageSquare className="w-3.5 h-3.5 text-primary" />
                )}
                <span>Message Counterparty</span>
              </button>
            )}
          </div>

          {/* Action Buttons */}
          {offer && isPending && (
            <div className="flex items-center gap-2">
              {isRecipient && !isRejecting && (
                <>
                  <button
                    type="button"
                    onClick={() => setIsRejecting(true)}
                    disabled={actionLoading}
                    className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-destructive/30 bg-card text-destructive hover:bg-destructive/10 text-xs font-semibold transition-colors"
                  >
                    <XCircle className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Reject</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsCounterModalOpen(true)}
                    disabled={actionLoading}
                    className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-primary/30 bg-card text-primary hover:bg-primary/10 text-xs font-semibold transition-colors"
                  >
                    <ArrowRightLeft className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Counter-Offer</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsAcceptModalOpen(true)}
                    disabled={actionLoading}
                    className="inline-flex items-center gap-1 px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-semibold transition-colors shadow-xs"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Accept Offer</span>
                  </button>
                </>
              )}

              {isSender && (
                <button
                  type="button"
                  onClick={handleWithdraw}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-1 px-3.5 py-2 rounded-lg border border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100 text-xs font-semibold transition-colors"
                >
                  <Ban className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Withdraw Proposal</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Sub-modals */}
      {offer && (
        <>
          <CounterOfferModal
            isOpen={isCounterModalOpen}
            parentOffer={offer}
            onClose={() => setIsCounterModalOpen(false)}
            onSuccess={handleCounterSuccess}
          />

          <OfferAcceptModal
            isOpen={isAcceptModalOpen}
            offer={offer}
            onClose={() => setIsAcceptModalOpen(false)}
            onSuccess={handleAcceptSuccess}
          />
        </>
      )}
    </div>
  );
};
