import React, { useState } from "react";
import { X, Loader2, AlertCircle, CheckCircle2, ShieldCheck, Info } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../store/authStore";
import { offersApi } from "../../api/offers";
import { ApiError } from "../../api/errors";
import { formatNumber } from "../../utils/formatters";
import type {
  ItemFulfillmentDecision,
  OfferAcceptPayload,
  OfferAcceptResponse,
  OfferDetail,
} from "../../types/offers";

interface OfferAcceptModalProps {
  isOpen: boolean;
  offer: OfferDetail;
  onClose: () => void;
  onSuccess: (response: OfferAcceptResponse) => void;
}

export const OfferAcceptModal: React.FC<OfferAcceptModalProps> = ({
  isOpen,
  offer,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["offers", "orders", "common", "errors"]);
  const { user } = useAuth();
  const isBuyer = user?.role === "buyer";

  // Global fulfillment directives for buyer
  const [applyToRequirement, setApplyToRequirement] = useState(true);
  const [closeRequirement, setCloseRequirement] = useState(false);

  // Per-item fulfillment controls (for items with buyer_requirement_id)
  const reqItems = offer.items.filter((item) => Boolean(item.buyer_requirement_id));
  const isMultiRequirement = reqItems.length > 1;

  const [itemFulfillments, setItemFulfillments] = useState<
    Record<
      string,
      {
        apply: boolean;
        approvedQty: string;
        closeReq: boolean;
      }
    >
  >(() => {
    const initial: Record<string, { apply: boolean; approvedQty: string; closeReq: boolean }> = {};
    reqItems.forEach((it) => {
      initial[it.id] = {
        apply: true,
        approvedQty: String(it.quantity),
        closeReq: false,
      };
    });
    return initial;
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const isSubmittingRef = React.useRef(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  React.useEffect(() => {
    if (!isOpen) {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
      setGeneralError(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleItemFulfillmentChange = (
    itemId: string,
    field: "apply" | "approvedQty" | "closeReq",
    value: boolean | string
  ) => {
    setItemFulfillments((prev) => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        [field]: value,
      },
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmittingRef.current || isSubmitting) return;
    isSubmittingRef.current = true;
    setIsSubmitting(true);
    setGeneralError(null);

    try {
      let payload: OfferAcceptPayload = {};

      if (isBuyer) {
        if (isMultiRequirement) {
          const decisions: ItemFulfillmentDecision[] = reqItems.map((it) => {
            const dec = itemFulfillments[it.id];
            const qtyNum = dec && dec.approvedQty ? Number(dec.approvedQty) : undefined;
            return {
              offer_item_id: it.id,
              apply_to_requirement: dec ? dec.apply : true,
              approved_quantity: qtyNum && !isNaN(qtyNum) ? qtyNum : undefined,
              close_requirement: dec ? dec.closeReq : false,
            };
          });

          payload = {
            apply_to_requirement: applyToRequirement,
            close_requirement: closeRequirement,
            item_fulfillments: decisions,
          };
        } else {
          payload = {
            apply_to_requirement: applyToRequirement,
            close_requirement: closeRequirement,
          };
        }
      }

      const response = await offersApi.acceptOffer(offer.id, payload);
      onSuccess(response);
    } catch (err: unknown) {
      if (err instanceof ApiError && (err.status === 409 || err.message?.includes("already been generated"))) {
        // Idempotent recovery: order already created, dismiss gracefully
        onClose();
        return;
      }
      if (err instanceof ApiError) {
        setGeneralError(
          err.message || t("errors:offer_accept_failed", "Failed to accept offer. The proposal or inventory state may have changed.")
        );
      } else {
        setGeneralError(t("errors:network_error_accept", "An unexpected network error occurred while accepting offer."));
      }
    } finally {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-accept-offer-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600">
              <CheckCircle2 className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="modal-accept-offer-title" className="text-base font-bold text-foreground">
                {t("offers:accept_offer_modal_title", "Accept Trade Offer")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {t("offers:finalizing_proposal", `Finalizing proposal ${offer.offer_number} (Total: ₹${formatNumber(Number(offer.total_amount))})`, {
                  num: offer.offer_number,
                  total: formatNumber(Number(offer.total_amount)),
                })}
              </p>
            </div>
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

        {/* Content Form */}
        <form onSubmit={handleSubmit}>
          <div className="p-6 max-h-[75vh] overflow-y-auto space-y-4 text-xs">
            {generalError && (
              <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
                <p className="font-semibold">{generalError}</p>
              </div>
            )}

            {/* Invariant Explanation */}
            <div className="p-3.5 rounded-xl bg-secondary/40 border border-border space-y-1.5 text-foreground leading-relaxed">
              <div className="flex items-center gap-1.5 font-bold text-primary">
                <ShieldCheck className="w-4 h-4" aria-hidden="true" />
                <span>{t("offers:binding_trade_commitment", "Binding Trade Commitment")}</span>
              </div>
              <p className="text-muted-foreground">
                {t(
                  "offers:binding_commitment_desc",
                  "Accepting this offer generates an official B2B trade Order and atomically updates producer inventory."
                )}
              </p>
            </div>

            {/* Buyer-Specific Fulfillment Options */}
            {isBuyer && reqItems.length > 0 ? (
              <div className="space-y-3 pt-1">
                <div className="font-bold text-foreground text-xs uppercase tracking-wider flex items-center gap-1">
                  <span>{t("offers:fulfillment_decision_heading", "Requirement Fulfillment Decision")}</span>
                </div>

                {!isMultiRequirement ? (
                  <div className="space-y-3 p-3.5 rounded-xl border border-border bg-secondary/20">
                    <label className="flex items-start gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={applyToRequirement}
                        onChange={(e) => setApplyToRequirement(e.target.checked)}
                        className="mt-0.5 rounded text-primary focus:ring-primary"
                      />
                      <div>
                        <span className="font-semibold text-foreground block">
                          {t("offers:deduct_remaining_demand", "Deduct from linked requirement remaining demand")}
                        </span>
                        <span className="text-[11px] text-muted-foreground block">
                          {t("offers:deduct_remaining_demand_desc", "Automatically reduces remaining demand on your procurement board.")}
                        </span>
                      </div>
                    </label>

                    <label className="flex items-start gap-2 cursor-pointer pt-2 border-t border-border">
                      <input
                        type="checkbox"
                        checked={closeRequirement}
                        onChange={(e) => setCloseRequirement(e.target.checked)}
                        className="mt-0.5 rounded text-primary focus:ring-primary"
                      />
                      <div>
                        <span className="font-semibold text-foreground block">
                          {t("offers:close_req_upon_acceptance", "Mark requirement as Closed upon acceptance")}
                        </span>
                        <span className="text-[11px] text-muted-foreground block">
                          {t("offers:close_req_desc", "Archiving requirement demand so no further offers can be submitted.")}
                        </span>
                      </div>
                    </label>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-[11px] text-muted-foreground">
                      {t("offers:multi_req_desc", "This multi-product proposal links to several procurement requirements. Specify decisions for each item:")}
                    </p>
                    {reqItems.map((it) => {
                      const dec = itemFulfillments[it.id] || {
                        apply: true,
                        approvedQty: String(it.quantity),
                        closeReq: false,
                      };
                      return (
                        <div
                          key={it.id}
                          className="p-3 rounded-xl border border-border bg-secondary/20 space-y-2"
                        >
                          <div className="font-semibold text-foreground">
                            {it.product_name} ({formatNumber(it.quantity)} {it.unit})
                          </div>
                          <label className="flex items-center gap-2 text-[11px]">
                            <input
                              type="checkbox"
                              checked={dec.apply}
                              onChange={(e) =>
                                handleItemFulfillmentChange(it.id, "apply", e.target.checked)
                              }
                              className="rounded text-primary focus:ring-primary"
                            />
                            <span>{t("offers:apply_qty_toward_fulfillment", "Apply quantity toward requirement fulfillment")}</span>
                          </label>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : !isBuyer ? (
              <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200 text-blue-900 flex items-start gap-2">
                <Info className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-[11px] leading-relaxed">
                  {t(
                    "offers:seller_acceptance_notice",
                    "As the seller, your acceptance commits your harvested produce supply. If this offer was placed against a buyer requirement, fulfillment deductions will be submitted for the buyer’s review under platform governance rules."
                  )}
                </p>
              </div>
            ) : null}
          </div>

          {/* Footer */}
          <div className="px-6 py-3.5 border-t border-border flex items-center justify-end gap-2 bg-secondary/20">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-3.5 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
            >
              {t("common:cancel", "Cancel")}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 transition-colors disabled:opacity-50 shadow-xs"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                  <span>{t("offers:processing_acceptance", "Processing Acceptance...")}</span>
                </>
              ) : (
                <span>{t("offers:confirm_create_order", "Confirm & Create Order")}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

