/**
 * Orders, Amendments, Inventory Audit, and Buyer Fulfillment Approvals API service.
 * Interacts with backend FastAPI endpoints defined in app.orders.routes and app.requirements.routes.
 */

import { apiClient, ApiClient } from "./client";
import type {
  ApproveFulfillmentPayload,
  DeliveryAcknowledgePayload,
  DeliveryArrangePayload,
  FulfillmentApproval,
  FulfillmentApprovalListResponse,
  InventoryAdjustmentListResponse,
  OrderAmendment,
  OrderAmendmentCreatePayload,
  OrderAmendmentListResponse,
  OrderCancelPayload,
  OrderDetail,
  OrderListFilterParams,
  OrderListResponse,
  RejectFulfillmentPayload,
} from "../types/orders";

export class OrdersApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  // -------------------------------------------------------------------------
  // Order Lifecycle
  // -------------------------------------------------------------------------

  /**
   * Retrieve paginated orders for the authenticated participant (buyer or farmer).
   */
  public async listOrders(
    params?: OrderListFilterParams
  ): Promise<OrderListResponse> {
    const query = new URLSearchParams();
    if (params?.role) query.set("role", params.role);
    if (params?.status) query.set("status", params.status);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    const endpoint = qs ? `/orders?${qs}` : "/orders";
    return this.client.get<OrderListResponse>(endpoint);
  }

  /**
   * Retrieve full details of an order, including snapshot line items and participants.
   */
  public async getOrderDetail(id: string): Promise<OrderDetail> {
    return this.client.get<OrderDetail>(`/orders/${id}`);
  }

  /**
   * Confirm fulfillment commitment for a pending order.
   * Restricted to the seller (farmer) exclusively.
   */
  public async confirmOrder(id: string): Promise<OrderDetail> {
    return this.client.post<OrderDetail>(`/orders/${id}/confirm`);
  }

  /**
   * Atomically cancel an order with automatic inventory and demand restitution.
   * Participant only (buyer or farmer). Requires commercial justification reason.
   */
  public async cancelOrder(
    id: string,
    payload: OrderCancelPayload
  ): Promise<OrderDetail> {
    return this.client.post<OrderDetail>(`/orders/${id}/cancel`, payload);
  }

  // -------------------------------------------------------------------------
  // Delivery Coordination & Order Completion
  // -------------------------------------------------------------------------

  /**
   * Schedule delivery method, destination address, and date.
   * Order transitions to delivery_arranged.
   */
  public async arrangeDelivery(
    orderId: string,
    payload: DeliveryArrangePayload
  ): Promise<OrderDetail> {
    return this.client.post<OrderDetail>(
      `/orders/${orderId}/delivery/arrange`,
      payload
    );
  }

  /**
   * Mark physical delivery dispatch/transit completed by one counterparty.
   * Order transitions to delivery_status=completion_marked.
   */
  public async markDeliveryCompleted(orderId: string): Promise<OrderDetail> {
    return this.client.post<OrderDetail>(
      `/orders/${orderId}/delivery/mark-completed`
    );
  }

  /**
   * Acknowledge physical receipt of delivered produce.
   * Counterparty only. Order transitions to completed atomically.
   */
  public async acknowledgeDelivery(
    orderId: string,
    payload?: DeliveryAcknowledgePayload
  ): Promise<OrderDetail> {
    return this.client.post<OrderDetail>(
      `/orders/${orderId}/delivery/acknowledge`,
      payload || {}
    );
  }

  // -------------------------------------------------------------------------
  // Order Amendments
  // -------------------------------------------------------------------------

  /**
   * List formal amendment records associated with an order.
   */
  public async listAmendments(
    orderId: string
  ): Promise<OrderAmendmentListResponse> {
    return this.client.get<OrderAmendmentListResponse>(
      `/orders/${orderId}/amendments`
    );
  }

  /**
   * Retrieve details of a specific proposed or finalized amendment.
   */
  public async getAmendment(
    orderId: string,
    amendmentId: string
  ): Promise<OrderAmendment> {
    return this.client.get<OrderAmendment>(
      `/orders/${orderId}/amendments/${amendmentId}`
    );
  }

  /**
   * Propose an order amendment (quantity, price, delivery date, terms).
   * Only one pending amendment is permitted per order.
   */
  public async proposeAmendment(
    orderId: string,
    payload: OrderAmendmentCreatePayload
  ): Promise<OrderAmendment> {
    return this.client.post<OrderAmendment>(
      `/orders/${orderId}/amendments`,
      payload
    );
  }

  /**
   * Accept an amendment proposed by the counterparty, executing atomic inventory accounting.
   * Restricted to the counterparty (proposer cannot accept their own amendment).
   */
  public async acceptAmendment(
    orderId: string,
    amendmentId: string
  ): Promise<OrderAmendment> {
    return this.client.post<OrderAmendment>(
      `/orders/${orderId}/amendments/${amendmentId}/accept`
    );
  }

  /**
   * Reject an amendment proposed by the counterparty.
   * Restricted to the counterparty.
   */
  public async rejectAmendment(
    orderId: string,
    amendmentId: string
  ): Promise<OrderAmendment> {
    return this.client.post<OrderAmendment>(
      `/orders/${orderId}/amendments/${amendmentId}/reject`
    );
  }

  // -------------------------------------------------------------------------
  // Inventory Audit Ledger
  // -------------------------------------------------------------------------

  /**
   * Retrieve append-only inventory adjustment audit entries associated with an order.
   */
  public async getOrderInventoryAdjustments(
    orderId: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<InventoryAdjustmentListResponse> {
    return this.client.get<InventoryAdjustmentListResponse>(
      `/orders/${orderId}/inventory-adjustments?page=${page}&page_size=${pageSize}`
    );
  }

  /**
   * Retrieve append-only inventory adjustment audit entries for a produce listing.
   * Restricted to the farmer owner.
   */
  public async getListingInventoryAdjustments(
    listingId: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<InventoryAdjustmentListResponse> {
    return this.client.get<InventoryAdjustmentListResponse>(
      `/listings/${listingId}/inventory-adjustments?page=${page}&page_size=${pageSize}`
    );
  }

  // -------------------------------------------------------------------------
  // Buyer Requirement Fulfillment Approvals (ADR-003)
  // -------------------------------------------------------------------------

  /**
   * List fulfillment approval requests for requirements owned by the authenticated buyer.
   */
  public async listFulfillmentApprovals(params?: {
    status?: string;
    requirement_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<FulfillmentApprovalListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.requirement_id) query.set("requirement_id", params.requirement_id);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    const endpoint = qs
      ? `/requirements/fulfillment-approvals?${qs}`
      : "/requirements/fulfillment-approvals";
    return this.client.get<FulfillmentApprovalListResponse>(endpoint);
  }

  /**
   * Retrieve single fulfillment approval record details.
   */
  public async getFulfillmentApproval(
    id: string
  ): Promise<FulfillmentApproval> {
    return this.client.get<FulfillmentApproval>(
      `/requirements/fulfillment-approvals/${id}`
    );
  }

  /**
   * Approve requirement fulfillment deduction (full or partial).
   * Restricted to verified buyer owning the requirement.
   */
  public async approveFulfillment(
    id: string,
    payload: ApproveFulfillmentPayload
  ): Promise<FulfillmentApproval> {
    return this.client.post<FulfillmentApproval>(
      `/requirements/fulfillment-approvals/${id}/approve`,
      payload
    );
  }

  /**
   * Reject requirement fulfillment deduction, leaving requirement demand untouched.
   * Restricted to verified buyer owning the requirement.
   */
  public async rejectFulfillment(
    id: string,
    payload: RejectFulfillmentPayload
  ): Promise<FulfillmentApproval> {
    return this.client.post<FulfillmentApproval>(
      `/requirements/fulfillment-approvals/${id}/reject`,
      payload
    );
  }
}

export const ordersApi = new OrdersApi();

