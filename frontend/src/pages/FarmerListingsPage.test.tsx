import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FarmerListingsPage } from "./FarmerListingsPage";
import { authStore } from "../store/authStore";
import { listingsApi } from "../api/listings";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { ProduceCategory, ProduceListingDetail, User } from "../types";

describe("FarmerListingsPage", () => {
  const verifiedFarmerUser: User = {
    id: "farmer-1",
    email: "ramesh@patelfarms.test",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-30T10:00:00Z",
    farmer_profile: {
      id: "fp-1",
      full_name: "Ramesh Patel",
      farm_name: "Patel Organic Farms",
      farm_location_address: "Survey 42",
      city: "Nashik",
      state: "Maharashtra",
      postal_code: "422004",
      farm_size_acres: 25,
      farming_practices: "organic",
      primary_crops: "Grapes, Wheat",
      created_at: "2026-10-30T10:00:00Z",
      updated_at: "2026-10-30T10:00:00Z",
    },
  };

  const unverifiedFarmerUser: User = {
    ...verifiedFarmerUser,
    id: "farmer-2",
    verification_status: "unverified",
  };

  const mockCategories: ProduceCategory[] = [
    { id: "cat-1", name: "Grains & Cereals", slug: "grains", is_active: true },
    { id: "cat-2", name: "Fruits & Orchards", slug: "fruits", is_active: true },
  ];

  const mockListings: ProduceListingDetail[] = [
    {
      id: "listing-1",
      farmer_id: "farmer-1",
      category_id: "cat-1",
      category: mockCategories[0],
      product_name: "Sharbati Wheat",
      title: "Certified Organic Sharbati Wheat Lot 1",
      description: "Sun-dried farm harvest with moisture < 12%",
      initial_quantity: 50,
      available_quantity: 45,
      unit: "quintal",
      price_per_unit: 2600,
      quality_grade: "Grade A",
      location_state: "Maharashtra",
      location_city: "Nashik",
      harvest_date: "2026-10-15",
      available_from: "2026-10-20",
      expires_at: "2026-11-20T00:00:00Z",
      status: "active",
      is_deleted: false,
      created_at: "2026-10-20T10:00:00Z",
      updated_at: "2026-10-20T10:00:00Z",
      images: [],
    },
    {
      id: "listing-2",
      farmer_id: "farmer-1",
      category_id: "cat-2",
      category: mockCategories[1],
      product_name: "Thompson Seedless Grapes",
      title: "Export Quality Table Grapes",
      description: "Cold-chain packed table grapes",
      initial_quantity: 200,
      available_quantity: 200,
      unit: "crate",
      price_per_unit: 1100,
      quality_grade: "Export Quality",
      location_state: "Maharashtra",
      location_city: "Nashik",
      harvest_date: "2026-10-25",
      available_from: "2026-10-28",
      expires_at: "2026-11-28T00:00:00Z",
      status: "draft",
      is_deleted: false,
      created_at: "2026-10-25T10:00:00Z",
      updated_at: "2026-10-25T10:00:00Z",
      images: [],
    },
  ];

  beforeEach(() => {
    tokenStorage.setProvider(new InMemoryTokenStorage());
    authStore.reset();
    vi.restoreAllMocks();

    vi.spyOn(listingsApi, "getCategories").mockResolvedValue(mockCategories);
  });

  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <FarmerListingsPage />
      </MemoryRouter>
    );
  };

  it("renders page header and farmer listings list", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: verifiedFarmerUser,
      error: null,
    };

    vi.spyOn(listingsApi, "getMyListings").mockResolvedValueOnce({
      items: mockListings,
      total: 2,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    renderComponent();

    expect(screen.getByRole("heading", { name: /my produce listings/i })).toBeInTheDocument();

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("Sharbati Wheat")).toBeInTheDocument();
      expect(within(table).getByText("Thompson Seedless Grapes")).toBeInTheDocument();
    });

    const table = screen.getByRole("table");
    expect(within(table).getByText(/45 quintal/i)).toBeInTheDocument();
    expect(within(table).getByText(/₹2,600/i)).toBeInTheDocument();
    expect(within(table).getByText("Active Lot")).toBeInTheDocument();
    expect(within(table).getByText("Draft")).toBeInTheDocument();
  });

  it("renders verification warning banner for unverified farmers", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: unverifiedFarmerUser,
      error: null,
    };

    vi.spyOn(listingsApi, "getMyListings").mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/producer verification incomplete/i)).toBeInTheDocument();
    });

    expect(screen.getByRole("link", { name: /complete verification/i })).toBeInTheDocument();
  });

  it("filters listings by status tab", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: verifiedFarmerUser,
      error: null,
    };

    const getListingsSpy = vi.spyOn(listingsApi, "getMyListings").mockResolvedValue({
      items: [mockListings[1]],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    renderComponent();

    await waitFor(() => {
      expect(getListingsSpy).toHaveBeenCalled();
    });

    const draftsTab = screen.getByRole("button", { name: /^drafts$/i });
    fireEvent.click(draftsTab);

    await waitFor(() => {
      expect(getListingsSpy).toHaveBeenCalledWith(
        expect.objectContaining({ status: "draft" })
      );
    });
  });

  it("toggles status from draft to active", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: verifiedFarmerUser,
      error: null,
    };

    vi.spyOn(listingsApi, "getMyListings").mockResolvedValueOnce({
      items: [mockListings[1]],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    const updateStatusSpy = vi.spyOn(listingsApi, "updateStatus").mockResolvedValueOnce({
      ...mockListings[1],
      status: "active",
    });

    renderComponent();

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("Thompson Seedless Grapes")).toBeInTheDocument();
    });

    const table = screen.getByRole("table");
    const publishBtn = within(table).getByRole("button", { name: /publish/i });
    fireEvent.click(publishBtn);

    await waitFor(() => {
      expect(updateStatusSpy).toHaveBeenCalledWith("listing-2", { status: "active" });
    });
  });

  it("opens delete modal and confirms removal", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: verifiedFarmerUser,
      error: null,
    };

    vi.spyOn(listingsApi, "getMyListings").mockResolvedValue({
      items: [mockListings[0]],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    const deleteSpy = vi.spyOn(listingsApi, "deleteListing").mockResolvedValueOnce(undefined);

    renderComponent();

    await waitFor(() => {
      const table = screen.getByRole("table");
      expect(within(table).getByText("Sharbati Wheat")).toBeInTheDocument();
    });

    const table = screen.getByRole("table");
    const deleteBtn = within(table).getByRole("button", { name: /delete certified organic sharbati wheat lot 1/i });
    fireEvent.click(deleteBtn);

    const dialog = screen.getByRole("dialog", { name: /remove produce listing/i });
    expect(dialog).toBeInTheDocument();

    const confirmBtn = within(dialog).getByRole("button", { name: /confirm removal/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith("listing-1");
    });
  });

  it("renders empty state when no produce listings exist", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: verifiedFarmerUser,
      error: null,
    };

    vi.spyOn(listingsApi, "getMyListings").mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("No produce listings yet")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /create first listing/i })).toBeInTheDocument();
  });
});