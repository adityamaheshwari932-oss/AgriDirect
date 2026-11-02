import React, { useRef, useState } from "react";
import {
  X,
  Upload,
  Trash2,
  Star,
  AlertCircle,
  Loader2,
  CheckCircle2,
  ImageIcon,
} from "lucide-react";
import { listingsApi } from "../../api/listings";
import { ApiError } from "../../api/errors";
import type { ListingImage, ProduceListingDetail } from "../../types/listings";

interface ListingImageModalProps {
  isOpen: boolean;
  listing: ProduceListingDetail;
  onClose: () => void;
  onImagesUpdated: (updatedImages: ListingImage[]) => void;
}

const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"];
const ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

export const ListingImageModal: React.FC<ListingImageModalProps> = ({
  isOpen,
  listing,
  onClose,
  onImagesUpdated,
}) => {
  const [images, setImages] = useState<ListingImage[]>(listing.images || []);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isPrimary, setIsPrimary] = useState(images.length === 0);
  const [isUploading, setIsUploading] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setSuccess(null);

    const files = e.target.files;
    if (!files || files.length === 0) {
      setSelectedFile(null);
      return;
    }

    const file = files[0];

    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      setError(`Image size exceeds the 5 MB limit (${(file.size / (1024 * 1024)).toFixed(2)} MB).`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    const lowerName = file.name.toLowerCase();
    const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
    const hasValidMime = ALLOWED_MIME_TYPES.includes(file.type);

    if (!hasValidExt || !hasValidMime) {
      setError("Unsupported image format. Please select a JPEG, PNG, or WebP photo.");
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select an image file to upload.");
      return;
    }

    if (images.length >= 5) {
      setError("Maximum limit of 5 images per listing has been reached.");
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccess(null);

    try {
      await listingsApi.uploadImage(
        listing.id,
        selectedFile,
        isPrimary,
        images.length
      );

      // Refresh images from backend
      const refreshed = await listingsApi.getListing(listing.id);
      setImages(refreshed.images);
      onImagesUpdated(refreshed.images);

      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setSuccess("Image uploaded successfully.");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message || "Failed to upload image. Please try again.");
      } else {
        setError("An unexpected network error occurred while uploading the photo.");
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    if (!window.confirm("Are you sure you want to delete this photo from the listing?")) {
      return;
    }

    setActionLoadingId(imageId);
    setError(null);
    setSuccess(null);

    try {
      await listingsApi.deleteImage(listing.id, imageId);
      const updated = images.filter((img) => img.id !== imageId);
      setImages(updated);
      onImagesUpdated(updated);
      setSuccess("Image deleted successfully.");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message || "Failed to delete image.");
      } else {
        setError("Network error while deleting image.");
      }
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleSetPrimary = async (imageId: string) => {
    setActionLoadingId(imageId);
    setError(null);
    setSuccess(null);

    try {
      await listingsApi.setPrimaryImage(listing.id, imageId);
      const updated = images.map((img) => ({
        ...img,
        is_primary: img.id === imageId,
      }));
      setImages(updated);
      onImagesUpdated(updated);
      setSuccess("Primary catalog thumbnail updated.");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message || "Failed to designate primary image.");
      } else {
        setError("Network error while updating primary image.");
      }
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-image-title"
    >
      <div className="bg-card w-full max-w-2xl rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div>
            <h2 id="modal-image-title" className="text-lg font-bold text-foreground">
              Manage Produce Photos
            </h2>
            <p className="text-xs text-muted-foreground">
              {listing.title} • {images.length}/5 photos attached
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

        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {error && (
            <div
              className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-start gap-2.5"
              role="alert"
            >
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div className="text-xs">{error}</div>
            </div>
          )}

          {success && (
            <div
              className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-sm flex items-start gap-2.5"
              role="status"
            >
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-600" aria-hidden="true" />
              <div className="text-xs font-medium">{success}</div>
            </div>
          )}

          {/* Current Gallery */}
          <div>
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
              Attached Produce Photos ({images.length}/5)
            </h3>
            {images.length === 0 ? (
              <div className="p-8 rounded-xl border border-dashed border-border text-center bg-secondary/20">
                <ImageIcon className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-50" aria-hidden="true" />
                <p className="text-sm font-medium text-foreground">No photos attached yet</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Upload crisp photos of your harvested produce lot to attract commercial buyers.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {images.map((img) => (
                  <div
                    key={img.id}
                    className={`relative rounded-xl border overflow-hidden p-2 bg-secondary/30 transition-all ${
                      img.is_primary ? "border-primary ring-2 ring-primary/20" : "border-border"
                    }`}
                  >
                    <div className="aspect-video w-full rounded-lg overflow-hidden bg-black/5 flex items-center justify-center relative">
                      <img
                        src={listingsApi.getImageUrl(listing.id, img.id)}
                        alt={`Produce lot photo ${img.display_order + 1}`}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          // Fallback placeholder if streaming fails
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                      {img.is_primary && (
                        <span className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-primary text-primary-foreground text-[10px] font-bold tracking-wider uppercase shadow-xs flex items-center gap-1">
                          <Star className="w-3 h-3 fill-current" aria-hidden="true" />
                          Primary Thumbnail
                        </span>
                      )}
                    </div>

                    <div className="mt-2 flex items-center justify-between pt-1">
                      {!img.is_primary ? (
                        <button
                          type="button"
                          onClick={() => handleSetPrimary(img.id)}
                          disabled={actionLoadingId === img.id}
                          className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary-800 font-semibold transition-colors disabled:opacity-50"
                        >
                          <Star className="w-3.5 h-3.5" aria-hidden="true" />
                          <span>Make Primary</span>
                        </button>
                      ) : (
                        <span className="text-[11px] text-muted-foreground font-medium">
                          Catalog Display Photo
                        </span>
                      )}

                      <button
                        type="button"
                        onClick={() => handleDeleteImage(img.id)}
                        disabled={actionLoadingId === img.id}
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
                        aria-label="Delete photo"
                      >
                        {actionLoadingId === img.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                        ) : (
                          <Trash2 className="w-4 h-4" aria-hidden="true" />
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Upload New Image Form */}
          {images.length < 5 && (
            <form onSubmit={handleUpload} className="p-4 rounded-xl border border-border bg-secondary/30 space-y-3">
              <h3 className="text-xs font-semibold text-foreground">Upload New Photo</h3>

              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp"
                  onChange={handleFileChange}
                  disabled={isUploading}
                  className="block w-full text-xs text-muted-foreground file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary-700 cursor-pointer disabled:opacity-50"
                />

                <label className="inline-flex items-center gap-1.5 text-xs text-foreground cursor-pointer flex-shrink-0">
                  <input
                    type="checkbox"
                    checked={isPrimary}
                    onChange={(e) => setIsPrimary(e.target.checked)}
                    className="rounded text-primary focus:ring-primary"
                  />
                  <span>Set as Primary</span>
                </label>
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] text-muted-foreground">
                  Max 5 MB • JPEG, PNG, or WebP
                </span>

                <button
                  type="submit"
                  disabled={!selectedFile || isUploading}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-700 transition-colors disabled:opacity-50 shadow-xs"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                      <span>Uploading...</span>
                    </>
                  ) : (
                    <>
                      <Upload className="w-3.5 h-3.5" aria-hidden="true" />
                      <span>Upload Photo</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border flex justify-end bg-secondary/20">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

