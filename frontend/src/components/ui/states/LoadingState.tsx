import React from "react";

interface LoadingStateProps {
  message?: string;
  subtext?: string;
  className?: string;
  size?: "sm" | "md" | "lg";
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = "Loading...",
  subtext,
  className = "",
  size = "md",
}) => {
  const spinnerSizes = {
    sm: "w-5 h-5 border-2",
    md: "w-8 h-8 border-3",
    lg: "w-12 h-12 border-4",
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex-1 flex flex-col items-center justify-center p-8 text-center min-h-[200px] ${className}`}
    >
      <div
        className={`${spinnerSizes[size]} border-primary-200 border-t-primary rounded-full animate-spin mb-3`}
        aria-hidden="true"
      />
      <p className="text-sm font-medium text-foreground">{message}</p>
      {subtext && <p className="text-xs text-muted-foreground mt-1 max-w-sm">{subtext}</p>}
    </div>
  );
};

