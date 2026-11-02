import React from "react";
import { MapPin, Clock } from "lucide-react";
import type { BuyerRequirementPublicSummary } from "../../types/requirements";

interface BuyerRequirementCardProps {
  requirement: BuyerRequirementPublicSummary;
  onViewDetails: (requirement: BuyerRequirementPublicSummary) => void;
}

export const BuyerRequirementCard: React.FC<BuyerRequirementCardProps> = ({
  requirement,
  onViewDetails,
}) => {
  return (
    <div className="rounded-2xl border border-border bg-card shadow-xs hover:shadow-md transition-all duration-200 p-5 flex flex-col justify-between space-y-4 group">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            {requirement.category_name && (
              <span className="inline-block text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-secondary text-foreground mb-1.5 border border-border">
                {requirement.category_name}
              </span>
            )}
            <h3 className="text-base font-bold text-foreground group-hover:text-primary transition-colors">
              {requirement.product_name}
            </h3>
          </div>

          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-800 border border-blue-200 flex-shrink-0">
            Verified Commercial Buyer
          </span>
        </div>

        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {requirement.title}
        </p>
      </div>

      {/* Demand & Price Specifications */}
      <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-secondary/40 border border-border/80 text-xs">
        <div>
          <span className="text-[11px] text-muted-foreground block">Required Quantity</span>
          <span className="text-sm font-extrabold text-foreground">
            {requirement.remaining_quantity}
            <span className="text-xs font-normal text-muted-foreground"> {requirement.unit}</span>
          </span>
          <span className="text-[10px] text-muted-foreground block">
            Total Demand: {requirement.required_quantity} {requirement.unit}
          </span>
        </div>

        <div>
          <span className="text-[11px] text-muted-foreground block">Target Price & Term</span>
          <span className="text-sm font-extrabold text-primary capitalize">
            {requirement.target_price_per_unit
              ? `₹${Number(requirement.target_price_per_unit).toLocaleString()} / ${requirement.unit}`
              : requirement.price_condition}
          </span>
          <span className="text-[10px] text-muted-foreground block capitalize">
            Term: {requirement.price_condition}
          </span>
        </div>
      </div>

      {/* Metadata */}
      <div className="space-y-1.5 pt-1 border-t border-border/60 text-xs text-muted-foreground">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 truncate">
            <MapPin className="w-3.5 h-3.5 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
            <span className="truncate">
              Dock: {requirement.destination_city}, {requirement.destination_state}
            </span>
          </div>

          {requirement.buyer?.business_name && (
            <span className="text-[11px] font-medium text-foreground truncate max-w-[140px]">
              {requirement.buyer.business_name}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 text-[11px] text-amber-700 font-medium">
          <Clock className="w-3.5 h-3.5 text-amber-600" aria-hidden="true" />
          <span>Needed by: {requirement.required_by_date}</span>
        </div>
      </div>

      {/* Action Trigger */}
      <button
        type="button"
        onClick={() => onViewDetails(requirement)}
        className="w-full py-2 px-4 rounded-xl border border-primary text-primary hover:bg-primary hover:text-primary-foreground text-xs font-bold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
      >
        View Procurement Demand Details
      </button>
    </div>
  );
};

