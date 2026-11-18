import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Truck,
  MapPin,
  Search,
  Phone,
  Weight,
  Calendar,
  AlertCircle,
  RefreshCw,
  MessageSquare,
} from "lucide-react";
import { transportersApi } from "../api/transporters";
import type {
  TransporterSearchResult,
  TransporterSearchParams,
} from "../types/transporter";

export const TransporterDiscoveryPage: React.FC = () => {
  const [transporters, setTransporters] = useState<TransporterSearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [filters, setFilters] = useState<TransporterSearchParams>({
    pickup_state: "",
    pickup_district: "",
    delivery_state: "",
    delivery_district: "",
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
      setError(err instanceof Error ? err.message : "Failed to load transporters");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransporters();
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

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-blue-950 via-slate-900 to-indigo-950 text-white shadow-md relative overflow-hidden">
        <div className="absolute end-0 bottom-0 rtl:-translate-x-8 translate-x-8 translate-y-8 opacity-10 pointer-events-none">
          <Truck className="w-64 h-64" aria-hidden="true" />
        </div>

        <div className="relative z-10 max-w-3xl space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-800/60 text-xs font-semibold text-blue-300">
            <Truck className="w-4 h-4" />
            <span>Agricultural Logistics Network</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Find Transportation Providers
          </h1>
          <p className="text-xs sm:text-sm text-blue-200/90 leading-relaxed">
            Connect directly with verified independent haulers and fleet operators to transport produce between farm gates and commercial facilities.
          </p>
        </div>
      </div>

      {/* Filter Card */}
      <form
        onSubmit={handleSearchSubmit}
        className="bg-card border border-border rounded-xl p-5 shadow-xs space-y-4"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div>
            <label className="block font-semibold text-foreground mb-1">Pickup State</label>
            <input
              type="text"
              value={filters.pickup_state}
              onChange={(e) => setFilters({ ...filters, pickup_state: e.target.value })}
              placeholder="e.g. Maharashtra"
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold text-foreground mb-1">Pickup District</label>
            <input
              type="text"
              value={filters.pickup_district}
              onChange={(e) => setFilters({ ...filters, pickup_district: e.target.value })}
              placeholder="e.g. Nashik"
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold text-foreground mb-1">Delivery State</label>
            <input
              type="text"
              value={filters.delivery_state}
              onChange={(e) => setFilters({ ...filters, delivery_state: e.target.value })}
              placeholder="e.g. Maharashtra"
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold text-foreground mb-1">Delivery District</label>
            <input
              type="text"
              value={filters.delivery_district}
              onChange={(e) => setFilters({ ...filters, delivery_district: e.target.value })}
              placeholder="e.g. Mumbai"
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold text-foreground mb-1">Vehicle Type</label>
            <select
              value={filters.transport_type}
              onChange={(e) => setFilters({ ...filters, transport_type: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            >
              <option value="">All Vehicle Types</option>
              <option value="mini_truck">Mini Truck</option>
              <option value="open_body">Open Body</option>
              <option value="refrigerated">Refrigerated / Cold-Chain</option>
              <option value="covered_truck">Covered Truck</option>
              <option value="tempo">Tempo</option>
              <option value="trailer">Trailer</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-foreground mb-1">Min Capacity (kg)</label>
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
              Only Available Fleets
            </label>
          </div>

          <div className="flex items-end gap-2 pt-2">
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary-700 transition-colors flex items-center justify-center gap-1.5 shadow-xs"
            >
              <Search className="w-4 h-4" />
              <span>Search</span>
            </button>
            <button
              type="button"
              onClick={handleResetFilters}
              className="px-3 py-2 border border-border text-foreground hover:bg-secondary rounded-lg font-semibold"
            >
              Reset
            </button>
          </div>
        </div>
      </form>

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
        <span>
          Showing <strong className="text-foreground">{transporters.length}</strong> of{" "}
          <strong className="text-foreground">{total}</strong> transportation providers
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
          <p className="text-sm font-semibold text-foreground">No transporters matched your search</p>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
            Try broadening your pickup or delivery location, or removing specific vehicle type constraints.
          </p>
        </div>
      )}

      {!loading && !error && transporters.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {transporters.map((t) => (
            <div
              key={t.id}
              className="bg-card border border-border rounded-xl p-5 shadow-xs hover:border-primary/50 transition-all flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-sm text-foreground">{t.business_name}</h3>
                    <p className="text-xs text-muted-foreground">{t.contact_name}</p>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      t.is_available
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                        : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    }`}
                  >
                    {t.is_available ? "Available" : "In Transit"}
                  </span>
                </div>

                {/* Specs Pills */}
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="px-2 py-1 rounded-md bg-secondary text-secondary-foreground font-medium capitalize flex items-center gap-1">
                    <Truck className="w-3.5 h-3.5 text-primary" />
                    {t.transport_type.replace("_", " ")}
                  </span>
                  <span className="px-2 py-1 rounded-md bg-secondary text-secondary-foreground font-medium flex items-center gap-1">
                    <Weight className="w-3.5 h-3.5 text-emerald-600" />
                    {t.vehicle_capacity_kg.toLocaleString()} kg
                  </span>
                  <span className="px-2 py-1 rounded-md bg-secondary text-secondary-foreground font-medium flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-amber-600" />
                    {t.experience_years}y Exp
                  </span>
                </div>

                {/* Service Areas Coverage Tags */}
                {t.service_areas.length > 0 && (
                  <div className="pt-2 border-t border-border/60">
                    <p className="text-[11px] font-semibold text-muted-foreground mb-1.5 flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Declared Coverage ({t.service_areas.length})</span>
                    </p>
                    <div className="flex flex-wrap gap-1.5 max-h-16 overflow-y-auto">
                      {t.service_areas.slice(0, 4).map((area) => (
                        <span
                          key={area.id}
                          className="px-2 py-0.5 rounded bg-muted text-[10px] text-muted-foreground font-mono"
                        >
                          {area.state} &bull; {area.district}
                        </span>
                      ))}
                      {t.service_areas.length > 4 && (
                        <span className="text-[10px] text-muted-foreground font-medium self-center">
                          +{t.service_areas.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Action: Direct Phone & Coordination */}
              <div className="pt-3 border-t border-border flex items-center justify-between text-xs">
                <a
                  href={`tel:${t.phone_number}`}
                  className="font-semibold text-primary hover:underline flex items-center gap-1.5"
                >
                  <Phone className="w-3.5 h-3.5" />
                  <span>{t.phone_number}</span>
                </a>

                <Link
                  to="/messages"
                  className="px-3 py-1.5 rounded-lg bg-secondary hover:bg-secondary/80 text-foreground font-semibold inline-flex items-center gap-1.5 transition-colors"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Message</span>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
