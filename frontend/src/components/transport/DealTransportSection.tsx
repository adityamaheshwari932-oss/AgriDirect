import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Truck,
  MapPin,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Plus,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { useTranslation } from "react-i18next";
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

  const [connectionRequests, setConnectionRequests] = useState<TransportConnectionRequest[]>([]);
  const [recommendedTransporters, setRecommendedTransporters] = useState<TransporterSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      case "accepted":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>{t("delivery:status_accepted", "Accepted")}</span>
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

      {loading && (
        <div className="py-8 flex items-center justify-center text-muted-foreground">
          <RefreshCw className="w-5 h-5 animate-spin text-primary mr-2" />
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
              <div key={req.id} className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-secondary/20">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-foreground text-xs">{req.transporter_business_name}</span>
                    {getStatusBadge(req.status)}
                    <span className="text-[11px] text-muted-foreground">
                      Requested {formatDate(req.created_at)}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground text-[11px]">
                    {req.cargo_description && <span><strong>Cargo:</strong> {req.cargo_description}</span>}
                    {req.weight_kg && <span><strong>Weight:</strong> {formatNumber(req.weight_kg)} kg</span>}
                    {req.required_delivery_date && <span><strong>Date:</strong> {formatDate(req.required_delivery_date)}</span>}
                    {req.pickup_district && <span><strong>Route:</strong> {req.pickup_district} &rarr; {req.delivery_district || "Destination"}</span>}
                  </div>

                  {req.notes && (
                    <p className="text-[11px] text-foreground italic bg-secondary/40 px-2.5 py-1 rounded-md mt-1">
                      &ldquo;{req.notes}&rdquo;
                    </p>
                  )}

                  {req.response_notes && (
                    <p className="text-[11px] text-emerald-800 dark:text-emerald-300 font-medium">
                      Transporter note: {req.response_notes}
                    </p>
                  )}

                  {req.rejection_reason && (
                    <p className="text-[11px] text-destructive">
                      Decline reason: {req.rejection_reason}
                    </p>
                  )}
                </div>

                {req.status === "pending" && canRequest && (
                  <button
                    type="button"
                    onClick={() => handleCancelRequest(req.id)}
                    className="px-2.5 py-1 rounded border border-border hover:bg-destructive/10 hover:text-destructive text-muted-foreground font-semibold text-[11px] transition-colors self-start sm:self-center"
                  >
                    {t("delivery:cancel_request", "Cancel Request")}
                  </button>
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
        initialCargoDescription={cargoDescription}
        initialWeightKg={weightKg}
        initialDeliveryDate={requiredDeliveryDate}
        isOpen={!!connectTransporter}
        onClose={() => setConnectTransporter(null)}
        onSuccess={handleConnectionSuccess}
      />
    </div>
  );
};
