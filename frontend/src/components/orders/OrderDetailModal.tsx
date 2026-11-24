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
  FileText,
  Check,
  Printer,
  Image as ImageIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { ordersApi } from "../../api/orders";
import { chatApi } from "../../api/chat";
import { paymentsApi } from "../../api/payments";
import { useAuth } from "../../store/authStore";
import type { OrderDetail, OrderAmendment } from "../../types/orders";
import type { PaymentSummary } from "../../types/payments";
import { formatDate, formatNumber } from "../../utils/formatters";
import { OrderCancelModal } from "./OrderCancelModal";
import { AmendmentProposalModal } from "./AmendmentProposalModal";
import { InventoryAuditModal } from "./InventoryAuditModal";
import { DeliveryArrangeModal } from "./DeliveryArrangeModal";
import { DeliveryAcknowledgeModal } from "./DeliveryAcknowledgeModal";
import { DealTransportSection } from "../transport/DealTransportSection";
import { PaymentSummaryCard } from "../payments/PaymentSummaryCard";
import { PaymentRecordModal } from "../payments/PaymentRecordModal";
import { PaymentHistoryModal } from "../payments/PaymentHistoryModal";
import { ReviewSubmitModal } from "../reviews/ReviewSubmitModal";
import { ReportCreateModal } from "../reports/ReportCreateModal";
import { OrderSlipModal } from "./OrderSlipModal";

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
  const { t } = useTranslation(["orders", "common", "errors", "navigation"]);
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
  const [isSlipModalOpen, setIsSlipModalOpen] = useState(false);

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
      const msg =
        err instanceof Error
          ? err.message
          : t("orders:detail.load_failed", "Failed to load order specifications.");
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [orderId, t]);

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
    ? order?.buyer?.business_name ||
      order?.buyer?.full_name ||
      t("orders:detail.buyer_default_name", "Commercial Buyer")
    : order?.farmer?.farm_name ||
      order?.farmer?.full_name ||
      t("orders:detail.farmer_default_name", "Agricultural Producer");

  const hasPendingAmendment = amendments.some((a) => a.status === "proposed");

  const formatDeliveryStatus = (status: unknown): string => {
    if (typeof status === "string" && status.trim().length > 0) {
      return status.replace(/_/g, " ");
    }
    return t("orders:detail.delivery_status_unavailable", "Unavailable");
  };

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
      setActionSuccess(
        t(
          "orders:detail.delivery_marked_success",
          "Delivery marked as completed by seller. Awaiting counterparty acknowledgement."
        )
      );
      if (onOrderUpdated) onOrderUpdated();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("orders:detail.mark_delivery_failed", "Failed to mark delivery completed.");
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
      setActionSuccess(
        t("orders:detail.order_confirmed_success", "Commercial order confirmed successfully.")
      );
      if (onOrderUpdated) onOrderUpdated();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("orders:detail.confirm_failed", "Failed to confirm order.");
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
      setActionSuccess(
        t("orders:detail.amendment_accepted_success", "Order amendment accepted and terms updated.")
      );
      await loadOrderData();
      if (onOrderUpdated) onOrderUpdated();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("orders:detail.accept_amendment_failed", "Failed to accept amendment.");
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
      setActionSuccess(
        t(
          "orders:detail.amendment_rejected_success",
          "Order amendment rejected. Original contract terms preserved."
        )
      );
      await loadOrderData();
      if (onOrderUpdated) onOrderUpdated();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("orders:detail.reject_amendment_failed", "Failed to reject amendment.");
      setActionError(msg);
    } finally {
      setProcessingAmendmentId(null);
    }
  };

  const getOrderStages = () => {
    if (!order) return [];

    const isCancelled = order.status === "cancelled";
    const isCompleted = order.status === "completed";

    // Stage 1: Created
    const s1Status = isCancelled ? "cancelled" : "complete";

    // Stage 2: Confirmed
    let s2Status: "complete" | "current" | "upcoming" | "cancelled" = "upcoming";
    let s2Desc = t("orders:lifecycle.terms_locked", "Terms locked");
    if (isCancelled) {
      s2Status = "cancelled";
    } else if (order.status === "pending") {
      s2Status = "current";
      s2Desc = t("orders:lifecycle.awaiting_confirmation", "Awaiting confirmation");
    } else {
      s2Status = "complete";
    }

    // Stage 3: In Transit / Dispatched
    let s3Status: "complete" | "current" | "upcoming" | "cancelled" = "upcoming";
    let s3Desc = t("orders:lifecycle.pending_dispatch", "Pending dispatch");
    if (isCancelled) {
      s3Status = "cancelled";
    } else if (order.status === "pending") {
      s3Status = "upcoming";
    } else if (order.delivery_status === "not_arranged") {
      s3Status = "current";
      s3Desc = t("orders:lifecycle.arrange_logistics", "Arrange logistics");
    } else {
      s3Status = "complete";
      s3Desc = t("orders:lifecycle.dispatched_enroute", "Dispatched / En route");
    }

    // Stage 4: Delivery Receipt
    let s4Status: "complete" | "current" | "upcoming" | "cancelled" = "upcoming";
    let s4Desc = t("orders:lifecycle.awaiting_delivery", "Awaiting delivery");
    if (isCancelled) {
      s4Status = "cancelled";
    } else if (order.delivery_status === "completed" || isCompleted) {
      s4Status = "complete";
      s4Desc = t("orders:lifecycle.receipt_confirmed", "Receipt confirmed");
    } else if (order.delivery_status === "completion_marked") {
      s4Status = "current";
      s4Desc = t("orders:lifecycle.pending_acknowledgement", "Pending acknowledgement");
    }

    // Stage 5: Settlement & Concluded
    let s5Status: "complete" | "current" | "upcoming" | "cancelled" = "upcoming";
    let s5Desc = t("orders:lifecycle.direct_settlement", "Direct settlement");
    if (isCancelled) {
      s5Status = "cancelled";
    } else if (isCompleted) {
      s5Status = "complete";
      s5Desc = t("orders:lifecycle.trade_concluded", "Trade concluded");
    } else if (order.delivery_status === "completed") {
      s5Status = "current";
      s5Desc = t("orders:lifecycle.finalizing_records", "Finalizing records");
    }

    return [
      {
        id: "created",
        step: 1,
        label: t("orders:lifecycle.created", "Created"),
        desc: t("orders:lifecycle.contract_bound", "Contract bound"),
        status: s1Status,
      },
      {
        id: "confirmed",
        step: 2,
        label: t("orders:lifecycle.confirmed", "Confirmed"),
        desc: s2Desc,
        status: s2Status,
      },
      {
        id: "transit",
        step: 3,
        label: t("orders:lifecycle.in_transit", "In Transit"),
        desc: s3Desc,
        status: s3Status,
      },
      {
        id: "received",
        step: 4,
        label: t("orders:lifecycle.delivered", "Delivered"),
        desc: s4Desc,
        status: s4Status,
      },
      {
        id: "concluded",
        step: 5,
        label: t("orders:lifecycle.concluded", "Concluded"),
        desc: s5Desc,
        status: s5Status,
      },
    ];
  };

  const getOrderStatusBadge = (st: string) => {
    switch (st) {
      case "pending":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700">
            <Clock className="w-3.5 h-3.5 text-amber-600" aria-hidden="true" />
            {t("orders:status.pending_farmer_confirmation", "Pending Farmer Confirmation")}
          </span>
        );
      case "confirmed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-700">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" aria-hidden="true" />
            {t("orders:status.confirmed_active", "Confirmed & Active")}
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-500/10 text-blue-700">
            <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" aria-hidden="true" />
            {t("orders:status.completed", "Completed")}
          </span>
        );
      case "cancelled":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-destructive/10 text-destructive">
            <XCircle className="w-3.5 h-3.5 text-destructive" aria-hidden="true" />
            {t("orders:status.cancelled", "Cancelled")}
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
                {order
                  ? t("orders:detail.order_title", "Order {{orderNumber}}", {
                      orderNumber: order.order_number,
                    })
                  : t("orders:detail.order_specs", "Order Specifications")}
              </h2>
              {order && getOrderStatusBadge(order.status)}
            </div>
            <p className="text-xs text-muted-foreground">
              {t(
                "orders:detail.subtitle",
                "Official binding trade record created via bilateral negotiation on AgriDirect"
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {order && (order.status === "completed" || order.status === "confirmed") && (
              <button
                type="button"
                onClick={() => setIsSlipModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 text-xs font-semibold transition-colors shadow-xs"
                title={t(
                  "orders:detail.trade_slip_tooltip",
                  "Print or download official B2B trade confirmation slip"
                )}
              >
                <Printer className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{t("orders:detail.trade_slip", "Trade Slip")}</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
              aria-label={t("common:actions.close", "Close dialog")}
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[75vh] overflow-y-auto space-y-6">
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center text-muted-foreground gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-primary" aria-hidden="true" />
              <p className="text-sm">
                {t("orders:detail.loading_specs", "Loading order contract specifications...")}
              </p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold">{t("orders:detail.unable_to_load", "Unable to Load Order")}</p>
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

              {/* Chronological Bilateral Trade Lifecycle Stepper */}
              <div className="p-4 rounded-xl border border-border bg-secondary/20 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
                    {t("orders:lifecycle_title", "Bilateral Trade Lifecycle")}
                  </span>
                  {order.status === "cancelled" ? (
                    <span className="text-xs font-semibold text-destructive flex items-center gap-1">
                      <XCircle className="w-3.5 h-3.5" aria-hidden="true" />{" "}
                      {t("orders:status.order_cancelled", "Order Cancelled")}
                    </span>
                  ) : order.status === "completed" ? (
                    <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />{" "}
                      {t("orders:status.trade_concluded", "Trade Concluded")}
                    </span>
                  ) : (
                    <span className="text-xs font-medium text-muted-foreground">
                      {t("orders:lifecycle.active_stage", "Active Stage:")}{" "}
                      <span className="font-semibold text-foreground capitalize">
                        {order.delivery_status === "completed"
                          ? t("orders:lifecycle.final_settlement", "Final Settlement")
                          : order.delivery_status === "completion_marked"
                          ? t("orders:lifecycle.receipt_ack", "Receipt Ack")
                          : order.delivery_status === "arranged"
                          ? t("orders:lifecycle.in_transit", "In Transit")
                          : order.status === "confirmed"
                          ? t("orders:lifecycle.logistics_planning", "Logistics Planning")
                          : t("orders:lifecycle.confirmation", "Confirmation")}
                      </span>
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  {getOrderStages().map((st) => {
                    const isComplete = st.status === "complete";
                    const isCurrent = st.status === "current";
                    const isCancelled = st.status === "cancelled";

                    return (
                      <div
                        key={st.id}
                        className={`p-2.5 rounded-lg border text-xs transition-colors flex flex-col justify-between ${
                          isComplete
                            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-800"
                            : isCurrent
                            ? "bg-primary/10 border-primary text-foreground shadow-xs"
                            : isCancelled
                            ? "bg-destructive/5 border-destructive/20 text-muted-foreground opacity-60"
                            : "bg-card/70 border-border text-muted-foreground"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span
                            className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                              isComplete
                                ? "bg-emerald-600 text-white"
                                : isCurrent
                                ? "bg-primary text-primary-foreground animate-pulse"
                                : isCancelled
                                ? "bg-destructive text-destructive-foreground"
                                : "bg-secondary text-muted-foreground"
                            }`}
                          >
                            {isComplete ? <Check className="w-3 h-3" aria-hidden="true" /> : st.step}
                          </span>
                          <span className="text-[10px] font-semibold uppercase tracking-wider">
                            {isComplete
                              ? t("common:status.done", "Done")
                              : isCurrent
                              ? t("common:status.active", "Active")
                              : isCancelled
                              ? t("common:status.void", "Void")
                              : t("common:status.next", "Next")}
                          </span>
                        </div>
                        <div>
                          <p className="font-bold text-xs leading-tight text-foreground">
                            {st.label}
                          </p>
                          <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                            {st.desc}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Status & Participants Overview */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Farmer Card */}
                <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    <Tractor className="w-4 h-4 text-primary" aria-hidden="true" />
                    <span>{t("orders:detail.producer_card_title", "Agricultural Producer")}</span>
                  </div>
                  <p className="font-bold text-sm text-foreground">
                    {order.farmer?.farm_name ||
                      order.farmer?.full_name ||
                      t("orders:detail.verified_producer", "Verified Producer")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {order.farmer?.email ||
                      t("orders:detail.producer_account", "Producer Account")}
                  </p>
                </div>

                {/* Buyer Card */}
                <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    <Building className="w-4 h-4 text-blue-600" aria-hidden="true" />
                    <span>{t("orders:detail.buyer_card_title", "Commercial Buyer")}</span>
                  </div>
                  <p className="font-bold text-sm text-foreground">
                    {order.buyer?.business_name ||
                      t("orders:detail.verified_buyer", "Verified Buyer")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {t("orders:detail.contact_prefix", "Contact:")}{" "}
                    {order.buyer?.full_name ||
                      order.buyer?.email ||
                      t("orders:detail.enterprise_rep", "Enterprise Representative")}
                  </p>
                </div>
              </div>

              {/* Order Line Items */}
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                  {t("orders:detail.items_count", "Contract Line Items ({{count}})", {
                    count: order.items.length,
                  })}
                </span>
                <div className="rounded-xl border border-border overflow-hidden">
                  <table className="w-full text-start text-xs">
                    <thead className="bg-secondary/60 text-muted-foreground border-b border-border font-bold">
                      <tr>
                        <th className="px-4 py-2.5">{t("orders:detail.col_item", "Produce Item")}</th>
                        <th className="px-4 py-2.5">{t("orders:detail.col_quality", "Quality")}</th>
                        <th className="px-4 py-2.5 text-end">{t("orders:detail.col_quantity", "Quantity")}</th>
                        <th className="px-4 py-2.5 text-end">{t("orders:detail.col_unit_price", "Unit Price")}</th>
                        <th className="px-4 py-2.5 text-end">{t("orders:detail.col_subtotal", "Line Subtotal")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {order.items.map((it) => (
                        <tr key={it.id} className="hover:bg-secondary/20 transition-colors">
                          <td className="px-4 py-3 font-semibold text-foreground">
                            {it.product_name}
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">
                            {it.quality_grade || t("orders:detail.standard_grade", "Standard")}
                          </td>
                          <td className="px-4 py-3 text-end font-medium">
                            {formatNumber(it.quantity)} {it.unit}
                          </td>
                          <td className="px-4 py-3 text-end text-muted-foreground font-mono">
                            ₹{formatNumber(Number(it.unit_price))}
                          </td>
                          <td className="px-4 py-3 text-end font-bold text-foreground font-mono">
                            ₹{formatNumber(Number(it.subtotal))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-secondary/40 border-t border-border font-bold text-xs">
                      <tr>
                        <td colSpan={4} className="px-4 py-3 text-end text-muted-foreground">
                          {t("orders:detail.total_valuation", "Total Commercial Valuation:")}
                        </td>
                        <td className="px-4 py-3 text-end text-base text-primary font-black font-mono">
                          ₹{formatNumber(Number(order.total_amount))}
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
                    {t("orders:detail.delivery_terms_title", "Delivery Terms & Instructions")}
                  </span>
                  <p className="text-foreground leading-relaxed">
                    {order.delivery_notes ||
                      t(
                        "orders:detail.default_delivery_notes",
                        "Standard delivery / Farm gate pickup as agreed"
                      )}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
                    {t("orders:detail.fulfillment_date_title", "Agreed Fulfillment Date")}
                  </span>
                  <p className="text-foreground font-semibold">
                    {order.delivery_arranged_date
                      ? formatDate(order.delivery_arranged_date)
                      : t("orders:detail.as_scheduled", "As scheduled")}
                  </p>
                  <div className="mt-2 text-[11px] text-muted-foreground">
                    {t("orders:detail.delivery_status_label", "Delivery Status:")}{" "}
                    <span className="font-semibold text-foreground capitalize">
                      {formatDeliveryStatus(order.delivery_status)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Attached Order Images & Documentation (Phase 2) */}
              {order.images && order.images.length > 0 && (
                <div className="p-4 rounded-xl border border-border bg-card space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <ImageIcon className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
                      <span>{t("orders:detail.order_photographs", "Order Documentation & Quality Photographs")}</span>
                    </span>
                    <span className="text-[11px] font-normal text-muted-foreground">
                      {order.images.length} {t("orders:detail.photos_attached", "photos attached")}
                    </span>
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {order.images.map((img) => (
                      <a
                        key={img.id}
                        href={img.image_url}
                        target="_blank"
                        rel="noreferrer"
                        className="group relative aspect-video rounded-lg overflow-hidden border border-border hover:border-primary transition-all bg-secondary/30 flex items-center justify-center"
                      >
                        <img
                          src={img.image_url}
                          alt="Order document"
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Delivery Coordination Controls */}
              {order.status !== "cancelled" &&
                order.status !== "completed" &&
                order.status !== "disputed" && (
                <div className="p-4 rounded-xl bg-primary-50/40 border border-primary/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                      <Truck className="w-4 h-4" />
                      {t("orders:detail.coordination_title", "Delivery Coordination")}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {t("orders:detail.current_stage_label", "Current Stage:")}{" "}
                      <span className="font-semibold text-foreground capitalize">
                        {formatDeliveryStatus(order.delivery_status)}
                      </span>
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {t(
                      "orders:detail.coordination_desc",
                      "Update fulfillment milestones as goods move from origin to destination. Once received, the counterparty must acknowledge receipt to conclude the order."
                    )}
                  </p>
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    {canArrangeDelivery && (
                      <button
                        type="button"
                        onClick={() => setIsDeliveryArrangeOpen(true)}
                        className="px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition-colors flex items-center gap-1"
                      >
                        <Truck className="w-3.5 h-3.5" />
                        <span>{t("orders:detail.btn_arrange_delivery", "Arrange Delivery")}</span>
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
                        <span>
                          {t("orders:detail.btn_mark_completed", "Mark Delivery Completed")}
                        </span>
                      </button>
                    )}
                    {canAcknowledgeDelivery && (
                      <button
                        type="button"
                        onClick={() => setIsDeliveryAcknowledgeOpen(true)}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-semibold shadow-xs transition-colors flex items-center gap-1"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>
                          {t(
                            "orders:detail.btn_acknowledge_receipt",
                            "Acknowledge Delivery Receipt"
                          )}
                        </span>
                      </button>
                    )}
                    {isAwaitingCounterpartyAck && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-800 text-xs font-semibold border border-amber-500/20">
                        <Clock className="w-3.5 h-3.5 text-amber-600" />
                        {t(
                          "orders:detail.awaiting_ack",
                          "Awaiting counterparty delivery receipt acknowledgement"
                        )}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Transportation & Hauling Connection Section */}
              <DealTransportSection
                orderId={order.id}
                orderNumber={order.order_number}
                offerId={order.source_offer_id || null}
                deliveryAddress={order.delivery_destination_address || ""}
                cargoDescription={order.items?.map((it) => `${it.product_name} (${it.quantity} ${it.unit})`).join(", ")}
                weightKg={
                  order.items?.reduce(
                    (acc, it) => (it.unit?.toLowerCase() === "kg" ? acc + Number(it.quantity) : acc),
                    0
                  ) || undefined
                }
                requiredDeliveryDate={order.delivery_arranged_date || undefined}
                canRequest={isParticipant}
                onTransportUpdated={() => void loadOrderData()}
              />

              {/* Payment Settlement Tracking */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                    {t(
                      "orders:detail.payment_tracking_title",
                      "Off-Platform Payment Tracking"
                    )}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsPaymentHistoryOpen(true)}
                      className="text-xs font-semibold text-primary hover:underline"
                    >
                      {t("orders:detail.payment_history_link", "Payment History")}
                    </button>
                    {!isFarmerSeller && order.status !== "cancelled" && (
                      <button
                        type="button"
                        onClick={() => setIsPaymentRecordOpen(true)}
                        className="px-2.5 py-1 rounded-md bg-primary text-primary-foreground text-xs font-semibold shadow-xs hover:bg-primary/90 transition-colors"
                      >
                        {t("orders:detail.btn_record_payment", "+ Record Payment")}
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
                      {t(
                        "orders:detail.concluded_feedback_title",
                        "Order Concluded — Leave Feedback"
                      )}
                    </span>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      {t(
                        "orders:detail.concluded_feedback_desc",
                        "Share your experience regarding produce quality, punctuality, and communication."
                      )}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsReviewModalOpen(true)}
                    className="shrink-0 px-3.5 py-1.5 rounded-lg bg-amber-500 text-white hover:bg-amber-600 font-semibold shadow-xs transition-colors flex items-center gap-1"
                  >
                    <Star className="w-3.5 h-3.5 fill-white" />
                    <span>{t("orders:detail.btn_rate_deal", "Rate Deal")}</span>
                  </button>
                </div>
              )}

              {/* Amendments Section */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                    {t(
                      "orders:detail.amendments_count",
                      "Post-Finalization Amendments ({{count}})",
                      { count: amendments.length }
                    )}
                  </span>
                  {order.status === "confirmed" && !hasPendingAmendment && (
                    <button
                      type="button"
                      onClick={() => setIsAmendmentModalOpen(true)}
                      className="text-xs font-semibold text-primary hover:text-primary/80 transition-colors"
                    >
                      {t("orders:detail.btn_propose_amendment", "+ Propose Amendment")}
                    </button>
                  )}
                </div>

                {amendments.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">
                    {t(
                      "orders:detail.no_amendments",
                      "No amendments proposed. Original contract terms remain in effect."
                    )}
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
                                {amd.amendment_type}{" "}
                                {t("orders:detail.amendment_suffix", "Amendment")}
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
                              {formatDate(amd.created_at)}
                            </span>
                          </div>

                          <div className="text-xs text-foreground bg-secondary/30 p-2.5 rounded-lg border border-border/50 space-y-1.5">
                            <div>
                              <span className="text-muted-foreground block text-[11px]">
                                {t("orders:detail.justification_label", "Justification:")}
                              </span>
                              <p className="font-medium">{amd.justification}</p>
                            </div>
                            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/50 text-[11px]">
                              <div>
                                <span className="text-muted-foreground block">
                                  {t("orders:detail.prev_spec_label", "Previous Specification:")}
                                </span>
                                <span className="font-mono text-muted-foreground">
                                  {amd.old_value || "—"}
                                </span>
                              </div>
                              <div>
                                <span className="text-muted-foreground block">
                                  {t("orders:detail.amended_proposal_label", "Amended Proposal:")}
                                </span>
                                <span className="font-mono font-bold text-primary">
                                  {amd.new_value}
                                </span>
                              </div>
                            </div>
                          </div>

                          {isPending && (
                            <div className="pt-1 flex items-center justify-end gap-2">
                              {isProposer ? (
                                <span className="text-[11px] text-amber-700 italic">
                                  {t(
                                    "orders:detail.awaiting_review",
                                    "Awaiting counterparty review"
                                  )}
                                </span>
                              ) : (
                                <>
                                  <button
                                    type="button"
                                    disabled={processingAmendmentId === amd.id}
                                    onClick={() => handleRejectAmendment(amd.id)}
                                    className="px-3 py-1 rounded-lg border border-destructive/30 text-destructive hover:bg-destructive/10 text-xs font-semibold transition-colors disabled:opacity-50"
                                  >
                                    {t("common:actions.reject", "Reject")}
                                  </button>
                                  <button
                                    type="button"
                                    disabled={processingAmendmentId === amd.id}
                                    onClick={() => handleAcceptAmendment(amd.id)}
                                    className="px-3.5 py-1 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold transition-colors disabled:opacity-50"
                                  >
                                    {t("orders:detail.btn_accept_amendment", "Accept Amendment")}
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
                  {t(
                    "orders:detail.disclaimer",
                    "AgriDirect is a pure trade matching platform. Payments and physical transportation are settled directly between buyer and farmer in accordance with agreed terms. AgriDirect never holds funds, processes escrow, or takes custody of agricultural commodities."
                  )}
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
                  <span>{t("orders:detail.btn_audit_ledger", "Audit Ledger")}</span>
                </button>
                {(order.status === "completed" || order.status === "confirmed") && (
                  <button
                    type="button"
                    onClick={() => setIsSlipModalOpen(true)}
                    className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline font-semibold transition-colors"
                  >
                    <Printer className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>{t("orders:detail.btn_print_slip", "Print Slip")}</span>
                  </button>
                )}
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
                  <span>
                    {t("orders:detail.btn_message_counterparty", "Message Counterparty")}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => setIsReportModalOpen(true)}
                  className="inline-flex items-center gap-1.5 text-xs text-destructive hover:underline font-semibold transition-colors"
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>{t("orders:detail.btn_report", "Report")}</span>
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
              {t("common:actions.close", "Close")}
            </button>

            {/* Cancel Button */}
            {order && (order.status === "pending" || order.status === "confirmed") && (
              <button
                type="button"
                onClick={() => setIsCancelModalOpen(true)}
                className="px-4 py-2 rounded-xl border border-destructive/30 text-destructive hover:bg-destructive/10 text-xs font-bold transition-colors flex items-center gap-1.5"
              >
                <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{t("orders:cancel_order", "Cancel Order")}</span>
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
                    <span>{t("orders:detail.confirming", "Confirming...")}</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>{t("orders:confirm_order", "Confirm Order")}</span>
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

          <OrderSlipModal
            isOpen={isSlipModalOpen}
            order={order}
            paymentSummary={paymentSummary}
            onClose={() => setIsSlipModalOpen(false)}
          />
        </>
      )}
    </div>
  );
};
