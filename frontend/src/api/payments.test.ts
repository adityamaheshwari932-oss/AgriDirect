import { describe, it, expect, vi, beforeEach } from "vitest";
import { paymentsApi } from "./payments";
import { apiClient } from "./client";

describe("PaymentsApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("records payment via JSON when no proof file is attached", async () => {
    const payload = {
      amount: "15000.00",
      payment_method: "bank_transfer" as const,
      payment_date: "2026-11-03",
      reference_number: "UTR987654321",
    };
    const mockRecord = { id: "pay-1", status: "recorded", amount: "15000.00" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockRecord);

    const res = await paymentsApi.recordPayment("order-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/orders/order-1/payments", {
      amount: "15000.00",
      payment_method: "bank_transfer",
      payment_date: "2026-11-03",
      reference_number: "UTR987654321",
    });
    expect(res).toEqual(mockRecord);
  });

  it("records payment via FormData when proof file is attached", async () => {
    const file = new File(["receipt pdf"], "receipt.pdf", { type: "application/pdf" });
    const payload = {
      amount: 5000,
      payment_method: "upi" as const,
      payment_date: "2026-11-03",
      proof_file: file,
    };
    const mockRecord = { id: "pay-2", status: "recorded", has_proof: true };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockRecord);

    const res = await paymentsApi.recordPayment("order-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith(
      "/orders/order-1/payments",
      expect.any(FormData)
    );
    expect(res).toEqual(mockRecord);
  });

  it("retrieves order payments list and financial summary", async () => {
    const mockList = { items: [], total: 0, limit: 50, offset: 0 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockList);

    const resList = await paymentsApi.listOrderPayments("order-1");
    expect(apiClient.get).toHaveBeenCalledWith("/orders/order-1/payments?limit=50&offset=0");
    expect(resList).toEqual(mockList);

    const mockSummary = { order_id: "order-1", order_total: "50000.00", settlement_status: "unpaid" };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockSummary);
    const resSummary = await paymentsApi.getOrderPaymentSummary("order-1");
    expect(apiClient.get).toHaveBeenCalledWith("/orders/order-1/payments/summary");
    expect(resSummary).toEqual(mockSummary);
  });

  it("acknowledges payment by farmer", async () => {
    const mockRecord = { id: "pay-1", status: "acknowledged" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockRecord);

    const res = await paymentsApi.acknowledgePayment("pay-1");
    expect(apiClient.post).toHaveBeenCalledWith("/payments/pay-1/acknowledge");
    expect(res).toEqual(mockRecord);
  });

  it("files payment complaint dispute", async () => {
    const payload = { complaint_reason: "Bank transaction bounced or fraudulent slip" };
    const mockComplaint = { id: "comp-1", status: "open" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockComplaint);

    const res = await paymentsApi.filePaymentComplaint("pay-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/payments/pay-1/complaints", payload);
    expect(res).toEqual(mockComplaint);
  });
});

