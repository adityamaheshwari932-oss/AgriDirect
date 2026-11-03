import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  Truck,
  Building,
  Tractor,
  DollarSign,
  History,
  AlertTriangle,
  MessageSquare,
  Star,
  ShieldAlert,
} from "lucide-react";
import { ordersApi } from "../../api/orders";
import { chatApi } from "../../api/chat";
import { paymentsApi } from "../../api/payments";
import { useAuth } from "../../store/authStore";
import type { OrderDetail, OrderAmendment } from "../../types/orders";
import type { PaymentSummary } from "../../types/payments";
import { OrderCancelModal } from "./OrderCancelModal";
import { AmendmentProposalModal } from "./AmendmentProposalModal";
import { InventoryAuditModal } from "./InventoryAuditModal";
import { DeliveryArrangeModal } from "./DeliveryArrangeModal";
import { DeliveryAcknowledgeModal } from "./DeliveryAcknowledgeModal";
import { PaymentSummaryCard } from "../payments/PaymentSummaryCard";
import { PaymentRecordModal } from "../payments/PaymentRecordModal";
import { PaymentHistoryModal } from "../payments/PaymentHistoryModal";
import { ReviewSubmitModal } from "../reviews/ReviewSubmitModal";
import { ReportCreateModal } from "../reports/ReportCreateModal";

interface OrderDetailModalProps {
  orderId: string | null;
  onClose: () => void;
  onOrderUpdated?: () => void;
}

export const OrderDetailModal: React.FC<OrderDetailModalProps> = ({
  orderId,
  onClose,
  onOrderUpdated,
}) => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [amendments, setAmendments] = useState<OrderAmendment[]>([]);
  const [paymentSummary, setPaymentSummary] = useState<PaymentSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sub-modals
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [isAmendmentModalOpen, setIsAmendmentModalOpen] = useState(false);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);
  const [isDeliveryArrangeOpen, setIsDeliveryArrangeOpen] = useState(false);
  const [isDeliveryAcknowledgeOpen, setIsDeliveryAcknowledgeOpen] = useState(false);
  const [isPaymentRecordOpen, setIsPaymentRecordOpen] = useState(false);
  const [isPaymentHistoryOpen, setIsPaymentHistoryOpen] = useState(false);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  // Action states
  const [isConfirming, setIsConfirming] = useState(false);
  const [isMarkingDelivery, setIsMarkingDelivery] = useState(false);
  const [isMessaging, setIsMessaging] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [processingAmendmentId, setProcessingAmendmentId] = useState<string | null>(null);

  const loadOrderData = useCallback(async () => {
    if (!orderId) {
      setOrder(null);
      setAmendments([]);
      setPaymentSummary(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const [orderData, amendmentData, paymentData] = await Promise.all([
        ordersApi.getOrderDetail(orderId),
        ordersApi.listAmendments(orderId).catch(() => ({ items: [], total: 0 })),
        paymentsApi.getOrderPaymentSummary(orderId).catch(() => null),
      ]);
      setOrder(orderData);
      setAmendments(amendmentData.items || []);
      setPaymentSummary(paymentData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load order specifications.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    void loadOrderData();
  }, [loadOrderData]);

  if (!orderId) return null;

  const isFarmerSeller =
    Boolean(user && (order?.farmer_id === user.id || (user.role === "farmer" && order?.buyer_id !== user.id)));

  const isParticipant = Boolean(user && order && (order.buyer_id === user.id || order.farmer_id === user.id));
  const hasMarkedCompletion = Boolean(user && order && order.delivery_completion_marked_by_user_id === user.id);
  const canArrangeDelivery = Boolean(isParticipant && order?.delivery_status === "not_arranged");
  const canMarkDeliveryCompleted = Boolean(isParticipant && order?.delivery_status === "arranged");
  const canAcknowledgeDelivery = Boolean(
    isParticipant && order?.delivery_status === "completion_marked" && !hasMarkedCompletion
  );
  const isAwaitingCounterpartyAck = Boolean(
    isParticipant && order?.delivery_status === "completion_marked" && hasMarkedCompletion
  );

  const counterpartyId = isFarmerSeller ? order?.buyer_id || "" : order?.farmer_id || "";
  const counterpartyName = isFarmerSeller
    ? order?.buyer?.business_name || order?.buyer?.full_name || "Commercial Buyer"
    : order?.farmer?.farm_name || order?.farmer?.full_name || "Agricultural Producer";

  const hasPendingAmendment = amendments.some((a) => a.status === "proposed");

  const handleMessageCounterparty = async () => {
    if (!order || !user || !counterpartyId) return;
    setIsMessaging(true);
    setActionError(null);
    try {
      const conv = await chatApi.createOrGetConversation({
        order_id: order.id,
        target_user_id: counterpartyId,
      });
      onClose();
      navigate(`/dashboard/messages?conversationId=${conv.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to open conversation.";
      setActionError(msg);
    } finally {
      setIsMessaging(false);
    }
  };

  const handleMarkDeliveryCompleted = async () => {
    if (!order) return;
    setIsMarkingDelivery(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const updated = await ordersApi.markDeliveryCompleted(order.id);
      setOrder(updated);
      setActionSuccess("Delivery marked as completed by seller. Awaiting counterparty acknowledgement.");
      if (onOrderUpdated) onOrderUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to mark delivery completed.";
      setActionError(msg);
    } finally {
      setIsMarkingDelivery(false);
    }
  };

  const handleConfirmOrder = async () => {
    if (!order) return;
    setIsConfirming(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const updated = await ordersApi.confirmOrder(order.id);
      setOrder(updated);
      setActionSuccess("Commercial order confirmed successfully.");
      if (onOrderUpdated) onOrderUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to confirm order.";
      setActionError(msg);
    } finally {
      setIsConfirming(false);
    }
  };

  const handleAcceptAmendment = async (aid: string) => {
    if (!order) return;
    setProcessingAmendmentId(aid);
    setActionError(null);
    setActionSuccess(null);
    try {
      await ordersApi.acceptAmendment(order.id, aid);
      setActionSuccess("Order amendment accepted and terms updated.");
      await loadOrderData();
      if (onOrderUpdated) onOrderUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to accept amendment.";
      setActionError(msg);
    } finally {
      setProcessingAmendmentId(null);
    }
  };

  const handleRejectAmendment = async (aid: string) => {
    if (!order) return;
    setProcessingAmendmentId(aid);
    setActionError(null);
    setActionSuccess(null);
    try {
      await ordersApi.rejectAmendment(order.id, aid);
      setActionSuccess("Order amendment rejected. Original contract terms preserved.");
      await loadOrderData();
      if (onOrderUpdated) onOrderUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reject amendment.";
      setActionError(msg);
    } finally {
      setProcessingAmendmentId(null);
    }
  };

  const getOrderStatusBadge = (st: string) => {
    switch (st) {
      case "pending":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700">
            <Clock className="w-3.5 h-3.5 text-amber-600" aria-hidden="true" />
            Pending Farmer Confirmation
          </span>
        );
      case "confirmed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-700">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" aria-hidden="true" />
            Confirmed & Active
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-500/10 text-blue-700">
            <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" aria-hidden="true" />
            Completed
          </span>
        );
      case "cancelled":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-destructive/10 text-destructive">
            <XCircle className="w-3.5 h-3.5 text-destructive" aria-hidden="true" />
            Cancelled
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-secondary text-foreground capitalize">
            {st}
          </span>
        );
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-order-detail-title"
    >
      <div className="bg-card w-full max-w-3xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div>
            <div className="flex items-center gap-2">
              <h2 id="modal-order-detail-title" className="text-lg font-bold text-foreground">
                Order {order?.order_number || "Specifications"}
              </h2>
              {order && getOrderStatusBadge(order.status)}
            </div>
            <p className="text-xs text-muted-foreground">
              Official binding trade record created via bilateral negotiation on AgriDirect
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
        <div className="p-6 max-h-[75vh] overflow-y-auto space-y-6">
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center text-muted-foreground gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-primary" aria-hidden="true" />
              <p className="text-sm">Loading order contract specifications...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold">Unable to Load Order</p>
                <p className="text-xs">{error}</p>
              </div>
            </div>
          ) : order ? (
            <>
              {/* Feedback messages */}
              {actionSuccess && (
                <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-600" aria-hidden="true" />
                  <span>{actionSuccess}</span>
                </div>
              )}
              {actionError && (
                <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                  <span>{actionError}</span>
                </div>
              )}

              {/* Status & Participants Overview */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Farmer Card */}
                <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    <Tractor className="w-4 h-4 text-primary" aria-hidden="true" />
                    <span>Agricultural Producer</span>
                  </div>
                  <p className="font-bold text-sm text-foreground">
                    {order.farmer?.farm_name || order.farmer?.full_name || "Verified Producer"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {order.farmer?.email || "Producer Account"}
                  </p>
                </div>

                {/* Buyer Card */}
                <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    <Building className="w-4 h-4 text-blue-600" aria-hidden="true" />
                    <span>Commercial Buyer</span>
                  </div>
                  <p className="font-bold text-sm text-foreground">
                    {order.buyer?.business_name || "Verified Buyer"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Contact: {order.buyer?.full_name || order.buyer?.email || "Enterprise Representative"}
                  </p>
                </div>
              </div>

              {/* Order Line Items */}
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                  Contract Line Items ({order.items.length})
                </span>
                <div className="rounded-xl border border-border overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-secondary/60 text-muted-foreground border-b border-border font-bold">
                      <tr>
                        <th className="px-4 py-2.5">Produce Item</th>
                        <th className="px-4 py-2.5">Quality</th>
                        <th className="px-4 py-2.5 text-right">Quantity</th>
                        <th className="px-4 py-2.5 text-right">Unit Price</th>
                        <th className="px-4 py-2.5 text-right">Line Subtotal</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {order.items.map((it) => (
                        <tr key={it.id} className="hover:bg-secondary/20 transition-colors">
                          <td className="px-4 py-3 font-semibold text-foreground">
                            {it.product_name}
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">
                            {it.quality_grade || "Standard"}
                          </td>
                          <td className="px-4 py-3 text-right font-medium">
                            {it.quantity} {it.unit}
                          </td>
                          <td className="px-4 py-3 text-right text-muted-foreground font-mono">
                            ₹{Number(it.unit_price).toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-right font-bold text-foreground font-mono">
                            ₹{Number(it.subtotal).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-secondary/40 border-t border-border font-bold text-xs">
                      <tr>
                        <td colSpan={4} className="px-4 py-3 text-right text-muted-foreground">
                          Total Commercial Valuation:
                        </td>
                        <td className="px-4 py-3 text-right text-base text-primary font-black font-mono">
                          ₹{Number(order.total_amount).toLocaleString()}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Terms & Logistics */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-secondary/30 border border-border text-xs">
                <div>
                  <span className="text-muted-foreground block text-[11px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Truck className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
                    Delivery Terms & Instructions
                  </span>
                  <p className="text-foreground leading-relaxed">
                    {order.delivery_notes || "Standard delivery / Farm gate pickup as agreed"}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
                    Agreed Fulfillment Date
                  </span>
                  <p className="text-foreground font-semibold">
                    {order.delivery_arranged_date || "As scheduled"}
                  </p>
                  <div className="mt-2 text-[11px] text-muted-foreground">
                    Delivery Status:{" "}
                    <span className="font-semibold text-foreground capitalize">
                      {order.delivery_status.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>
              </div>

              {/* Delivery Coordination Controls */}
              {order.status !== "cancelled" &&
                order.status !== "completed" &&
                order.status !== "disputed" && (
                <div className="p-4 rounded-xl bg-primary-50/40 border border-primary/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                      <Truck className="w-4 h-4" />
                      Delivery Coordination
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      Current Stage:{" "}
                      <span className="font-semibold text-foreground capitalize">
                        {order.delivery_status.replace(/_/g, " ")}
                      </span>
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Update fulfillment milestones as goods move from origin to destination. Once received, the counterparty must acknowledge receipt to conclude the order.
                  </p>
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    {canArrangeDelivery && (
                      <button
                        type="button"
                        onClick={() => setIsDeliveryArrangeOpen(true)}
                        className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition-colors flex items-center gap-1"
                      >
                        <Truck className="w-3.5 h-3.5" />
                        <span>Arrange Delivery</span>
                      </button>
                    )}
                    {canMarkDeliveryCompleted && (
                      <button
                        type="button"
                        disabled={isMarkingDelivery}
                        onClick={handleMarkDeliveryCompleted}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-semibold shadow-xs transition-colors flex items-center gap-1 disabled:opacity-50"
                      >
                        {isMarkingDelivery ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        )}
                        <span>Mark Delivery Completed</span>
                      </button>
                    )}
                    {canAcknowledgeDelivery && (
                      <button
                        type="button"
                        onClick={() => setIsDeliveryAcknowledgeOpen(true)}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-semibold shadow-xs transition-colors flex items-center gap-1"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Acknowledge Delivery Receipt</span>
                      </button>
                    )}
                    {isAwaitingCounterpartyAck && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-800 text-xs font-semibold border border-amber-500/20">
                        <Clock className="w-3.5 h-3.5 text-amber-600" />
                        Awaiting counterparty delivery receipt acknowledgement
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Payment Settlement Tracking */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                    Off-Platform Payment Tracking
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsPaymentHistoryOpen(true)}
                      className="text-xs font-semibold text-primary hover:underline"
                    >
                      Payment History
                    </button>
                    {!isFarmerSeller && order.status !== "cancelled" && (
                      <button
                        type="button"
                        onClick={() => setIsPaymentRecordOpen(true)}
                        className="px-2.5 py-1 rounded-md bg-primary text-primary-foreground text-xs font-semibold shadow-xs hover:bg-primary/90 transition-colors"
                      >
                        + Record Payment
                      </button>
                    )}
                  </div>
                </div>
                <PaymentSummaryCard summary={paymentSummary} isLoading={isLoading} />
              </div>

              {/* Completed Order Review Section */}
              {order.status === "completed" && (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
                  <div>
                    <span className="font-bold text-foreground flex items-center gap-1.5">
                      <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                      Order Concluded — Leave Feedback
                    </span>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Share your experience regarding produce quality, punctuality, and communication.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsReviewModalOpen(true)}
                    className="shrink-0 px-3.5 py-1.5 rounded-lg bg-amber-500 text-white hover:bg-amber-600 font-semibold shadow-xs transition-colors flex items-center gap-1"
                  >
                    <Star className="w-3.5 h-3.5 fill-white" />
                    <span>Rate Deal</span>
                  </button>
                </div>
              )}

              {/* Amendments Section */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                    Post-Finalization Amendments ({amendments.length})
                  </span>
                  {order.status === "confirmed" && !hasPendingAmendment && (
                    <button
                      type="button"
                      onClick={() => setIsAmendmentModalOpen(true)}
                      className="text-xs font-semibold text-primary hover:text-primary/80 transition-colors"
                    >
                      + Propose Amendment
                    </button>
                  )}
                </div>

                {amendments.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">
                    No amendments proposed. Original contract terms remain in effect.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {amendments.map((amd) => {
                      const isProposer = user?.id === amd.proposed_by_user_id;
                      const isPending = amd.status === "proposed";

                      return (
                        <div
                          key={amd.id}
                          className="p-3.5 rounded-xl border border-border bg-card space-y-2 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-foreground uppercase tracking-wider text-[11px]">
                                {amd.amendment_type} Amendment
                              </span>
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold capitalize ${
                                  amd.status === "effective"
                                    ? "bg-emerald-500/10 text-emerald-700"
                                    : amd.status === "rejected"
                                    ? "bg-destructive/10 text-destructive"
                                    : "bg-amber-500/10 text-amber-700"
                                }`}
                              >
                                {amd.status}
                              </span>
                            </div>
                            <span className="text-[11px] text-muted-foreground font-mono">
                              {new Date(amd.created_at).toLocaleDateString()}
                            </span>
                          </div>

                          <div className="text-xs text-foreground bg-secondary/30 p-2.5 rounded-lg border border-border/50 space-y-1.5">
                            <div>
                              <span className="text-muted-foreground block text-[11px]">Justification:</span>
                              <p className="font-medium">{amd.justification}</p>
                            </div>
                            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/50 text-[11px]">
                              <div>
                                <span className="text-muted-foreground block">Previous Specification:</span>
                                <span className="font-mono text-muted-foreground">{amd.old_value || "—"}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground block">Amended Proposal:</span>
                                <span className="font-mono font-bold text-primary">{amd.new_value}</span>
                              </div>
                            </div>
                          </div>

                          {isPending && (
                            <div className="pt-1 flex items-center justify-end gap-2">
                              {isProposer ? (
                                <span className="text-[11px] text-amber-700 italic">
                                  Awaiting counterparty review
                                </span>
                              ) : (
                                <>
                                  <button
                                    type="button"
                                    disabled={processingAmendmentId === amd.id}
                                    onClick={() => handleRejectAmendment(amd.id)}
                                    className="px-3 py-1 rounded-lg border border-destructive/30 text-destructive hover:bg-destructive/10 text-xs font-semibold transition-colors disabled:opacity-50"
                                  >
                                    Reject
                                  </button>
                                  <button
                                    type="button"
                                    disabled={processingAmendmentId === amd.id}
                                    onClick={() => handleAcceptAmendment(amd.id)}
                                    className="px-3.5 py-1 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold transition-colors disabled:opacity-50"
                                  >
                                    Accept Amendment
                                  </button>
                                </>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* System Governance & Non-Involvement Notice */}
              <div className="p-3.5 rounded-xl bg-secondary/40 border border-border text-[11px] text-muted-foreground flex items-start gap-2.5">
                <DollarSign className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="leading-relaxed">
                  AgriDirect is a pure trade matching platform. Payments and physical transportation
                  are settled directly between buyer and farmer in accordance with agreed terms.
                  AgriDirect never holds funds, processes escrow, or takes custody of agricultural commodities.
                </p>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-3 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3 bg-secondary/20">
          <div className="flex items-center gap-3">
            {order && (
              <>
                <button
                  type="button"
                  onClick={() => setIsAuditModalOpen(true)}
                  className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground font-semibold transition-colors"
                >
                  <History className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Audit Ledger</span>
                </button>
                <button
                  type="button"
                  onClick={handleMessageCounterparty}
                  disabled={isMessaging}
                  className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline font-semibold transition-colors disabled:opacity-50"
                >
                  {isMessaging ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <MessageSquare className="w-3.5 h-3.5" />
                  )}
                  <span>Message Counterparty</span>
                </button>
                <button
                  type="button"
                  onClick={() => setIsReportModalOpen(true)}
                  className="inline-flex items-center gap-1.5 text-xs text-destructive hover:underline font-semibold transition-colors"
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Report</span>
                </button>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
            >
              Close
            </button>

            {/* Cancel Button */}
            {order && (order.status === "pending" || order.status === "confirmed") && (
              <button
                type="button"
                onClick={() => setIsCancelModalOpen(true)}
                className="px-4 py-2 rounded-xl border border-destructive/30 text-destructive hover:bg-destructive/10 text-xs font-bold transition-colors flex items-center gap-1.5"
              >
                <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Cancel Order</span>
              </button>
            )}

            {/* Confirm Order (Farmer only, when pending) */}
            {order && order.status === "pending" && isFarmerSeller && (
              <button
                type="button"
                disabled={isConfirming}
                onClick={handleConfirmOrder}
                className="px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                {isConfirming ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                    <span>Confirming...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Confirm Order</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Sub-modals */}
      {order && (
        <>
          <OrderCancelModal
            isOpen={isCancelModalOpen}
            order={order}
            onClose={() => setIsCancelModalOpen(false)}
            onSuccess={(updated) => {
              setOrder(updated);
              if (onOrderUpdated) onOrderUpdated();
            }}
          />

          <AmendmentProposalModal
            isOpen={isAmendmentModalOpen}
            order={order}
            onClose={() => setIsAmendmentModalOpen(false)}
            onSuccess={() => {
              void loadOrderData();
              if (onOrderUpdated) onOrderUpdated();
            }}
          />

          <InventoryAuditModal
            isOpen={isAuditModalOpen}
            orderId={order.id}
            orderNumber={order.order_number}
            onClose={() => setIsAuditModalOpen(false)}
          />

          <DeliveryArrangeModal
            isOpen={isDeliveryArrangeOpen}
            order={order}
            onClose={() => setIsDeliveryArrangeOpen(false)}
            onSuccess={(updated) => {
              setOrder(updated);
              if (onOrderUpdated) onOrderUpdated();
            }}
          />

          <DeliveryAcknowledgeModal
            isOpen={isDeliveryAcknowledgeOpen}
            order={order}
            onClose={() => setIsDeliveryAcknowledgeOpen(false)}
            onSuccess={(updated) => {
              setOrder(updated);
              if (onOrderUpdated) onOrderUpdated();
            }}
          />

          <PaymentRecordModal
            isOpen={isPaymentRecordOpen}
            orderId={order.id}
            orderNumber={order.order_number}
            maxPayableAmount={paymentSummary?.max_available_for_new_payment}
            onClose={() => setIsPaymentRecordOpen(false)}
            onSuccess={() => {
              void loadOrderData();
              if (onOrderUpdated) onOrderUpdated();
            }}
          />

          <PaymentHistoryModal
            isOpen={isPaymentHistoryOpen}
            orderId={order.id}
            orderNumber={order.order_number}
            isFarmer={isFarmerSeller}
            onClose={() => setIsPaymentHistoryOpen(false)}
            onPaymentUpdated={() => {
              void loadOrderData();
              if (onOrderUpdated) onOrderUpdated();
            }}
          />

          <ReviewSubmitModal
            isOpen={isReviewModalOpen}
            orderId={order.id}
            orderReference={order.order_number}
            counterpartyName={counterpartyName}
            onClose={() => setIsReviewModalOpen(false)}
            onSuccess={() => {
              setActionSuccess("Review submitted successfully.");
              if (onOrderUpdated) onOrderUpdated();
            }}
          />

          <ReportCreateModal
            isOpen={isReportModalOpen}
            reportedUserId={counterpartyId}
            reportedUserName={counterpartyName}
            onClose={() => setIsReportModalOpen(false)}
            onSuccess={() => {
              setActionSuccess("Safety report submitted.");
            }}
          />
        </>
      )}
    </div>
  );
};
