import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { DashboardLayout } from "./DashboardLayout";
import { authStore } from "../../store/authStore";
import type { User } from "../../types";

describe("DashboardLayout — D-1 Tablet Header Overflow Regression Tests", () => {
  const mockFarmer: User = {
    id: "farmer-1",
    email: "ramesh@patelfarms.in",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    farmer_profile: {
      id: "fp-1",
      full_name: "Ramesh Patel",
      farm_name: "Patel Organic Farms",
      farm_location_address: "Village Narsinghpur",
      city: "Narsinghpur",
      state: "Madhya Pradesh",
      postal_code: "487001",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  };

  beforeEach(() => {
    authStore.reset();
    authStore.setUser(mockFarmer);
  });

  const renderDashboard = () =>
    render(
      <MemoryRouter initialEntries={["/dashboard/farmer"]}>
        <Routes>
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route path="farmer" element={<div>Farmer Home Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

  it("applies hidden lg:flex to desktop controls to prevent duplicate controls on tablet (640px-1023px)", () => {
    renderDashboard();

    // Verify desktop user info wrapper has 'hidden lg:flex' and NOT 'hidden sm:flex'
    const desktopSignOutBtn = screen.getByRole("button", {
      name: /Sign out of AgriDirect/i,
    });
    const desktopUserControls = desktopSignOutBtn.closest("div.items-center");

    expect(desktopUserControls).not.toBeNull();
    expect(desktopUserControls?.className).toContain("hidden");
    expect(desktopUserControls?.className).toContain("lg:flex");
    expect(desktopUserControls?.className).not.toContain("sm:flex");
  });

  it("applies hidden lg:flex to desktop navigation links", () => {
    renderDashboard();

    const desktopNav = screen.getByLabelText("Dashboard Navigation");
    expect(desktopNav).toBeInTheDocument();
    expect(desktopNav.className).toContain("hidden");
    expect(desktopNav.className).toContain("lg:flex");
  });

  it("applies flex lg:hidden to mobile hamburger controls", () => {
    renderDashboard();

    const mobileMenuButton = screen.getByRole("button", {
      name: /Open navigation menu/i,
    });
    const mobileControls = mobileMenuButton.closest("div.items-center");

    expect(mobileControls).not.toBeNull();
    expect(mobileControls?.className).toContain("flex");
    expect(mobileControls?.className).toContain("lg:hidden");
  });

  it("opens and closes mobile navigation drawer via hamburger button", () => {
    renderDashboard();

    const mobileMenuButton = screen.getByRole("button", {
      name: /Open navigation menu/i,
    });

    // Drawer is closed initially
    expect(
      screen.queryByLabelText("Mobile Dashboard Navigation")
    ).not.toBeInTheDocument();

    // Open drawer
    fireEvent.click(mobileMenuButton);
    expect(
      screen.getByLabelText("Mobile Dashboard Navigation")
    ).toBeInTheDocument();

    // Close drawer
    const closeButton = screen.getByRole("button", {
      name: /Close navigation menu/i,
    });
    fireEvent.click(closeButton);
    expect(
      screen.queryByLabelText("Mobile Dashboard Navigation")
    ).not.toBeInTheDocument();
  });
});
