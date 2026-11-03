/**
 * Participant-Facing Off-Platform Payment Tracking & Disputes API service (Module 6).
 * Connects to FastAPI endpoints versioned under /api/v1.
 * Strict Constraint: AgriDirect records off-platform settlements only (no payment gateway, no escrow).
 * Note: Administrative dispute moderation is excluded and belongs to Stage 6.
 */

import { apiClient, ApiClient } from "./client";
import type {
  PaymentComplaint,
  PaymentComplaintCreatePayload,
  PaymentRecord,
  PaymentRecordCreatePayload,
  PaymentRecordListResponse,
  PaymentSummary,
} from "../types/payments";

export class PaymentsApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  /**
   * Record an off-platform payment claim against an order (UPI, Bank Transfer, Cash, Other).
   * Verified buyer only. Supports optional receipt proof file upload (multipart/form-data).
   */
  public async recordPayment(
    orderId: string,
    payload: PaymentRecordCreatePayload
  ): Promise<PaymentRecord> {
    if (payload.proof_file) {
      const formData = new FormData();
      formData.append("amount", String(payload.amount));
      formData.append("payment_method", payload.payment_method);
      formData.append("payment_date", payload.payment_date);
      if (payload.reference_number) {
        formData.append("reference_number", payload.reference_number);
      }
      formData.append("proof_file", payload.proof_file);

      return this.client.post<PaymentRecord>(
        `/orders/${orderId}/payments`,
        formData
      );
    }

    return this.client.post<PaymentRecord>(`/orders/${orderId}/payments`, {
      amount: payload.amount,
      payment_method: payload.payment_method,
      payment_date: payload.payment_date,
      reference_number: payload.reference_number || undefined,
    });
  }

  /**
   * List recorded payments associated with an order.
   * Restricted to order participants and administrators.
   */
  public async listOrderPayments(
    orderId: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<PaymentRecordListResponse> {
    return this.client.get<PaymentRecordListResponse>(
      `/orders/${orderId}/payments?limit=${limit}&offset=${offset}`
    );
  }

  /**
   * Retrieve aggregate financial reconciliation summary for an order.
   */
  public async getOrderPaymentSummary(orderId: string): Promise<PaymentSummary> {
    return this.client.get<PaymentSummary>(`/orders/${orderId}/payments/summary`);
  }

  /**
   * Retrieve details of a specific payment record.
   */
  public async getPaymentDetails(paymentId: string): Promise<PaymentRecord> {
    return this.client.get<PaymentRecord>(`/payments/${paymentId}`);
  }

  /**
   * Farmer acknowledges receipt of off-platform payment.
   * Restricted to the seller (farmer) exclusively.
   */
  public async acknowledgePayment(paymentId: string): Promise<PaymentRecord> {
    return this.client.post<PaymentRecord>(`/payments/${paymentId}/acknowledge`);
  }

  /**
   * File a dispute complaint against a payment record with optional evidence file.
   * Order participants only.
   */
  public async filePaymentComplaint(
    paymentId: string,
    payload: PaymentComplaintCreatePayload
  ): Promise<PaymentComplaint> {
    if (payload.evidence_file) {
      const formData = new FormData();
      formData.append("complaint_reason", payload.complaint_reason);
      formData.append("evidence_file", payload.evidence_file);

      return this.client.post<PaymentComplaint>(
        `/payments/${paymentId}/complaints`,
        formData
      );
    }

    return this.client.post<PaymentComplaint>(
      `/payments/${paymentId}/complaints`,
      {
        complaint_reason: payload.complaint_reason,
      }
    );
  }

  /**
   * Get direct authenticated streaming URL for payment proof.
   */
  public getProofUrl(paymentId: string): string {
    return `${this.client.getBaseUrl()}/payments/${paymentId}/proof`;
  }

  /**
   * Get direct authenticated streaming URL for dispute evidence.
   */
  public getEvidenceUrl(complaintId: string): string {
    return `${this.client.getBaseUrl()}/payment-complaints/${complaintId}/evidence`;
  }
}

export const paymentsApi = new PaymentsApi();

