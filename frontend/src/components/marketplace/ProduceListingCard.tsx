import React from "react";
import {
  MapPin,
  Calendar,
  Sparkles,
  Tractor,
} from "lucide-react";
import type { ProduceListingPublicSummary } from "../../types/listings";

interface ProduceListingCardProps {
  listing: ProduceListingPublicSummary;
  onViewDetails: (listing: ProduceListingPublicSummary) => void;
}

export const ProduceListingCard: React.FC<ProduceListingCardProps> = ({
  listing,
  onViewDetails,
}) => {
  return (
    <div className="rounded-2xl border border-border bg-card shadow-xs hover:shadow-md transition-all duration-200 overflow-hidden flex flex-col group">
      {/* Thumbnail */}
      <div className="relative aspect-video w-full bg-secondary/60 overflow-hidden">
        {listing.primary_image_uri ? (
          <img
            src={listing.primary_image_uri}
            alt={listing.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              (e.target as HTMLElement).style.display = "none";
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground/40 bg-secondary/40">
            <Tractor className="w-12 h-12 stroke-[1.5]" aria-hidden="true" />
          </div>
        )}

        {/* Category Pill */}
        {listing.category_name && (
          <span className="absolute top-3 left-3 px-2.5 py-1 rounded-full text-[11px] font-bold bg-background/90 text-foreground backdrop-blur-xs shadow-xs border border-border/60">
            {listing.category_name}
          </span>
        )}

        {/* Quality Grade */}
        {listing.quality_grade && (
          <span className="absolute top-3 right-3 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-primary text-primary-foreground shadow-xs flex items-center gap-1">
            <Sparkles className="w-3 h-3 fill-current" aria-hidden="true" />
            {listing.quality_grade}
          </span>
        )}
      </div>

      {/* Card Content */}
      <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-base font-bold text-foreground group-hover:text-primary transition-colors">
              {listing.product_name}
            </h3>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 flex-shrink-0">
              Verified Producer
            </span>
          </div>

          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {listing.title}
          </p>
        </div>

        {/* Pricing & Supply Data */}
        <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-secondary/40 border border-border/80">
          <div>
            <span className="text-[11px] text-muted-foreground block">Wholesale Price</span>
            <span className="text-sm font-extrabold text-foreground">
              ₹{Number(listing.price_per_unit).toLocaleString()}
              <span className="text-xs font-normal text-muted-foreground"> / {listing.unit}</span>
            </span>
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground block">Available Volume</span>
            <span className="text-sm font-extrabold text-primary">
              {listing.available_quantity}{" "}
              <span className="text-xs font-semibold text-muted-foreground">{listing.unit}</span>
            </span>
          </div>
        </div>

        {/* Metadata Footer */}
        <div className="space-y-2 pt-1 border-t border-border/60 text-xs text-muted-foreground">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 truncate">
              <MapPin className="w-3.5 h-3.5 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
              <span className="truncate">
                {listing.location_city}, {listing.location_state}
              </span>
            </div>

            {listing.farmer?.farm_name && (
              <span className="text-[11px] font-medium text-foreground truncate max-w-[140px]">
                {listing.farmer.farm_name}
              </span>
            )}
          </div>

          {listing.available_from && (
            <div className="flex items-center gap-1.5 text-[11px]">
              <Calendar className="w-3 h-3 text-muted-foreground" aria-hidden="true" />
              <span>Ready from: {listing.available_from}</span>
            </div>
          )}
        </div>

        {/* Action Button */}
        <button
          type="button"
          onClick={() => onViewDetails(listing)}
          className="w-full py-2 px-4 rounded-xl border border-primary text-primary hover:bg-primary hover:text-primary-foreground text-xs font-bold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
        >
          View Produce Lot Details
        </button>
      </div>
    </div>
  );
};

