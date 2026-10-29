import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { FarmerDashboardPage } from "./FarmerDashboardPage";
import { authStore } from "../store/authStore";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { User } from "../types";

describe("FarmerDashboardPage", () => {
  const completeFarmer: User = {
    id: "farmer-uuid-1",
    email: "farmer@greenacres.test",
    phone_number: "+15551234567",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    farmer_profile: {
      id: "f-prof-1",
      full_name: "Sarah Jenkins",
      farm_name: "Green Acres Organic Farm",
      farm_location_address: "123 Valley Road",
      city: "Salinas",
      state: "CA",
      postal_code: "93901",
      farm_size_acres: 45.5,
      farming_practices: "organic",
      primary_crops: "Organic Heirloom Tomatoes, Basil",
      bio: "Generational family farm specializing in high-flavor produce.",
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
    },
  };

  const minimalFarmer: User = {
    id: "farmer-uuid-2",
    email: "newfarmer@agri.test",
    role: "farmer",
    verification_status: "unverified",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    farmer_profile: {
      id: "f-prof-2",
      full_name: "John Doe",
      farm_name: "",
      farm_location_address: "",
      city: "",
      state: "",
      postal_code: "",
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
    },
  };

  beforeEach(() => {
    tokenStorage.setProvider(new InMemoryTokenStorage());
    authStore.reset();
  });

  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <FarmerDashboardPage />
      </MemoryRouter>
    );
  };

  it("renders welcome banner with farmer name and producer portal branding", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeFarmer,
      error: null,
    };

    renderComponent();

    expect(
      screen.getByRole("heading", { name: /welcome back, sarah jenkins/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/agricultural producer portal/i)).toBeInTheDocument();
  });

  it("renders farm details and contact attributes accurately from backend", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeFarmer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Green Acres Organic Farm")).toBeInTheDocument();
    expect(screen.getByText("45.5 Acres")).toBeInTheDocument();
    expect(screen.getByText("Organic Heirloom Tomatoes, Basil")).toBeInTheDocument();
    expect(screen.getByText("organic")).toBeInTheDocument();
    expect(screen.getByText("Salinas, CA, 93901")).toBeInTheDocument();
    expect(screen.getByText("+15551234567")).toBeInTheDocument();
    expect(screen.getByText("farmer@greenacres.test")).toBeInTheDocument();
  });

  it("displays verified status banner and description", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeFarmer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Account Verification Status")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(
      screen.getByText(/your farm credentials are verified/i)
    ).toBeInTheDocument();
  });

  it("displays unverified status and guidance when account is not yet verified", () => {
    authStore["state"] = {
      status: "authenticated",
      user: minimalFarmer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Not Verified")).toBeInTheDocument();
    expect(
      screen.getByText(/verified identity unlocks bulk produce listings/i)
    ).toBeInTheDocument();
  });

  it("handles missing optional farm fields gracefully with placeholders", () => {
    authStore["state"] = {
      status: "authenticated",
      user: minimalFarmer,
      error: null,
    };

    renderComponent();

    // Missing farm name, acreage, crops show graceful fallbacks
    expect(screen.getAllByText(/not specified/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/no crops specified/i)).toBeInTheDocument();
    expect(screen.getByText(/no phone added/i)).toBeInTheDocument();
  });

  it("calculates and displays profile completion percentage", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeFarmer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Profile Completion")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("displays missing attribute recommendations for partial profiles", () => {
    authStore["state"] = {
      status: "authenticated",
      user: minimalFarmer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Profile Completion")).toBeInTheDocument();
    expect(screen.getByText(/recommended additions:/i)).toBeInTheDocument();
  });

  it("contains working navigation links to profile and verification pages", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeFarmer,
      error: null,
    };

    renderComponent();

    const profileLinks = screen.getAllByRole("link", { name: /profile/i });
    expect(profileLinks.length).toBeGreaterThan(0);
    expect(profileLinks[0]).toHaveAttribute("href", "/dashboard/profile");

    const verificationLinks = screen.getAllByRole("link", { name: /verification/i });
    expect(verificationLinks.length).toBeGreaterThan(0);
    expect(verificationLinks[0]).toHaveAttribute("href", "/dashboard/verification");
  });

  it("does not render fake statistics, sample orders, or fabricated revenue", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeFarmer,
      error: null,
    };

    renderComponent();

    expect(screen.queryByText(/total sales/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/revenue/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/orders completed/i)).not.toBeInTheDocument();
  });
});
