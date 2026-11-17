import React, { useState } from "react";
import { Star } from "lucide-react";
import { useTranslation } from "react-i18next";

interface StarRatingInputProps {
  value: number;
  onChange: (value: number) => void;
  label?: string;
  required?: boolean;
}

export const StarRatingInput: React.FC<StarRatingInputProps> = ({
  value,
  onChange,
  label,
  required = false,
}) => {
  const { t } = useTranslation(["reviews"]);
  const [hovered, setHovered] = useState<number | null>(null);

  const activeValue = hovered !== null ? hovered : value;

  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-xs font-medium text-foreground">
          {label} {required && <span className="text-destructive">*</span>}
        </label>
      )}
      <div
        className="flex items-center gap-1.5"
        role="radiogroup"
        aria-label={label || t("reviews:rating_label", "Rating")}
      >
        {[1, 2, 3, 4, 5].map((star) => {
          const isSelected = star <= activeValue;
          return (
            <button
              key={star}
              type="button"
              role="radio"
              aria-checked={value === star}
              aria-label={t("reviews:star_count_aria", "{{count}} star", { count: star })}
              onClick={() => onChange(star)}
              onMouseEnter={() => setHovered(star)}
              onMouseLeave={() => setHovered(null)}
              className="p-1 rounded hover:bg-secondary/60 transition-transform active:scale-95 focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <Star
                className={`w-6 h-6 transition-colors ${
                  isSelected
                    ? "text-amber-400 fill-amber-400"
                    : "text-muted-foreground/30 fill-muted-foreground/10"
                }`}
              />
            </button>
          );
        })}
        <span className="text-xs font-semibold text-muted-foreground ms-2 min-w-[3ch]">
          {activeValue > 0 ? `${activeValue}/5` : "-"}
        </span>
      </div>
    </div>
  );
};

