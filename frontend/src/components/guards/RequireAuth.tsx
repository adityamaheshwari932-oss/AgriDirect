import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../store/authStore";

interface RequireAuthProps {
  children?: React.ReactNode;
}

export const RequireAuth: React.FC<RequireAuthProps> = ({ children }) => {
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

  if (status === "unauthenticated" || user === null) {
    // Preserve requested path in navigation state for post-login redirection
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname + location.search }}
        replace
      />
    );
  }

  return children ? <>{children}</> : null;
};
