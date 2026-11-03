import React, { useState } from "react";
import { X, Loader2, AlertCircle, ArrowRightLeft } from "lucide-react";
import { offersApi } from "../../api/offers";
import { ApiError } from "../../api/errors";
import type {
  CounterOfferCreatePayload,
  OfferDetail,
  OfferItemCreatePayload,
} from "../../types/offers";

interface CounterOfferModalProps {
  isOpen: boolean;
  parentOffer: OfferDetail;
  onClose: () => void;
  onSuccess: (newCounterOffer: OfferDetail) => void;
}

export const CounterOfferModal: React.FC<CounterOfferModalProps> = ({
  isOpen,
  parentOffer,
  onClose,
  onSuccess,
}) => {
  const [deliveryTerms, setDeliveryTerms] = useState<string>(
    parentOffer.delivery_terms || ""
  );
  const [proposedDeliveryDate, setProposedDeliveryDate] = useState<string>(
    parentOffer.proposed_delivery_date || ""
  );

  // Pre-populate items from parent offer
  const [items, setItems] = useState<
    Array<{
      listing_id: string;
      buyer_requirement_id?: string | null;
      product_name: string;
      quantity: string;
      unit: string;
      unit_price: string;
      quality_grade?: string | null;
    }>
  >(
    parentOffer.items.map((item) => ({
      listing_id: item.listing_id || "",
      buyer_requirement_id: item.buyer_requirement_id || null,
      product_name: item.product_name,
      quantity: String(item.quantity),
      unit: item.unit,
      unit_price: String(item.unit_price),
      quality_grade: item.quality_grade || null,
    }))
  );

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  if (!isOpen) return null;

  const handleItemChange = (
    index: number,
    field: "quantity" | "unit_price",
    value: string
  ) => {
    setItems((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    items.forEach((item, idx) => {
      const qty = Number(item.quantity);
      if (!item.quantity || isNaN(qty) || qty <= 0) {
        errors[`item_${idx}_quantity`] = "Quantity must be greater than zero.";
      }
      const price = Number(item.unit_price);
      if (!item.unit_price || isNaN(price) || price <= 0) {
        errors[`item_${idx}_price`] = "Unit price must be greater than zero.";
      }
    });

    if (proposedDeliveryDate) {
      const todayStr = new Date().toISOString().slice(0, 10);
      if (proposedDeliveryDate < todayStr) {
        errors.proposed_delivery_date = "Delivery date cannot be in the past.";
      }
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError(null);

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const preparedItems: OfferItemCreatePayload[] = items.map((item) => ({
        listing_id: item.listing_id,
        buyer_requirement_id: item.buyer_requirement_id || null,
        product_name: item.product_name,
        quantity: Number(item.quantity),
        unit: item.unit,
        unit_price: Number(item.unit_price),
        quality_grade: item.quality_grade || null,
      }));

      const payload: CounterOfferCreatePayload = {
        delivery_terms: deliveryTerms.trim() || null,
        proposed_delivery_date: proposedDeliveryDate || null,
        items: preparedItems,
      };

      const newOffer = await offersApi.counterOffer(parentOffer.id, payload);
      onSuccess(newOffer);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setGeneralError(
          err.message || "Failed to submit counter-proposal. Please review your terms."
        );
      } else {
        setGeneralError("An unexpected network error occurred while submitting counter-offer.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const counterpartyName =
    parentOffer.sender?.name || parentOffer.sender?.business_name || "Counterparty";

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-counter-offer-title"
    >
      <div className="bg-card w-full max-w-xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <ArrowRightLeft className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="modal-counter-offer-title" className="text-base font-bold text-foreground">
                Submit Counter-Offer
              </h2>
              <p className="text-xs text-muted-foreground">
                Responding to proposal {parentOffer.offer_number} from {counterpartyName}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content Form */}
        <form onSubmit={handleSubmit}>
          <div className="p-6 max-h-[75vh] overflow-y-auto space-y-5 text-xs">
            {generalError && (
              <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
                <p className="font-semibold">{generalError}</p>
              </div>
            )}

            {/* Explanatory Banner */}
            <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200 text-blue-900 leading-relaxed">
              Adjust the unit price or quantity to propose amended commercial terms. The existing
              offer will transition to <strong>Countered</strong>, and this new proposal will be
              transmitted directly to {counterpartyName}.
            </div>

            {/* Line Items Modification */}
            <div className="space-y-3">
              <label className="block text-xs font-bold text-foreground uppercase tracking-wider">
                Produce Line Items
              </label>

              {items.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl border border-border bg-secondary/20 space-y-2.5"
                >
                  <div className="font-bold text-foreground text-sm flex items-center justify-between">
                    <span>{item.product_name}</span>
                    <span className="text-[11px] text-muted-foreground font-normal">
                      Item #{idx + 1}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label
                        htmlFor={`counter-qty-${idx}`}
                        className="block text-[11px] font-semibold text-muted-foreground mb-1"
                      >
                        Quantity ({item.unit}) <span className="text-destructive">*</span>
                      </label>
                      <input
                        id={`counter-qty-${idx}`}
                        type="number"
                        step="any"
                        value={item.quantity}
                        onChange={(e) => handleItemChange(idx, "quantity", e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                      {fieldErrors[`item_${idx}_quantity`] && (
                        <p className="text-[11px] text-destructive mt-1">
                          {fieldErrors[`item_${idx}_quantity`]}
                        </p>
                      )}
                    </div>

                    <div>
                      <label
                        htmlFor={`counter-price-${idx}`}
                        className="block text-[11px] font-semibold text-muted-foreground mb-1"
                      >
                        Unit Price (₹ / {item.unit}) <span className="text-destructive">*</span>
                      </label>
                      <input
                        id={`counter-price-${idx}`}
                        type="number"
                        step="any"
                        value={item.unit_price}
                        onChange={(e) => handleItemChange(idx, "unit_price", e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                      {fieldErrors[`item_${idx}_price`] && (
                        <p className="text-[11px] text-destructive mt-1">
                          {fieldErrors[`item_${idx}_price`]}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Delivery Terms */}
            <div>
              <label
                htmlFor="counter-delivery-terms"
                className="block text-xs font-semibold text-foreground mb-1"
              >
                Delivery & Transport Terms
              </label>
              <textarea
                id="counter-delivery-terms"
                rows={2}
                value={deliveryTerms}
                onChange={(e) => setDeliveryTerms(e.target.value)}
                placeholder="e.g. Farm gate pickup by buyer, or seller delivery to warehouse dock..."
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Proposed Delivery Date */}
            <div>
              <label
                htmlFor="counter-delivery-date"
                className="block text-xs font-semibold text-foreground mb-1"
              >
                Target Delivery Date
              </label>
              <input
                id="counter-delivery-date"
                type="date"
                min={new Date().toISOString().slice(0, 10)}
                value={proposedDeliveryDate}
                onChange={(e) => setProposedDeliveryDate(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-border bg-background text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {fieldErrors.proposed_delivery_date && (
                <p className="text-[11px] text-destructive mt-1">
                  {fieldErrors.proposed_delivery_date}
                </p>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-3.5 border-t border-border flex items-center justify-end gap-2 bg-secondary/20">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-3.5 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-700 transition-colors disabled:opacity-50 shadow-xs"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                  <span>Transmitting Proposal...</span>
                </>
              ) : (
                <span>Submit Counter-Offer</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

