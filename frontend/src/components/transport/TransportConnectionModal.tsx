import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  X,
  Truck,
  MapPin,
  AlertCircle,
  ShieldAlert,
  Loader2,
  CheckCircle2,
  Link as LinkIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../store/authStore";
import { transportersApi } from "../../api/transporters";
import type {
  TransporterSearchResult,
  TransportConnectionRequest,
  TransportConnectionRequestCreate,
} from "../../types/transporter";

interface TransportConnectionModalProps {
  transporter: TransporterSearchResult | null;
  orderId?: string | null;
  orderNumber?: string | null;
  offerId?: string | null;
  offerNumber?: string | null;
  initialPickupState?: string;
  initialPickupDistrict?: string;
  initialPickupAddress?: string;
  initialDeliveryState?: string;
  initialDeliveryDistrict?: string;
  initialDeliveryAddress?: string;
  initialCargoDescription?: string;
  initialWeightKg?: number;
  initialDeliveryDate?: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (request: TransportConnectionRequest) => void;
}

export const TransportConnectionModal: React.FC<TransportConnectionModalProps> = ({
  transporter,
  orderId,
  orderNumber,
  offerId,
  offerNumber,
  initialPickupState = "",
  initialPickupDistrict = "",
  initialPickupAddress = "",
  initialDeliveryState = "",
  initialDeliveryDistrict = "",
  initialDeliveryAddress = "",
  initialCargoDescription = "",
  initialWeightKg,
  initialDeliveryDate = "",
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["delivery", "common"]);
  const { user } = useAuth();
  const isVerified = user?.role === "admin" || user?.verification_status === "verified";

  const [pickupState, setPickupState] = useState(initialPickupState);
  const [pickupDistrict, setPickupDistrict] = useState(initialPickupDistrict);
  const [pickupAddress, setPickupAddress] = useState(initialPickupAddress);

  const [deliveryState, setDeliveryState] = useState(initialDeliveryState);
  const [deliveryDistrict, setDeliveryDistrict] = useState(initialDeliveryDistrict);
  const [deliveryAddress, setDeliveryAddress] = useState(initialDeliveryAddress);

  const [cargoDescription, setCargoDescription] = useState(
    initialCargoDescription.length > 255 ? initialCargoDescription.slice(0, 255) : initialCargoDescription
  );
  const [weightKg, setWeightKg] = useState<number | "">(initialWeightKg || "");
  const [requiredDeliveryDate, setRequiredDeliveryDate] = useState(initialDeliveryDate);
  const [notes, setNotes] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !transporter) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isVerified) {
      setError(
        t(
          "delivery:verification_required_transport",
          "Account verification is required to request transportation services. Please verify your account."
        )
      );
      return;
    }

    if (!transporter.user_id) {
      setError(
        t(
          "delivery:transporter_user_id_missing",
          "Transporter user identifier is missing. Please select another provider or refresh."
        )
      );
      return;
    }

    if (!cargoDescription.trim() && !orderId && !offerId) {
      setError(t("delivery:cargo_desc_required", "Please describe the cargo or select an active transaction."));
      return;
    }

    const payload: TransportConnectionRequestCreate = {
      transporter_user_id: transporter.user_id,
      order_id: orderId || undefined,
      offer_id: offerId || undefined,
      pickup_state: pickupState.trim() || undefined,
      pickup_district: pickupDistrict.trim() || undefined,
      pickup_address: pickupAddress.trim() || undefined,
      delivery_state: deliveryState.trim() || undefined,
      delivery_district: deliveryDistrict.trim() || undefined,
      delivery_address: deliveryAddress.trim() || undefined,
      cargo_description: cargoDescription.trim().slice(0, 255) || undefined,
      weight_kg: weightKg ? Number(weightKg) : undefined,
      required_delivery_date: requiredDeliveryDate || undefined,
      notes: notes.trim() || undefined,
    };

    setIsSubmitting(true);
    try {
      const res = await transportersApi.createConnectionRequest(payload);
      onSuccess(res);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("already exists") || msg.includes("409")) {
        setError(
          t(
            "delivery:duplicate_request_warning",
            "A pending or active transportation request already exists for this provider and transaction."
          )
        );
      } else {
        setError(msg || t("delivery:request_failed", "Failed to submit transport request."));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="transport-connection-modal-title"
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <div className="bg-card border border-border w-full max-w-xl rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-border flex items-center justify-between bg-secondary/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <h2 id="transport-connection-modal-title" className="text-base font-bold text-foreground">
                {t("delivery:request_transport_title", "Request Transport Service")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {transporter.business_name} ({transporter.transport_type.replace("_", " ")})
              </p>
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

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-4 text-xs flex-1">
          {!isVerified && (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-xs">
                  {t("delivery:verification_required_title", "Account Verification Required")}
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {t(
                    "delivery:verification_required_transport",
                    "Account verification is required to request transportation services. Please complete profile verification."
                  )}
                </p>
                <Link
                  to="/verification"
                  className="inline-block text-[11px] font-bold text-primary hover:underline mt-0.5"
                >
                  {t("delivery:go_to_verification", "Go to Verification →")}
                </Link>
              </div>
            </div>
          )}

          {/* Associated Context Pill if linked to deal */}
          {(orderNumber || offerNumber) && (
            <div className="p-3 rounded-xl bg-primary/5 border border-primary/20 text-foreground flex items-center gap-2">
              <LinkIcon className="w-4 h-4 text-primary flex-shrink-0" />
              <span>
                <strong>{t("delivery:linked_transaction", "Linked Deal Context")}:</strong>{" "}
                {orderNumber ? `Order #${orderNumber}` : `Offer Proposal #${offerNumber}`}
              </span>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Pickup Location Group */}
          <div className="space-y-2 p-3.5 rounded-xl border border-border/80 bg-secondary/20">
            <h3 className="font-bold text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-emerald-600" />
              <span>{t("delivery:pickup_location", "Origin / Farm Gate Pickup")}</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold mb-1 text-foreground">{t("delivery:state", "State")}</label>
                <input
                  type="text"
                  value={pickupState}
                  onChange={(e) => setPickupState(e.target.value)}
                  placeholder="e.g. Maharashtra"
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold mb-1 text-foreground">{t("delivery:district", "District")}</label>
                <input
                  type="text"
                  value={pickupDistrict}
                  onChange={(e) => setPickupDistrict(e.target.value)}
                  placeholder="e.g. Nashik"
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block font-semibold mb-1 text-foreground">{t("delivery:pickup_address_label", "Pickup Address / Landmark")}</label>
              <input
                type="text"
                value={pickupAddress}
                onChange={(e) => setPickupAddress(e.target.value)}
                placeholder="e.g. Gate 2, Dindori Farm Estate"
                className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
              />
            </div>
          </div>

          {/* Delivery Location Group */}
          <div className="space-y-2 p-3.5 rounded-xl border border-border/80 bg-secondary/20">
            <h3 className="font-bold text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-blue-600" />
              <span>{t("delivery:delivery_destination", "Destination / Receiving Facility")}</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold mb-1 text-foreground">{t("delivery:state", "State")}</label>
                <input
                  type="text"
                  value={deliveryState}
                  onChange={(e) => setDeliveryState(e.target.value)}
                  placeholder="e.g. Maharashtra"
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold mb-1 text-foreground">{t("delivery:district", "District")}</label>
                <input
                  type="text"
                  value={deliveryDistrict}
                  onChange={(e) => setDeliveryDistrict(e.target.value)}
                  placeholder="e.g. Mumbai"
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block font-semibold mb-1 text-foreground">{t("delivery:delivery_address_label", "Destination Address")}</label>
              <input
                type="text"
                value={deliveryAddress}
                onChange={(e) => setDeliveryAddress(e.target.value)}
                placeholder="e.g. APMC Wholesale Yard, Vashi"
                className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
              />
            </div>
          </div>

          {/* Cargo Specs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold mb-1 text-foreground">{t("delivery:cargo_desc", "Cargo Description")}</label>
              <input
                type="text"
                maxLength={255}
                value={cargoDescription}
                onChange={(e) => setCargoDescription(e.target.value)}
                placeholder="e.g. 300 Crates Alphonso Mangoes"
                className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
              />
            </div>

            <div>
              <label className="block font-semibold mb-1 text-foreground">{t("delivery:cargo_weight", "Total Weight (kg)")}</label>
              <input
                type="number"
                value={weightKg}
                onChange={(e) => setWeightKg(e.target.value ? Number(e.target.value) : "")}
                placeholder="e.g. 5000"
                className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold mb-1 text-foreground">{t("delivery:required_date", "Target Delivery Date")}</label>
            <input
              type="date"
              value={requiredDeliveryDate}
              onChange={(e) => setRequiredDeliveryDate(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold mb-1 text-foreground">{t("delivery:special_instructions", "Transit Notes & Instructions")}</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Keep temperature between 4°C - 8°C. Arrive before 7 AM."
              className="w-full px-3 py-2 rounded-lg border border-input bg-background focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div className="p-3 border-t border-border flex items-center justify-between gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg border border-border text-foreground hover:bg-secondary font-semibold transition-colors"
            >
              {t("common:actions.cancel", "Cancel")}
            </button>

            <button
              type="submit"
              disabled={isSubmitting || !isVerified}
              className="px-5 py-2 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary-700 transition-colors flex items-center gap-1.5 shadow-xs disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>{t("delivery:submitting_request", "Sending Request...")}</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{t("delivery:send_transport_request", "Send Transport Request")}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
