import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TransporterDiscoveryPage } from "./TransporterDiscoveryPage";
import { authStore } from "../store/authStore";
import { transportersApi } from "../api/transporters";
import type { TransporterSearchResult, User } from "../types";

describe("TransporterDiscoveryPage & Marketplace Integration", () => {
  const mockFarmerUser: User = {
    id: "farmer-user-1",
    email: "farmer@test.com",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-11-18T10:00:00Z",
    updated_at: "2026-11-18T10:00:00Z",
  };

  const mockTransporters: TransporterSearchResult[] = [
    {
      id: "tp-1",
      user_id: "transporter-user-1",
      business_name: "Deccan Express Logistics",
      contact_name: "Ramesh Pawar",
      phone_number: "+919876543210",
      transport_type: "open_truck",
      vehicle_capacity_kg: 8000,
      vehicle_registration_number: "MH-12-AB-1234",
      experience_years: 7,
      operating_states: "Maharashtra, Karnataka",
      bio: "Heavy agricultural freight specialist.",
      is_available: true,
      verification_status: "verified",
      service_areas: [
        {
          id: "sa-1",
          transporter_profile_id: "tp-1",
          state: "Maharashtra",
          district: "Pune",
          coverage_type: "both",
          is_active: true,
          created_at: "2026-11-20T00:00:00Z",
          updated_at: "2026-11-20T00:00:00Z",
        },
      ],
    },
    {
      id: "tp-2",
      user_id: "transporter-user-2",
      business_name: "ColdChain AgriTrans",
      contact_name: "Sunil Verma",
      phone_number: "+919876543211",
      transport_type: "refrigerated",
      vehicle_capacity_kg: 5000,
      vehicle_registration_number: "MH-14-CD-5678",
      experience_years: 5,
      operating_states: "Maharashtra, Gujarat",
      bio: "Temperature controlled produce carrier.",
      is_available: false,
      verification_status: "verified",
      service_areas: [],
    },
  ];

  beforeEach(() => {
    authStore.reset();
    authStore.setUser(mockFarmerUser);
    vi.restoreAllMocks();
  });

  it("renders page title and filters properly", async () => {
    vi.spyOn(transportersApi, "discoverTransporters").mockResolvedValueOnce({
      total: 2,
      items: mockTransporters,
    });

    render(
      <MemoryRouter>
        <TransporterDiscoveryPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Connected Transportation Marketplace/i)).toBeInTheDocument();
    const stateInputs = screen.getAllByPlaceholderText(/e.g. Maharashtra/i);
    expect(stateInputs.length).toBe(2);
    expect(screen.getByPlaceholderText(/e.g. Nashik/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Deccan Express Logistics")).toBeInTheDocument();
      expect(screen.getByText("ColdChain AgriTrans")).toBeInTheDocument();
    });
  });

  it("opens transporter detail modal with independent carrier disclaimer", async () => {
    vi.spyOn(transportersApi, "discoverTransporters").mockResolvedValueOnce({
      total: 2,
      items: mockTransporters,
    });

    render(
      <MemoryRouter>
        <TransporterDiscoveryPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Deccan Express Logistics")).toBeInTheDocument();
    });

    const viewDetailsButtons = screen.getAllByRole("button", { name: /View Details/i });
    fireEvent.click(viewDetailsButtons[0]);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText(/Independent Logistics Provider/i)).toBeInTheDocument();
      expect(screen.getByText(/AgriDirect facilitates discovery and coordination/i)).toBeInTheDocument();
      expect(screen.getByText(/MH-12-AB-1234/i)).toBeInTheDocument();
    });
  });

  it("opens transport connection modal and sends a request", async () => {
    vi.spyOn(transportersApi, "discoverTransporters").mockResolvedValueOnce({
      total: 2,
      items: mockTransporters,
    });

    const mockCreatedRequest = {
      id: "req-123",
      requester_id: mockFarmerUser.id,
      transporter_id: mockTransporters[0].id,
      requester_name: "Farmer John",
      requester_role: "farmer",
      transporter_business_name: mockTransporters[0].business_name,
      transporter_contact_name: mockTransporters[0].contact_name,
      transporter_phone: mockTransporters[0].phone_number,
      status: "pending" as const,
      pickup_state: "Maharashtra",
      pickup_district: "Pune",
      cargo_description: "100 quintals Sharbati wheat",
      weight_kg: 8000,
      created_at: "2026-11-23T12:00:00Z",
      updated_at: "2026-11-23T12:00:00Z",
    };

    const createSpy = vi.spyOn(transportersApi, "createConnectionRequest").mockResolvedValueOnce(mockCreatedRequest);

    render(
      <MemoryRouter>
        <TransporterDiscoveryPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Deccan Express Logistics")).toBeInTheDocument();
    });

    const requestButtons = screen.getAllByRole("button", { name: /Request Transport/i });
    fireEvent.click(requestButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Request Transportation Services/i)).toBeInTheDocument();
    });

    // Fill cargo description
    const cargoInput = screen.getByPlaceholderText(/e.g. 300 Crates Alphonso Mangoes/i);
    fireEvent.change(cargoInput, { target: { value: "100 quintals Sharbati wheat" } });

    // Submit request
    const submitButton = screen.getByRole("button", { name: /Send Transport Request/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          transporter_user_id: mockTransporters[0].user_id,
          cargo_description: "100 quintals Sharbati wheat",
        })
      );
      expect(screen.getByText(/Transport connection request successfully sent!/i)).toBeInTheDocument();
    });
  });

  it("pre-populates filters and deals context from query params", async () => {
    vi.spyOn(transportersApi, "discoverTransporters").mockResolvedValueOnce({
      total: 1,
      items: [mockTransporters[0]],
    });

    render(
      <MemoryRouter initialEntries={["/dashboard/transporters?pickup_state=Maharashtra&order_id=ord-999&weight_kg=8000"]}>
        <Routes>
          <Route path="/dashboard/transporters" element={<TransporterDiscoveryPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const inputs = screen.getAllByPlaceholderText(/e.g. Maharashtra/i) as HTMLInputElement[];
      expect(inputs[0].value).toBe("Maharashtra");
    });
  });
});
