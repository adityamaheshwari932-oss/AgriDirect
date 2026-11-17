import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  X,
  Loader2,
  AlertCircle,
  Clock,
  ShieldCheck,
  Building,
  Handshake,
  MessageSquare,
} from "lucide-react";
import { requirementsApi } from "../../api/requirements";
import { chatApi } from "../../api/chat";
import type { BuyerRequirementDetail } from "../../types/requirements";
import { useAuth } from "../../store/authStore";
import { OfferCreateModal } from "../offers/OfferCreateModal";
import { useTranslation } from "react-i18next";
import { formatNumber, formatDate } from "../../utils/formatters";

interface RequirementDetailModalProps {
  requirementId: string | null;
  onClose: () => void;
}

export const RequirementDetailModal: React.FC<RequirementDetailModalProps> = ({
  requirementId,
  onClose,
}) => {
  const { t } = useTranslation(["requirements", "marketplace", "common"]);
  const { user } = useAuth();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<BuyerRequirementDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isMessaging, setIsMessaging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOfferModalOpen, setIsOfferModalOpen] = useState(false);

  const canSubmitOffer =
    Boolean(user && user.role === "farmer" && user.verification_status === "verified" && detail && detail.status === "active");

  const canMessageBuyer =
    Boolean(user && detail && user.id !== detail.buyer?.id);

  const handleMessageBuyer = async () => {
    if (!detail || !user) return;
    setIsMessaging(true);
    try {
      const conv = await chatApi.createOrGetConversation({
        requirement_id: detail.id,
        target_user_id: detail.buyer?.id || null,
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
    if (!requirementId) {
      setDetail(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    requirementsApi
      .getRequirement(requirementId)
      .then((data) => {
        setDetail(data);
      })
      .catch((err) => {
        setError(err.message || "Failed to load procurement requirement specifications.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [requirementId]);

  if (!requirementId) return null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-req-detail-title"
    >
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div>
            <h2 id="modal-req-detail-title" className="text-lg font-bold text-foreground">
              {t("requirements:detail_title", "Procurement Demand Specifications")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {t("requirements:detail_subtitle", "Official procurement requirement posted by verified commercial buyer")}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label={t("common:close_dialog", "Close dialog")}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[75vh] overflow-y-auto space-y-6">
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center text-muted-foreground gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-primary" aria-hidden="true" />
              <p className="text-sm">{t("requirements:loading_details", "Retrieving procurement demand details...")}</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold">{t("common:unable_to_load", "Unable to Load Details")}</p>
                <p className="text-xs">{error}</p>
              </div>
            </div>
          ) : detail ? (
            <>
              {/* Title & Badges */}
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-800 border border-blue-200 flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-blue-600" aria-hidden="true" />
                    {t("marketplace:verified_buyer", "Verified Commercial Buyer")}
                  </span>

                  {detail.category?.name && (
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-secondary text-foreground border border-border">
                      {detail.category.name}
                    </span>
                  )}

                  {detail.quality_grade && (
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-secondary text-foreground border border-border">
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
                    {t("requirements:specifications_heading", "Procurement Specifications & Receiving Dock Instructions")}
                  </h4>
                  <p className="text-xs text-foreground leading-relaxed whitespace-pre-line">
                    {detail.description}
                  </p>
                </div>
              )}

              {/* Demand Specifications Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-secondary/40 border border-border text-xs">
                <div>
                  <span className="text-muted-foreground block text-[11px]">{t("requirements:remaining_demand", "Remaining Demand")}</span>
                  <span className="text-base font-bold text-primary">
                    {formatNumber(detail.remaining_quantity)} {detail.unit}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">{t("requirements:total_volume", "Total Volume")}</span>
                  <span className="text-base font-bold text-foreground">
                    {formatNumber(detail.required_quantity)} {detail.unit}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">{t("requirements:pricing_term", "Pricing Term")}</span>
                  <span className="font-semibold text-foreground capitalize">
                    {detail.price_condition}
                  </span>
                  {detail.target_price_per_unit && (
                    <span className="text-[11px] text-muted-foreground block">
                      {t("requirements:target_label", "Target: ₹{{price}}", {
                        price: formatNumber(Number(detail.target_price_per_unit)),
                      })}
                    </span>
                  )}
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">{t("requirements:required_by_date", "Required By Date")}</span>
                  <span className="font-semibold text-amber-700 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-amber-600" aria-hidden="true" />
                    {formatDate(detail.required_by_date)}
                  </span>
                </div>
              </div>

              {/* Commercial Enterprise Summary */}
              {detail.buyer && (
                <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <Building className="w-4 h-4 text-blue-600" aria-hidden="true" />
                    <span>{t("requirements:enterprise_summary", "Commercial Buyer Enterprise")}</span>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-muted-foreground">{t("requirements:business_name", "Business Name:")}</span>{" "}
                      <span className="font-semibold text-foreground">{detail.buyer.business_name}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t("requirements:contact_person", "Contact Person:")}</span>{" "}
                      <span className="font-semibold text-foreground">{detail.buyer.contact_person_name}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t("requirements:enterprise_type", "Enterprise Type:")}</span>{" "}
                      <span className="font-semibold text-foreground capitalize">{detail.buyer.business_type}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t("requirements:delivery_dock", "Delivery Receiving Dock:")}</span>{" "}
                      <span className="font-semibold text-foreground">
                        {detail.destination_city}, {detail.destination_state}
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
            {t("requirements:direct_procurement_footer", "Direct Commercial Procurement — Standardized Grading & Trade Terms")}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
            >
              {t("common:close", "Close")}
            </button>
            {canMessageBuyer && (
              <button
                type="button"
                onClick={handleMessageBuyer}
                disabled={isMessaging}
                className="px-3.5 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                {isMessaging ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <MessageSquare className="w-3.5 h-3.5 text-primary" />
                )}
                <span>{t("requirements:message_buyer", "Message Buyer")}</span>
              </button>
            )}
            {canSubmitOffer && (
              <button
                type="button"
                onClick={() => setIsOfferModalOpen(true)}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors flex items-center gap-1.5"
              >
                <Handshake className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{t("requirements:submit_supply_offer", "Submit Supply Offer")}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {detail && (
        <OfferCreateModal
          isOpen={isOfferModalOpen}
          onClose={() => setIsOfferModalOpen(false)}
          targetType="requirement"
          targetRequirement={detail}
          onSuccess={() => {
            setIsOfferModalOpen(false);
            onClose();
          }}
        />
      )}
    </div>
  );
};

