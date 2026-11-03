import React, { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout, DashboardLayout } from "./components/layout";
import { GuestOnly, RequireAdmin, RequireAuth, RequireRole } from "./components/guards";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { ToastProvider, useToast } from "./components/ui/toast";
import { AUTH_EVENTS, type ForbiddenEventDetail } from "./api/events";
import {
  LandingPage,
  LoginPage,
  RegisterRolePage,
  FarmerRegisterPage,
  BuyerRegisterPage,
  NotFoundPage,
  ProtectedPlaceholderPage,
  DashboardRedirectPage,
  FarmerDashboardPage,
  BuyerDashboardPage,
  VerificationPage,
  ProfilePage,
  FarmerListingsPage,
  BuyerRequirementsPage,
  MarketplacePage,
  OffersPage,
  OrdersPage,
  MessagesPage,
  AnalyticsDashboardPage,
  UserReportsPage,
  AdminPlatformAnalyticsPage,
  AdminUsersPage,
  AdminContentModerationPage,
  AdminVerificationQueuePage,
  AdminAuditLogsPage,
} from "./pages";
import { useAuth } from "./store/authStore";

const AppEventListeners: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { logout } = useAuth();
  const { error: toastError, warning: toastWarning } = useToast();

  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
      toastWarning("Your session has expired. Please log in again.", "Session Expired");
    };

    const handleForbidden = (event: Event) => {
      const customEvent = event as CustomEvent<ForbiddenEventDetail>;
      const detail = customEvent.detail;
      if (detail?.isAccountSuspendedOrRestricted) {
        toastError(
          detail.message ||
            "Your account is currently restricted or suspended. Transactional operations are disabled.",
          "Account Restricted"
        );
      } else {
        toastError(detail?.message || "You do not have permission for this operation.", "Access Denied");
      }
    };

    window.addEventListener(AUTH_EVENTS.UNAUTHORIZED, handleUnauthorized);
    window.addEventListener(AUTH_EVENTS.FORBIDDEN, handleForbidden);

    return () => {
      window.removeEventListener(AUTH_EVENTS.UNAUTHORIZED, handleUnauthorized);
      window.removeEventListener(AUTH_EVENTS.FORBIDDEN, handleForbidden);
    };
  }, [logout, toastError, toastWarning]);

  return <>{children}</>;
};

export const App: React.FC = () => {
  const { restoreSession } = useAuth();

  useEffect(() => {
    // Attempt session restoration once on application mount
    void restoreSession();
  }, [restoreSession]);

  return (
    <ErrorBoundary>
      <ToastProvider>
        <AppEventListeners>
          <BrowserRouter>
            <Routes>
              {/* Authenticated Dashboard Shell (Farmer & Buyer) */}
              <Route
                path="/dashboard"
                element={
                  <RequireAuth>
                    <DashboardLayout />
                  </RequireAuth>
                }
              >
                <Route index element={<DashboardRedirectPage />} />
                <Route
                  path="farmer"
                  element={
                    <RequireRole allowedRoles={["farmer"]}>
                      <FarmerDashboardPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="buyer"
                  element={
                    <RequireRole allowedRoles={["buyer"]}>
                      <BuyerDashboardPage />
                    </RequireRole>
                  }
                />
                {/* Farmer specific routes */}
                <Route
                  path="listings"
                  element={
                    <RequireRole allowedRoles={["farmer"]}>
                      <FarmerListingsPage />
                    </RequireRole>
                  }
                />
                {/* Marketplace Discovery route (Farmer & Buyer) */}
                <Route
                  path="marketplace"
                  element={
                    <RequireRole allowedRoles={["farmer", "buyer"]}>
                      <MarketplacePage />
                    </RequireRole>
                  }
                />
                {/* Buyer specific routes */}
                <Route
                  path="requirements"
                  element={
                    <RequireRole allowedRoles={["buyer"]}>
                      <BuyerRequirementsPage />
                    </RequireRole>
                  }
                />
                {/* Shared authenticated routes */}
                <Route
                  path="offers"
                  element={
                    <RequireRole allowedRoles={["farmer", "buyer"]}>
                      <OffersPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="orders"
                  element={
                    <RequireRole allowedRoles={["farmer", "buyer"]}>
                      <OrdersPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="messages"
                  element={
                    <RequireRole allowedRoles={["farmer", "buyer", "admin"]}>
                      <MessagesPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="analytics"
                  element={
                    <RequireRole allowedRoles={["farmer", "buyer"]}>
                      <AnalyticsDashboardPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="reports"
                  element={
                    <RequireRole allowedRoles={["farmer", "buyer"]}>
                      <UserReportsPage />
                    </RequireRole>
                  }
                />
                <Route path="profile" element={<ProfilePage />} />
                <Route path="verification" element={<VerificationPage />} />
              </Route>

              {/* Authenticated Administrator Console Shell */}
              <Route
                path="/admin"
                element={
                  <RequireAdmin>
                    <DashboardLayout />
                  </RequireAdmin>
                }
              >
                <Route index element={<Navigate to="/admin/analytics" replace />} />
                <Route path="analytics" element={<AdminPlatformAnalyticsPage />} />
                <Route path="users" element={<AdminUsersPage />} />
                <Route path="content" element={<AdminContentModerationPage />} />
                <Route path="verification" element={<AdminVerificationQueuePage />} />
                <Route path="audit-logs" element={<AdminAuditLogsPage />} />
              </Route>

              {/* Public & Authentication Shell */}
              <Route element={<AppLayout />}>
                <Route path="/" element={<LandingPage />} />
                <Route path="/marketplace" element={<MarketplacePage />} />
                <Route
                  path="/login"
                  element={
                    <GuestOnly>
                      <LoginPage />
                    </GuestOnly>
                  }
                />
                <Route
                  path="/register"
                  element={
                    <GuestOnly>
                      <RegisterRolePage />
                    </GuestOnly>
                  }
                />
                <Route
                  path="/register/farmer"
                  element={
                    <GuestOnly>
                      <FarmerRegisterPage />
                    </GuestOnly>
                  }
                />
                <Route
                  path="/register/buyer"
                  element={
                    <GuestOnly>
                      <BuyerRegisterPage />
                    </GuestOnly>
                  }
                />
                <Route
                  path="/protected-test"
                  element={
                    <RequireAuth>
                      <ProtectedPlaceholderPage />
                    </RequireAuth>
                  }
                />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AppEventListeners>
      </ToastProvider>
    </ErrorBoundary>
  );
};

export default App;
