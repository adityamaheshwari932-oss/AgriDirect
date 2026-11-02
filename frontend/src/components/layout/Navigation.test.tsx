import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardLayout } from "./DashboardLayout";
import { authStore } from "../../store/authStore";
import { InMemoryTokenStorage, tokenStorage } from "../../api/tokenStorage";
import type { User } from "../../types";

const renderDashboard = (initialRoute = "/dashboard") => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <DashboardLayout />
    </MemoryRouter>
  );
};

describe("Role-Aware Responsive Dashboard Navigation", () => {
  const farmerUser: User = {
    id: "f-1",
    email: "farmer@greenacres.test",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-30T10:00:00Z",
    farmer_profile: {
      id: "fp-1",
      full_name: "Sarah Jenkins",
      farm_name: "Green Acres Farm",
      farm_location_address: "123 Farm Rd",
      city: "Salinas",
      state: "CA",
      postal_code: "93901",
      farm_size_acres: 40,
      farming_practices: "organic",
      primary_crops: "Lettuce",
      created_at: "2026-10-30T10:00:00Z",
      updated_at: "2026-10-30T10:00:00Z",
    },
  };

  const buyerUser: User = {
    id: "b-1",
    email: "buyer@freshdirect.test",
    role: "buyer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-30T10:00:00Z",
    buyer_profile: {
      id: "bp-1",
      contact_person_name: "Rahul Verma",
      business_name: "FreshDirect Wholesalers",
      business_type: "wholesaler",
      delivery_receiving_address: "Dock 1",
      city: "Mumbai",
      state: "MH",
      postal_code: "400001",
      procurement_summary: "Bulk produce",
      created_at: "2026-10-30T10:00:00Z",
      updated_at: "2026-10-30T10:00:00Z",
    },
  };

  const adminUser: User = {
    id: "a-1",
    email: "admin@agridirect.gov",
    role: "admin",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-30T10:00:00Z",
  };

  beforeEach(() => {
    tokenStorage.setProvider(new InMemoryTokenStorage());
    authStore.reset();
  });

  it("renders Farmer-specific navigation links and portal title", () => {
    authStore["state"] = {
      status: "authenticated",
      user: farmerUser,
      error: null,
    };

    renderDashboard("/dashboard/farmer");

    expect(screen.getByText("Farmer Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Producer Portal — Verification:")).toBeInTheDocument();

    // Verify presence of farmer navigation links
    expect(screen.getByRole("link", { name: /my listings/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /orders/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /messages/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /analytics/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /profile/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /verification/i })).toBeInTheDocument();

    // Ensure buyer/admin specific items are not in farmer navigation
    expect(screen.queryByRole("link", { name: /^marketplace$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /user moderation/i })).not.toBeInTheDocument();
  });

  it("renders Buyer-specific navigation links and portal title", () => {
    authStore["state"] = {
      status: "authenticated",
      user: buyerUser,
      error: null,
    };

    renderDashboard("/dashboard/buyer");

    expect(screen.getByText("Buyer Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Commercial Procurement Portal — Verification:")).toBeInTheDocument();

    // Verify presence of buyer navigation links
    expect(screen.getByRole("link", { name: /^marketplace$/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /requirements/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /orders/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /messages/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /analytics/i })).toBeInTheDocument();

    // Ensure farmer/admin specific items are not in buyer navigation
    expect(screen.queryByRole("link", { name: /my listings/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /user moderation/i })).not.toBeInTheDocument();
  });

  it("renders Administrator navigation links, admin console title, and admin badge", () => {
    authStore["state"] = {
      status: "authenticated",
      user: adminUser,
      error: null,
    };

    renderDashboard("/admin/users");

    expect(screen.getByText("Admin Console")).toBeInTheDocument();
    expect(
      screen.getByText(/platform governance portal — administrator console/i)
    ).toBeInTheDocument();

    // Admin links
    expect(screen.getByRole("link", { name: /user moderation/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /content moderation/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /verification queue/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /audit logs/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /platform analytics/i })).toBeInTheDocument();

    // Admin badge
    expect(screen.getAllByText("Admin").length).toBeGreaterThanOrEqual(1);
  });

  it("displays persistent warning banner when account status is restricted", () => {
    authStore["state"] = {
      status: "authenticated",
      user: { ...farmerUser, account_status: "restricted" },
      error: null,
    };

    renderDashboard();

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/account restricted:/i)).toBeInTheDocument();
    expect(
      screen.getByText(/your account is currently in read-only mode/i)
    ).toBeInTheDocument();
  });

  it("displays persistent warning banner when account status is suspended", () => {
    authStore["state"] = {
      status: "authenticated",
      user: { ...buyerUser, account_status: "suspended" },
      error: null,
    };

    renderDashboard();

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/account suspended:/i)).toBeInTheDocument();
  });

  it("toggles mobile menu drawer on hamburger click", () => {
    authStore["state"] = {
      status: "authenticated",
      user: farmerUser,
      error: null,
    };

    renderDashboard();

    const menuToggle = screen.getByLabelText("Open navigation menu");
    expect(menuToggle).toBeInTheDocument();
    expect(menuToggle).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(menuToggle);

    expect(screen.getByLabelText("Close navigation menu")).toHaveAttribute(
      "aria-expanded",
      "true"
    );
    expect(screen.getByLabelText("Mobile Dashboard Navigation")).toBeInTheDocument();
  });

  it("triggers logout when sign out button is clicked", () => {
    const logoutSpy = vi.spyOn(authStore, "logout");
    authStore["state"] = {
      status: "authenticated",
      user: farmerUser,
      error: null,
    };

    renderDashboard();

    const signOutBtn = screen.getByRole("button", { name: /sign out of agridirect/i });
    fireEvent.click(signOutBtn);

    expect(logoutSpy).toHaveBeenCalledTimes(1);
  });
});
