import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  X,
  Sparkles,
  Tractor,
  Loader2,
  AlertCircle,
  ShieldCheck,
  Handshake,
  MessageSquare,
  ShoppingCart,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { listingsApi } from "../../api/listings";
import { chatApi } from "../../api/chat";
import type { ProduceListingDetail } from "../../types/listings";
import { useAuth } from "../../store/authStore";
import { OfferCreateModal } from "../offers/OfferCreateModal";
import { OrderCreateModal } from "../orders/OrderCreateModal";
import { formatNumber, formatDate } from "../../utils/formatters";

interface ProduceDetailModalProps {
  listingId: string | null;
  onClose: () => void;
}

export const ProduceDetailModal: React.FC<ProduceDetailModalProps> = ({
  listingId,
  onClose,
}) => {
  const { t } = useTranslation(["marketplace", "common"]);
  const { user } = useAuth();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<ProduceListingDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isMessaging, setIsMessaging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [isOfferModalOpen, setIsOfferModalOpen] = useState(false);
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);

  const canMakeOffer =
    Boolean(user && user.role === "buyer" && user.verification_status === "verified" && detail && detail.status === "active");

  const canMessageFarmer =
    Boolean(user && detail && user.id !== detail.farmer?.id);

  const handleMessageFarmer = async () => {
    if (!detail || !user) return;
    setIsMessaging(true);
    try {
      const conv = await chatApi.createOrGetConversation({
        listing_id: detail.id,
        target_user_id: detail.farmer?.id || null,
      });
      onClose();
      navigate(`/dashboard/messages?conversationId=${conv.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to open conversation.";
      setError(msg);
    } finally {
      setIsMessaging(false);
    }
  };

  useEffect(() => {
    if (!listingId) {
      setDetail(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    listingsApi
      .getListing(listingId)
      .then((data) => {
        setDetail(data);
        setActiveImageIndex(0);
      })
      .catch((err) => {
        setError(err.message || "Failed to load complete produce listing specifications.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [listingId]);

  if (!listingId) return null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-produce-detail-title"
    >
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div>
            <h2 id="modal-produce-detail-title" className="text-lg font-bold text-foreground">
              {t("marketplace:produce_detail.title", "Produce Lot Specifications")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {t(
                "marketplace:produce_detail.subtitle",
                "Official catalog listing published by verified agricultural producer"
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label={t("common:actions.close", "Close dialog")}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[75vh] overflow-y-auto space-y-6">
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center text-muted-foreground gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-primary" aria-hidden="true" />
              <p className="text-sm">
                {t(
                  "marketplace:produce_detail.loading",
                  "Retrieving lot specifications and verified farm credentials..."
                )}
              </p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold">
                  {t("marketplace:produce_detail.error_title", "Unable to Load Details")}
                </p>
                <p className="text-xs">{error}</p>
              </div>
            </div>
          ) : detail ? (
            <>
              {/* Photo Gallery (if images present) or Fallback Placeholder */}
              {detail.images && detail.images.length > 0 ? (
                <div className="space-y-3">
                  <div className="aspect-video w-full rounded-xl overflow-hidden bg-secondary relative">
                    <img
                      src={
                        detail.images[activeImageIndex]?.image_url ||
                        listingsApi.getImageUrl(detail.id, detail.images[activeImageIndex]?.id)
                      }
                      alt={detail.title}
                      className="w-full h-full object-cover"
                    />
                    {detail.images[activeImageIndex]?.is_primary && (
                      <span className="absolute top-3 start-3 px-2 py-0.5 rounded-md bg-primary text-primary-foreground text-[10px] font-bold uppercase tracking-wider shadow-xs">
                        {t("marketplace:catalog_primary_photo", "Catalog Primary Photo")}
                      </span>
                    )}
                  </div>

                  {detail.images.length > 1 && (
                    <div className="flex items-center gap-2 overflow-x-auto pb-1">
                      {detail.images.map((img, idx) => (
                        <button
                          key={img.id}
                          type="button"
                          onClick={() => setActiveImageIndex(idx)}
                          className={`w-16 h-12 rounded-lg overflow-hidden border-2 flex-shrink-0 transition-all ${
                            activeImageIndex === idx ? "border-primary ring-2 ring-primary/20" : "border-border opacity-60 hover:opacity-100"
                          }`}
                        >
                          <img
                            src={img.image_url || listingsApi.getImageUrl(detail.id, img.id)}
                            alt={t("marketplace:thumbnail_n", "Thumbnail {{n}}", { n: idx + 1 })}
                            className="w-full h-full object-cover"
                          />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="aspect-video w-full rounded-xl overflow-hidden bg-secondary/40 border border-border flex flex-col items-center justify-center text-muted-foreground/40 gap-2">
                  <Tractor className="w-14 h-14 stroke-[1.25]" aria-hidden="true" />
                  <span className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider">
                    {t("marketplace:no_photos_uploaded", "No photographs uploaded for this produce lot")}
                  </span>
                </div>
              )}

              {/* Title & Headline */}
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" aria-hidden="true" />
                    {t("marketplace:verified_producer", "Verified Agricultural Producer")}
                  </span>

                  {detail.category?.name && (
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-secondary text-foreground border border-border">
                      {detail.category.name}
                    </span>
                  )}

                  {detail.quality_grade && (
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 flex items-center gap-1">
                      <Sparkles className="w-3 h-3 fill-current" aria-hidden="true" />
                      {detail.quality_grade}
                    </span>
                  )}
                </div>

                <h3 className="text-xl font-bold text-foreground">{detail.product_name}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed font-medium">
                  {detail.title}
                </p>
              </div>

              {/* Description */}
              {detail.description && (
                <div className="space-y-1 p-4 rounded-xl bg-secondary/30 border border-border">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    {t("marketplace:produce_description_heading", "Produce Lot Description & Storage")}
                  </h4>
                  <p className="text-xs text-foreground leading-relaxed whitespace-pre-line">
                    {detail.description}
                  </p>
                </div>
              )}

              {/* Lot Specifications Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-secondary/40 border border-border text-xs">
                <div>
                  <span className="text-muted-foreground block text-[11px]">{t("marketplace:available_volume", "Available Volume")}</span>
                  <span className="text-base font-bold text-primary">
                    {formatNumber(detail.available_quantity)} {detail.unit}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">{t("marketplace:wholesale_unit_price", "Wholesale Unit Price")}</span>
                  <span className="text-base font-bold text-foreground">
                    ₹{formatNumber(Number(detail.price_per_unit))}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">{t("marketplace:dispatch_available_from", "Dispatch Available From")}</span>
                  <span className="font-semibold text-foreground">{formatDate(detail.available_from)}</span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">{t("marketplace:harvest_date", "Harvest Date")}</span>
                  <span className="font-semibold text-foreground">{detail.harvest_date ? formatDate(detail.harvest_date) : "—"}</span>
                </div>
              </div>

              {/* Farm Origin Summary */}
              {detail.farmer && (
                <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <Tractor className="w-4 h-4 text-primary" aria-hidden="true" />
                    <span>{t("marketplace:originating_farm_producer", "Originating Farm & Producer")}</span>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-muted-foreground">{t("marketplace:producer_name", "Producer Name:")}</span>{" "}
                      <span className="font-semibold text-foreground">{detail.farmer.full_name}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t("marketplace:farm_operation", "Farm Operation:")}</span>{" "}
                      <span className="font-semibold text-foreground">{detail.farmer.farm_name}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t("marketplace:location", "Location:")}</span>{" "}
                      <span className="font-semibold text-foreground">
                        {detail.farmer.city}, {detail.farmer.state}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border flex items-center justify-between bg-secondary/20">
          <span className="text-[11px] text-muted-foreground">
            {t("marketplace:direct_trade_footer", "Direct B2B Agricultural Trade — No Middlemen Markups")}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
            >
              {t("common:close", "Close")}
            </button>
            {canMessageFarmer && (
              <button
                type="button"
                onClick={handleMessageFarmer}
                disabled={isMessaging}
                className="px-3.5 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                {isMessaging ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <MessageSquare className="w-3.5 h-3.5 text-primary" />
                )}
                <span>{t("marketplace:message_farmer", "Message Farmer")}</span>
              </button>
            )}
            {canMakeOffer && (
              <>
                <button
                  type="button"
                  onClick={() => setIsOfferModalOpen(true)}
                  className="px-3.5 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors flex items-center gap-1.5"
                >
                  <Handshake className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>{t("marketplace:make_purchase_offer", "Make Purchase Offer")}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setIsOrderModalOpen(true)}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors flex items-center gap-1.5"
                >
                  <ShoppingCart className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>{t("marketplace:place_direct_order", "Place Order")}</span>
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {detail && (
        <>
          <OfferCreateModal
            isOpen={isOfferModalOpen}
            onClose={() => setIsOfferModalOpen(false)}
            targetType="listing"
            targetListing={detail}
            onSuccess={() => {
              setIsOfferModalOpen(false);
              onClose();
            }}
          />
          <OrderCreateModal
            isOpen={isOrderModalOpen}
            listing={detail}
            onClose={() => setIsOrderModalOpen(false)}
            onSuccess={() => {
              setIsOrderModalOpen(false);
              onClose();
              navigate("/dashboard/orders");
            }}
          />
        </>
      )}
    </div>
  );
};

