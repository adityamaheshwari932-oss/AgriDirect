import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { OffersPage } from "./OffersPage";
import { offersApi } from "../api/offers";
import { authStore } from "../store/authStore";
import type { OfferSummary, OfferListResponse } from "../types/offers";
import type { User } from "../types";

describe("OffersPage", () => {
  const mockUser: User = {
    id: "user-buyer-1",
    email: "buyer@agrocorp.com",
    role: "buyer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
  };

  const mockOffers: OfferSummary[] = [
    {
      id: "offer-001",
      offer_number: "OFF-2026-0001",
      conversation_id: "conv-1",
      sender_id: "farmer-1",
      recipient_id: "user-buyer-1",
      parent_offer_id: null,
      delivery_terms: "Direct farm delivery",
      proposed_delivery_date: "2026-11-20",
      total_amount: 15000,
      item_count: 2,
      status: "pending",
      expires_at: "2026-11-25T00:00:00Z",
      created_at: "2026-11-02T10:00:00Z",
      updated_at: "2026-11-02T10:00:00Z",
    },
  ];

  const mockListResponse: OfferListResponse = {
    items: mockOffers,
    total: 1,
    page: 1,
    page_size: 10,
    pages: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    authStore.reset();
    authStore.setUser(mockUser);
  });

  it("renders page header, status filters and received offers table", async () => {
    vi.spyOn(offersApi, "listOffers").mockResolvedValue(mockListResponse);

    render(
      <MemoryRouter>
        <OffersPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Offers & Negotiations/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Received Proposals/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sent Proposals/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText("OFF-2026-0001").length).toBeGreaterThan(0);
    });

    // Check desktop table row using within
    const rows = screen.getAllByRole("row");
    const dataRow = rows.find((r) => within(r).queryByText("OFF-2026-0001"));
    expect(dataRow).toBeDefined();
    if (dataRow) {
      expect(within(dataRow).getByText(/2 produce items/i)).toBeInTheDocument();
      expect(within(dataRow).getByText(/₹15,000/i)).toBeInTheDocument();
    }
  });

  it("switches to Sent Offers tab and reloads with sent filter", async () => {
    vi.spyOn(offersApi, "listOffers").mockResolvedValue({
      ...mockListResponse,
      items: [],
      total: 0,
    });

    render(
      <MemoryRouter>
        <OffersPage />
      </MemoryRouter>
    );

    const sentTab = screen.getByRole("button", { name: /Sent Proposals/i });
    fireEvent.click(sentTab);

    await waitFor(() => {
      expect(offersApi.listOffers).toHaveBeenCalledWith(
        expect.objectContaining({ role: "sent" })
      );
    });
  });

  it("filters offers by status button click", async () => {
    vi.spyOn(offersApi, "listOffers").mockResolvedValue(mockListResponse);

    render(
      <MemoryRouter>
        <OffersPage />
      </MemoryRouter>
    );

    const pendingBtn = screen.getByRole("button", { name: /^Pending$/i });
    fireEvent.click(pendingBtn);

    await waitFor(() => {
      expect(offersApi.listOffers).toHaveBeenCalledWith(
        expect.objectContaining({ status: "pending" })
      );
    });
  });

  it("opens offer detail modal when clicking View Details", async () => {
    vi.spyOn(offersApi, "listOffers").mockResolvedValue(mockListResponse);
    vi.spyOn(offersApi, "getOffer").mockResolvedValue({
      ...mockOffers[0],
      items: [],
    });
    vi.spyOn(offersApi, "getOfferHistory").mockResolvedValue({
      root_offer_id: "offer-001",
      current_offer_id: "offer-001",
      chain_length: 1,
      history: [
        {
          ...mockOffers[0],
          items: [],
        },
      ],
    });

    render(
      <MemoryRouter>
        <OffersPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText("OFF-2026-0001").length).toBeGreaterThan(0);
    });

    const viewButtons = screen.getAllByRole("button", { name: /View Details/i });
    fireEvent.click(viewButtons[0]);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });
});
