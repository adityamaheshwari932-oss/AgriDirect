import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Truck,
  Search,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { transportersApi } from "../api/transporters";
import type {
  TransporterSearchResult,
  TransporterSearchParams,
  TransportConnectionRequest,
} from "../types/transporter";
import { TransporterCard } from "../components/transport/TransporterCard";
import { TransporterDetailModal } from "../components/transport/TransporterDetailModal";
import { TransportConnectionModal } from "../components/transport/TransportConnectionModal";

export const TransporterDiscoveryPage: React.FC = () => {
  const { t } = useTranslation(["delivery", "common"]);
  const [searchParams] = useSearchParams();

  // URL query context (e.g. from an active deal or order)
  const initialOrderId = searchParams.get("order_id");
  const initialOrderNumber = searchParams.get("order_number");
  const initialOfferId = searchParams.get("offer_id");
  const initialOfferNumber = searchParams.get("offer_number");
  const initialPickupState = searchParams.get("pickup_state") || "";
  const initialPickupDistrict = searchParams.get("pickup_district") || "";
  const initialDeliveryState = searchParams.get("delivery_state") || "";
  const initialDeliveryDistrict = searchParams.get("delivery_district") || "";

  const [transporters, setTransporters] = useState<TransporterSearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Selected modals
  const [detailTransporter, setDetailTransporter] = useState<TransporterSearchResult | null>(null);
  const [connectTransporter, setConnectTransporter] = useState<TransporterSearchResult | null>(null);

  // Filter state
  const [filters, setFilters] = useState<TransporterSearchParams>({
    pickup_state: initialPickupState,
    pickup_district: initialPickupDistrict,
    delivery_state: initialDeliveryState,
    delivery_district: initialDeliveryDistrict,
    transport_type: "",
    min_capacity_kg: undefined,
    only_available: true,
  });

  const fetchTransporters = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await transportersApi.discoverTransporters({
        ...filters,
        pickup_state: filters.pickup_state?.trim() || undefined,
        pickup_district: filters.pickup_district?.trim() || undefined,
        delivery_state: filters.delivery_state?.trim() || undefined,
        delivery_district: filters.delivery_district?.trim() || undefined,
        transport_type: filters.transport_type || undefined,
        min_capacity_kg: filters.min_capacity_kg ? Number(filters.min_capacity_kg) : undefined,
      });
      setTransporters(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("delivery:load_failed", "Failed to load transporters"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransporters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTransporters();
  };

  const handleResetFilters = () => {
    setFilters({
      pickup_state: "",
      pickup_district: "",
      delivery_state: "",
      delivery_district: "",
      transport_type: "",
      min_capacity_kg: undefined,
      only_available: true,
    });
  };

  const handleConnectionSuccess = (req: TransportConnectionRequest) => {
    setSuccessMessage(
      t(
        "delivery:request_sent_success",
        `Transport request sent to ${req.transporter_business_name}! You can monitor status in your dashboard.`
      )
    );
    setTimeout(() => setSuccessMessage(null), 8000);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-blue-950 via-slate-900 to-indigo-950 text-white shadow-md relative overflow-hidden">
        <div className="absolute end-0 bottom-0 rtl:-translate-x-8 translate-x-8 translate-y-8 opacity-10 pointer-events-none">
          <Truck className="w-64 h-64" aria-hidden="true" />
        </div>

        <div className="relative z-10 max-w-3xl space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-800/60 text-xs font-semibold text-blue-300">
            <Truck className="w-4 h-4" />
            <span>{t("delivery:logistics_network", "Agricultural Logistics Network")}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            {t("delivery:marketplace_heading", "Connected Transportation Marketplace")}
          </h1>
          <p className="text-xs sm:text-sm text-blue-200/90 leading-relaxed">
            {t(
              "delivery:marketplace_description",
              "Connect directly with verified independent haulers and fleet operators to transport produce between farm gates and commercial facilities."
            )}
          </p>
        </div>
      </div>

      {/* Success alert banner */}
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300 text-xs flex items-center justify-between gap-3 animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span className="font-semibold">{successMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMessage(null)}
            className="text-xs hover:underline text-emerald-700 dark:text-emerald-400 font-bold"
          >
            {t("common:actions.dismiss", "Dismiss")}
          </button>
        </div>
      )}

      {/* Filter Card */}
      <form
        onSubmit={handleSearchSubmit}
        className="bg-card border border-border rounded-xl p-5 shadow-xs space-y-4"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div>
            <label className="block font-semibold text-foreground mb-1">{t("delivery:pickup_state", "Pickup State")}</label>
            <input
              type="text"
              value={filters.pickup_state}
              onChange={(e) => setFilters({ ...filters, pickup_state: e.target.value })}
              placeholder="e.g. Maharashtra"
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold text-foreground mb-1">{t("delivery:pickup_district", "Pickup District")}</label>
            <input
              type="text"
              value={filters.pickup_district}
              onChange={(e) => setFilters({ ...filters, pickup_district: e.target.value })}
              placeholder="e.g. Nashik"
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold text-foreground mb-1">{t("delivery:delivery_state", "Delivery State")}</label>
            <input
              type="text"
              value={filters.delivery_state}
              onChange={(e) => setFilters({ ...filters, delivery_state: e.target.value })}
              placeholder="e.g. Maharashtra"
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold text-foreground mb-1">{t("delivery:delivery_district", "Delivery District")}</label>
            <input
              type="text"
              value={filters.delivery_district}
              onChange={(e) => setFilters({ ...filters, delivery_district: e.target.value })}
              placeholder="e.g. Mumbai"
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold text-foreground mb-1">{t("delivery:vehicle_type", "Vehicle Type")}</label>
            <select
              value={filters.transport_type}
              onChange={(e) => setFilters({ ...filters, transport_type: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            >
              <option value="">{t("delivery:all_vehicle_types", "All Vehicle Types")}</option>
              <option value="mini_truck">{t("delivery:type_mini_truck", "Mini Truck")}</option>
              <option value="open_body">{t("delivery:type_open_body", "Open Body")}</option>
              <option value="refrigerated">{t("delivery:type_refrigerated", "Refrigerated / Cold-Chain")}</option>
              <option value="covered_truck">{t("delivery:type_covered_truck", "Covered Truck")}</option>
              <option value="tempo">{t("delivery:type_tempo", "Tempo")}</option>
              <option value="trailer">{t("delivery:type_trailer", "Trailer")}</option>
              <option value="other">{t("delivery:type_other", "Other")}</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-foreground mb-1">{t("delivery:min_capacity", "Min Capacity (kg)")}</label>
            <input
              type="number"
              value={filters.min_capacity_kg ?? ""}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  min_capacity_kg: e.target.value ? Number(e.target.value) : undefined,
                })
              }
              placeholder="e.g. 2000"
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div className="flex items-center gap-2 pt-5">
            <input
              type="checkbox"
              id="only_available"
              checked={filters.only_available}
              onChange={(e) => setFilters({ ...filters, only_available: e.target.checked })}
              className="w-4 h-4 rounded text-primary focus:ring-primary border-input"
            />
            <label htmlFor="only_available" className="font-semibold text-foreground cursor-pointer">
              {t("delivery:only_available_fleets", "Only Available Fleets")}
            </label>
          </div>

          <div className="flex items-end gap-2 pt-2">
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary-700 transition-colors flex items-center justify-center gap-1.5 shadow-xs"
            >
              <Search className="w-4 h-4" />
              <span>{t("common:actions.search", "Search")}</span>
            </button>
            <button
              type="button"
              onClick={handleResetFilters}
              className="px-3 py-2 border border-border text-foreground hover:bg-secondary rounded-lg font-semibold"
            >
              {t("common:actions.reset", "Reset")}
            </button>
          </div>
        </div>
      </form>

      {/* Results Count Header */}
      <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
        <span>
          {t("delivery:showing_providers", "Showing {{count}} of {{total}} verified transportation providers", {
            count: transporters.length,
            total,
          })}
        </span>
      </div>

      {/* Loading & Error States */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <RefreshCw className="w-8 h-8 text-primary animate-spin" />
        </div>
      )}

      {error && (
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results Grid */}
      {!loading && !error && transporters.length === 0 && (
        <div className="p-12 text-center border border-dashed border-border rounded-xl space-y-2">
          <Truck className="w-10 h-10 text-muted-foreground mx-auto opacity-40" />
          <p className="text-sm font-semibold text-foreground">
            {t("delivery:no_transporters_matched", "No verified transporters matched your search")}
          </p>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
            {t(
              "delivery:no_transporters_hint",
              "Try broadening your pickup or delivery location, or removing specific vehicle type constraints."
            )}
          </p>
        </div>
      )}

      {!loading && !error && transporters.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {transporters.map((t) => (
            <TransporterCard
              key={t.id}
              transporter={t}
              onViewDetails={(item) => setDetailTransporter(item)}
              onRequestConnect={(item) => setConnectTransporter(item)}
            />
          ))}
        </div>
      )}

      {/* Transporter Details Modal */}
      <TransporterDetailModal
        transporter={detailTransporter}
        isOpen={!!detailTransporter}
        onClose={() => setDetailTransporter(null)}
        onRequestConnect={(item) => setConnectTransporter(item)}
      />

      {/* Transport Connection Request Modal */}
      <TransportConnectionModal
        transporter={connectTransporter}
        orderId={initialOrderId}
        orderNumber={initialOrderNumber}
        offerId={initialOfferId}
        offerNumber={initialOfferNumber}
        initialPickupState={filters.pickup_state}
        initialPickupDistrict={filters.pickup_district}
        initialDeliveryState={filters.delivery_state}
        initialDeliveryDistrict={filters.delivery_district}
        isOpen={!!connectTransporter}
        onClose={() => setConnectTransporter(null)}
        onSuccess={handleConnectionSuccess}
      />
    </div>
  );
};
