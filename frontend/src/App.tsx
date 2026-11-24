import React, { Suspense, useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout, DashboardLayout } from "./components/layout";
import { GuestOnly, RequireAdmin, RequireAuth, RequireRole } from "./components/guards";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { ToastProvider, useToast } from "./components/ui/toast";
import { AUTH_EVENTS, type ForbiddenEventDetail } from "./api/events";
import { useAuth } from "./store/authStore";

// Route-level code splitting via React.lazy
const LandingPage = React.lazy(() => import("./pages/LandingPage").then((m) => ({ default: m.LandingPage })));
const LoginPage = React.lazy(() => import("./pages/LoginPage").then((m) => ({ default: m.LoginPage })));
const RegisterRolePage = React.lazy(() => import("./pages/RegisterRolePage").then((m) => ({ default: m.RegisterRolePage })));
const FarmerRegisterPage = React.lazy(() => import("./pages/FarmerRegisterPage").then((m) => ({ default: m.FarmerRegisterPage })));
const BuyerRegisterPage = React.lazy(() => import("./pages/BuyerRegisterPage").then((m) => ({ default: m.BuyerRegisterPage })));
const TransporterRegisterPage = React.lazy(() => import("./pages/TransporterRegisterPage").then((m) => ({ default: m.TransporterRegisterPage })));
const NotFoundPage = React.lazy(() => import("./pages/NotFoundPage").then((m) => ({ default: m.NotFoundPage })));
const ProtectedPlaceholderPage = React.lazy(() => import("./pages/ProtectedPlaceholderPage").then((m) => ({ default: m.ProtectedPlaceholderPage })));
const DashboardRedirectPage = React.lazy(() => import("./pages/DashboardRedirectPage").then((m) => ({ default: m.DashboardRedirectPage })));
const FarmerDashboardPage = React.lazy(() => import("./pages/FarmerDashboardPage").then((m) => ({ default: m.FarmerDashboardPage })));
const BuyerDashboardPage = React.lazy(() => import("./pages/BuyerDashboardPage").then((m) => ({ default: m.BuyerDashboardPage })));
const TransporterDashboardPage = React.lazy(() => import("./pages/TransporterDashboardPage").then((m) => ({ default: m.TransporterDashboardPage })));
const TransporterDiscoveryPage = React.lazy(() => import("./pages/TransporterDiscoveryPage").then((m) => ({ default: m.TransporterDiscoveryPage })));
const VerificationPage = React.lazy(() => import("./pages/VerificationPage").then((m) => ({ default: m.VerificationPage })));
const ProfilePage = React.lazy(() => import("./pages/ProfilePage").then((m) => ({ default: m.ProfilePage })));
const FarmerListingsPage = React.lazy(() => import("./pages/FarmerListingsPage").then((m) => ({ default: m.FarmerListingsPage })));
const BuyerRequirementsPage = React.lazy(() => import("./pages/BuyerRequirementsPage").then((m) => ({ default: m.BuyerRequirementsPage })));
const MarketplacePage = React.lazy(() => import("./pages/MarketplacePage").then((m) => ({ default: m.MarketplacePage })));
const OffersPage = React.lazy(() => import("./pages/OffersPage").then((m) => ({ default: m.OffersPage })));
const OrdersPage = React.lazy(() => import("./pages/OrdersPage").then((m) => ({ default: m.OrdersPage })));
const MessagesPage = React.lazy(() => import("./pages/MessagesPage").then((m) => ({ default: m.MessagesPage })));
const AnalyticsDashboardPage = React.lazy(() => import("./pages/AnalyticsDashboardPage").then((m) => ({ default: m.AnalyticsDashboardPage })));
const UserReportsPage = React.lazy(() => import("./pages/UserReportsPage").then((m) => ({ default: m.UserReportsPage })));

// Admin Console Lazy Routes
const AdminPlatformAnalyticsPage = React.lazy(() => import("./pages/admin/AdminPlatformAnalyticsPage").then((m) => ({ default: m.AdminPlatformAnalyticsPage })));
const AdminUsersPage = React.lazy(() => import("./pages/admin/AdminUsersPage").then((m) => ({ default: m.AdminUsersPage })));
const AdminContentModerationPage = React.lazy(() => import("./pages/admin/AdminContentModerationPage").then((m) => ({ default: m.AdminContentModerationPage })));
const AdminVerificationQueuePage = React.lazy(() => import("./pages/admin/AdminVerificationQueuePage").then((m) => ({ default: m.AdminVerificationQueuePage })));
const AdminAuditLogsPage = React.lazy(() => import("./pages/admin/AdminAuditLogsPage").then((m) => ({ default: m.AdminAuditLogsPage })));

const PageLoadingFallback: React.FC = () => (
  <div
    className="flex-1 flex flex-col items-center justify-center min-h-[50vh] p-8"
    role="status"
    aria-live="polite"
  >
    <div className="w-8 h-8 border-4 border-primary-200 border-t-primary rounded-full animate-spin mb-4" />
    <p className="text-sm text-muted-foreground font-medium">Loading...</p>
  </div>
);

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
            <Suspense fallback={<PageLoadingFallback />}>
              <Routes>
                {/* Authenticated Dashboard Shell (Farmer, Buyer, Transporter) */}
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
                  <Route
                    path="transporter"
                    element={
                      <RequireRole allowedRoles={["transporter"]}>
                        <TransporterDashboardPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="transporters"
                    element={
                      <RequireRole allowedRoles={["farmer", "buyer"]}>
                        <TransporterDiscoveryPage />
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
                      <RequireRole allowedRoles={["farmer", "buyer", "transporter"]}>
                        <OrdersPage />
                      </RequireRole>
                    }
                  />
                  <Route
                    path="messages"
                    element={
                      <RequireRole allowedRoles={["farmer", "buyer", "transporter", "admin"]}>
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
                  <Route path="/verification" element={<Navigate to="/dashboard/verification" replace />} />
                  <Route path="/marketplace" element={<MarketplacePage />} />
                  <Route path="/transporters" element={<TransporterDiscoveryPage />} />
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
                    path="/register/transporter"
                    element={
                      <GuestOnly>
                        <TransporterRegisterPage />
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
            </Suspense>
          </BrowserRouter>
        </AppEventListeners>
      </ToastProvider>
    </ErrorBoundary>
  );
};

export default App;
