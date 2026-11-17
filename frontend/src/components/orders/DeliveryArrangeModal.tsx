import React, { useState } from "react";
import { X, Truck, Calendar, MapPin, FileText, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ordersApi } from "../../api/orders";
import type { DeliveryArrangePayload, OrderDetail } from "../../types/orders";

interface DeliveryArrangeModalProps {
  isOpen: boolean;
  order: OrderDetail | null;
  onClose: () => void;
  onSuccess: (updated: OrderDetail) => void;
}

export const DeliveryArrangeModal: React.FC<DeliveryArrangeModalProps> = ({
  isOpen,
  order,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["orders", "validation", "common", "errors"]);
  const [deliveryMethod, setDeliveryMethod] = useState(
    order?.delivery_method || "seller_dispatch"
  );
  const [destinationAddress, setDestinationAddress] = useState(
    order?.delivery_destination_address || ""
  );
  const [arrangedDate, setArrangedDate] = useState(
    order?.delivery_arranged_date || ""
  );
  const [deliveryNotes, setDeliveryNotes] = useState(
    order?.delivery_notes || ""
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !order) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!destinationAddress.trim()) {
      setError(
        t("orders:delivery.address_required", "Delivery destination address is required.")
      );
      return;
    }
    if (!arrangedDate) {
      setError(
        t("orders:delivery.date_required", "Scheduled delivery or pickup date is required.")
      );
      return;
    }

    const payload: DeliveryArrangePayload = {
      delivery_method: deliveryMethod,
      delivery_destination_address: destinationAddress.trim(),
      delivery_arranged_date: arrangedDate,
      delivery_notes: deliveryNotes.trim() ? deliveryNotes.trim() : null,
    };

    setIsSubmitting(true);
    try {
      const updated = await ordersApi.arrangeDelivery(order.id, payload);
      onSuccess(updated);
      onClose();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("orders:delivery.failed", "Failed to arrange delivery.");
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-delivery-arrange-title"
    >
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-primary-50/50">
          <div className="flex items-center gap-2">
            <Truck className="w-5 h-5 text-primary" aria-hidden="true" />
            <h2 id="modal-delivery-arrange-title" className="text-base font-bold text-foreground">
              {t("orders:delivery.arrange_title", "Arrange Delivery Logistics")}
            </h2>
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

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs">
              {error}
            </div>
          )}

          <div className="text-xs text-muted-foreground space-y-1">
            <p>
              {t("orders:order_number", "Order Reference")}:{" "}
              <strong className="text-foreground">{order.order_number}</strong>
            </p>
            <p className="text-[11px]">
              {t(
                "orders:delivery.stage_notice",
                "Scheduling delivery will notify the counterparty and transition the order to Delivery Arranged."
              )}
            </p>
          </div>

          {/* Delivery Method */}
          <div className="space-y-1.5">
            <label
              htmlFor="delivery-method-select"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
            >
              {t("orders:delivery.method_label", "Logistics Method")}{" "}
              <span className="text-destructive">*</span>
            </label>
            <select
              id="delivery-method-select"
              value={deliveryMethod}
              onChange={(e) => setDeliveryMethod(e.target.value)}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
              required
            >
              <option value="seller_dispatch">
                {t(
                  "orders:delivery.method_seller_dispatch",
                  "Farmer Dispatch / Seller Transport"
                )}
              </option>
              <option value="buyer_pickup">
                {t(
                  "orders:delivery.method_buyer_pickup",
                  "Buyer Pickup at Farm Gate / Mandi"
                )}
              </option>
              <option value="third_party_transport">
                {t(
                  "orders:delivery.method_third_party",
                  "Third-Party Logistics / Freight Service"
                )}
              </option>
            </select>
          </div>

          {/* Arranged Date */}
          <div className="space-y-1.5">
            <label
              htmlFor="arranged-date-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"
            >
              <Calendar className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
              <span>{t("orders:delivery.scheduled_date_label", "Scheduled Date")}</span>{" "}
              <span className="text-destructive">*</span>
            </label>
            <input
              id="arranged-date-input"
              type="date"
              value={arrangedDate}
              onChange={(e) => setArrangedDate(e.target.value)}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
              required
            />
          </div>

          {/* Destination Address */}
          <div className="space-y-1.5">
            <label
              htmlFor="destination-address-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"
            >
              <MapPin className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
              <span>
                {t(
                  "orders:delivery.destination_address_label",
                  "Physical Destination Address"
                )}
              </span>{" "}
              <span className="text-destructive">*</span>
            </label>
            <textarea
              id="destination-address-input"
              rows={2}
              value={destinationAddress}
              onChange={(e) => setDestinationAddress(e.target.value)}
              placeholder={t(
                "orders:delivery.destination_placeholder",
                "Full street address, district, state, pin code..."
              )}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
              required
            />
          </div>

          {/* Special Notes / Instructions */}
          <div className="space-y-1.5">
            <label
              htmlFor="delivery-notes-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
              <span>
                {t(
                  "orders:delivery.notes_label",
                  "Handling & Contact Instructions (Optional)"
                )}
              </span>
            </label>
            <textarea
              id="delivery-notes-input"
              rows={2}
              value={deliveryNotes}
              onChange={(e) => setDeliveryNotes(e.target.value)}
              placeholder={t(
                "orders:delivery.notes_placeholder",
                "e.g., Driver phone number, vehicle plate number, gate entry contact..."
              )}
              maxLength={1000}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
            />
          </div>

          {/* Actions */}
          <div className="pt-3 flex items-center justify-end gap-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
            >
              {t("common:actions.cancel", "Cancel")}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>{t("orders:delivery.scheduling", "Scheduling...")}</span>
                </>
              ) : (
                <span>{t("orders:delivery.confirm_logistics", "Confirm Logistics")}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

