import React from "react";
import { useTranslation } from "react-i18next";
import { MapPin, Clock, Building2, ArrowUpRight } from "lucide-react";
import type { BuyerRequirementPublicSummary } from "../../types/requirements";
import { formatNumber } from "../../utils/formatters";

interface BuyerRequirementCardProps {
  requirement: BuyerRequirementPublicSummary;
  onViewDetails: (requirement: BuyerRequirementPublicSummary) => void;
}

export const BuyerRequirementCard: React.FC<BuyerRequirementCardProps> = ({
  requirement,
  onViewDetails,
}) => {
  const { t } = useTranslation(["marketplace", "requirements"]);

  return (
    <div
      onClick={() => onViewDetails(requirement)}
      className="group rounded-2xl border border-border bg-card shadow-2xs hover:shadow-md hover:border-blue-500/40 transition-all duration-200 p-5 flex flex-col justify-between space-y-4 cursor-pointer"
    >
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            {requirement.category_name && (
              <span className="inline-block text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-secondary text-foreground mb-1.5 border border-border/80">
                {requirement.category_name}
              </span>
            )}
            <h3 className="text-base font-bold text-foreground group-hover:text-blue-700 transition-colors flex items-center gap-1">
              <span>{requirement.product_name}</span>
              <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-blue-600 rtl:-scale-x-100" />
            </h3>
          </div>

          <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-800 border border-blue-500/20 flex-shrink-0">
            <Building2 className="w-3 h-3 text-blue-600" />
            {t("marketplace:verified_buyer", "Verified Commercial Buyer")}
          </span>
        </div>

        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {requirement.title}
        </p>
      </div>

      {/* Demand & Price Specifications */}
      <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-secondary/35 border border-border/70 text-xs">
        <div>
          <span className="text-[10px] uppercase font-bold text-muted-foreground block tracking-wider">
            {t("marketplace:required_volume", "Required Volume")}
          </span>
          <div className="text-base font-extrabold text-foreground tabular">
            {formatNumber(Number(requirement.remaining_quantity))}
            <span className="text-xs font-normal text-muted-foreground"> {requirement.unit}</span>
          </div>
          <span className="text-[10px] text-muted-foreground block mt-0.5">
            Total Target: {formatNumber(Number(requirement.required_quantity))} {requirement.unit}
          </span>
        </div>

        <div>
          <span className="text-[10px] uppercase font-bold text-muted-foreground block tracking-wider">
            {t("marketplace:target_rate", "Target Price")}
          </span>
          <div className="text-base font-extrabold text-blue-700 capitalize tabular">
            {requirement.target_price_per_unit
              ? `₹${formatNumber(Number(requirement.target_price_per_unit))} / ${requirement.unit}`
              : requirement.price_condition}
          </div>
          <span className="text-[10px] text-muted-foreground block capitalize mt-0.5">
            Term: {requirement.price_condition}
          </span>
        </div>
      </div>

      {/* Metadata */}
      <div className="space-y-1.5 pt-2 border-t border-border/60 text-xs text-muted-foreground">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 truncate">
            <MapPin className="w-3.5 h-3.5 flex-shrink-0 text-blue-600" aria-hidden="true" />
            <span className="truncate font-medium text-foreground">
              Receiving Hub: {requirement.destination_city}, {requirement.destination_state}
            </span>
          </div>

          {requirement.buyer?.business_name && (
            <span className="text-[11px] font-semibold text-muted-foreground truncate max-w-[140px]">
              {requirement.buyer.business_name}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 text-[11px] text-amber-700 font-medium">
          <Clock className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" aria-hidden="true" />
          <span>
            {t("requirements:procurement_deadline", "Procurement Deadline")}: {requirement.required_by_date}
          </span>
        </div>
      </div>

      {/* Action Trigger */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onViewDetails(requirement);
        }}
        className="w-full py-2.5 px-4 rounded-xl border border-blue-500/30 bg-blue-500/5 hover:bg-blue-600 hover:text-white text-blue-700 text-xs font-bold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 flex items-center justify-center gap-1.5 shadow-2xs"
      >
        <span>View Procurement Demand Details</span>
      </button>
    </div>
  );
};
