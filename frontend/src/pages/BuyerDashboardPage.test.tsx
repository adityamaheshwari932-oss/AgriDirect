import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { BuyerDashboardPage } from "./BuyerDashboardPage";
import { authStore } from "../store/authStore";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { User } from "../types";

describe("BuyerDashboardPage", () => {
  const completeBuyer: User = {
    id: "buyer-uuid-1",
    email: "procurement@grandhotel.test",
    phone_number: "+91 22 1234 5678",
    role: "buyer",
    verification_status: "pending",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    buyer_profile: {
      id: "b-prof-1",
      contact_person_name: "Rahul Verma",
      business_name: "Grand Hotel & Dining Group",
      business_type: "hotel",
      business_registration_number: "27AAAAA0000A1Z5",
      delivery_receiving_address: "Dock 4, Central Commissary Kitchen",
      city: "Mumbai",
      state: "Maharashtra",
      postal_code: "400001",
      procurement_summary: "Bulk weekly supply of organic potatoes, onions, and seasonal berries.",
      bio: "Five-star hospitality enterprise procuring locally sourced organic produce.",
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
    },
  };

  const minimalBuyer: User = {
    id: "buyer-uuid-2",
    email: "newbuyer@retail.test",
    role: "buyer",
    verification_status: "unverified",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    buyer_profile: {
      id: "b-prof-2",
      contact_person_name: "Anita Sharma",
      business_name: "",
      business_type: "restaurant",
      delivery_receiving_address: "",
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
        <BuyerDashboardPage />
      </MemoryRouter>
    );
  };

  it("renders welcome banner with contact person name and commercial procurement portal branding", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeBuyer,
      error: null,
    };

    renderComponent();

    expect(
      screen.getByRole("heading", { name: /welcome back, rahul verma/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/commercial procurement portal/i)).toBeInTheDocument();
  });

  it("renders business entity details and contact attributes accurately from backend", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeBuyer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Grand Hotel & Dining Group")).toBeInTheDocument();
    expect(screen.getByText("Hotel / Hospitality")).toBeInTheDocument();
    expect(screen.getByText("27AAAAA0000A1Z5")).toBeInTheDocument();
    expect(screen.getByText("Dock 4, Central Commissary Kitchen")).toBeInTheDocument();
    expect(screen.getByText("Mumbai, Maharashtra, 400001")).toBeInTheDocument();
    expect(screen.getByText("+91 22 1234 5678")).toBeInTheDocument();
    expect(screen.getByText("procurement@grandhotel.test")).toBeInTheDocument();
    expect(
      screen.getByText(/bulk weekly supply of organic potatoes/i)
    ).toBeInTheDocument();
  });

  it("displays pending review status card when verification is submitted", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeBuyer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Account Verification Status")).toBeInTheDocument();
    expect(screen.getByText("Pending Review")).toBeInTheDocument();
    expect(
      screen.getByText(/business registration and tax identification/i)
    ).toBeInTheDocument();
  });

  it("displays unverified status card for unverified buyer accounts", () => {
    authStore["state"] = {
      status: "authenticated",
      user: minimalBuyer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Not Verified")).toBeInTheDocument();
    expect(
      screen.getByText(/commercial verification is required before initiating supplier negotiations/i)
    ).toBeInTheDocument();
  });

  it("handles missing optional business fields gracefully with placeholders", () => {
    authStore["state"] = {
      status: "authenticated",
      user: minimalBuyer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText(/not provided/i)).toBeInTheDocument();
    expect(screen.getByText(/no receiving dock specified/i)).toBeInTheDocument();
    expect(screen.getByText(/no phone added/i)).toBeInTheDocument();
  });

  it("calculates and displays profile completion percentage", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeBuyer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Profile Completion")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("displays missing recommendations for partial buyer profile", () => {
    authStore["state"] = {
      status: "authenticated",
      user: minimalBuyer,
      error: null,
    };

    renderComponent();

    expect(screen.getByText("Profile Completion")).toBeInTheDocument();
    expect(screen.getByText(/recommended additions:/i)).toBeInTheDocument();
  });

  it("contains working navigation links to profile and verification portals", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeBuyer,
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

  it("does not render fake procurement statistics or sample orders", () => {
    authStore["state"] = {
      status: "authenticated",
      user: completeBuyer,
      error: null,
    };

    renderComponent();

    expect(screen.queryByText(/total spend/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/active inquiries/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/fictional orders/i)).not.toBeInTheDocument();
  });
});
