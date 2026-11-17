import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { X, Star, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { reviewsApi } from "../../api/reviews";
import { StarRatingInput } from "./StarRatingInput";
import type { ReviewItem } from "../../types/reviews";

interface ReviewSubmitModalProps {
  orderId: string;
  orderReference?: string;
  counterpartyName: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (review: ReviewItem) => void;
}

export const ReviewSubmitModal: React.FC<ReviewSubmitModalProps> = ({
  orderId,
  orderReference,
  counterpartyName,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(["reviews", "common", "errors", "validation"]);
  const [overallRating, setOverallRating] = useState<number>(5);
  const [qualityRating, setQualityRating] = useState<number>(0);
  const [accuracyRating, setAccuracyRating] = useState<number>(0);
  const [communicationRating, setCommunicationRating] = useState<number>(0);
  const [reliabilityRating, setReliabilityRating] = useState<number>(0);
  const [reviewText, setReviewText] = useState<string>("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (overallRating < 1 || overallRating > 5) {
      setError(
        t(
          "reviews:error_rating_range",
          "Please select an overall rating between 1 and 5 stars."
        )
      );
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const review = await reviewsApi.submitReview({
        order_id: orderId,
        overall_rating: overallRating,
        quality_rating: qualityRating > 0 ? qualityRating : null,
        accuracy_rating: accuracyRating > 0 ? accuracyRating : null,
        communication_rating: communicationRating > 0 ? communicationRating : null,
        reliability_rating: reliabilityRating > 0 ? reliabilityRating : null,
        review_text: reviewText.trim() ? reviewText.trim() : null,
      });
      onSuccess(review);
      onClose();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : t("reviews:error_submit_failed", "Failed to submit review.");
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
      <div className="relative w-full max-w-lg bg-card border border-border rounded-xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-secondary/30">
          <div>
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
              {t("reviews:submit_modal_title", "Rate & Review Deal")}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {t("reviews:submit_modal_subtitle", "Reviewing experience with {{counterparty}}", {
                counterparty: counterpartyName,
              })}
              {orderReference && ` ${t("reviews:order_ref", `(Order #${orderReference})`, { reference: orderReference })}`}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            aria-label={t("common:actions.close", "Close")}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 text-xs bg-destructive/10 border border-destructive/20 text-destructive rounded-lg flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Overall Rating */}
          <div className="p-3.5 bg-secondary/30 rounded-xl border border-border">
            <StarRatingInput
              label={t("reviews:overall_experience", "Overall Experience")}
              value={overallRating}
              onChange={setOverallRating}
              required
            />
          </div>

          {/* Sub-ratings */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-secondary/20 rounded-lg border border-border/60">
              <StarRatingInput
                label={t("reviews:produce_quality", "Produce Quality")}
                value={qualityRating}
                onChange={setQualityRating}
              />
            </div>
            <div className="p-3 bg-secondary/20 rounded-lg border border-border/60">
              <StarRatingInput
                label={t("reviews:description_accuracy", "Description Accuracy")}
                value={accuracyRating}
                onChange={setAccuracyRating}
              />
            </div>
            <div className="p-3 bg-secondary/20 rounded-lg border border-border/60">
              <StarRatingInput
                label={t("reviews:communication", "Communication")}
                value={communicationRating}
                onChange={setCommunicationRating}
              />
            </div>
            <div className="p-3 bg-secondary/20 rounded-lg border border-border/60">
              <StarRatingInput
                label={t("reviews:reliability_punctuality", "Reliability & Punctuality")}
                value={reliabilityRating}
                onChange={setReliabilityRating}
              />
            </div>
          </div>

          {/* Written feedback */}
          <div className="space-y-1">
            <div className="flex justify-between items-center text-xs">
              <label htmlFor="review_text" className="font-medium text-foreground">
                {t("reviews:written_review_label", "Written Review (Optional)")}
              </label>
              <span className="text-muted-foreground text-[11px]">{reviewText.length}/2000</span>
            </div>
            <textarea
              id="review_text"
              rows={4}
              maxLength={2000}
              value={reviewText}
              onChange={(e) => setReviewText(e.target.value)}
              placeholder={t(
                "reviews:written_review_placeholder",
                "Share details about fulfillment quality, packaging, communication, or delivery timeliness..."
              )}
              className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-medium rounded-lg border border-border bg-background hover:bg-secondary text-foreground transition-colors"
            >
              {t("common:actions.cancel", "Cancel")}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors shadow-sm"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  {t("common:status.submitting", "Submitting...")}
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {t("reviews:submit_review_action", "Submit Review")}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
