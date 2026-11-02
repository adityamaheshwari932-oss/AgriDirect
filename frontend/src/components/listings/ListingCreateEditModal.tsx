import React, { useEffect, useState } from "react";
import { X, Save, AlertCircle, Loader2 } from "lucide-react";
import { listingsApi } from "../../api/listings";
import { ApiError } from "../../api/errors";
import type {
  ListingCreatePayload,
  ListingUpdatePayload,
  ProduceCategory,
  ProduceListingDetail,
} from "../../types/listings";

interface ListingCreateEditModalProps {
  isOpen: boolean;
  listingToEdit?: ProduceListingDetail | null;
  categories: ProduceCategory[];
  defaultState?: string;
  defaultCity?: string;
  onClose: () => void;
  onSuccess: (listing: ProduceListingDetail, isEdit: boolean) => void;
}

const CANONICAL_UNITS = [
  { value: "kg", label: "Kilogram (kg)" },
  { value: "quintal", label: "Quintal (100 kg)" },
  { value: "metric_ton", label: "Metric Ton (1,000 kg)" },
  { value: "bag", label: "Bag (Standard Farm Sack)" },
  { value: "crate", label: "Crate (Produce Box)" },
  { value: "box", label: "Box / Carton" },
];

const QUALITY_GRADES = [
  { value: "", label: "Standard Commercial Grade (Unspecified)" },
  { value: "Grade A", label: "Grade A (Premium Selection)" },
  { value: "Grade B", label: "Grade B (Fair Commercial)" },
  { value: "Organic", label: "Certified Organic" },
  { value: "Natural / GAP", label: "Natural / Good Agricultural Practice (GAP)" },
  { value: "Export Quality", label: "Export Grade" },
];

export const ListingCreateEditModal: React.FC<ListingCreateEditModalProps> = ({
  isOpen,
  listingToEdit,
  categories,
  defaultState = "",
  defaultCity = "",
  onClose,
  onSuccess,
}) => {
  const isEdit = Boolean(listingToEdit);

  const [productName, setProductName] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [initialQuantity, setInitialQuantity] = useState("");
  const [unit, setUnit] = useState("kg");
  const [pricePerUnit, setPricePerUnit] = useState("");
  const [qualityGrade, setQualityGrade] = useState("");
  const [locationState, setLocationState] = useState("");
  const [locationCity, setLocationCity] = useState("");
  const [harvestDate, setHarvestDate] = useState("");
  const [availableFrom, setAvailableFrom] = useState("");
  const [status, setStatus] = useState<"active" | "draft">("active");

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (listingToEdit) {
      setProductName(listingToEdit.product_name);
      setTitle(listingToEdit.title);
      setDescription(listingToEdit.description || "");
      setCategoryId(listingToEdit.category_id || "");
      setInitialQuantity(String(listingToEdit.initial_quantity));
      setUnit(listingToEdit.unit);
      setPricePerUnit(String(listingToEdit.price_per_unit));
      setQualityGrade(listingToEdit.quality_grade || "");
      setLocationState(listingToEdit.location_state || defaultState);
      setLocationCity(listingToEdit.location_city || defaultCity);
      setHarvestDate(listingToEdit.harvest_date || "");
      setAvailableFrom(listingToEdit.available_from ? listingToEdit.available_from.slice(0, 10) : "");
      setStatus(listingToEdit.status === "draft" ? "draft" : "active");
    } else {
      setProductName("");
      setTitle("");
      setDescription("");
      setCategoryId(categories.length > 0 ? categories[0].id : "");
      setInitialQuantity("");
      setUnit("kg");
      setPricePerUnit("");
      setQualityGrade("");
      setLocationState(defaultState);
      setLocationCity(defaultCity);
      setHarvestDate("");
      setAvailableFrom(new Date().toISOString().slice(0, 10));
      setStatus("active");
    }
    setFieldErrors({});
    setGeneralError(null);
  }, [listingToEdit, defaultState, defaultCity, categories, isOpen]);

  if (!isOpen) return null;

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!productName.trim()) {
      errors.product_name = "Produce name is required (e.g. Sharbati Wheat, Alphonso Mango).";
    }
    if (!title.trim()) {
      errors.title = "Listing title is required.";
    }
    const qty = Number(initialQuantity);
    if (!initialQuantity || isNaN(qty) || qty <= 0) {
      errors.initial_quantity = "Initial supply quantity must be greater than zero.";
    }
    const price = Number(pricePerUnit);
    if (!pricePerUnit || isNaN(price) || price <= 0) {
      errors.price_per_unit = "Price per unit must be greater than zero.";
    }
    if (!unit.trim()) {
      errors.unit = "Measurement unit is required.";
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
      if (isEdit && listingToEdit) {
        // Update payload - CRITICAL: never send available_quantity
        const payload: ListingUpdatePayload = {
          product_name: productName.trim(),
          title: title.trim(),
          description: description.trim() || null,
          category_id: categoryId || null,
          initial_quantity: Number(initialQuantity),
          unit: unit.trim(),
          price_per_unit: Number(pricePerUnit),
          quality_grade: qualityGrade.trim() || null,
          location_state: locationState.trim() || null,
          location_city: locationCity.trim() || null,
          harvest_date: harvestDate || null,
          available_from: availableFrom || null,
        };

        const updated = await listingsApi.updateListing(listingToEdit.id, payload);
        onSuccess(updated, true);
      } else {
        const payload: ListingCreatePayload = {
          product_name: productName.trim(),
          title: title.trim(),
          description: description.trim() || null,
          category_id: categoryId || null,
          initial_quantity: Number(initialQuantity),
          unit: unit.trim(),
          price_per_unit: Number(pricePerUnit),
          quality_grade: qualityGrade.trim() || null,
          location_state: locationState.trim() || null,
          location_city: locationCity.trim() || null,
          harvest_date: harvestDate || null,
          available_from: availableFrom || null,
          status,
        };

        const created = await listingsApi.createListing(payload);
        onSuccess(created, false);
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.isValidationError) {
          setGeneralError("Validation error: please check highlighted fields.");
          const backendErrors: Record<string, string> = {};
          for (const [key, msgs] of Object.entries(err.fieldErrors)) {
            backendErrors[key] = msgs[0];
          }
          setFieldErrors(backendErrors);
        } else {
          setGeneralError(err.message || "Failed to save listing. Please try again.");
        }
      } else {
        setGeneralError("An unexpected network error occurred while saving the listing.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-listing-title"
    >
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div>
            <h2 id="modal-listing-title" className="text-lg font-bold text-foreground">
              {isEdit ? "Edit Produce Listing" : "Create New Produce Listing"}
            </h2>
            <p className="text-xs text-muted-foreground">
              {isEdit
                ? "Update pricing, specifications, or harvest details for this produce lot"
                : "Publish an agricultural produce lot to the direct B2B wholesale marketplace"}
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
        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {generalError && (
            <div
              className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-2.5"
              role="alert"
            >
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div className="text-xs">{generalError}</div>
            </div>
          )}

          {/* Core Info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="listing-product-name" className="block text-xs font-semibold text-foreground mb-1">
                Produce Name <span className="text-destructive">*</span>
              </label>
              <input
                id="listing-product-name"
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="e.g. Sharbati Wheat, Alphonso Mango"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {fieldErrors.product_name && (
                <p className="text-xs text-destructive mt-1">{fieldErrors.product_name}</p>
              )}
            </div>

            <div>
              <label htmlFor="listing-category" className="block text-xs font-semibold text-foreground mb-1">
                Produce Category
              </label>
              <select
                id="listing-category"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select Category (Optional)</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="listing-title" className="block text-xs font-semibold text-foreground mb-1">
              Headline Title <span className="text-destructive">*</span>
            </label>
            <input
              id="listing-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Farm Fresh Certified Sharbati Wheat — 2026 Harvest"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
            {fieldErrors.title && (
              <p className="text-xs text-destructive mt-1">{fieldErrors.title}</p>
            )}
          </div>

          <div>
            <label htmlFor="listing-description" className="block text-xs font-semibold text-foreground mb-1">
              Produce Description & Storage Notes
            </label>
            <textarea
              id="listing-description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe moisture content, packaging, storage conditions, or sorting specifications..."
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-y"
            />
          </div>

          {/* Pricing & Quantity */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-secondary/30 border border-border">
            <div>
              <label htmlFor="listing-initial-quantity" className="block text-xs font-semibold text-foreground mb-1">
                Total Supply Quantity <span className="text-destructive">*</span>
              </label>
              <input
                id="listing-initial-quantity"
                type="number"
                step="any"
                min="0.001"
                value={initialQuantity}
                onChange={(e) => setInitialQuantity(e.target.value)}
                placeholder="e.g. 500"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {fieldErrors.initial_quantity && (
                <p className="text-xs text-destructive mt-1">{fieldErrors.initial_quantity}</p>
              )}
            </div>

            <div>
              <label htmlFor="listing-unit" className="block text-xs font-semibold text-foreground mb-1">
                Measurement Unit <span className="text-destructive">*</span>
              </label>
              <select
                id="listing-unit"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {CANONICAL_UNITS.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="listing-price-per-unit" className="block text-xs font-semibold text-foreground mb-1">
                Price per Unit (₹) <span className="text-destructive">*</span>
              </label>
              <input
                id="listing-price-per-unit"
                type="number"
                step="0.01"
                min="0.01"
                value={pricePerUnit}
                onChange={(e) => setPricePerUnit(e.target.value)}
                placeholder="e.g. 2400.00"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {fieldErrors.price_per_unit && (
                <p className="text-xs text-destructive mt-1">{fieldErrors.price_per_unit}</p>
              )}
            </div>
          </div>

          {/* Quality & Dates */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="listing-quality-grade" className="block text-xs font-semibold text-foreground mb-1">
                Quality Grade
              </label>
              <select
                id="listing-quality-grade"
                value={qualityGrade}
                onChange={(e) => setQualityGrade(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {QUALITY_GRADES.map((g) => (
                  <option key={g.value} value={g.value}>
                    {g.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="listing-harvest-date" className="block text-xs font-semibold text-foreground mb-1">
                Harvest Date
              </label>
              <input
                id="listing-harvest-date"
                type="date"
                value={harvestDate}
                onChange={(e) => setHarvestDate(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label htmlFor="listing-available-from" className="block text-xs font-semibold text-foreground mb-1">
                Ready for Dispatch From
              </label>
              <input
                id="listing-available-from"
                type="date"
                value={availableFrom}
                onChange={(e) => setAvailableFrom(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          {/* Sourcing Location */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="listing-location-state" className="block text-xs font-semibold text-foreground mb-1">
                Sourcing State
              </label>
              <input
                id="listing-location-state"
                type="text"
                value={locationState}
                onChange={(e) => setLocationState(e.target.value)}
                placeholder="e.g. Madhya Pradesh"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label htmlFor="listing-location-city" className="block text-xs font-semibold text-foreground mb-1">
                Sourcing City / District
              </label>
              <input
                id="listing-location-city"
                type="text"
                value={locationCity}
                onChange={(e) => setLocationCity(e.target.value)}
                placeholder="e.g. Sehore"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          {/* Initial Status (Create Mode only) */}
          {!isEdit && (
            <div className="p-3 rounded-lg bg-secondary/50 border border-border flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-foreground block">Listing Publication Status</span>
                <span className="text-xs text-muted-foreground block">
                  Choose whether this lot becomes immediately visible on the public marketplace.
                </span>
              </div>
              <div className="flex items-center gap-3">
                <label className="inline-flex items-center gap-1.5 text-xs text-foreground font-medium cursor-pointer">
                  <input
                    type="radio"
                    name="status"
                    value="active"
                    checked={status === "active"}
                    onChange={() => setStatus("active")}
                    className="text-primary focus:ring-primary"
                  />
                  <span>Active (Live)</span>
                </label>
                <label className="inline-flex items-center gap-1.5 text-xs text-foreground font-medium cursor-pointer">
                  <input
                    type="radio"
                    name="status"
                    value="draft"
                    checked={status === "draft"}
                    onChange={() => setStatus("draft")}
                    className="text-primary focus:ring-primary"
                  />
                  <span>Save as Draft</span>
                </label>
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className="pt-4 border-t border-border flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-sm font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary-700 text-sm font-semibold transition-colors shadow-sm disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" aria-hidden="true" />
                  <span>{isEdit ? "Update Listing" : "Publish Listing"}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

