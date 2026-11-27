import React, { useContext, useEffect, useRef, useState } from "react";
import {
  X,
  Loader2,
  AlertCircle,
  ShoppingCart,
  Image as ImageIcon,
  Trash2,
  Calendar,
  MapPin,
  CheckCircle2,
  ShieldCheck,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { ordersApi } from "../../api/orders";
import { useAuth } from "../../store/authStore";
import { ToastContext } from "../ui/toast/toastContextDef";
import { formatNumber } from "../../utils/formatters";
import type { ProduceListingDetail, ProduceListingPublicSummary } from "../../types/listings";
import type { OrderCreatePayload, OrderDetail } from "../../types/orders";

interface OrderCreateModalProps {
  isOpen: boolean;
  listing: ProduceListingDetail | ProduceListingPublicSummary;
  onClose: () => void;
  onSuccess: (order: OrderDetail) => void;
}

export const OrderCreateModal: React.FC<OrderCreateModalProps> = ({
  isOpen,
  listing,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["orders", "marketplace", "validation", "common", "errors"]);
  const { user } = useAuth();
  const toast = useContext(ToastContext);

  const [quantity, setQuantity] = useState<number | "">(1);
  const [deliveryAddress, setDeliveryAddress] = useState<string>("");
  const [deliveryDate, setDeliveryDate] = useState<string>("");
  const [deliveryNotes, setDeliveryNotes] = useState<string>("");
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const isSubmittingRef = useRef(false);
  const idempotencyKeyRef = useRef<string>("");
  const [error, setError] = useState<string | null>(null);

  const maxAvailable = Number(listing.available_quantity) || 0;
  const unitPrice = Number(listing.price_per_unit) || 0;
  const todayStr = new Date().toISOString().split("T")[0];

  useEffect(() => {
    if (isOpen) {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
      setError(null);
      // Generate a fresh idempotency key every time the modal opens
      idempotencyKeyRef.current = crypto.randomUUID();

      setQuantity(Math.min(100, Math.max(1, maxAvailable)));
      setDeliveryDate(listing.available_from || todayStr);
      setDeliveryAddress(user?.buyer_profile?.delivery_receiving_address || "");
      setDeliveryNotes("");
      setSelectedImages([]);
      setImagePreviews([]);
    }
  }, [isOpen, listing, user, maxAvailable, todayStr]);

  // Clean up object URLs on unmount or change
  useEffect(() => {
    return () => {
      imagePreviews.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [imagePreviews]);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    setError(null);

    if (selectedImages.length + files.length > 5) {
      setError(t("orders:max_images_limit", "You can attach a maximum of 5 images per order."));
      return;
    }

    const validFiles: File[] = [];
    const newPreviews: string[] = [];

    for (const f of files) {
      if (f.size > 5 * 1024 * 1024) {
        setError(t("orders:file_too_large", "Each image must not exceed 5 MB."));
        return;
      }
      const ext = f.name.toLowerCase();
      if (!ext.endsWith(".jpg") && !ext.endsWith(".jpeg") && !ext.endsWith(".png") && !ext.endsWith(".webp")) {
        setError(t("orders:unsupported_format", "Only JPEG, PNG, and WebP images are permitted."));
        return;
      }
      validFiles.push(f);
      newPreviews.push(URL.createObjectURL(f));
    }

    setSelectedImages((prev) => [...prev, ...validFiles]);
    setImagePreviews((prev) => [...prev, ...newPreviews]);
    e.target.value = "";
  };

  const removeImage = (index: number) => {
    URL.revokeObjectURL(imagePreviews[index]);
    setSelectedImages((prev) => prev.filter((_, i) => i !== index));
    setImagePreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const totalCost = typeof quantity === "number" && !isNaN(quantity) ? (quantity * unitPrice).toFixed(2) : "0.00";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmittingRef.current || isSubmitting) return;

    setError(null);
    const numQty = Number(quantity);

    if (isNaN(numQty) || numQty <= 0) {
      setError(t("validation:valid_quantity_gt_zero", "Please specify a valid quantity greater than 0."));
      return;
    }

    if (numQty > maxAvailable) {
      setError(
        t("validation:qty_exceeds_stock", `Order quantity exceeds available stock (${maxAvailable} ${listing.unit}).`, {
          stock: maxAvailable,
          unit: listing.unit,
        })
      );
      return;
    }

    // Synchronous UI lock
    isSubmittingRef.current = true;
    setIsSubmitting(true);

    try {
      const payload: OrderCreatePayload = {
        listing_id: listing.id,
        quantity: numQty,
        delivery_destination_address: deliveryAddress.trim() || undefined,
        delivery_arranged_date: deliveryDate || undefined,
        delivery_notes: deliveryNotes.trim() || undefined,
        idempotency_key: idempotencyKeyRef.current,
      };

      const createdOrder = await ordersApi.createOrder(payload, idempotencyKeyRef.current);

      // Attach photographic assets if any selected
      if (selectedImages.length > 0) {
        try {
          await ordersApi.uploadOrderImages(createdOrder.id, selectedImages);
        } catch {
          // Non-fatal if secondary image upload fails; order is created
        }
      }

      toast?.success(
        t("orders:order_placed_success", "Purchase order placed successfully!"),
        t("common:success", "Success")
      );

      onSuccess(createdOrder);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("orders:order_placement_failed", "Failed to place order.");
      setError(msg);
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-order-create-title"
    >
      <div className="bg-card w-full max-w-xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <ShoppingCart className="w-4 h-4" />
            </div>
            <div>
              <h2 id="modal-order-create-title" className="text-lg font-bold text-foreground">
                {t("orders:place_direct_order", "Place Purchase Order")}
              </h2>
              <p className="text-xs text-muted-foreground">
                {t("orders:direct_order_subtitle", "Direct purchase with instant inventory reservation")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            aria-label={t("common:actions.close", "Close dialog")}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div
              className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-start gap-2.5"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Product Summary Box */}
          <div className="p-3.5 rounded-xl border border-border bg-secondary/20 flex items-center justify-between gap-3 text-xs">
            <div>
              <span className="font-bold text-foreground block text-sm">{listing.product_name}</span>
              <span className="text-muted-foreground line-clamp-1">{listing.title}</span>
              {listing.quality_grade && (
                <span className="inline-flex items-center gap-1 mt-1 text-[11px] font-semibold text-primary">
                  <ShieldCheck className="w-3 h-3" />
                  {listing.quality_grade}
                </span>
              )}
            </div>
            <div className="text-end">
              <span className="text-muted-foreground block text-[11px]">{t("marketplace:rate", "Rate")}</span>
              <span className="text-base font-extrabold text-foreground">
                ₹{formatNumber(unitPrice)} <span className="text-xs font-normal text-muted-foreground">/ {listing.unit}</span>
              </span>
            </div>
          </div>

          {/* Quantity & Total Price */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="order-quantity" className="block text-xs font-semibold text-foreground mb-1">
                {t("orders:order_quantity", "Order Volume")} ({listing.unit}) *
              </label>
              <input
                id="order-quantity"
                type="number"
                min={1}
                max={maxAvailable}
                step="any"
                required
                value={quantity}
                onChange={(e) => setQuantity(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isSubmitting}
              />
              <span className="text-[11px] text-muted-foreground mt-0.5 block">
                {t("marketplace:available_stock", "Available:")} {formatNumber(maxAvailable)} {listing.unit}
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1">
                {t("orders:estimated_total", "Estimated Total Amount")}
              </label>
              <div className="px-3 py-2 rounded-lg border border-border bg-secondary/30 text-sm font-bold text-foreground flex items-center justify-between">
                <span>₹{formatNumber(Number(totalCost))}</span>
                <span className="text-[11px] font-normal text-muted-foreground">INR</span>
              </div>
            </div>
          </div>

          {/* Delivery Date & Destination Address */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="order-delivery-date" className="block text-xs font-semibold text-foreground mb-1 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
                <span>{t("orders:target_delivery_date", "Target Delivery Date")}</span>
              </label>
              <input
                id="order-delivery-date"
                type="date"
                min={todayStr}
                value={deliveryDate}
                onChange={(e) => setDeliveryDate(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label htmlFor="order-delivery-address" className="block text-xs font-semibold text-foreground mb-1 flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-muted-foreground" />
                <span>{t("orders:delivery_address", "Delivery Address")}</span>
              </label>
              <input
                id="order-delivery-address"
                type="text"
                placeholder={t("orders:enter_delivery_address", "Warehouse dock / Receiving point")}
                value={deliveryAddress}
                onChange={(e) => setDeliveryAddress(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isSubmitting}
              />
            </div>
          </div>

          {/* Special Notes */}
          <div>
            <label htmlFor="order-delivery-notes" className="block text-xs font-semibold text-foreground mb-1">
              {t("orders:handling_instructions", "Special Handling & Delivery Instructions")}
            </label>
            <textarea
              id="order-delivery-notes"
              rows={2}
              placeholder={t("orders:notes_placeholder", "e.g., Crate packaging, morning delivery slot, inspection contact person")}
              value={deliveryNotes}
              onChange={(e) => setDeliveryNotes(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isSubmitting}
            />
          </div>

          {/* Phase 2: Photographic Evidence & Reference Upload */}
          <div className="space-y-2 pt-2 border-t border-border">
            <label className="block text-xs font-semibold text-foreground flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <ImageIcon className="w-3.5 h-3.5 text-primary" />
                <span>{t("orders:attach_reference_photos", "Order Quality Evidence & Reference Photos")}</span>
              </span>
              <span className="text-[11px] font-normal text-muted-foreground">
                {selectedImages.length}/5 {t("orders:images_count", "photos")}
              </span>
            </label>

            <div className="flex flex-wrap gap-2.5 items-center">
              {imagePreviews.map((previewUrl, idx) => (
                <div key={idx} className="relative w-16 h-16 rounded-lg overflow-hidden border border-border group bg-secondary/40">
                  <img src={previewUrl} alt={`Upload preview ${idx + 1}`} className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => removeImage(idx)}
                    className="absolute top-1 end-1 p-0.5 rounded-full bg-black/70 text-white hover:bg-destructive opacity-80 group-hover:opacity-100 transition-opacity"
                    aria-label="Remove image"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))}

              {selectedImages.length < 5 && (
                <label className="w-16 h-16 rounded-lg border border-dashed border-border hover:border-primary flex flex-col items-center justify-center cursor-pointer transition-colors bg-secondary/15 hover:bg-secondary/30">
                  <ImageIcon className="w-5 h-5 text-muted-foreground" />
                  <span className="text-[9px] text-muted-foreground mt-0.5">{t("common:add", "Add")}</span>
                  <input
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    onChange={handleFileChange}
                    disabled={isSubmitting}
                  />
                </label>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground">
              {t("orders:supported_image_types", "Attach specifications, quality requirements, or purchase documents (JPEG, PNG, WebP ≤ 5 MB).")}
            </p>
          </div>

          {/* Modal Actions */}
          <div className="pt-4 border-t border-border flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
            >
              {t("common:cancel", "Cancel")}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || maxAvailable <= 0}
              className="px-5 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>{t("orders:placing_order", "Placing Order...")}</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{t("orders:confirm_and_place_order", "Confirm & Place Order")}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

