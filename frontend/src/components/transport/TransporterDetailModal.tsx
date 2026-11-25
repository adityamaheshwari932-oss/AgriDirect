import React from "react";
import {
  X,
  Truck,
  MapPin,
  Weight,
  Calendar,
  CheckCircle2,
  Shield,
  Phone,
  ArrowRight,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import type { TransporterSearchResult } from "../../types/transporter";
import { formatNumber } from "../../utils/formatters";

interface TransporterDetailModalProps {
  transporter: TransporterSearchResult | null;
  isOpen: boolean;
  onClose: () => void;
  onRequestConnect: (transporter: TransporterSearchResult) => void;
}

export const TransporterDetailModal: React.FC<TransporterDetailModalProps> = ({
  transporter,
  isOpen,
  onClose,
  onRequestConnect,
}) => {
  const { t } = useTranslation(["delivery", "common"]);

  if (!isOpen || !transporter) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="transporter-detail-title"
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="bg-card border border-border w-full max-w-2xl rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-border flex items-center justify-between bg-secondary/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 id="transporter-detail-title" className="text-base font-bold text-foreground">
                  {transporter.business_name}
                </h2>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                  <span>{t("delivery:verified_hauler", "Verified Provider")}</span>
                </span>
              </div>
              <p className="text-xs text-muted-foreground">{transporter.contact_name}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            aria-label={t("common:actions.close", "Close dialog")}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs flex-1">
          {/* Key Fleet Specifications Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl bg-secondary/40 border border-border/60">
              <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider block mb-1">
                {t("delivery:vehicle_type", "Vehicle Type")}
              </span>
              <p className="font-bold text-foreground capitalize flex items-center gap-1">
                <Truck className="w-3.5 h-3.5 text-primary" />
                <span>{transporter.transport_type.replace("_", " ")}</span>
              </p>
            </div>

            <div className="p-3 rounded-xl bg-secondary/40 border border-border/60">
              <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider block mb-1">
                {t("delivery:capacity", "Capacity")}
              </span>
              <p className="font-bold text-foreground flex items-center gap-1">
                <Weight className="w-3.5 h-3.5 text-emerald-600" />
                <span>{formatNumber(transporter.vehicle_capacity_kg)} kg</span>
              </p>
            </div>

            <div className="p-3 rounded-xl bg-secondary/40 border border-border/60">
              <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider block mb-1">
                {t("delivery:experience", "Experience")}
              </span>
              <p className="font-bold text-foreground flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-amber-600" />
                <span>{transporter.experience_years} {t("delivery:years", "Years")}</span>
              </p>
            </div>

            <div className="p-3 rounded-xl bg-secondary/40 border border-border/60">
              <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider block mb-1">
                {t("delivery:availability", "Availability")}
              </span>
              <span
                className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  transporter.is_available
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                    : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                }`}
              >
                {transporter.is_available
                  ? t("delivery:status_available", "Available")
                  : t("delivery:status_in_transit", "In Transit")}
              </span>
            </div>
          </div>

          {/* Registration & Contact */}
          <div className="p-4 rounded-xl border border-border bg-card space-y-2">
            <h3 className="font-bold text-xs uppercase tracking-wider text-muted-foreground">
              {t("delivery:registration_and_contact", "Registration & Contact")}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <span className="text-muted-foreground block text-[11px]">
                  {t("delivery:vehicle_reg_plate", "Registration Plate")}
                </span>
                <span className="font-mono font-bold text-foreground text-xs">
                  {transporter.vehicle_registration_number}
                </span>
              </div>

              <div>
                <span className="text-muted-foreground block text-[11px]">
                  {t("delivery:phone_number", "Phone Contact")}
                </span>
                <a
                  href={`tel:${transporter.phone_number}`}
                  className="font-semibold text-primary hover:underline inline-flex items-center gap-1.5"
                >
                  <Phone className="w-3.5 h-3.5" />
                  <span>{transporter.phone_number}</span>
                </a>
              </div>
            </div>

            {transporter.bio && (
              <div className="pt-2 border-t border-border/60">
                <span className="text-muted-foreground block text-[11px] mb-1">
                  {t("delivery:overview", "Company Overview")}
                </span>
                <p className="text-foreground leading-relaxed">{transporter.bio}</p>
              </div>
            )}
          </div>

          {/* Declared Service Areas Table */}
          <div className="space-y-2">
            <h3 className="font-bold text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-emerald-600" />
              <span>{t("delivery:declared_service_areas", "Service Areas & Coverage")} ({transporter.service_areas.length})</span>
            </h3>

            {transporter.service_areas.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                {t("delivery:no_service_areas_declared", "No specific local service areas declared. Operates regionally.")}
              </p>
            ) : (
              <div className="rounded-xl border border-border overflow-hidden">
                <table className="w-full text-start border-collapse text-xs">
                  <thead className="bg-secondary/40 text-muted-foreground font-semibold border-b border-border">
                    <tr>
                      <th className="py-2 px-3">{t("delivery:state", "State")}</th>
                      <th className="py-2 px-3">{t("delivery:district", "District")}</th>
                      <th className="py-2 px-3">{t("delivery:coverage", "Coverage")}</th>
                      <th className="py-2 px-3">{t("delivery:pincode", "Pincode")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {transporter.service_areas.map((sa) => (
                      <tr key={sa.id} className="hover:bg-secondary/20">
                        <td className="py-2 px-3 font-semibold text-foreground">{sa.state}</td>
                        <td className="py-2 px-3 text-foreground">{sa.district}</td>
                        <td className="py-2 px-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold capitalize bg-primary/10 text-primary">
                            {sa.coverage_type.replace("_", " ")}
                          </span>
                        </td>
                        <td className="py-2 px-3 font-mono text-muted-foreground">
                          {sa.pincode || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Legal / Marketplace Disclaimer Notice */}
          <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-900 dark:text-amber-200 flex items-start gap-2.5">
            <Shield className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
            <p className="text-[11px] leading-relaxed">
              <strong>{t("delivery:disclaimer_title", "Independent Logistics Provider")}:</strong>{" "}
              {t(
                "delivery:disclaimer_full",
                "AgriDirect facilitates hauler discovery and bilateral communication. Transportation service providers are independent third-party operators and are not employees, agents, or fleet contractors of AgriDirect. Hauling terms and transit conditions are agreed directly between participants."
              )}
            </p>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-border bg-secondary/20 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-border text-foreground hover:bg-secondary font-semibold transition-colors text-xs"
          >
            {t("common:actions.cancel", "Close")}
          </button>

          <button
            type="button"
            onClick={() => {
              onClose();
              onRequestConnect(transporter);
            }}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary-700 transition-colors inline-flex items-center gap-1.5 shadow-xs text-xs"
          >
            <Truck className="w-4 h-4" />
            <span>{t("delivery:request_transport_services", "Request Transportation Services")}</span>
            <ArrowRight className="w-3.5 h-3.5 rtl:rotate-180" />
          </button>
        </div>
      </div>
    </div>
  );
};
