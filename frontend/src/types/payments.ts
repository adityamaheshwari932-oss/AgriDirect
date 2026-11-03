/**
 * Domain types for AgriDirect Off-Platform Payment Tracking & Disputes (Module 6).
 * Aligned with backend Pydantic models in app.payments.schemas.
 */

export type PaymentMethod = "upi" | "bank_transfer" | "cash" | "other";

export type PaymentRecordStatus = "recorded" | "acknowledged" | "disputed";

export type PaymentComplaintStatus = "open" | "under_review" | "resolved" | "dismissed";

export type PaymentSettlementStatus =
  | "unpaid"
  | "payment_pending_acknowledgement"
  | "disputed"
  | "partially_settled"
  | "fully_settled";

export interface PaymentRecordCreatePayload {
  amount: number | string;
  payment_method: PaymentMethod;
  reference_number?: string | null;
  payment_date: string; // YYYY-MM-DD
  proof_file?: File | null;
}

export interface PaymentRecord {
  id: string;
  order_id: string;
  recorded_by_user_id: string;
  amount: string;
  payment_method: PaymentMethod;
  reference_number?: string | null;
  has_proof: boolean;
  proof_file_path?: string | null;
  status: PaymentRecordStatus;
  payment_date: string;
  acknowledged_at?: string | null;
  original_acknowledged_at?: string | null;
  has_historical_acknowledgement: boolean;
  acknowledged_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentRecordListResponse {
  items: PaymentRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface PaymentSummary {
  order_id: string;
  order_total: string;
  total_recorded: string;
  total_acknowledged: string;
  total_disputed: string;
  unacknowledged_amount: string;
  remaining_acknowledged_balance: string;
  remaining_payable_amount: string;
  max_available_for_new_payment: string;
  settlement_status: PaymentSettlementStatus;
  records_count: number;
}

export interface PaymentComplaintCreatePayload {
  complaint_reason: string;
  evidence_file?: File | null;
}

export interface PaymentComplaint {
  id: string;
  payment_record_id: string;
  payment_id?: string | null;
  complainant_user_id: string;
  complainant_id?: string | null;
  complaint_reason: string;
  reason?: string | null;
  has_evidence: boolean;
  evidence_file_path?: string | null;
  status: PaymentComplaintStatus;
  admin_resolution_notes?: string | null;
  resolved_by_admin_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentComplaintListResponse {
  items: PaymentComplaint[];
  total: number;
  limit: number;
  offset: number;
}

