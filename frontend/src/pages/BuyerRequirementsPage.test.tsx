import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BuyerRequirementsPage } from "./BuyerRequirementsPage";
import { authStore } from "../store/authStore";
import { requirementsApi } from "../api/requirements";
import { listingsApi } from "../api/listings";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { BuyerRequirementDetail, ProduceCategory, User } from "../types";

describe("BuyerRequirementsPage", () => {
  const verifiedBuyerUser: User = {
    id: "buyer-1",
    email: "procurement@tajdining.test",
    role: "buyer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-10-30T10:00:00Z",
    updated_at: "2026-10-30T10:00:00Z",
    buyer_profile: {
      id: "bp-1",
      contact_person_name: "Pooja Mehta",
      business_name: "Taj Dining Enterprises",
      business_type: "restaurant",
      delivery_receiving_address: "Central Receiving Dock",
      city: "Mumbai",
      state: "Maharashtra",
      postal_code: "400001",
      procurement_summary: "High volume daily organic produce",
      created_at: "2026-10-30T10:00:00Z",
      updated_at: "2026-10-30T10:00:00Z",
    },
  };

  const unverifiedBuyerUser: User = {
    ...verifiedBuyerUser,
    id: "buyer-2",
    verification_status: "unverified",
  };

  const mockCategories: ProduceCategory[] = [
    { id: "cat-1", name: "Tubers & Root Vegetables", slug: "tubers", is_active: true },
    { id: "cat-2", name: "Grains & Cereals", slug: "grains", is_active: true },
  ];

  const mockRequirements: BuyerRequirementDetail[] = [
    {
      id: "req-1",
      buyer_id: "buyer-1",
      category_id: "cat-1",
      category: mockCategories[0],
      product_name: "Processing Potatoes",
      title: "Weekly Bulk Potatoes for Processing Kitchen",
      description: "Dry, clean, medium-sized tubers",
      required_quantity: 100,
      remaining_quantity: 80,
      unit: "quintal",
      target_price_per_unit: 1950,
      price_condition: "negotiable",
      quality_grade: "Grade A",
      destination_state: "Maharashtra",
      destination_city: "Mumbai",
      required_by_date: "2026-11-25",
      status: "active",
      is_deleted: false,
      created_at: "2026-10-25T10:00:00Z",
      updated_at: "2026-10-25T10:00:00Z",
    },
    {
      id: "req-2",
      buyer_id: "buyer-1",
      category_id: "cat-2",
      category: mockCategories[1],
      product_name: "Basmati Rice",
      title: "Aged 1121 Steam Basmati Rice",
      description: "Moisture < 12.5%, minimum grain length 8.35mm",
      required_quantity: 50,
      remaining_quantity: 50,
      unit: "bag",
      target_price_per_unit: 4200,
      price_condition: "exact",
      quality_grade: "Export Quality",
      destination_state: "Maharashtra",
      destination_city: "Mumbai",
      required_by_date: "2026-11-30",
      status: "draft",
      is_deleted: false,
      created_at: "2026-10-28T10:00:00Z",
      updated_at: "2026-10-28T10:00:00Z",
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
        <BuyerRequirementsPage />
      </MemoryRouter>
    );
  };

  it("renders page header and buyer requirements list", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: verifiedBuyerUser,
      error: null,
    };

    vi.spyOn(requirementsApi, "getMyRequirements").mockResolvedValueOnce({
      items: mockRequirements,
      total: 2,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    renderComponent();

    expect(screen.getByRole("heading", { name: /buyer requirements board/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText("Processing Potatoes")[0]).toBeInTheDocument();
      expect(screen.getAllByText("Basmati Rice")[0]).toBeInTheDocument();
    });

    expect(screen.getAllByText(/80 quintal remaining/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/Active Demand/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/Draft/i)[0]).toBeInTheDocument();
  });

  it("renders verification warning for unverified commercial buyers", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: unverifiedBuyerUser,
      error: null,
    };

    vi.spyOn(requirementsApi, "getMyRequirements").mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });

    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByText(/commercial buyer verification incomplete/i)
      ).toBeInTheDocument();
    });

    expect(screen.getByRole("link", { name: /complete verification/i })).toBeInTheDocument();
  });

  it("filters requirements by status tab", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: verifiedBuyerUser,
      error: null,
    };

    const getReqsSpy = vi.spyOn(requirementsApi, "getMyRequirements").mockResolvedValue({
      items: [mockRequirements[1]],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    renderComponent();

    await waitFor(() => {
      expect(getReqsSpy).toHaveBeenCalled();
    });

    const draftsTab = screen.getByRole("button", { name: /^drafts$/i });
    fireEvent.click(draftsTab);

    await waitFor(() => {
      expect(getReqsSpy).toHaveBeenCalledWith(
        expect.objectContaining({ status: "draft" })
      );
    });
  });

  it("toggles requirement status from draft to active", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: verifiedBuyerUser,
      error: null,
    };

    vi.spyOn(requirementsApi, "getMyRequirements").mockResolvedValueOnce({
      items: [mockRequirements[1]],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    const updateStatusSpy = vi.spyOn(requirementsApi, "updateStatus").mockResolvedValueOnce({
      ...mockRequirements[1],
      status: "active",
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getAllByText("Basmati Rice")[0]).toBeInTheDocument();
    });

    const publishBtn = screen.getAllByRole("button", { name: /publish/i })[0];
    fireEvent.click(publishBtn);

    await waitFor(() => {
      expect(updateStatusSpy).toHaveBeenCalledWith("req-2", { status: "active" });
    });
  });

  it("opens delete modal and confirms removal", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: verifiedBuyerUser,
      error: null,
    };

    vi.spyOn(requirementsApi, "getMyRequirements").mockResolvedValue({
      items: [mockRequirements[0]],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });

    const deleteSpy = vi.spyOn(requirementsApi, "deleteRequirement").mockResolvedValueOnce(undefined);

    renderComponent();

    await waitFor(() => {
      expect(screen.getAllByText("Processing Potatoes")[0]).toBeInTheDocument();
    });

    const deleteBtn = screen.getAllByRole("button", { name: /delete weekly bulk potatoes for processing kitchen/i })[0];
    fireEvent.click(deleteBtn);

    expect(screen.getByRole("dialog", { name: /remove procurement requirement/i })).toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: /confirm removal/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith("req-1");
    });
  });

  it("renders empty state when no requirements exist", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: verifiedBuyerUser,
      error: null,
    };

    vi.spyOn(requirementsApi, "getMyRequirements").mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("No procurement requirements yet")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /post first requirement/i })).toBeInTheDocument();
  });
});
