import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../store/authStore";

export const DashboardRedirectPage: React.FC = () => {
  const { status, user } = useAuth();

  if (status === "uninitialized" || status === "restoring") {
    return (
      <div
        className="flex-1 flex flex-col items-center justify-center min-h-[50vh] p-8"
        role="status"
        aria-live="polite"
      >
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mb-4" />
        <p className="text-sm text-muted-foreground font-medium">
          Loading dashboard...
        </p>
      </div>
    );
  }

  if (status !== "authenticated" || !user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role === "farmer") {
    return <Navigate to="/dashboard/farmer" replace />;
  }

  if (user.role === "buyer") {
    return <Navigate to="/dashboard/buyer" replace />;
  }

  return <Navigate to="/" replace />;
};
