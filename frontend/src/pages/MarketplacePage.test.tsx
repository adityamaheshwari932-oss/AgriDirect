import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MarketplacePage } from "./MarketplacePage";
import { listingsApi } from "../api/listings";
import { requirementsApi } from "../api/requirements";
import type {
  BuyerRequirementPublicSummary,
  ProduceCategory,
  ProduceListingPublicSummary,
} from "../types";

describe("MarketplacePage", () => {
  const mockCategories: ProduceCategory[] = [
    { id: "cat-1", name: "Grains & Cereals", slug: "grains", is_active: true },
    { id: "cat-2", name: "Tubers & Roots", slug: "tubers", is_active: true },
  ];

  const mockProduce: ProduceListingPublicSummary[] = [
    {
      id: "prod-1",
      category_id: "cat-1",
      category_name: "Grains & Cereals",
      product_name: "Sharbati Wheat",
      title: "Clean Harvested Sharbati Wheat",
      description: "Moisture < 12%",
      available_quantity: 40,
      unit: "quintal",
      price_per_unit: 2750,
      quality_grade: "Grade A",
      location_state: "Madhya Pradesh",
      location_city: "Sehore",
      available_from: "2026-10-25",
      expires_at: "2026-11-25T00:00:00Z",
      status: "active",
      created_at: "2026-10-25T10:00:00Z",
      farmer: {
        id: "farmer-1",
        full_name: "Shivraj Singh",
        farm_name: "Narmada Valley Farms",
        city: "Sehore",
        state: "Madhya Pradesh",
      },
    },
  ];

  const mockRequirements: BuyerRequirementPublicSummary[] = [
    {
      id: "req-1",
      category_id: "cat-2",
      category_name: "Tubers & Roots",
      product_name: "Industrial Potatoes",
      title: "Bulk Potatoes for Crisp Processing",
      description: "Clean sorted tubers",
      required_quantity: 150,
      remaining_quantity: 120,
      unit: "quintal",
      target_price_per_unit: 1800,
      price_condition: "negotiable",
      quality_grade: "Grade A",
      destination_state: "Gujarat",
      destination_city: "Ahmedabad",
      required_by_date: "2026-11-28",
      status: "active",
      created_at: "2026-10-28T10:00:00Z",
      buyer: {
        id: "buyer-1",
        contact_person_name: "Amit Shah",
        business_name: "Gujarat Agro Snacks Ltd",
        business_type: "food_processor",
        city: "Ahmedabad",
        state: "Gujarat",
      },
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(listingsApi, "getCategories").mockResolvedValue(mockCategories);
  });

  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <MarketplacePage />
      </MemoryRouter>
    );
  };

  it("renders dual tabs and defaults to 'Find Produce' discovery view", async () => {
    const searchProduceSpy = vi.spyOn(listingsApi, "searchMarketplace").mockResolvedValueOnce({
      items: mockProduce,
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });

    renderComponent();

    expect(screen.getByRole("heading", { name: /agridirect wholesale marketplace/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /find produce/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /find buyers/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(searchProduceSpy).toHaveBeenCalled();
      expect(screen.getByText("Sharbati Wheat")).toBeInTheDocument();
    });

    expect(screen.getByText("40")).toBeInTheDocument();
    expect(screen.getByText("quintal")).toBeInTheDocument();
    expect(screen.getByText(/₹2,750/i)).toBeInTheDocument();
  });

  it("switches to 'Find Buyers' tab and renders buyer requirements", async () => {
    vi.spyOn(listingsApi, "searchMarketplace").mockResolvedValueOnce({
      items: mockProduce,
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });

    const searchReqSpy = vi.spyOn(requirementsApi, "searchMarketplace").mockResolvedValueOnce({
      items: mockRequirements,
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Sharbati Wheat")).toBeInTheDocument();
    });

    const buyersTab = screen.getByRole("tab", { name: /find buyers/i });
    fireEvent.click(buyersTab);

    await waitFor(() => {
      expect(searchReqSpy).toHaveBeenCalled();
      expect(screen.getByText("Industrial Potatoes")).toBeInTheDocument();
    });

    expect(screen.getByText("120")).toBeInTheDocument();
    expect(screen.getByText(/Gujarat Agro Snacks Ltd/i)).toBeInTheDocument();
  });

  it("opens produce lot detail modal on card action click", async () => {
    vi.spyOn(listingsApi, "searchMarketplace").mockResolvedValueOnce({
      items: mockProduce,
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });

    const getListingSpy = vi.spyOn(listingsApi, "getListing").mockResolvedValueOnce({
      ...mockProduce[0],
      status: "active",
      farmer_id: "farmer-1",
      initial_quantity: 50,
      is_deleted: false,
      updated_at: "2026-10-25T10:00:00Z",
      images: [],
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Sharbati Wheat")).toBeInTheDocument();
    });

    const viewDetailsBtn = screen.getByRole("button", { name: /view produce lot details/i });
    fireEvent.click(viewDetailsBtn);

    await waitFor(() => {
      expect(getListingSpy).toHaveBeenCalledWith("prod-1");
      expect(screen.getByRole("dialog", { name: /produce lot specifications/i })).toBeInTheDocument();
    });

    expect(screen.getAllByText("Narmada Valley Farms")[0]).toBeInTheDocument();
  });

  it("opens requirement detail modal on card action click", async () => {
    vi.spyOn(listingsApi, "searchMarketplace").mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      total_pages: 0,
    });

    vi.spyOn(requirementsApi, "searchMarketplace").mockResolvedValueOnce({
      items: mockRequirements,
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });

    const getReqSpy = vi.spyOn(requirementsApi, "getRequirement").mockResolvedValueOnce({
      ...mockRequirements[0],
      status: "active",
      buyer_id: "buyer-1",
      is_deleted: false,
      updated_at: "2026-10-28T10:00:00Z",
    });

    renderComponent();

    const buyersTab = screen.getByRole("tab", { name: /find buyers/i });
    fireEvent.click(buyersTab);

    await waitFor(() => {
      expect(screen.getByText("Industrial Potatoes")).toBeInTheDocument();
    });

    const viewDetailsBtn = screen.getByRole("button", { name: /view procurement demand details/i });
    fireEvent.click(viewDetailsBtn);

    await waitFor(() => {
      expect(getReqSpy).toHaveBeenCalledWith("req-1");
      expect(screen.getByRole("dialog", { name: /procurement demand specifications/i })).toBeInTheDocument();
    });

    expect(screen.getAllByText("Gujarat Agro Snacks Ltd")[0]).toBeInTheDocument();
  });

  it("renders empty state when search returns zero lots", async () => {
    vi.spyOn(listingsApi, "searchMarketplace").mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      total_pages: 0,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("No produce lots found")).toBeInTheDocument();
    });
  });
});
