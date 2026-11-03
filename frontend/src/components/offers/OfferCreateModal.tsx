import React, { useEffect, useState } from "react";
import {
  X,
  Loader2,
  AlertCircle,
  Calendar,
  Truck,
  CheckCircle2,
  DollarSign,
  Package,
} from "lucide-react";
import { offersApi } from "../../api/offers";
import { listingsApi } from "../../api/listings";
import { requirementsApi } from "../../api/requirements";
import type { ProduceListingDetail } from "../../types/listings";
import type { BuyerRequirementDetail } from "../../types/requirements";
import type { OfferCreatePayload, OfferDetail } from "../../types/offers";

interface OfferCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (offer: OfferDetail) => void;
  targetType: "listing" | "requirement";
  targetListing?: ProduceListingDetail | null;
  targetRequirement?: BuyerRequirementDetail | null;
}

export const OfferCreateModal: React.FC<OfferCreateModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  targetType,
  targetListing,
  targetRequirement,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [quantity, setQuantity] = useState<number | "">("");
  const [unitPrice, setUnitPrice] = useState<number | "">("");
  const [deliveryTerms, setDeliveryTerms] = useState<string>("");
  const [proposedDeliveryDate, setProposedDeliveryDate] = useState<string>("");
  const [qualityGrade, setQualityGrade] = useState<string>("");

  // Target-specific selections
  const [myListings, setMyListings] = useState<ProduceListingDetail[]>([]);
  const [selectedListingId, setSelectedListingId] = useState<string>("");
  const [myRequirements, setMyRequirements] = useState<BuyerRequirementDetail[]>([]);
  const [selectedRequirementId, setSelectedRequirementId] = useState<string>("");
  const [isLoadingRelated, setIsLoadingRelated] = useState(false);

  // Today's date string in YYYY-MM-DD format for min date
  const todayStr = new Date().toISOString().split("T")[0];

  useEffect(() => {
    if (!isOpen) {
      setError(null);
      setIsSubmitting(false);
      return;
    }

    if (targetType === "listing" && targetListing) {
      setQuantity(Number(targetListing.available_quantity) || 1);
      setUnitPrice(Number(targetListing.price_per_unit) || "");
      setQualityGrade(targetListing.quality_grade || "");
      setDeliveryTerms("Standard delivery / Farm pickup as per agreed terms");
      setProposedDeliveryDate(targetListing.available_from || todayStr);

      // Optionally fetch buyer's active requirements to link
      setIsLoadingRelated(true);
      requirementsApi
        .getMyRequirements({ status: "active", page_size: 50 })
        .then((res) => {
          setMyRequirements(res.items || []);
        })
        .catch(() => {
          // Non-critical if fails
        })
        .finally(() => {
          setIsLoadingRelated(false);
        });
    } else if (targetType === "requirement" && targetRequirement) {
      setQuantity(Number(targetRequirement.remaining_quantity) || 1);
      setUnitPrice(
        targetRequirement.target_price_per_unit
          ? Number(targetRequirement.target_price_per_unit)
          : ""
      );
      setQualityGrade(targetRequirement.quality_grade || "");
      setDeliveryTerms("Direct farm delivery to buyer receiving dock");
      setProposedDeliveryDate(targetRequirement.required_by_date || todayStr);

      // Farmer must select one of their own active produce listings to back the offer
      setIsLoadingRelated(true);
      listingsApi
        .getMyListings({ status: "active", page_size: 50 })
        .then((res) => {
          const items = res.items || [];
          setMyListings(items);
          if (items.length > 0) {
            setSelectedListingId(items[0].id);
            if (!unitPrice && items[0].price_per_unit) {
              setUnitPrice(Number(items[0].price_per_unit));
            }
          }
        })
        .catch(() => {
          // Non-critical
        })
        .finally(() => {
          setIsLoadingRelated(false);
        });
    }
  }, [isOpen, targetType, targetListing, targetRequirement, todayStr]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const numQty = Number(quantity);
    const numPrice = Number(unitPrice);

    if (isNaN(numQty) || numQty <= 0) {
      setError("Please specify a valid physical quantity greater than 0.");
      return;
    }

    if (isNaN(numPrice) || numPrice <= 0) {
      setError("Please specify a valid wholesale unit price greater than 0.");
      return;
    }

    let recipientId = "";
    let listingId = "";
    let requirementId: string | undefined = undefined;
    let unit = "";
    let productName = "";

    if (targetType === "listing") {
      if (!targetListing) {
        setError("Missing reference listing.");
        return;
      }
      recipientId = targetListing.farmer_id;
      listingId = targetListing.id;
      requirementId = selectedRequirementId || undefined;
      unit = targetListing.unit;
      productName = targetListing.product_name;

      if (numQty > Number(targetListing.available_quantity)) {
        setError(`Offered quantity exceeds available stock (${targetListing.available_quantity} ${unit}).`);
        return;
      }
    } else {
      if (!targetRequirement) {
        setError("Missing reference requirement.");
        return;
      }
      if (!selectedListingId) {
        setError("Please select one of your active produce listings to back this offer.");
        return;
      }
      recipientId = targetRequirement.buyer_id;
      listingId = selectedListingId;
      requirementId = targetRequirement.id;
      unit = targetRequirement.unit;
      productName = targetRequirement.product_name;

      if (numQty > Number(targetRequirement.remaining_quantity)) {
        setError(`Offered quantity exceeds buyer remaining demand (${targetRequirement.remaining_quantity} ${unit}).`);
        return;
      }
    }

    const payload: OfferCreatePayload = {
      recipient_id: recipientId,
      delivery_terms: deliveryTerms.trim() || undefined,
      proposed_delivery_date: proposedDeliveryDate || undefined,
      items: [
        {
          listing_id: listingId,
          buyer_requirement_id: requirementId,
          product_name: productName,
          quantity: numQty,
          unit: unit.toLowerCase(),
          unit_price: numPrice,
          quality_grade: qualityGrade.trim() || undefined,
        },
      ],
    };

    setIsSubmitting(true);
    try {
      const createdOffer = await offersApi.createOffer(payload);
      if (onSuccess) {
        onSuccess(createdOffer);
      }
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit offer proposal.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const estimatedTotal =
    typeof quantity === "number" && typeof unitPrice === "number"
      ? (quantity * unitPrice).toFixed(2)
      : "0.00";

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-offer-create-title"
    >
      <div className="bg-card w-full max-w-xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div>
            <h2 id="modal-offer-create-title" className="text-lg font-bold text-foreground">
              {targetType === "listing" ? "Submit Commercial Purchase Offer" : "Submit Produce Supply Offer"}
            </h2>
            <p className="text-xs text-muted-foreground">
              Direct B2B negotiation without intermediaries — terms legally binding upon counterparty acceptance
            </p>
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

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-semibold">Offer Submission Error</p>
                <p className="text-xs">{error}</p>
              </div>
            </div>
          )}

          {/* Reference Target Info */}
          <div className="p-4 rounded-xl bg-secondary/30 border border-border text-xs space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block">
              Reference Market Context
            </span>
            {targetType === "listing" && targetListing && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-muted-foreground">Produce Catalog Item:</span>{" "}
                  <span className="font-semibold text-foreground">{targetListing.product_name}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Available Stock:</span>{" "}
                  <span className="font-semibold text-foreground">
                    {targetListing.available_quantity} {targetListing.unit}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Listed Unit Price:</span>{" "}
                  <span className="font-semibold text-foreground">
                    ₹{Number(targetListing.price_per_unit).toLocaleString()} / {targetListing.unit}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Producer:</span>{" "}
                  <span className="font-semibold text-foreground">
                    {targetListing.farmer?.farm_name || targetListing.farmer?.full_name || "Verified Producer"}
                  </span>
                </div>
              </div>
            )}

            {targetType === "requirement" && targetRequirement && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-muted-foreground">Procurement Item:</span>{" "}
                  <span className="font-semibold text-foreground">{targetRequirement.product_name}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Remaining Demand:</span>{" "}
                  <span className="font-semibold text-foreground">
                    {targetRequirement.remaining_quantity} {targetRequirement.unit}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Buyer Target Price:</span>{" "}
                  <span className="font-semibold text-foreground">
                    {targetRequirement.target_price_per_unit
                      ? `₹${Number(targetRequirement.target_price_per_unit).toLocaleString()} / ${targetRequirement.unit}`
                      : "Negotiable"}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Buyer Enterprise:</span>{" "}
                  <span className="font-semibold text-foreground">
                    {targetRequirement.buyer?.business_name || "Commercial Buyer"}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Mode-Specific Selectors */}
          {targetType === "requirement" && (
            <div className="space-y-1.5">
              <label
                htmlFor="farmer-backing-listing-select"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                Select Backing Produce Lot <span className="text-destructive">*</span>
              </label>
              {isLoadingRelated ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" aria-hidden="true" />
                  <span>Loading your available produce lots...</span>
                </div>
              ) : myListings.length === 0 ? (
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-700 text-xs">
                  You do not have any active produce listings. You must publish an active listing
                  to back physical goods delivery before submitting an offer.
                </div>
              ) : (
                <select
                  id="farmer-backing-listing-select"
                  value={selectedListingId}
                  onChange={(e) => setSelectedListingId(e.target.value)}
                  className="w-full rounded-xl border border-border bg-card px-3.5 py-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
                  required
                >
                  <option value="" disabled>Choose one of your active listings...</option>
                  {myListings.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.product_name} — {l.available_quantity} {l.unit} available (₹{Number(l.price_per_unit).toLocaleString()}/{l.unit})
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}

          {targetType === "listing" && myRequirements.length > 0 && (
            <div className="space-y-1.5">
              <label
                htmlFor="buyer-linked-req-select"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                Link to Buyer Requirement (Optional)
              </label>
              <select
                id="buyer-linked-req-select"
                value={selectedRequirementId}
                onChange={(e) => setSelectedRequirementId(e.target.value)}
                className="w-full rounded-xl border border-border bg-card px-3.5 py-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
              >
                <option value="">None (Independent Spot Purchase)</option>
                {myRequirements.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title} — {r.remaining_quantity} {r.unit} remaining
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Quantity & Unit Price */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label
                htmlFor="offer-quantity-input"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                Physical Quantity ({targetType === "listing" ? targetListing?.unit : targetRequirement?.unit}) <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <input
                  id="offer-quantity-input"
                  type="number"
                  step="0.001"
                  min="0.001"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value === "" ? "" : parseFloat(e.target.value))}
                  placeholder="e.g. 50"
                  className="w-full rounded-xl border border-border bg-card pl-9 pr-4 py-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
                <Package className="w-4 h-4 text-muted-foreground absolute left-3 top-3" aria-hidden="true" />
              </div>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="offer-unitprice-input"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                Offered Unit Price (₹ / {targetType === "listing" ? targetListing?.unit : targetRequirement?.unit}) <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <input
                  id="offer-unitprice-input"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={unitPrice}
                  onChange={(e) => setUnitPrice(e.target.value === "" ? "" : parseFloat(e.target.value))}
                  placeholder="e.g. 24.50"
                  className="w-full rounded-xl border border-border bg-card pl-9 pr-4 py-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
                <DollarSign className="w-4 h-4 text-muted-foreground absolute left-3 top-3" aria-hidden="true" />
              </div>
            </div>
          </div>

          {/* Quality Grade & Delivery Date */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label
                htmlFor="offer-qualitygrade-input"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                Quality Grade
              </label>
              <input
                id="offer-qualitygrade-input"
                type="text"
                value={qualityGrade}
                onChange={(e) => setQualityGrade(e.target.value)}
                placeholder="e.g. Grade A, FAQ Grade"
                maxLength={32}
                className="w-full rounded-xl border border-border bg-card px-3.5 py-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="offer-deliverydate-input"
                className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
              >
                Proposed Delivery Date
              </label>
              <div className="relative">
                <input
                  id="offer-deliverydate-input"
                  type="date"
                  min={todayStr}
                  value={proposedDeliveryDate}
                  onChange={(e) => setProposedDeliveryDate(e.target.value)}
                  className="w-full rounded-xl border border-border bg-card pl-9 pr-4 py-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <Calendar className="w-4 h-4 text-muted-foreground absolute left-3 top-3" aria-hidden="true" />
              </div>
            </div>
          </div>

          {/* Delivery Terms */}
          <div className="space-y-1.5">
            <label
              htmlFor="offer-deliveryterms-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
            >
              Logistics & Delivery Terms
            </label>
            <div className="relative">
              <input
                id="offer-deliveryterms-input"
                type="text"
                value={deliveryTerms}
                onChange={(e) => setDeliveryTerms(e.target.value)}
                placeholder="e.g. Farm gate pickup by buyer truck, payment upon delivery dock inspection"
                maxLength={2000}
                className="w-full rounded-xl border border-border bg-card pl-9 pr-4 py-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <Truck className="w-4 h-4 text-muted-foreground absolute left-3 top-3" aria-hidden="true" />
            </div>
          </div>

          {/* Financial Calculation Disclaimer Banner */}
          <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 flex items-center justify-between">
            <div>
              <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block">
                Estimated Commercial Total
              </span>
              <p className="text-[11px] text-muted-foreground">
                Authoritative gross total is computed server-side upon submission
              </p>
            </div>
            <div className="text-right">
              <span className="text-xl font-black text-primary">₹{Number(estimatedTotal).toLocaleString()}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="pt-2 flex items-center justify-end gap-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || (targetType === "requirement" && myListings.length === 0)}
              className="px-5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>Submitting Offer...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                  <span>Submit Formal Proposal</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
