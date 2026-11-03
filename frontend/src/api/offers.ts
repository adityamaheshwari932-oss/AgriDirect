/**
 * Structured Offers and Negotiation API service.
 * Interacts with backend FastAPI endpoints defined in app.offers.routes.
 */

import { apiClient, ApiClient } from "./client";
import type {
  CounterOfferCreatePayload,
  OfferAcceptPayload,
  OfferAcceptResponse,
  OfferCreatePayload,
  OfferDetail,
  OfferHistoryResponse,
  OfferListFilterParams,
  OfferListResponse,
  OfferRejectPayload,
} from "../types/offers";

export class OffersApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  /**
   * Submit an initial structured trade offer against a listing or requirement.
   * Restricted to authenticated verified farmers and buyers.
   */
  public async createOffer(payload: OfferCreatePayload): Promise<OfferDetail> {
    return this.client.post<OfferDetail>("/offers", payload);
  }

  /**
   * Retrieve paginated sent and received offers for the authenticated user.
   */
  public async listOffers(
    params?: OfferListFilterParams
  ): Promise<OfferListResponse> {
    const query = new URLSearchParams();
    if (params?.role) query.set("role", params.role);
    if (params?.status) query.set("status", params.status);
    if (params?.conversation_id) query.set("conversation_id", params.conversation_id);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    const endpoint = qs ? `/offers?${qs}` : "/offers";
    return this.client.get<OfferListResponse>(endpoint);
  }

  /**
   * Retrieve detailed specifications of an offer including line items.
   */
  public async getOffer(id: string): Promise<OfferDetail> {
    return this.client.get<OfferDetail>(`/offers/${id}`);
  }

  /**
   * Retrieve the complete chronological negotiation lineage chain.
   */
  public async getOfferHistory(id: string): Promise<OfferHistoryResponse> {
    return this.client.get<OfferHistoryResponse>(`/offers/${id}/history`);
  }

  /**
   * Submit a counter-offer proposal responding to a pending offer.
   * Restricted to the recipient of the pending offer.
   */
  public async counterOffer(
    id: string,
    payload: CounterOfferCreatePayload
  ): Promise<OfferDetail> {
    return this.client.post<OfferDetail>(`/offers/${id}/counter`, payload);
  }

  /**
   * Accept a pending offer, atomically updating inventory and generating an Order.
   * Recipient only. Accepts optional requirement fulfillment decisions in request body.
   */
  public async acceptOffer(
    id: string,
    payload?: OfferAcceptPayload
  ): Promise<OfferAcceptResponse> {
    return this.client.post<OfferAcceptResponse>(
      `/offers/${id}/accept`,
      payload ?? {}
    );
  }

  /**
   * Reject a pending offer with an optional rejection reason.
   * Recipient only.
   */
  public async rejectOffer(
    id: string,
    payload?: OfferRejectPayload
  ): Promise<OfferDetail> {
    return this.client.post<OfferDetail>(
      `/offers/${id}/reject`,
      payload ?? {}
    );
  }

  /**
   * Withdraw an offer previously sent by the current user.
   * Sender only.
   */
  public async withdrawOffer(id: string): Promise<OfferDetail> {
    return this.client.post<OfferDetail>(`/offers/${id}/withdraw`);
  }
}

export const offersApi = new OffersApi();

