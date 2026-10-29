import React, { useEffect } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout, DashboardLayout } from "./components/layout";
import { GuestOnly, RequireAuth, RequireRole } from "./components/guards";
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
} from "./pages";
import { useAuth } from "./store/authStore";

export const App: React.FC = () => {
  const { restoreSession } = useAuth();

  useEffect(() => {
    // Attempt session restoration once on application mount
    void restoreSession();
  }, [restoreSession]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Authenticated Dashboard Shell */}
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
          <Route path="profile" element={<ProfilePage />} />
          <Route path="verification" element={<VerificationPage />} />
        </Route>

        {/* Public & Authentication Shell */}
        <Route element={<AppLayout />}>
          <Route path="/" element={<LandingPage />} />
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
  );
};

export default App;
