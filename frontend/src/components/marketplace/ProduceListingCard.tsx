import React from "react";
import { useTranslation } from "react-i18next";
import {
  MapPin,
  Calendar,
  Sparkles,
  Tractor,
  ShieldCheck,
  ArrowUpRight,
} from "lucide-react";
import type { ProduceListingPublicSummary } from "../../types/listings";
import { formatNumber } from "../../utils/formatters";

interface ProduceListingCardProps {
  listing: ProduceListingPublicSummary;
  onViewDetails: (listing: ProduceListingPublicSummary) => void;
}

export const ProduceListingCard: React.FC<ProduceListingCardProps> = ({
  listing,
  onViewDetails,
}) => {
  const { t } = useTranslation("marketplace");
  const formattedPrice = formatNumber(Number(listing.price_per_unit), {
    maximumFractionDigits: 2,
  });

  return (
    <div
      onClick={() => onViewDetails(listing)}
      className="group rounded-2xl border border-border bg-card shadow-2xs hover:shadow-md hover:border-primary/40 transition-all duration-200 overflow-hidden flex flex-col cursor-pointer"
    >
      {/* Thumbnail with overlay tags */}
      <div className="relative aspect-video w-full bg-secondary/50 overflow-hidden">
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
          <div className="w-full h-full flex flex-col items-center justify-center text-muted-foreground/30 bg-gradient-to-br from-secondary/30 to-secondary/60">
            <Tractor className="w-12 h-12 stroke-[1.25]" aria-hidden="true" />
            <span className="text-[10px] font-medium text-muted-foreground/60 mt-1 uppercase tracking-wider">
              {t("farm_direct_lot", "Farm Direct Lot")}
            </span>
          </div>
        )}

        {/* Top Floating Category Tag */}
        {listing.category_name && (
          <span className="absolute top-3 start-3 px-2.5 py-1 rounded-full text-[11px] font-bold bg-background/90 text-foreground backdrop-blur-xs shadow-2xs border border-border/70">
            {listing.category_name}
          </span>
        )}

        {/* Quality Grade Floating Badge */}
        {listing.quality_grade && (
          <span className="absolute top-3 end-3 px-2.5 py-1 rounded-full text-[11px] font-bold bg-primary text-primary-foreground shadow-2xs flex items-center gap-1">
            <Sparkles className="w-3 h-3 fill-current" aria-hidden="true" />
            {listing.quality_grade}
          </span>
        )}
      </div>

      {/* Card Body */}
      <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-base font-bold text-foreground group-hover:text-primary transition-colors flex items-center gap-1">
              <span>{listing.product_name}</span>
              <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-primary rtl:-scale-x-100" />
            </h3>
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 border border-emerald-500/20 flex-shrink-0">
              <ShieldCheck className="w-3 h-3 text-emerald-600" />
              {t("verified_producer", "Verified Producer")}
            </span>
          </div>

          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {listing.title}
          </p>
        </div>

        {/* B2B Wholesale Pricing & Volume Matrix */}
        <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-secondary/35 border border-border/70">
          <div>
            <span className="text-[10px] uppercase font-bold text-muted-foreground block tracking-wider">
              {t("wholesale_rate", "Wholesale Rate")}
            </span>
            <div className="text-base font-extrabold text-foreground tabular">
              ₹{formattedPrice}
              <span className="text-xs font-normal text-muted-foreground"> / {listing.unit}</span>
            </div>
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-muted-foreground block tracking-wider">
              {t("available_volume", "Available Volume")}
            </span>
            <div className="text-base font-extrabold text-primary tabular">
              {formatNumber(Number(listing.available_quantity))}{" "}
              <span className="text-xs font-semibold text-muted-foreground">{listing.unit}</span>
            </div>
          </div>
        </div>

        {/* Metadata Footer: Location & Farm Details */}
        <div className="space-y-2 pt-2 border-t border-border/60 text-xs text-muted-foreground">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 truncate">
              <MapPin className="w-3.5 h-3.5 flex-shrink-0 text-primary/80" aria-hidden="true" />
              <span className="truncate font-medium text-foreground">
                {listing.location_city}, {listing.location_state}
              </span>
            </div>

            {listing.farmer?.farm_name && (
              <span className="text-[11px] font-semibold text-muted-foreground truncate max-w-[140px]">
                {listing.farmer.farm_name}
              </span>
            )}
          </div>

          {listing.available_from && (
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <Calendar className="w-3 h-3 text-muted-foreground/70" aria-hidden="true" />
              <span>
                {t("ready_for_dispatch", "Ready for dispatch: {{date}}", {
                  date: listing.available_from,
                })}
              </span>
            </div>
          )}
        </div>

        {/* Action Button */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onViewDetails(listing);
          }}
          className="w-full py-2.5 px-4 rounded-xl border border-primary/30 bg-primary/5 hover:bg-primary hover:text-primary-foreground text-primary text-xs font-bold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 flex items-center justify-center gap-1.5 shadow-2xs"
        >
          <span>{t("card_view_details", "View Produce Lot Details")}</span>
        </button>
      </div>
    </div>
  );
};
