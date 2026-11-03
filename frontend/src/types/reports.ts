/**
 * Domain types for AgriDirect Platform Safety & User Conduct Reports (Module 8).
 * Aligned with backend Pydantic models in app.reports.schemas.
 */

export type ReportCategory =
  | "payment"
  | "quantity_mismatch"
  | "quality_issue"
  | "fraud"
  | "harassment"
  | "other";

export type ReportStatus = "open" | "under_review" | "action_taken" | "dismissed";

export interface ReportCreatePayload {
  reported_user_id?: string | null;
  listing_id?: string | null;
  category: ReportCategory | string;
  description: string; // min 5, max 2000 chars
}

export interface ReportItem {
  id: string;
  reporter_id: string;
  reported_user_id?: string | null;
  listing_id?: string | null;
  category: string;
  description: string;
  status: ReportStatus;
  admin_notes?: string | null;
  reviewed_by_admin_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportListResponse {
  items: ReportItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

