import React, { useEffect, useState } from "react";
import { X, Save, AlertCircle, Loader2 } from "lucide-react";
import { requirementsApi } from "../../api/requirements";
import { ApiError } from "../../api/errors";
import type {
  BuyerRequirementDetail,
  PriceCondition,
  ProduceCategory,
  RequirementCreatePayload,
  RequirementUpdatePayload,
} from "../../types";

interface RequirementCreateEditModalProps {
  isOpen: boolean;
  requirementToEdit?: BuyerRequirementDetail | null;
  categories: ProduceCategory[];
  defaultState?: string;
  defaultCity?: string;
  onClose: () => void;
  onSuccess: (requirement: BuyerRequirementDetail, isEdit: boolean) => void;
}

const CANONICAL_UNITS = [
  { value: "kg", label: "Kilogram (kg)" },
  { value: "quintal", label: "Quintal (100 kg)" },
  { value: "metric_ton", label: "Metric Ton (1,000 kg)" },
  { value: "bag", label: "Bag (Standard Farm Sack)" },
  { value: "crate", label: "Crate (Produce Box)" },
  { value: "box", label: "Box / Carton" },
];

const PRICE_CONDITIONS: { value: PriceCondition; label: string; desc: string }[] = [
  {
    value: "negotiable",
    label: "Negotiable",
    desc: "Open to counter-offers from verified producers",
  },
  {
    value: "exact",
    label: "Fixed Target Price",
    desc: "Procuring strictly at stated unit benchmark price",
  },
  {
    value: "range",
    label: "Price Range",
    desc: "Flexible ceiling subject to produce quality grading",
  },
];

const QUALITY_GRADES = [
  { value: "", label: "Standard Commercial (Any Grade)" },
  { value: "Grade A", label: "Grade A (Premium Selection)" },
  { value: "Grade B", label: "Grade B (Fair Commercial)" },
  { value: "Organic", label: "Certified Organic" },
  { value: "Natural / GAP", label: "Natural / Good Agricultural Practice (GAP)" },
  { value: "Export Quality", label: "Export Grade" },
];

export const RequirementCreateEditModal: React.FC<RequirementCreateEditModalProps> = ({
  isOpen,
  requirementToEdit,
  categories,
  defaultState = "",
  defaultCity = "",
  onClose,
  onSuccess,
}) => {
  const isEdit = Boolean(requirementToEdit);

  const [productName, setProductName] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [requiredQuantity, setRequiredQuantity] = useState("");
  const [unit, setUnit] = useState("kg");
  const [priceCondition, setPriceCondition] = useState<PriceCondition>("negotiable");
  const [targetPricePerUnit, setTargetPricePerUnit] = useState("");
  const [qualityGrade, setQualityGrade] = useState("");
  const [destinationState, setDestinationState] = useState("");
  const [destinationCity, setDestinationCity] = useState("");
  const [requiredByDate, setRequiredByDate] = useState("");
  const [status, setStatus] = useState<"active" | "draft">("active");

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Minimum date is today (YYYY-MM-DD)
  const todayStr = new Date().toISOString().slice(0, 10);

  useEffect(() => {
    if (requirementToEdit) {
      setProductName(requirementToEdit.product_name);
      setTitle(requirementToEdit.title);
      setDescription(requirementToEdit.description || "");
      setCategoryId(requirementToEdit.category_id || "");
      setRequiredQuantity(String(requirementToEdit.required_quantity));
      setUnit(requirementToEdit.unit);
      setPriceCondition((requirementToEdit.price_condition as PriceCondition) || "negotiable");
      setTargetPricePerUnit(
        requirementToEdit.target_price_per_unit !== null &&
          requirementToEdit.target_price_per_unit !== undefined
          ? String(requirementToEdit.target_price_per_unit)
          : ""
      );
      setQualityGrade(requirementToEdit.quality_grade || "");
      setDestinationState(requirementToEdit.destination_state || defaultState);
      setDestinationCity(requirementToEdit.destination_city || defaultCity);
      setRequiredByDate(requirementToEdit.required_by_date || "");
      setStatus(requirementToEdit.status === "draft" ? "draft" : "active");
    } else {
      setProductName("");
      setTitle("");
      setDescription("");
      setCategoryId(categories.length > 0 ? categories[0].id : "");
      setRequiredQuantity("");
      setUnit("kg");
      setPriceCondition("negotiable");
      setTargetPricePerUnit("");
      setQualityGrade("");
      setDestinationState(defaultState);
      setDestinationCity(defaultCity);
      // Default to 14 days from today
      const defaultDeadline = new Date();
      defaultDeadline.setDate(defaultDeadline.getDate() + 14);
      setRequiredByDate(defaultDeadline.toISOString().slice(0, 10));
      setStatus("active");
    }
    setFieldErrors({});
    setGeneralError(null);
  }, [requirementToEdit, defaultState, defaultCity, categories, isOpen]);

  if (!isOpen) return null;

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!productName.trim()) {
      errors.product_name = "Produce demand name is required (e.g. Processing Potatoes, Basmati Rice).";
    }
    if (!title.trim()) {
      errors.title = "Procurement requirement title is required.";
    }
    const qty = Number(requiredQuantity);
    if (!requiredQuantity || isNaN(qty) || qty <= 0) {
      errors.required_quantity = "Required quantity must be greater than zero.";
    }
    if (!unit.trim()) {
      errors.unit = "Measurement unit is required.";
    }
    if (targetPricePerUnit) {
      const price = Number(targetPricePerUnit);
      if (isNaN(price) || price <= 0) {
        errors.target_price_per_unit = "Target price must be a positive number if provided.";
      }
    }
    if (!requiredByDate) {
      errors.required_by_date = "Procurement deadline date is required.";
    } else if (requiredByDate < todayStr) {
      errors.required_by_date = "Procurement deadline cannot be in the past.";
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
      if (isEdit && requirementToEdit) {
        // CRITICAL: never send remaining_quantity or buyer_id
        const payload: RequirementUpdatePayload = {
          product_name: productName.trim(),
          title: title.trim(),
          description: description.trim() || null,
          category_id: categoryId || null,
          required_quantity: Number(requiredQuantity),
          unit: unit.trim(),
          target_price_per_unit: targetPricePerUnit ? Number(targetPricePerUnit) : null,
          price_condition: priceCondition,
          quality_grade: qualityGrade.trim() || null,
          destination_state: destinationState.trim() || null,
          destination_city: destinationCity.trim() || null,
          required_by_date: requiredByDate,
        };

        const updated = await requirementsApi.updateRequirement(requirementToEdit.id, payload);
        onSuccess(updated, true);
      } else {
        const payload: RequirementCreatePayload = {
          product_name: productName.trim(),
          title: title.trim(),
          description: description.trim() || null,
          category_id: categoryId || null,
          required_quantity: Number(requiredQuantity),
          unit: unit.trim(),
          target_price_per_unit: targetPricePerUnit ? Number(targetPricePerUnit) : null,
          price_condition: priceCondition,
          quality_grade: qualityGrade.trim() || null,
          destination_state: destinationState.trim() || null,
          destination_city: destinationCity.trim() || null,
          required_by_date: requiredByDate,
          status,
        };

        const created = await requirementsApi.createRequirement(payload);
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
          setGeneralError(err.message || "Failed to save requirement. Please try again.");
        }
      } else {
        setGeneralError("An unexpected network error occurred while saving the requirement.");
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
      aria-labelledby="modal-req-title"
    >
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div>
            <h2 id="modal-req-title" className="text-lg font-bold text-foreground">
              {isEdit ? "Edit Procurement Requirement" : "Post Procurement Demand"}
            </h2>
            <p className="text-xs text-muted-foreground">
              {isEdit
                ? "Update procurement specifications or delivery deadlines"
                : "Post commercial produce requirements to source directly from verified farmers"}
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
              <label htmlFor="req-product-name" className="block text-xs font-semibold text-foreground mb-1">
                Produce Demand Name <span className="text-destructive">*</span>
              </label>
              <input
                id="req-product-name"
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="e.g. Processing Potatoes, Basmati Rice"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {fieldErrors.product_name && (
                <p className="text-xs text-destructive mt-1">{fieldErrors.product_name}</p>
              )}
            </div>

            <div>
              <label htmlFor="req-category" className="block text-xs font-semibold text-foreground mb-1">
                Produce Category
              </label>
              <select
                id="req-category"
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
            <label htmlFor="req-title" className="block text-xs font-semibold text-foreground mb-1">
              Headline Title <span className="text-destructive">*</span>
            </label>
            <input
              id="req-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Bulk Weekly Grade-A Processing Potatoes for Industrial Kitchen"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
            {fieldErrors.title && (
              <p className="text-xs text-destructive mt-1">{fieldErrors.title}</p>
            )}
          </div>

          <div>
            <label htmlFor="req-description" className="block text-xs font-semibold text-foreground mb-1">
              Procurement Specifications & Receiving Instructions
            </label>
            <textarea
              id="req-description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detail required packaging, sorting tolerances, receiving dock timing, or quality checks..."
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-y"
            />
          </div>

          {/* Quantity & Unit */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-secondary/30 border border-border">
            <div>
              <label htmlFor="req-quantity" className="block text-xs font-semibold text-foreground mb-1">
                Required Procurement Volume <span className="text-destructive">*</span>
              </label>
              <input
                id="req-quantity"
                type="number"
                step="any"
                min="0.001"
                value={requiredQuantity}
                onChange={(e) => setRequiredQuantity(e.target.value)}
                placeholder="e.g. 100"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {fieldErrors.required_quantity && (
                <p className="text-xs text-destructive mt-1">{fieldErrors.required_quantity}</p>
              )}
            </div>

            <div>
              <label htmlFor="req-unit" className="block text-xs font-semibold text-foreground mb-1">
                Measurement Unit <span className="text-destructive">*</span>
              </label>
              <select
                id="req-unit"
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
          </div>

          {/* Pricing Condition & Target Price */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="req-price-condition" className="block text-xs font-semibold text-foreground mb-1">
                Pricing Term <span className="text-destructive">*</span>
              </label>
              <select
                id="req-price-condition"
                value={priceCondition}
                onChange={(e) => setPriceCondition(e.target.value as PriceCondition)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {PRICE_CONDITIONS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label} ({c.desc})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="req-target-price" className="block text-xs font-semibold text-foreground mb-1">
                Target Unit Price (₹) <span className="text-muted-foreground font-normal">(Optional)</span>
              </label>
              <input
                id="req-target-price"
                type="number"
                step="0.01"
                min="0.01"
                value={targetPricePerUnit}
                onChange={(e) => setTargetPricePerUnit(e.target.value)}
                placeholder="e.g. 1850.00"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {fieldErrors.target_price_per_unit && (
                <p className="text-xs text-destructive mt-1">{fieldErrors.target_price_per_unit}</p>
              )}
            </div>
          </div>

          {/* Quality Grade & Deadline */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="req-quality-grade" className="block text-xs font-semibold text-foreground mb-1">
                Desired Quality Grade
              </label>
              <select
                id="req-quality-grade"
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
              <label htmlFor="req-deadline" className="block text-xs font-semibold text-foreground mb-1">
                Procurement Deadline Date <span className="text-destructive">*</span>
              </label>
              <input
                id="req-deadline"
                type="date"
                min={todayStr}
                value={requiredByDate}
                onChange={(e) => setRequiredByDate(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {fieldErrors.required_by_date && (
                <p className="text-xs text-destructive mt-1">{fieldErrors.required_by_date}</p>
              )}
            </div>
          </div>

          {/* Destination Delivery Dock */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="req-dest-state" className="block text-xs font-semibold text-foreground mb-1">
                Delivery Destination State
              </label>
              <input
                id="req-dest-state"
                type="text"
                value={destinationState}
                onChange={(e) => setDestinationState(e.target.value)}
                placeholder="e.g. Maharashtra"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label htmlFor="req-dest-city" className="block text-xs font-semibold text-foreground mb-1">
                Delivery Destination City / Dock
              </label>
              <input
                id="req-dest-city"
                type="text"
                value={destinationCity}
                onChange={(e) => setDestinationCity(e.target.value)}
                placeholder="e.g. Mumbai"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          {/* Initial Status (Create Mode only) */}
          {!isEdit && (
            <div className="p-3 rounded-lg bg-secondary/50 border border-border flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-foreground block">Requirement Visibility</span>
                <span className="text-xs text-muted-foreground block">
                  Publish directly to the public demand board or save as an internal procurement draft.
                </span>
              </div>
              <div className="flex items-center gap-3">
                <label className="inline-flex items-center gap-1.5 text-xs text-foreground font-medium cursor-pointer">
                  <input
                    type="radio"
                    name="req-status"
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
                    name="req-status"
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
                  <span>{isEdit ? "Update Requirement" : "Publish Requirement"}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

