import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../store/authStore";
import { getSafeRedirectUrl } from "../../utils/redirect";

interface GuestOnlyProps {
  children?: React.ReactNode;
}

export const GuestOnly: React.FC<GuestOnlyProps> = ({ children }) => {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "uninitialized" || status === "restoring") {
    return (
      <div
        className="flex-1 flex flex-col items-center justify-center min-h-[50vh] p-8"
        role="status"
        aria-live="polite"
      >
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mb-4" />
        <p className="text-sm text-muted-foreground font-medium">Verifying session...</p>
      </div>
    );
  }

  if (status === "authenticated" && user !== null) {
    const rawFrom = (location.state as { from?: unknown } | null)?.from;
    const safeDestination = getSafeRedirectUrl(rawFrom, "/");
    return <Navigate to={safeDestination} replace />;
  }

  return children ? <>{children}</> : null;
};
