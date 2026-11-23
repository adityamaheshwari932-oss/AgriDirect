import React from "react";
import {
  Truck,
  MapPin,
  Weight,
  Calendar,
  CheckCircle2,
  Shield,
  ArrowRight,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import type { TransporterSearchResult } from "../../types/transporter";
import { formatNumber } from "../../utils/formatters";

interface TransporterCardProps {
  transporter: TransporterSearchResult;
  onViewDetails: (transporter: TransporterSearchResult) => void;
  onRequestConnect: (transporter: TransporterSearchResult) => void;
}

export const TransporterCard: React.FC<TransporterCardProps> = ({
  transporter: t,
  onViewDetails,
  onRequestConnect,
}) => {
  const { t: i18n } = useTranslation(["delivery", "common"]);

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-xs hover:border-primary/50 transition-all flex flex-col justify-between space-y-4">
      <div className="space-y-3">
        {/* Header: Business & Verification */}
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5 flex-wrap">
              <h3 className="font-bold text-sm text-foreground">{t.business_name}</h3>
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                <span>{i18n("delivery:verified_hauler", "Verified")}</span>
              </span>
            </div>
            <p className="text-xs text-muted-foreground">{t.contact_name}</p>
          </div>

          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              t.is_available
                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
            }`}
          >
            {t.is_available
              ? i18n("delivery:status_available", "Available")
              : i18n("delivery:status_in_transit", "In Transit")}
          </span>
        </div>

        {/* Vehicle Specs Pills */}
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="px-2 py-1 rounded-md bg-secondary text-secondary-foreground font-medium capitalize flex items-center gap-1">
            <Truck className="w-3.5 h-3.5 text-primary" />
            {t.transport_type.replace("_", " ")}
          </span>
          <span className="px-2 py-1 rounded-md bg-secondary text-secondary-foreground font-medium flex items-center gap-1">
            <Weight className="w-3.5 h-3.5 text-emerald-600" />
            {formatNumber(t.vehicle_capacity_kg)} kg
          </span>
          <span className="px-2 py-1 rounded-md bg-secondary text-secondary-foreground font-medium flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5 text-amber-600" />
            {t.experience_years}y Exp
          </span>
        </div>

        {/* Declared Service Areas */}
        {t.service_areas.length > 0 && (
          <div className="pt-2 border-t border-border/60">
            <p className="text-[11px] font-semibold text-muted-foreground mb-1.5 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-emerald-600" />
              <span>
                {i18n("delivery:declared_coverage", "Declared Coverage")} ({t.service_areas.length})
              </span>
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

        {/* Third-party disclaimer badge */}
        <div className="text-[10px] text-muted-foreground/80 flex items-center gap-1">
          <Shield className="w-3 h-3 text-muted-foreground flex-shrink-0" />
          <span>{i18n("delivery:independent_disclaimer_short", "Independent 3rd-party logistics provider")}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="pt-3 border-t border-border flex items-center justify-between gap-2 text-xs">
        <button
          type="button"
          onClick={() => onViewDetails(t)}
          className="px-3 py-1.5 rounded-lg border border-border text-foreground hover:bg-secondary font-medium transition-colors"
        >
          {i18n("delivery:view_details", "Details")}
        </button>

        <button
          type="button"
          onClick={() => onRequestConnect(t)}
          className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary-700 transition-colors inline-flex items-center gap-1.5 shadow-xs"
        >
          <span>{i18n("delivery:request_transport", "Request Transport")}</span>
          <ArrowRight className="w-3.5 h-3.5 rtl:rotate-180" />
        </button>
      </div>
    </div>
  );
};
