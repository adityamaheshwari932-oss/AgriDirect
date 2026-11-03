import { describe, it, expect, vi, beforeEach } from "vitest";
import { ordersApi } from "./orders";
import { apiClient } from "./client";
import type {
  OrderCancelPayload,
  OrderAmendmentCreatePayload,
  ApproveFulfillmentPayload,
  RejectFulfillmentPayload,
} from "../types/orders";

describe("Orders API Service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists orders with optional role and status filters", async () => {
    const mockList = { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockList);

    const result = await ordersApi.listOrders({ role: "buyer", status: "confirmed", page: 1 });
    expect(apiClient.get).toHaveBeenCalledWith("/orders?role=buyer&status=confirmed&page=1");
    expect(result).toEqual(mockList);
  });

  it("retrieves full order details", async () => {
    const mockDetail = { id: "order-1", order_number: "ORD-2026-0001", status: "confirmed" };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockDetail);

    const result = await ordersApi.getOrderDetail("order-1");
    expect(apiClient.get).toHaveBeenCalledWith("/orders/order-1");
    expect(result).toEqual(mockDetail);
  });

  it("confirms an order by farmer", async () => {
    const mockConfirmed = { id: "order-1", status: "confirmed" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockConfirmed);

    const result = await ordersApi.confirmOrder("order-1");
    expect(apiClient.post).toHaveBeenCalledWith("/orders/order-1/confirm");
    expect(result).toEqual(mockConfirmed);
  });

  it("cancels an order with mandatory reason", async () => {
    const payload: OrderCancelPayload = { reason: "Crop failure due to hailstorm" };
    const mockCancelled = { id: "order-1", status: "cancelled" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockCancelled);

    const result = await ordersApi.cancelOrder("order-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/orders/order-1/cancel", payload);
    expect(result).toEqual(mockCancelled);
  });

  it("proposes an order amendment", async () => {
    const payload: OrderAmendmentCreatePayload = {
      amendment_type: "delivery_date",
      new_delivery_date: "2026-11-25",
      justification: "Logistics truck scheduled late",
    };
    const mockAmendment = { id: "amd-1", status: "proposed" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockAmendment);

    const result = await ordersApi.proposeAmendment("order-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/orders/order-1/amendments", payload);
    expect(result).toEqual(mockAmendment);
  });

  it("lists amendments on an order", async () => {
    const mockList = { items: [], total: 0 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockList);

    const result = await ordersApi.listAmendments("order-1");
    expect(apiClient.get).toHaveBeenCalledWith("/orders/order-1/amendments");
    expect(result).toEqual(mockList);
  });

  it("accepts an amendment", async () => {
    const mockResponse = { id: "amd-1", status: "effective" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const result = await ordersApi.acceptAmendment("order-1", "amd-1");
    expect(apiClient.post).toHaveBeenCalledWith("/orders/order-1/amendments/amd-1/accept");
    expect(result).toEqual(mockResponse);
  });

  it("rejects an amendment", async () => {
    const mockResponse = { id: "amd-1", status: "rejected" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const result = await ordersApi.rejectAmendment("order-1", "amd-1");
    expect(apiClient.post).toHaveBeenCalledWith("/orders/order-1/amendments/amd-1/reject");
    expect(result).toEqual(mockResponse);
  });

  it("lists fulfillment approvals for buyer", async () => {
    const mockList = { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockList);

    const result = await ordersApi.listFulfillmentApprovals({ status: "pending" });
    expect(apiClient.get).toHaveBeenCalledWith("/requirements/fulfillment-approvals?status=pending");
    expect(result).toEqual(mockList);
  });

  it("approves fulfillment deduction", async () => {
    const payload: ApproveFulfillmentPayload = {
      approved_quantity: 50,
      close_requirement: true,
    };
    const mockResponse = { id: "app-1", status: "approved" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const result = await ordersApi.approveFulfillment("app-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/requirements/fulfillment-approvals/app-1/approve", payload);
    expect(result).toEqual(mockResponse);
  });

  it("rejects fulfillment deduction", async () => {
    const payload: RejectFulfillmentPayload = { reason: "Not aligned with requirement" };
    const mockResponse = { id: "app-1", status: "rejected" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const result = await ordersApi.rejectFulfillment("app-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/requirements/fulfillment-approvals/app-1/reject", payload);
    expect(result).toEqual(mockResponse);
  });

  it("retrieves order inventory adjustments audit trail", async () => {
    const mockAdjustments = { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockAdjustments);

    const result = await ordersApi.getOrderInventoryAdjustments("order-1");
    expect(apiClient.get).toHaveBeenCalledWith("/orders/order-1/inventory-adjustments?page=1&page_size=20");
    expect(result).toEqual(mockAdjustments);
  });

  it("arranges order delivery logistics", async () => {
    const payload = {
      delivery_method: "seller_dispatch",
      delivery_destination_address: "Kharar Mandi, Punjab",
      delivery_arranged_date: "2026-11-15",
      delivery_notes: "Handle carefully",
    };
    const mockOrder = { id: "order-1", status: "delivery_arranged", delivery_status: "arranged" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockOrder);

    const result = await ordersApi.arrangeDelivery("order-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/orders/order-1/delivery/arrange", payload);
    expect(result).toEqual(mockOrder);
  });

  it("marks delivery completed by one party", async () => {
    const mockOrder = { id: "order-1", delivery_status: "completion_marked" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockOrder);

    const result = await ordersApi.markDeliveryCompleted("order-1");
    expect(apiClient.post).toHaveBeenCalledWith("/orders/order-1/delivery/mark-completed");
    expect(result).toEqual(mockOrder);
  });

  it("acknowledges delivery receipt by counterparty", async () => {
    const payload = { notes: "Received in pristine condition" };
    const mockOrder = { id: "order-1", status: "completed", delivery_status: "completed" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockOrder);

    const result = await ordersApi.acknowledgeDelivery("order-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/orders/order-1/delivery/acknowledge", payload);
    expect(result).toEqual(mockOrder);
  });
});
