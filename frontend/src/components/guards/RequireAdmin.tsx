import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../store/authStore";

interface RequireAdminProps {
  children?: React.ReactNode;
}

export const RequireAdmin: React.FC<RequireAdminProps> = ({ children }) => {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "uninitialized" || status === "restoring") {
    return (
      <div
        className="flex-1 flex flex-col items-center justify-center min-h-[50vh] p-8"
        role="status"
        aria-live="polite"
        aria-label="Verifying administrative privileges"
      >
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mb-4" />
        <p className="text-sm text-muted-foreground font-medium">
          Verifying administrator authorization...
        </p>
      </div>
    );
  }

  if (status !== "authenticated" || !user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    );
  }

  if (user.role !== "admin") {
    // Non-admin users must not see administrator content; redirect to role-appropriate home
    if (user.role === "farmer") {
      return <Navigate to="/dashboard/farmer" replace />;
    }
    if (user.role === "buyer") {
      return <Navigate to="/dashboard/buyer" replace />;
    }
    return <Navigate to="/" replace />;
  }

  return children ? <>{children}</> : null;
};

