import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { DashboardLayout } from "../components/layout";
import { RequireAuth, RequireRole } from "../components/guards";
import {
  DashboardRedirectPage,
  FarmerDashboardPage,
  BuyerDashboardPage,
  ProfilePage,
  VerificationPage,
} from "../pages";
import { authStore } from "../store/authStore";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { User } from "../types";

const renderDashboardWithRouter = (initialRoute: string) => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route path="/login" element={<div>Sign In Page</div>} />
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
      </Routes>
    </MemoryRouter>
  );
};

describe("Dashboard Routing and Role-Based Route Guards", () => {
  const mockFarmerUser: User = {
    id: "farmer-uuid-1",
    email: "farmer@greenacres.test",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    farmer_profile: {
      id: "f-prof-1",
      full_name: "Sarah Jenkins",
      farm_name: "Green Acres Farm",
      farm_location_address: "123 Valley Road",
      city: "Salinas",
      state: "CA",
      postal_code: "93901",
      farm_size_acres: 50,
      farming_practices: "organic",
      primary_crops: "Tomatoes, Lettuce",
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
    },
  };

  const mockBuyerUser: User = {
    id: "buyer-uuid-2",
    email: "buyer@grandhotel.test",
    role: "buyer",
    verification_status: "pending",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    buyer_profile: {
      id: "b-prof-1",
      contact_person_name: "Rahul Verma",
      business_name: "Grand Hotel & Suites",
      business_type: "hotel",
      business_registration_number: "27AAAAA0000A1Z5",
      delivery_receiving_address: "Dock 3, Central Kitchen",
      city: "Mumbai",
      state: "Maharashtra",
      postal_code: "400001",
      procurement_summary: "Weekly bulk organic produce",
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
    },
  };

  beforeEach(() => {
    tokenStorage.setProvider(new InMemoryTokenStorage());
    authStore.reset();
  });

  it("redirects unauthenticated user from /dashboard to /login", () => {
    authStore.logout(); // Unauthenticated state
    renderDashboardWithRouter("/dashboard");

    expect(screen.getByText("Sign In Page")).toBeInTheDocument();
  });

  it("redirects authenticated farmer from /dashboard to /dashboard/farmer", () => {
    authStore.setUser(mockFarmerUser);
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    renderDashboardWithRouter("/dashboard");

    expect(screen.getByText(/welcome back, sarah jenkins/i)).toBeInTheDocument();
    expect(screen.getAllByText(/producer portal/i).length).toBeGreaterThanOrEqual(1);
  });

  it("redirects authenticated buyer from /dashboard to /dashboard/buyer", () => {
    authStore.setUser(mockBuyerUser);
    authStore["state"] = {
      status: "authenticated",
      user: mockBuyerUser,
      error: null,
    };

    renderDashboardWithRouter("/dashboard");

    expect(screen.getByText(/welcome back, rahul verma/i)).toBeInTheDocument();
    expect(screen.getAllByText(/commercial procurement portal/i).length).toBeGreaterThanOrEqual(1);
  });

  it("allows farmer to directly access /dashboard/farmer", () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    renderDashboardWithRouter("/dashboard/farmer");

    expect(screen.getByText(/farm & producer overview/i)).toBeInTheDocument();
    expect(screen.getAllByText("Green Acres Farm").length).toBeGreaterThanOrEqual(1);
  });

  it("prevents farmer from accessing buyer-only /dashboard/buyer and redirects to farmer dashboard", () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    renderDashboardWithRouter("/dashboard/buyer");

    // Blocked and redirected to their own farmer dashboard
    expect(screen.getByText(/welcome back, sarah jenkins/i)).toBeInTheDocument();
    expect(screen.queryByText(/commercial procurement portal/i)).not.toBeInTheDocument();
  });

  it("prevents buyer from accessing farmer-only /dashboard/farmer and redirects to buyer dashboard", () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockBuyerUser,
      error: null,
    };

    renderDashboardWithRouter("/dashboard/farmer");

    // Blocked and redirected to their own buyer dashboard
    expect(screen.getByText(/welcome back, rahul verma/i)).toBeInTheDocument();
    expect(screen.queryByText(/producer portal/i)).not.toBeInTheDocument();
  });

  it("allows farmer to access /dashboard/profile", () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    renderDashboardWithRouter("/dashboard/profile");

    expect(screen.getByText(/account & commercial profile/i)).toBeInTheDocument();
    expect(screen.getByText(/producer & farm information/i)).toBeInTheDocument();
  });

  it("allows buyer to access /dashboard/profile", () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockBuyerUser,
      error: null,
    };

    renderDashboardWithRouter("/dashboard/profile");

    expect(screen.getByText(/account & commercial profile/i)).toBeInTheDocument();
    expect(screen.getByText(/commercial entity information/i)).toBeInTheDocument();
  });

  it("allows authenticated user to access /dashboard/verification", () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    renderDashboardWithRouter("/dashboard/verification");

    expect(screen.getByRole("heading", { name: /^account verification$/i })).toBeInTheDocument();
    expect(screen.getByText(/producer verification requirements/i)).toBeInTheDocument();
  });
});
