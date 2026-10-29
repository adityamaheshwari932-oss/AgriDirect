import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../store/authStore";
import type { UserRole } from "../../types";

interface RequireRoleProps {
  allowedRoles: UserRole[];
  children?: React.ReactNode;
}

export const RequireRole: React.FC<RequireRoleProps> = ({
  allowedRoles,
  children,
}) => {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "uninitialized" || status === "restoring") {
    return (
      <div
        className="flex-1 flex flex-col items-center justify-center min-h-[50vh] p-8"
        role="status"
        aria-live="polite"
        aria-label="Verifying role permissions"
      >
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mb-4" />
        <p className="text-sm text-muted-foreground font-medium">
          Verifying authorization...
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

  if (!allowedRoles.includes(user.role)) {
    // Role mismatch: redirect user to their role-appropriate home
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
