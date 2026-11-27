import React, { useEffect, useRef, useState } from "react";
import {
  X,
  Save,
  AlertCircle,
  Loader2,
  ImagePlus,
  Star,
  Trash2,
  ImageIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { listingsApi } from "../../api/listings";
import { ApiError } from "../../api/errors";
import type {
  ListingCreatePayload,
  ListingImage,
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

const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const MAX_IMAGES_LIMIT = 10;
const ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"];
const ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

export const ListingCreateEditModal: React.FC<ListingCreateEditModalProps> = ({
  isOpen,
  listingToEdit,
  categories,
  defaultState = "",
  defaultCity = "",
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["dashboard", "validation", "errors", "common"]);
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

  // Image Upload & Management State
  const [existingImages, setExistingImages] = useState<ListingImage[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [newPrimaryIndex, setNewPrimaryIndex] = useState(0);
  const [imageError, setImageError] = useState<string | null>(null);
  const [deletingImageId, setDeletingImageId] = useState<string | null>(null);
  const [settingPrimaryId, setSettingPrimaryId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isSubmittingRef = React.useRef(false);
  const createdListingRef = React.useRef<ProduceListingDetail | null>(null);
  const previewUrlsRef = useRef<string[]>([]);
  previewUrlsRef.current = previewUrls;

  // Revoke object URLs on cleanup
  useEffect(() => {
    return () => {
      previewUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [previewUrls]);

  useEffect(() => {
    // Revoke previous URLs
    previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    setSelectedFiles([]);
    setPreviewUrls([]);
    setNewPrimaryIndex(0);
    setImageError(null);

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
      setExistingImages(listingToEdit.images || []);
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
      setExistingImages([]);
      createdListingRef.current = null;
    }
    isSubmittingRef.current = false;
    setFieldErrors({});
    setGeneralError(null);
  }, [listingToEdit, defaultState, defaultCity, categories, isOpen]);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setImageError(null);
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const fileList = Array.from(files);
    const currentTotal = existingImages.length + selectedFiles.length;

    if (currentTotal + fileList.length > MAX_IMAGES_LIMIT) {
      setImageError(
        t(
          "errors:image_limit_reached",
          `Selecting ${fileList.length} photo(s) would exceed the maximum limit of ${MAX_IMAGES_LIMIT} photos. (Currently: ${currentTotal})`
        )
      );
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    const validNewFiles: File[] = [];
    const validNewUrls: string[] = [];

    for (const file of fileList) {
      if (file.size > MAX_IMAGE_SIZE_BYTES) {
        setImageError(
          t(
            "errors:image_size_exceeded",
            `"${file.name}" exceeds the 5 MB limit (${(file.size / (1024 * 1024)).toFixed(2)} MB).`
          )
        );
        if (fileInputRef.current) fileInputRef.current.value = "";
        return;
      }

      const lowerName = file.name.toLowerCase();
      const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
      const hasValidMime = ALLOWED_MIME_TYPES.includes(file.type);

      if (!hasValidExt || !hasValidMime) {
        setImageError(
          t(
            "errors:unsupported_image_format",
            `"${file.name}" has an unsupported format. Please select JPEG, PNG, or WebP photographs.`
          )
        );
        if (fileInputRef.current) fileInputRef.current.value = "";
        return;
      }

      validNewFiles.push(file);
      validNewUrls.push(URL.createObjectURL(file));
    }

    setSelectedFiles((prev) => [...prev, ...validNewFiles]);
    setPreviewUrls((prev) => [...prev, ...validNewUrls]);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleRemoveSelectedFile = (index: number) => {
    URL.revokeObjectURL(previewUrls[index]);
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviewUrls((prev) => prev.filter((_, i) => i !== index));
    if (newPrimaryIndex === index) {
      setNewPrimaryIndex(0);
    } else if (newPrimaryIndex > index) {
      setNewPrimaryIndex((prev) => prev - 1);
    }
  };

  const handleDeleteExistingImage = async (imageId: string) => {
    if (!listingToEdit) return;
    if (
      !window.confirm(
        t(
          "dashboard:confirm_delete_photo",
          "Are you sure you want to remove this photograph from the listing?"
        )
      )
    ) {
      return;
    }

    setDeletingImageId(imageId);
    setImageError(null);
    try {
      await listingsApi.deleteImage(listingToEdit.id, imageId);
      setExistingImages((prev) => prev.filter((img) => img.id !== imageId));
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : "Failed to delete photograph.";
      setImageError(msg);
    } finally {
      setDeletingImageId(null);
    }
  };

  const handleSetPrimaryExisting = async (imageId: string) => {
    if (!listingToEdit) return;
    setSettingPrimaryId(imageId);
    setImageError(null);
    try {
      await listingsApi.setPrimaryImage(listingToEdit.id, imageId);
      setExistingImages((prev) =>
        prev.map((img) => ({
          ...img,
          is_primary: img.id === imageId,
        }))
      );
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : "Failed to set primary thumbnail.";
      setImageError(msg);
    } finally {
      setSettingPrimaryId(null);
    }
  };

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!productName.trim()) {
      errors.product_name = t(
        "validation:produce_name_required",
        "Produce name is required (e.g. Sharbati Wheat, Alphonso Mango)."
      );
    }
    if (!title.trim()) {
      errors.title = t("validation:title_required", "Listing title is required.");
    }
    const qty = Number(initialQuantity);
    if (!initialQuantity || isNaN(qty) || qty <= 0) {
      errors.initial_quantity = t(
        "validation:quantity_gt_zero",
        "Initial supply quantity must be greater than zero."
      );
    }
    const price = Number(pricePerUnit);
    if (!pricePerUnit || isNaN(price) || price <= 0) {
      errors.price_per_unit = t(
        "validation:price_gt_zero",
        "Price per unit must be greater than zero."
      );
    }
    if (!unit.trim()) {
      errors.unit = t("validation:unit_required", "Measurement unit is required.");
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError(null);

    if (!validate()) return;
    if (isSubmittingRef.current || isSubmitting) return;
    isSubmittingRef.current = true;
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

        // Upload any newly selected images
        if (selectedFiles.length > 0) {
          await listingsApi.uploadImages(listingToEdit.id, selectedFiles);
          const refreshed = await listingsApi.getListing(listingToEdit.id);
          onSuccess(refreshed, true);
        } else {
          onSuccess(updated, true);
        }
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

        let created = createdListingRef.current;
        if (!created) {
          created = await listingsApi.createListing(payload);
          createdListingRef.current = created;
        }

        // Upload attached photographs
        if (selectedFiles.length > 0) {
          try {
            const uploaded = await listingsApi.uploadImages(created.id, selectedFiles);
            if (newPrimaryIndex > 0 && uploaded.length > newPrimaryIndex) {
              await listingsApi.setPrimaryImage(created.id, uploaded[newPrimaryIndex].id);
            }
          } catch (uploadErr) {
            // Even if an image upload fails, notify caller that listing was established
            const refreshed = await listingsApi.getListing(created.id).catch(() => created!);
            onSuccess(refreshed, false);
            throw uploadErr;
          }
          const refreshed = await listingsApi.getListing(created.id);
          onSuccess(refreshed, false);
        } else {
          onSuccess(created, false);
        }
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.isValidationError) {
          setGeneralError(t("validation:check_fields", "Validation error: please check highlighted fields."));
          const backendErrors: Record<string, string> = {};
          for (const [key, msgs] of Object.entries(err.fieldErrors)) {
            backendErrors[key] = msgs[0];
          }
          setFieldErrors(backendErrors);
        } else {
          setGeneralError(err.message || t("errors:save_failed", "Failed to save listing. Please try again."));
        }
      } else {
        setGeneralError(t("errors:network_error_save", "An unexpected network error occurred while saving the listing."));
      }
    } finally {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  };

  const totalImagesCount = existingImages.length + selectedFiles.length;

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
              {isEdit ? t("dashboard:edit_listing", "Edit Produce Listing") : t("dashboard:create_listing", "Create New Produce Listing")}
            </h2>
            <p className="text-xs text-muted-foreground">
              {isEdit
                ? t("dashboard:edit_listing_subtitle", "Update pricing, specifications, or harvest details for this produce lot")
                : t("dashboard:create_listing_subtitle", "Publish an agricultural produce lot to the direct B2B wholesale marketplace")}
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
                {t("dashboard:produce_name_label", "Produce Name")} <span className="text-destructive">*</span>
              </label>
              <input
                id="listing-product-name"
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder={t("dashboard:produce_name_placeholder", "e.g. Sharbati Wheat, Alphonso Mango")}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {fieldErrors.product_name && (
                <p className="text-xs text-destructive mt-1">{fieldErrors.product_name}</p>
              )}
            </div>

            <div>
              <label htmlFor="listing-category" className="block text-xs font-semibold text-foreground mb-1">
                {t("dashboard:produce_category_label", "Produce Category")}
              </label>
              <select
                id="listing-category"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">{t("dashboard:select_category_opt", "Select Category (Optional)")}</option>
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
              {t("dashboard:headline_title_label", "Headline Title")} <span className="text-destructive">*</span>
            </label>
            <input
              id="listing-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("dashboard:headline_title_placeholder", "e.g. Farm Fresh Certified Sharbati Wheat — 2026 Harvest")}
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
            {fieldErrors.title && (
              <p className="text-xs text-destructive mt-1">{fieldErrors.title}</p>
            )}
          </div>

          <div>
            <label htmlFor="listing-description" className="block text-xs font-semibold text-foreground mb-1">
              {t("dashboard:description_notes_label", "Produce Description & Storage Notes")}
            </label>
            <textarea
              id="listing-description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("dashboard:description_notes_placeholder", "Describe moisture content, packaging, storage conditions, or sorting specifications...")}
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-y"
            />
          </div>

          {/* Pricing & Quantity */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-secondary/30 border border-border">
            <div>
              <label htmlFor="listing-initial-quantity" className="block text-xs font-semibold text-foreground mb-1">
                {t("dashboard:total_supply_quantity_label", "Total Supply Quantity")} <span className="text-destructive">*</span>
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
                {t("dashboard:measurement_unit_label", "Measurement Unit")} <span className="text-destructive">*</span>
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
                {t("dashboard:price_per_unit_inr_label", "Price per Unit (₹)")} <span className="text-destructive">*</span>
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
                {t("dashboard:quality_grading_label", "Quality Grading")}
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
                {t("dashboard:harvest_date_label", "Harvest Date")}
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
                {t("dashboard:available_from_label", "Dispatch Readiness Date")}
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
                {t("dashboard:sourcing_state_label", "Sourcing State")}
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
                {t("dashboard:sourcing_city_label", "Sourcing City / District")}
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

          {/* Product Photographs Section */}
          <div className="p-4 rounded-xl bg-secondary/30 border border-border space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-primary" aria-hidden="true" />
                <span className="text-xs font-bold text-foreground">
                  {t("dashboard:produce_photos_title", "Produce Lot Photographs")}
                </span>
                <span className="text-[11px] font-semibold text-muted-foreground px-2 py-0.5 rounded-full bg-secondary border border-border">
                  {totalImagesCount} / {MAX_IMAGES_LIMIT}
                </span>
              </div>
              <span className="text-[11px] text-muted-foreground">
                {t("dashboard:photo_limits_guidance", "Max 10 photos, 5 MB each (JPEG, PNG, WebP)")}
              </span>
            </div>

            {imageError && (
              <div className="p-2.5 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{imageError}</span>
              </div>
            )}

            {/* Existing Images (Edit Mode) */}
            {existingImages.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-[11px] font-semibold text-muted-foreground block">
                  {t("dashboard:current_photos_label", "Existing Photographs:")}
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {existingImages.map((img) => (
                    <div
                      key={img.id}
                      className="relative rounded-lg border border-border overflow-hidden bg-background aspect-square group flex flex-col justify-between"
                    >
                      <img
                        src={img.image_url || listingsApi.getImageUrl(listingToEdit!.id, img.id)}
                        alt="Produce Lot"
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 p-1">
                        {!img.is_primary && (
                          <button
                            type="button"
                            onClick={() => handleSetPrimaryExisting(img.id)}
                            disabled={settingPrimaryId === img.id}
                            className="p-1.5 rounded-md bg-background/90 text-foreground hover:bg-background text-xs shadow-xs"
                            title={t("dashboard:make_primary_photo", "Make Primary Photo")}
                          >
                            <Star className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleDeleteExistingImage(img.id)}
                          disabled={deletingImageId === img.id}
                          className="p-1.5 rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs shadow-xs"
                          title={t("dashboard:delete_photo", "Delete Photo")}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      {img.is_primary && (
                        <span className="absolute top-1.5 start-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-primary text-primary-foreground shadow-xs flex items-center gap-1">
                          <Star className="w-3 h-3 fill-current" />
                          {t("dashboard:primary_photo_badge", "Primary")}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Selected New Previews */}
            {selectedFiles.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-[11px] font-semibold text-muted-foreground block">
                  {t("dashboard:photos_to_upload_label", "Photographs to be uploaded:")}
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {selectedFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className="relative rounded-lg border border-primary/40 overflow-hidden bg-background aspect-square group"
                    >
                      <img
                        src={previewUrls[idx]}
                        alt={file.name}
                        className="w-full h-full object-cover"
                      />
                      <button
                        type="button"
                        onClick={() => handleRemoveSelectedFile(idx)}
                        className="absolute top-1.5 end-1.5 p-1 rounded-full bg-destructive/90 text-destructive-foreground hover:bg-destructive shadow-xs"
                        title={t("common:remove", "Remove")}
                      >
                        <X className="w-3 h-3" />
                      </button>
                      <div className="absolute bottom-0 inset-x-0 bg-background/90 backdrop-blur-xs p-1 text-[10px] truncate text-center">
                        <span className="truncate block font-medium">{file.name}</span>
                        <span className="text-muted-foreground">
                          {(file.size / 1024).toFixed(0)} KB
                        </span>
                      </div>
                      {/* Primary selector for new files if no existing images */}
                      {existingImages.length === 0 && (
                        <button
                          type="button"
                          onClick={() => setNewPrimaryIndex(idx)}
                          className={`absolute top-1.5 start-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold shadow-xs flex items-center gap-1 ${
                            newPrimaryIndex === idx
                              ? "bg-primary text-primary-foreground"
                              : "bg-background/80 text-foreground hover:bg-background"
                          }`}
                        >
                          <Star className={`w-3 h-3 ${newPrimaryIndex === idx ? "fill-current" : ""}`} />
                          {newPrimaryIndex === idx
                            ? t("dashboard:primary_photo_badge", "Primary")
                            : t("dashboard:set_primary", "Set Primary")}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Upload File Input */}
            {totalImagesCount < MAX_IMAGES_LIMIT && (
              <div>
                <input
                  ref={fileInputRef}
                  id="listing-images-input"
                  type="file"
                  multiple
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full py-3 px-4 rounded-xl border border-dashed border-border bg-background hover:bg-secondary/50 text-foreground text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <ImagePlus className="w-4 h-4 text-primary" />
                  <span>
                    {totalImagesCount === 0
                      ? t("dashboard:add_first_photos", "Select or Take Harvest Photographs")
                      : t("dashboard:add_more_photos", "Add More Photographs ({{remaining}} remaining)", {
                          remaining: MAX_IMAGES_LIMIT - totalImagesCount,
                        })}
                  </span>
                </button>
              </div>
            )}
          </div>

          {/* Initial Status (Create Mode only) */}
          {!isEdit && (
            <div className="p-3 rounded-lg bg-secondary/50 border border-border flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-foreground block">{t("dashboard:publication_status_label", "Listing Publication Status")}</span>
                <span className="text-xs text-muted-foreground block">
                  {t("dashboard:publication_status_desc", "Choose whether this lot becomes immediately visible on the public marketplace.")}
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
                  <span>{t("dashboard:status_active_live", "Active (Live)")}</span>
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
                  <span>{t("dashboard:status_save_draft", "Save as Draft")}</span>
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
              {t("common:cancel", "Cancel")}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary-700 text-sm font-semibold transition-colors shadow-sm disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>{t("common:saving", "Saving...")}</span>
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" aria-hidden="true" />
                  <span>{isEdit ? t("dashboard:update_listing_btn", "Update Listing") : t("dashboard:publish_listing_btn", "Publish Listing")}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
