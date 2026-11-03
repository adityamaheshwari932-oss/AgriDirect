import { describe, it, expect, vi, beforeEach } from "vitest";
import { offersApi } from "./offers";
import { apiClient } from "./client";
import type {
  OfferCreatePayload,
  CounterOfferCreatePayload,
  OfferAcceptPayload,
  OfferRejectPayload,
} from "../types/offers";

describe("Offers API Service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits a new structured offer proposal", async () => {
    const payload: OfferCreatePayload = {
      recipient_id: "user-buyer-1",
      delivery_terms: "Ex-farm pickup",
      proposed_delivery_date: "2026-11-20",
      items: [
        {
          listing_id: "listing-1",
          quantity: 10,
          unit: "kg",
          unit_price: 25.5,
        },
      ],
    };

    const mockResponse = { id: "offer-1", offer_number: "OFF-2026-0001", status: "pending" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const result = await offersApi.createOffer(payload);
    expect(apiClient.post).toHaveBeenCalledWith("/offers", payload);
    expect(result).toEqual(mockResponse);
  });

  it("lists offers with filter parameters", async () => {
    const mockList = { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockList);

    const result = await offersApi.listOffers({ role: "received", status: "pending", page: 1 });
    expect(apiClient.get).toHaveBeenCalledWith("/offers?role=received&status=pending&page=1");
    expect(result).toEqual(mockList);
  });

  it("retrieves single offer details", async () => {
    const mockDetail = { id: "offer-1", offer_number: "OFF-1" };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockDetail);

    const result = await offersApi.getOffer("offer-1");
    expect(apiClient.get).toHaveBeenCalledWith("/offers/offer-1");
    expect(result).toEqual(mockDetail);
  });

  it("retrieves offer negotiation chain history", async () => {
    const mockHistory = { root_offer_id: "root-1", offers: [] };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockHistory);

    const result = await offersApi.getOfferHistory("offer-1");
    expect(apiClient.get).toHaveBeenCalledWith("/offers/offer-1/history");
    expect(result).toEqual(mockHistory);
  });

  it("submits a counter-offer", async () => {
    const payload: CounterOfferCreatePayload = {
      delivery_terms: "Modified terms",
      items: [
        {
          listing_id: "listing-1",
          quantity: 8,
          unit: "kg",
          unit_price: 28.0,
        },
      ],
    };

    const mockResponse = { id: "offer-2", status: "pending" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const result = await offersApi.counterOffer("offer-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/offers/offer-1/counter", payload);
    expect(result).toEqual(mockResponse);
  });

  it("accepts an offer with structured fulfillment payload", async () => {
    const payload: OfferAcceptPayload = {
      apply_to_requirement: true,
      approved_quantity: 10,
      close_requirement: false,
    };

    const mockResponse = {
      offer_id: "offer-1",
      order_id: "order-1",
      order_number: "ORD-2026-0001",
      status: "accepted",
    };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const result = await offersApi.acceptOffer("offer-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/offers/offer-1/accept", payload);
    expect(result).toEqual(mockResponse);
  });

  it("rejects an offer with an optional reason", async () => {
    const payload: OfferRejectPayload = { reason: "Price is too low" };
    const mockResponse = { id: "offer-1", status: "rejected" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const result = await offersApi.rejectOffer("offer-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/offers/offer-1/reject", payload);
    expect(result).toEqual(mockResponse);
  });

  it("withdraws an offer proposal", async () => {
    const mockResponse = { id: "offer-1", status: "withdrawn" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const result = await offersApi.withdrawOffer("offer-1");
    expect(apiClient.post).toHaveBeenCalledWith("/offers/offer-1/withdraw");
    expect(result).toEqual(mockResponse);
  });
});
