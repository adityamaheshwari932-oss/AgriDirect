import React from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, ArrowRight, UserCheck, AlertCircle } from "lucide-react";
import type { User } from "../../types";
import { calculateProfileCompletion } from "../../utils/status";

interface ProfileCompletionCardProps {
  user: User;
  className?: string;
}

export const ProfileCompletionCard: React.FC<ProfileCompletionCardProps> = ({
  user,
  className = "",
}) => {
  const completion = calculateProfileCompletion(user);
  const isComplete = completion.percentage === 100;

  return (
    <div
      className={`p-5 rounded-xl border bg-card shadow-xs space-y-4 ${className}`}
      role="region"
      aria-labelledby="profile-completion-heading"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
            {isComplete ? (
              <CheckCircle2 className="w-5 h-5" aria-hidden="true" />
            ) : (
              <UserCheck className="w-5 h-5" aria-hidden="true" />
            )}
          </div>
          <div>
            <h2
              id="profile-completion-heading"
              className="text-base font-bold text-foreground"
            >
              Profile Completion
            </h2>
            <p className="text-xs text-muted-foreground">
              {isComplete
                ? "Your commercial profile is comprehensive"
                : `${completion.completedCount} of ${completion.totalCount} attributes recorded`}
            </p>
          </div>
        </div>

        <div className="text-right">
          <span className="text-lg font-bold text-primary">
            {completion.percentage}%
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div
        className="w-full bg-secondary rounded-full h-2 overflow-hidden"
        role="progressbar"
        aria-valuenow={completion.percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Profile completion progress"
      >
        <div
          className="bg-primary h-2 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${completion.percentage}%` }}
        />
      </div>

      {/* Missing Recommendations */}
      {!isComplete && completion.missingFields.length > 0 ? (
        <div className="text-xs text-muted-foreground space-y-2">
          <div className="flex items-center gap-1.5 font-medium text-foreground">
            <AlertCircle className="w-3.5 h-3.5 text-harvest-600" aria-hidden="true" />
            <span>Recommended additions:</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {completion.missingFields.slice(0, 4).map((field) => (
              <span
                key={field}
                className="px-2 py-0.5 rounded bg-secondary text-foreground text-[11px] border border-border"
              >
                + {field}
              </span>
            ))}
            {completion.missingFields.length > 4 && (
              <span className="text-[11px] text-muted-foreground self-center">
                +{completion.missingFields.length - 4} more
              </span>
            )}
          </div>
        </div>
      ) : (
        <p className="text-xs text-emerald-700 bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">
          All recommended profile attributes have been completed.
        </p>
      )}

      {/* Action */}
      <div className="pt-1">
        <Link
          to="/dashboard/profile"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:text-primary-800 transition-colors focus:outline-none focus:ring-2 focus:ring-primary rounded"
        >
          <span>{isComplete ? "Manage Profile" : "Complete Missing Attributes"}</span>
          <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
};
