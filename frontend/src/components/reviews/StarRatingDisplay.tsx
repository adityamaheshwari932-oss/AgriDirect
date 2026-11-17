import React from "react";
import { Star } from "lucide-react";
import { useTranslation } from "react-i18next";

interface StarRatingDisplayProps {
  rating: number; // 0 to 5
  totalReviews?: number;
  size?: "sm" | "md" | "lg";
  showValue?: boolean;
}

export const StarRatingDisplay: React.FC<StarRatingDisplayProps> = ({
  rating,
  totalReviews,
  size = "md",
  showValue = true,
}) => {
  const { t } = useTranslation(["reviews"]);
  const sizeClasses = {
    sm: "w-3 h-3",
    md: "w-4 h-4",
    lg: "w-5 h-5",
  };

  const textClasses = {
    sm: "text-[11px]",
    md: "text-xs",
    lg: "text-sm",
  };

  const roundedRating = Math.round(rating * 10) / 10;

  return (
    <div
      className="inline-flex items-center gap-1.5"
      aria-label={t("reviews:rating_aria", "Rating: {{rating}} out of 5 stars", { rating: roundedRating })}
    >
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => {
          const isFilled = star <= Math.round(rating);
          return (
            <Star
              key={star}
              className={`${sizeClasses[size]} ${
                isFilled
                  ? "text-amber-400 fill-amber-400"
                  : "text-muted-foreground/30 fill-muted-foreground/10"
              }`}
              aria-hidden="true"
            />
          );
        })}
      </div>
      {showValue && (
        <span className={`font-semibold text-foreground ${textClasses[size]}`}>
          {roundedRating > 0 ? roundedRating.toFixed(1) : "N/A"}
        </span>
      )}
      {totalReviews !== undefined && (
        <span className={`text-muted-foreground ${textClasses[size]}`}>
          ({totalReviews})
        </span>
      )}
    </div>
  );
};

