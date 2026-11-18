import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TransporterDashboardPage } from "./TransporterDashboardPage";
import { authStore } from "../store/authStore";
import { transportersApi } from "../api/transporters";
import type { TransporterDetail, User } from "../types";

describe("TransporterDashboardPage", () => {
  const mockTransporterUser: User = {
    id: "user-transporter-1",
    email: "transporter@test.com",
    role: "transporter",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-11-18T10:00:00Z",
    updated_at: "2026-11-18T10:00:00Z",
  };

  const mockDetail: TransporterDetail = {
    id: "transporter-prof-1",
    business_name: "Sahyadri Agro Haulage",
    contact_name: "Santosh Shinde",
    phone_number: "+919876500000",
    transport_type: "refrigerated",
    vehicle_capacity_kg: 5000,
    vehicle_registration_number: "MH-14-GH-1212",
    is_available: true,
    experience_years: 6,
    operating_states: "Maharashtra, Goa",
    bio: "Refrigerated transport for perishable vegetables.",
    created_at: "2026-11-18T10:00:00Z",
    updated_at: "2026-11-18T10:00:00Z",
    service_areas: [
      {
        id: "area-1",
        transporter_profile_id: "transporter-prof-1",
        state: "Maharashtra",
        district: "Nashik",
        taluka_subdistrict: "Niphad",
        pincode: "422303",
        coverage_type: "both",
        is_active: true,
        created_at: "2026-11-18T10:00:00Z",
        updated_at: "2026-11-18T10:00:00Z",
      },
    ],
  };

  beforeEach(() => {
    authStore.reset();
    vi.restoreAllMocks();
  });

  it("renders restricted message when user is not a transporter", () => {
    authStore.setUser({ ...mockTransporterUser, role: "farmer" });
    render(
      <MemoryRouter>
        <TransporterDashboardPage />
      </MemoryRouter>
    );
    expect(screen.getByText(/Access restricted to registered transportation providers/i)).toBeInTheDocument();
  });

  it("loads and displays transporter profile and declared service areas", async () => {
    authStore.setUser(mockTransporterUser);
    vi.spyOn(transportersApi, "getMyProfile").mockResolvedValueOnce(mockDetail);

    render(
      <MemoryRouter>
        <TransporterDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Sahyadri Agro Haulage")).toBeInTheDocument();
      expect(screen.getByText(/Santosh Shinde/i)).toBeInTheDocument();
      expect(screen.getByText(/5,000 kg Payload/i)).toBeInTheDocument();
      expect(screen.getByText(/Available for Loads/i)).toBeInTheDocument();
      expect(screen.getByText(/Maharashtra • Nashik/i)).toBeInTheDocument();
    });
  });

  it("toggles fleet availability status", async () => {
    authStore.setUser(mockTransporterUser);
    vi.spyOn(transportersApi, "getMyProfile").mockResolvedValueOnce(mockDetail);
    vi.spyOn(transportersApi, "updateMyProfile").mockResolvedValueOnce({
      ...mockDetail,
      is_available: false,
    });

    render(
      <MemoryRouter>
        <TransporterDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Available for Loads/i)).toBeInTheDocument();
    });

    const toggleBtn = screen.getByText(/Available for Loads/i);
    fireEvent.click(toggleBtn);

    await waitFor(() => {
      expect(transportersApi.updateMyProfile).toHaveBeenCalledWith({ is_available: false });
    });
  });
});
