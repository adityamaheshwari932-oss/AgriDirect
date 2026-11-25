import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Truck,
  MapPin,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ShieldAlert,
  Plus,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../store/authStore";
import { transportersApi } from "../../api/transporters";
import type {
  TransportConnectionRequest,
  TransporterSearchResult,
} from "../../types/transporter";
import { TransporterCard } from "./TransporterCard";
import { TransporterDetailModal } from "./TransporterDetailModal";
import { TransportConnectionModal } from "./TransportConnectionModal";
import { formatNumber, formatDate } from "../../utils/formatters";

interface DealTransportSectionProps {
  orderId?: string | null;
  orderNumber?: string | null;
  offerId?: string | null;
  offerNumber?: string | null;
  pickupState?: string;
  pickupDistrict?: string;
  pickupAddress?: string;
  deliveryState?: string;
  deliveryDistrict?: string;
  deliveryAddress?: string;
  cargoDescription?: string;
  weightKg?: number;
  requiredDeliveryDate?: string;
  canRequest?: boolean;
  onTransportUpdated?: () => void;
}

export const DealTransportSection: React.FC<DealTransportSectionProps> = ({
  orderId,
  orderNumber,
  offerId,
  offerNumber,
  pickupState = "",
  pickupDistrict = "",
  pickupAddress = "",
  deliveryState = "",
  deliveryDistrict = "",
  deliveryAddress = "",
  cargoDescription = "",
  weightKg,
  requiredDeliveryDate = "",
  canRequest = true,
  onTransportUpdated,
}) => {
  const { t } = useTranslation(["delivery", "common"]);
  const { user } = useAuth();
  const isVerified = user?.role === "admin" || user?.verification_status === "verified";

  const [connectionRequests, setConnectionRequests] = useState<TransportConnectionRequest[]>([]);
  const [recommendedTransporters, setRecommendedTransporters] = useState<TransporterSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Counterparty approval/rejection state
  const [rejectingRequestId, setRejectingRequestId] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  // Modals
  const [detailTransporter, setDetailTransporter] = useState<TransporterSearchResult | null>(null);
  const [connectTransporter, setConnectTransporter] = useState<TransporterSearchResult | null>(null);

  const loadTransportData = useCallback(async () => {
    if (!orderId && !offerId) return;
    setLoading(true);
    setError(null);
    try {
      const [reqsResponse, discResponse] = await Promise.all([
        transportersApi.listConnectionRequests({
          order_id: orderId || undefined,
          offer_id: offerId || undefined,
          page_size: 10,
        }).catch(() => ({ total: 0, items: [] })),
        transportersApi.discoverTransporters({
          pickup_state: pickupState || undefined,
          pickup_district: pickupDistrict || undefined,
          delivery_state: deliveryState || undefined,
          delivery_district: deliveryDistrict || undefined,
          min_capacity_kg: weightKg || undefined,
          only_available: true,
          page_size: 4,
        }).catch(() => ({ total: 0, items: [] })),
      ]);

      setConnectionRequests(reqsResponse.items || []);
      setRecommendedTransporters(discResponse.items || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load transport details.");
    } finally {
      setLoading(false);
    }
  }, [orderId, offerId, pickupState, pickupDistrict, deliveryState, deliveryDistrict, weightKg]);

  useEffect(() => {
    void loadTransportData();
  }, [loadTransportData]);

  const handleCancelRequest = async (requestId: string) => {
    try {
      await transportersApi.cancelConnectionRequest(requestId);
      void loadTransportData();
      if (onTransportUpdated) onTransportUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to cancel request.");
    }
  };

  const handleApproveAssignment = async (requestId: string) => {
    try {
      setActionLoading(true);
      await transportersApi.approveConnectionRequest(requestId);
      void loadTransportData();
      if (onTransportUpdated) onTransportUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to approve assignment.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectAssignment = async (requestId: string, reason?: string) => {
    try {
      setActionLoading(true);
      await transportersApi.rejectConnectionRequest(requestId, {
        counterparty_rejection_reason: reason || undefined,
      });
      setRejectingRequestId(null);
      setRejectionReason("");
      void loadTransportData();
      if (onTransportUpdated) onTransportUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to reject assignment.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleConnectionSuccess = () => {
    void loadTransportData();
    if (onTransportUpdated) onTransportUpdated();
  };

  const marketplaceUrl = `/dashboard/transporters?${new URLSearchParams({
    ...(orderId ? { order_id: orderId, order_number: orderNumber || "" } : {}),
    ...(offerId ? { offer_id: offerId, offer_number: offerNumber || "" } : {}),
    ...(pickupState ? { pickup_state: pickupState } : {}),
    ...(pickupDistrict ? { pickup_district: pickupDistrict } : {}),
    ...(deliveryState ? { delivery_state: deliveryState } : {}),
    ...(deliveryDistrict ? { delivery_district: deliveryDistrict } : {}),
  }).toString()}`;

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "counterparty_approved":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>{t("delivery:status_counterparty_approved", "Assignment Confirmed")}</span>
          </span>
        );
      case "counterparty_rejected":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">
            <XCircle className="w-3.5 h-3.5 text-red-600" />
            <span>{t("delivery:status_counterparty_rejected", "Assignment Rejected")}</span>
          </span>
        );
      case "transporter_accepted":
      case "accepted":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
            <Clock className="w-3.5 h-3.5 text-blue-600" />
            <span>{t("delivery:status_transporter_accepted", "Accepted — Awaiting Counterparty Approval")}</span>
          </span>
        );
      case "declined":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">
            <XCircle className="w-3.5 h-3.5 text-red-600" />
            <span>{t("delivery:status_declined", "Declined")}</span>
          </span>
        );
      case "cancelled":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
            <XCircle className="w-3.5 h-3.5 text-slate-500" />
            <span>{t("delivery:status_cancelled", "Cancelled")}</span>
          </span>
        );
      case "pending":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
            <Clock className="w-3.5 h-3.5 text-amber-600" />
            <span>{t("delivery:status_pending", "Pending Response")}</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-4 pt-4 border-t border-border text-xs">
      {/* Section Title & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <Truck className="w-4 h-4 text-primary" />
            <span>{t("delivery:deal_transport_title", "Transportation & Hauling Services")}</span>
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {t(
              "delivery:deal_transport_desc",
              "Connect with verified haulers for farm-gate lot collection and dock delivery."
            )}
          </p>
        </div>

        <Link
          to={marketplaceUrl}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-foreground hover:bg-secondary font-semibold transition-colors self-start sm:self-auto"
        >
          <span>{t("delivery:browse_marketplace", "Browse Marketplace")}</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </Link>
      </div>

      {!isVerified && (
        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
            <span className="text-xs">
              {t("delivery:verification_required_transport", "Account verification is required to request transportation services.")}
            </span>
          </div>
          <Link
            to="/verification"
            className="text-xs font-bold text-primary hover:underline whitespace-nowrap"
          >
            {t("delivery:go_to_verification", "Verify Account →")}
          </Link>
        </div>
      )}

      {loading && (
        <div className="py-8 flex items-center justify-center text-muted-foreground">
          <RefreshCw className="w-5 h-5 animate-spin text-primary me-2" />
          <span>{t("delivery:loading_transport_data", "Loading logistics information...")}</span>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 1. Active Connection Requests for this Deal */}
      {!loading && connectionRequests.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-semibold text-foreground uppercase tracking-wider text-[11px] text-muted-foreground">
            {t("delivery:active_connection_requests", "Transport Connection Requests")} ({connectionRequests.length})
          </h4>

          <div className="rounded-xl border border-border overflow-hidden bg-card divide-y divide-border">
            {connectionRequests.map((req) => (
              <div key={req.id} className="p-3.5 space-y-3 hover:bg-secondary/20">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-foreground text-xs">{req.transporter_business_name}</span>
                      {getStatusBadge(req.status)}
                      <span className="text-[11px] text-muted-foreground">
                        {t("delivery:requested_on", "Requested")} {formatDate(req.created_at)}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground text-[11px]">
                      {req.cargo_description && <span><strong>{t("delivery:cargo_label", "Cargo:")}</strong> {req.cargo_description}</span>}
                      {req.weight_kg && <span><strong>{t("delivery:weight_label", "Weight:")}</strong> {formatNumber(req.weight_kg)} kg</span>}
                      {req.required_delivery_date && <span><strong>{t("delivery:date_label", "Date:")}</strong> {formatDate(req.required_delivery_date)}</span>}
                      {req.pickup_district && <span><strong>{t("delivery:route_label", "Route:")}</strong> {req.pickup_district} &rarr; {req.delivery_district || "Destination"}</span>}
                    </div>

                    {req.notes && (
                      <p className="text-[11px] text-foreground italic bg-secondary/40 px-2.5 py-1 rounded-md mt-1">
                        &ldquo;{req.notes}&rdquo;
                      </p>
                    )}

                    {req.response_notes && (
                      <p className="text-[11px] text-emerald-800 dark:text-emerald-300 font-medium">
                        {t("delivery:transporter_note", "Transporter note:")} {req.response_notes}
                      </p>
                    )}

                    {req.rejection_reason && (
                      <p className="text-[11px] text-destructive">
                        {t("delivery:decline_reason_label", "Decline reason:")} {req.rejection_reason}
                      </p>
                    )}

                    {req.counterparty_rejection_reason && (
                      <p className="text-[11px] text-destructive font-medium">
                        {t("delivery:counterparty_rejection_reason_label", "Counterparty Rejection Reason:")} {req.counterparty_rejection_reason}
                      </p>
                    )}

                    {req.status === "counterparty_approved" && (
                      <p className="text-[11px] text-emerald-800 dark:text-emerald-300 font-medium">
                        {t("delivery:approved_by_counterparty", "Assignment approved by {{name}}", { name: req.counterparty_name || "counterparty" })}
                      </p>
                    )}
                  </div>

                  {(req.status === "pending" || req.status === "transporter_accepted" || req.status === "accepted") && canRequest && req.requester_id === user?.id && (
                    <button
                      type="button"
                      onClick={() => handleCancelRequest(req.id)}
                      className="px-2.5 py-1 rounded border border-border hover:bg-destructive/10 hover:text-destructive text-muted-foreground font-semibold text-[11px] transition-colors self-start sm:self-center"
                    >
                      {t("delivery:cancel_request", "Cancel Request")}
                    </button>
                  )}
                </div>

                {/* Counterparty Approval Banner & Controls */}
                {req.can_current_user_approve && (req.status === "transporter_accepted" || req.status === "accepted") && (
                  <div className="p-3 rounded-xl border border-primary/30 bg-primary/5 space-y-2.5">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-bold text-xs text-foreground">
                          {t("delivery:action_required_counterparty", "Approval Required: Transporter Accepted Assignment")}
                        </p>
                        <p className="text-[11px] text-muted-foreground mt-0.5">
                          {t(
                            "delivery:counterparty_approval_prompt",
                            "This transporter accepted the haulage request. Both parties must approve before the transporter is officially assigned to this deal."
                          )}
                        </p>
                      </div>
                    </div>

                    {rejectingRequestId === req.id ? (
                      <div className="space-y-2 pt-1">
                        <label className="text-[11px] font-semibold text-foreground block">
                          {t("delivery:reject_reason_label", "Reason for Rejecting Assignment (Optional):")}
                        </label>
                        <input
                          type="text"
                          value={rejectionReason}
                          onChange={(e) => setRejectionReason(e.target.value)}
                          placeholder={t("delivery:reject_reason_placeholder", "e.g. Alternative arrangement preferred")}
                          className="w-full text-xs p-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-destructive outline-none"
                        />
                        <div className="flex items-center gap-2 justify-end">
                          <button
                            type="button"
                            disabled={actionLoading}
                            onClick={() => {
                              setRejectingRequestId(null);
                              setRejectionReason("");
                            }}
                            className="px-2.5 py-1 rounded text-[11px] font-medium text-muted-foreground hover:bg-secondary"
                          >
                            {t("common:actions.cancel", "Cancel")}
                          </button>
                          <button
                            type="button"
                            disabled={actionLoading}
                            onClick={() => handleRejectAssignment(req.id, rejectionReason)}
                            className="px-3 py-1 rounded text-[11px] font-semibold bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors"
                          >
                            {actionLoading ? t("delivery:processing", "Processing...") : t("delivery:confirm_reject", "Confirm Rejection")}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 pt-1">
                        <button
                          type="button"
                          disabled={actionLoading}
                          onClick={() => handleApproveAssignment(req.id)}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shadow-xs disabled:opacity-50"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>{t("delivery:approve_assignment", "Approve Assignment")}</span>
                        </button>
                        <button
                          type="button"
                          disabled={actionLoading}
                          onClick={() => setRejectingRequestId(req.id)}
                          className="px-3 py-1.5 rounded-lg border border-destructive/30 text-destructive hover:bg-destructive/10 font-semibold text-xs transition-colors"
                        >
                          {t("delivery:reject_assignment", "Reject Assignment")}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 2. Recommended Verified Transporters for this Route */}
      {!loading && recommendedTransporters.length > 0 && (
        <div className="space-y-2 pt-2">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-foreground uppercase tracking-wider text-[11px] text-muted-foreground flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-emerald-600" />
              <span>{t("delivery:available_route_haulers", "Available Route Transporters")}</span>
            </h4>
            <span className="text-[11px] text-muted-foreground">
              {pickupDistrict ? `Near ${pickupDistrict}` : "All verified fleets"}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {recommendedTransporters.map((t) => (
              <TransporterCard
                key={t.id}
                transporter={t}
                onViewDetails={(item) => setDetailTransporter(item)}
                onRequestConnect={(item) => setConnectTransporter(item)}
              />
            ))}
          </div>
        </div>
      )}

      {!loading && connectionRequests.length === 0 && recommendedTransporters.length === 0 && (
        <div className="p-6 rounded-xl border border-dashed border-border text-center space-y-2">
          <Truck className="w-8 h-8 text-muted-foreground mx-auto opacity-40" />
          <p className="font-semibold text-foreground text-xs">
            {t("delivery:no_haulers_yet", "No transportation connected to this deal yet.")}
          </p>
          <p className="text-muted-foreground text-[11px] max-w-sm mx-auto">
            {t(
              "delivery:browse_marketplace_prompt",
              "You can discover verified haulers covering this route and request dedicated transportation."
            )}
          </p>
          <Link
            to={marketplaceUrl}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold shadow-xs hover:bg-primary-700 transition-colors text-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>{t("delivery:find_transporters_button", "Find Transporters for this Deal")}</span>
          </Link>
        </div>
      )}

      {/* Detail Modal */}
      <TransporterDetailModal
        transporter={detailTransporter}
        isOpen={!!detailTransporter}
        onClose={() => setDetailTransporter(null)}
        onRequestConnect={(item) => setConnectTransporter(item)}
      />

      {/* Connection Modal */}
      <TransportConnectionModal
        transporter={connectTransporter}
        orderId={orderId}
        orderNumber={orderNumber}
        offerId={offerId}
        offerNumber={offerNumber}
        initialPickupState={pickupState}
        initialPickupDistrict={pickupDistrict}
        initialPickupAddress={pickupAddress}
        initialDeliveryState={deliveryState}
        initialDeliveryDistrict={deliveryDistrict}
        initialDeliveryAddress={deliveryAddress}
        initialCargoDescription={
          cargoDescription && cargoDescription.length > 250
            ? cargoDescription.slice(0, 247) + "..."
            : cargoDescription
        }
        initialWeightKg={weightKg}
        initialDeliveryDate={requiredDeliveryDate}
        isOpen={!!connectTransporter}
        onClose={() => setConnectTransporter(null)}
        onSuccess={handleConnectionSuccess}
      />
    </div>
  );
};
