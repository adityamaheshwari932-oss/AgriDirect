/**
 * Transporters API client.
 * Interacts with backend FastAPI endpoints under /api/v1/transporters and /api/v1/orders/{id}/transport-coordination.
 */

import { apiClient, ApiClient } from "./client";
import type {
  OrderTransportCoordinationRequest,
  OrderTransportCoordinationResponse,
  ServiceArea,
  ServiceAreaCreate,
  ServiceAreaUpdate,
  TransporterDetail,
  TransporterProfileUpdate,
  TransporterSearchParams,
  TransporterSearchResponse,
  TransportConnectionApprovalPayload,
  TransportConnectionRejectionPayload,
  TransportConnectionRequest,
  TransportConnectionRequestCreate,
  TransportConnectionRequestListResponse,
  TransportConnectionRequestResponse,
} from "../types/transporter";

export class TransportersApi {
  private client: ApiClient;

  constructor(client: ApiClient = apiClient) {
    this.client = client;
  }

  /**
   * Fetch authenticated transporter's profile and active service areas.
   */
  public async getMyProfile(): Promise<TransporterDetail> {
    return this.client.get<TransporterDetail>("/transporters/me");
  }

  /**
   * Update authenticated transporter's profile.
   */
  public async updateMyProfile(
    payload: TransporterProfileUpdate
  ): Promise<TransporterDetail> {
    return this.client.patch<TransporterDetail>("/transporters/me", payload);
  }

  /**
   * List all service areas for authenticated transporter.
   */
  public async getServiceAreas(): Promise<ServiceArea[]> {
    return this.client.get<ServiceArea[]>("/transporters/service-areas");
  }

  /**
   * Register a new serviceable area.
   */
  public async addServiceArea(payload: ServiceAreaCreate): Promise<ServiceArea> {
    return this.client.post<ServiceArea>("/transporters/service-areas", payload);
  }

  /**
   * Update an existing service area.
   */
  public async updateServiceArea(
    areaId: string,
    payload: ServiceAreaUpdate
  ): Promise<ServiceArea> {
    return this.client.patch<ServiceArea>(
      `/transporters/service-areas/${areaId}`,
      payload
    );
  }

  /**
   * Remove a service area.
   */
  public async deleteServiceArea(
    areaId: string
  ): Promise<{ status: string; message: string }> {
    return this.client.delete<{ status: string; message: string }>(
      `/transporters/service-areas/${areaId}`
    );
  }

  /**
   * Discover available transporters based on location, capacity, and fleet specs.
   */
  public async discoverTransporters(
    params: TransporterSearchParams = {}
  ): Promise<TransporterSearchResponse> {
    const query = new URLSearchParams();
    if (params.pickup_state) query.set("pickup_state", params.pickup_state);
    if (params.pickup_district) query.set("pickup_district", params.pickup_district);
    if (params.delivery_state) query.set("delivery_state", params.delivery_state);
    if (params.delivery_district) query.set("delivery_district", params.delivery_district);
    if (params.transport_type) query.set("transport_type", params.transport_type);
    if (params.min_capacity_kg !== undefined) query.set("min_capacity_kg", String(params.min_capacity_kg));
    if (params.only_available !== undefined) query.set("only_available", String(params.only_available));
    if (params.page !== undefined) query.set("page", String(params.page));
    if (params.page_size !== undefined) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    const endpoint = `/transporters/discover${qs ? `?${qs}` : ""}`;
    return this.client.get<TransporterSearchResponse>(endpoint);
  }

  /**
   * Get public profile and service coverage for a transporter.
   */
  public async getTransporterById(profileId: string): Promise<TransporterDetail> {
    return this.client.get<TransporterDetail>(`/transporters/${profileId}`);
  }

  /**
   * Coordinate transportation details on an order.
   */
  public async coordinateOrderTransport(
    orderId: string,
    payload: OrderTransportCoordinationRequest
  ): Promise<OrderTransportCoordinationResponse> {
    return this.client.post<OrderTransportCoordinationResponse>(
      `/orders/${orderId}/transport-coordination`,
      payload
    );
  }

  /**
   * Create a new transportation connection request.
   */
  public async createConnectionRequest(
    payload: TransportConnectionRequestCreate
  ): Promise<TransportConnectionRequest> {
    return this.client.post<TransportConnectionRequest>(
      "/transporters/connection-requests",
      payload
    );
  }

  /**
   * List transportation connection requests.
   */
  public async listConnectionRequests(params: {
    status?: string;
    order_id?: string;
    offer_id?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<TransportConnectionRequestListResponse> {
    const query = new URLSearchParams();
    if (params.status) query.set("status", params.status);
    if (params.order_id) query.set("order_id", params.order_id);
    if (params.offer_id) query.set("offer_id", params.offer_id);
    if (params.page !== undefined) query.set("page", String(params.page));
    if (params.page_size !== undefined) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    const endpoint = `/transporters/connection-requests${qs ? `?${qs}` : ""}`;
    return this.client.get<TransportConnectionRequestListResponse>(endpoint);
  }

  /**
   * Get single transportation connection request.
   */
  public async getConnectionRequest(
    requestId: string
  ): Promise<TransportConnectionRequest> {
    return this.client.get<TransportConnectionRequest>(
      `/transporters/connection-requests/${requestId}`
    );
  }

  /**
   * Transporter accepts connection request.
   */
  public async acceptConnectionRequest(
    requestId: string,
    payload: TransportConnectionRequestResponse = {}
  ): Promise<TransportConnectionRequest> {
    return this.client.post<TransportConnectionRequest>(
      `/transporters/connection-requests/${requestId}/accept`,
      payload
    );
  }

  /**
   * Transporter declines connection request.
   */
  public async declineConnectionRequest(
    requestId: string,
    payload: TransportConnectionRequestResponse = {}
  ): Promise<TransportConnectionRequest> {
    return this.client.post<TransportConnectionRequest>(
      `/transporters/connection-requests/${requestId}/decline`,
      payload
    );
  }

  /**
   * Requester cancels connection request.
   */
  public async cancelConnectionRequest(
    requestId: string
  ): Promise<TransportConnectionRequest> {
    return this.client.post<TransportConnectionRequest>(
      `/transporters/connection-requests/${requestId}/cancel`
    );
  }

  /**
   * Deal counterparty approves transporter assignment.
   */
  public async approveConnectionRequest(
    requestId: string,
    payload: TransportConnectionApprovalPayload = {}
  ): Promise<TransportConnectionRequest> {
    return this.client.post<TransportConnectionRequest>(
      `/transporters/connection-requests/${requestId}/approve`,
      payload
    );
  }

  /**
   * Deal counterparty rejects transporter assignment.
   */
  public async rejectConnectionRequest(
    requestId: string,
    payload: TransportConnectionRejectionPayload = {}
  ): Promise<TransportConnectionRequest> {
    return this.client.post<TransportConnectionRequest>(
      `/transporters/connection-requests/${requestId}/reject`,
      payload
    );
  }
}

export const transportersApi = new TransportersApi();
