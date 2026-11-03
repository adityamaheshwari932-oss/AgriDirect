import React, { useEffect, useState } from "react";
import { X, Star, Loader2, AlertCircle, Calendar } from "lucide-react";
import { reviewsApi } from "../../api/reviews";
import { StarRatingDisplay } from "./StarRatingDisplay";
import type { ReviewItem, UserReputationSummary } from "../../types/reviews";

interface UserReviewsModalProps {
  userId: string;
  userName: string;
  userRole?: string;
  isOpen: boolean;
  onClose: () => void;
}

export const UserReviewsModal: React.FC<UserReviewsModalProps> = ({
  userId,
  userName,
  userRole,
  isOpen,
  onClose,
}) => {
  const [summary, setSummary] = useState<UserReputationSummary | null>(null);
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !userId) return;

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    Promise.all([
      reviewsApi.getUserReputationSummary(userId),
      reviewsApi.listUserReviews(userId, 1, 20),
    ])
      .then(([rep, revList]) => {
        if (!isMounted) return;
        setSummary(rep);
        setReviews(revList.items);
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        const msg = err instanceof Error ? err.message : "Failed to load reviews.";
        setError(msg);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, userId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
      <div className="relative w-full max-w-2xl bg-card border border-border rounded-xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-secondary/30 shrink-0">
          <div>
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
              Reputation & Verified Reviews
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Performance feedback for <span className="font-semibold text-foreground">{userName}</span>
              {userRole && ` (${userRole})`}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-muted-foreground">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <p className="text-xs">Loading reputation history...</p>
            </div>
          ) : error ? (
            <div className="p-4 text-center space-y-2">
              <AlertCircle className="w-6 h-6 text-destructive mx-auto" />
              <p className="text-xs text-destructive font-medium">{error}</p>
            </div>
          ) : summary ? (
            <>
              {/* Summary Scorecard */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4 rounded-xl bg-secondary/30 border border-border">
                {/* Left: Overall score */}
                <div className="md:col-span-5 flex flex-col items-center justify-center text-center p-2 border-b md:border-b-0 md:border-r border-border/80">
                  <span className="text-4xl font-extrabold text-foreground">
                    {summary.average_rating ? summary.average_rating.toFixed(1) : "0.0"}
                  </span>
                  <div className="mt-1">
                    <StarRatingDisplay rating={summary.average_rating} size="lg" showValue={false} />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1.5 font-medium">
                    Based on {summary.total_reviews} verified {summary.total_reviews === 1 ? "review" : "reviews"}
                  </p>
                </div>

                {/* Right: Sub-dimension averages */}
                <div className="md:col-span-7 flex flex-col justify-center space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Produce Quality</span>
                    <span className="font-semibold text-foreground">
                      {summary.quality_rating_avg ? `${summary.quality_rating_avg.toFixed(1)} / 5` : "N/A"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Description Accuracy</span>
                    <span className="font-semibold text-foreground">
                      {summary.accuracy_rating_avg ? `${summary.accuracy_rating_avg.toFixed(1)} / 5` : "N/A"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Communication</span>
                    <span className="font-semibold text-foreground">
                      {summary.communication_rating_avg ? `${summary.communication_rating_avg.toFixed(1)} / 5` : "N/A"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Reliability & Fulfillment</span>
                    <span className="font-semibold text-foreground">
                      {summary.reliability_rating_avg ? `${summary.reliability_rating_avg.toFixed(1)} / 5` : "N/A"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Reviews List */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Recent Feedback ({reviews.length})
                </h3>

                {reviews.length === 0 ? (
                  <div className="py-8 text-center text-xs text-muted-foreground bg-secondary/20 rounded-lg border border-border">
                    No verified reviews on record yet.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {reviews.map((rev) => {
                      const dateStr = new Date(rev.created_at).toLocaleDateString([], {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      });

                      return (
                        <div
                          key={rev.id}
                          className="p-3.5 rounded-lg border border-border bg-card space-y-2 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <StarRatingDisplay rating={rev.overall_rating} size="sm" />
                            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {dateStr}
                            </span>
                          </div>

                          {rev.review_text && (
                            <p className="text-foreground leading-relaxed italic">
                              "{rev.review_text}"
                            </p>
                          )}

                          {/* Sub-rating tags */}
                          <div className="flex flex-wrap gap-2 text-[10px] text-muted-foreground pt-1 border-t border-border/40">
                            {rev.quality_rating && (
                              <span>Quality: {rev.quality_rating}/5</span>
                            )}
                            {rev.accuracy_rating && (
                              <span>Accuracy: {rev.accuracy_rating}/5</span>
                            )}
                            {rev.communication_rating && (
                              <span>Communication: {rev.communication_rating}/5</span>
                            )}
                            {rev.reliability_rating && (
                              <span>Reliability: {rev.reliability_rating}/5</span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};

