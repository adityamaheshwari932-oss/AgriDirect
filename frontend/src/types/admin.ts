/**
 * Domain types for AgriDirect Platform Administration, Moderation & Governance (Module 10 & Stage 6).
 * Aligned with backend Pydantic models in:
 * - app.admin.schemas
 * - app.analytics.schemas
 * - app.reports.schemas
 * - app.payments.schemas
 * - app.verification.schemas
 */

import type { BuyerProfile, FarmerProfile } from "./user";
import type { PaymentComplaint, PaymentRecord } from "./payments";
import type { VerificationSubmission } from "./verification";

// ---------------------------------------------------------------------------
// 1. Administrative Audit Logs
// ---------------------------------------------------------------------------

export interface AdminAuditLog {
  id: string;
  admin_user_id: string;
  action: string;
  target_entity_type: string;
  target_entity_id: string;
  reason?: string | null;
  ip_address?: string | null;
  created_at: string;
}

export interface AdminAuditLogListResponse {
  items: AdminAuditLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminAuditLogFilterParams {
  admin_user_id?: string;
  action?: string;
  target_entity_type?: string;
  target_entity_id?: string;
  page?: number;
  page_size?: number;
}

// ---------------------------------------------------------------------------
// 2. User Directory & Moderation
// ---------------------------------------------------------------------------

export type AdminAccountStatus = "active" | "restricted" | "suspended" | "blocked";

export interface AdminUserSummary {
  id: string;
  email: string;
  phone_number?: string | null;
  role: string;
  verification_status: string;
  account_status: string;
  display_name: string;
  organization_name?: string | null;
  location_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminUserListResponse {
  items: AdminUserSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminUserActivityCounts {
  listings_count: number;
  requirements_count: number;
  completed_orders_count: number;
  reports_filed_count: number;
  reports_received_count: number;
}

export interface AdminVerificationSummary {
  latest_submission_id?: string | null;
  status?: string | null;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
  documents_count: number;
}

export interface AdminUserDetail {
  id: string;
  email: string;
  phone_number?: string | null;
  role: string;
  verification_status: string;
  account_status: string;
  created_at: string;
  updated_at: string;
  farmer_profile?: FarmerProfile | null;
  buyer_profile?: BuyerProfile | null;
  verification_summary?: AdminVerificationSummary | null;
  activity_counts: AdminUserActivityCounts;
  recent_audit_logs: AdminAuditLog[];
}

export interface AdminUserStatusUpdateRequest {
  account_status: AdminAccountStatus | string;
  reason: string;
}

export interface AdminUserStatusUpdateResponse {
  user: AdminUserSummary;
  previous_status: string;
  new_status: string;
  audit_log_id: string;
  reason: string;
  updated_at: string;
}

export interface AdminUserFilterParams {
  search?: string;
  role?: string;
  account_status?: string;
  verification_status?: string;
  registered_from?: string;
  registered_to?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

// ---------------------------------------------------------------------------
// 3. Catalog Moderation (Listings & Requirements)
// ---------------------------------------------------------------------------

export type AdminCatalogAction = "close" | "remove" | "restore";

export interface AdminListingSummary {
  id: string;
  farmer_id: string;
  farmer_email: string;
  farmer_name: string;
  product_name: string;
  title: string;
  category_id?: string | null;
  category_name?: string | null;
  initial_quantity: string | number;
  available_quantity: string | number;
  unit: string;
  price_per_unit: string | number;
  status: string;
  is_deleted: boolean;
  deleted_at?: string | null;
  expires_at: string;
  reports_count: number;
  created_at: string;
  updated_at: string;
}

export interface AdminListingListResponse {
  items: AdminListingSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminListingModerateRequest {
  action: AdminCatalogAction | string;
  reason: string;
}

export interface AdminListingModerateResponse {
  listing: AdminListingSummary;
  action: string;
  previous_status: string;
  new_status: string;
  is_deleted: boolean;
  audit_log_id: string;
  reason: string;
  updated_at: string;
}

export interface AdminListingFilterParams {
  search?: string;
  status?: string;
  category_id?: string;
  farmer_id?: string;
  is_deleted?: boolean;
  has_reports?: boolean;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface AdminRequirementSummary {
  id: string;
  buyer_id: string;
  buyer_email: string;
  buyer_name: string;
  product_name: string;
  title: string;
  category_id?: string | null;
  category_name?: string | null;
  required_quantity: string | number;
  remaining_quantity: string | number;
  unit: string;
  target_price_per_unit?: string | number | null;
  price_condition: string;
  required_by_date: string;
  status: string;
  is_deleted: boolean;
  deleted_at?: string | null;
  reports_count: number;
  created_at: string;
  updated_at: string;
}

export interface AdminRequirementListResponse {
  items: AdminRequirementSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminRequirementModerateRequest {
  action: AdminCatalogAction | string;
  reason: string;
}

export interface AdminRequirementModerateResponse {
  requirement: AdminRequirementSummary;
  action: string;
  previous_status: string;
  new_status: string;
  is_deleted: boolean;
  audit_log_id: string;
  reason: string;
  updated_at: string;
}

export interface AdminRequirementFilterParams {
  search?: string;
  status?: string;
  category_id?: string;
  buyer_id?: string;
  is_deleted?: boolean;
  has_reports?: boolean;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

// ---------------------------------------------------------------------------
// 4. Safety Reports Moderation
// ---------------------------------------------------------------------------

export interface AdminReportFilterParams {
  status?: string;
  category?: string;
  page?: number;
  page_size?: number;
}

export interface AdminReportModerateRequest {
  status: "under_review" | "action_taken" | "dismissed" | string;
  admin_notes: string;
}

// ---------------------------------------------------------------------------
// 5. Payment Dispute Complaints Moderation
// ---------------------------------------------------------------------------

export interface AdminPaymentComplaintFilterParams {
  status?: string;
  limit?: number;
  offset?: number;
}

export interface AdminComplaintResolveRequest {
  status?: "under_review" | "resolved" | "dismissed" | string;
  resolution_action?: string;
  admin_resolution_notes?: string;
  resolution_notes?: string;
}

export interface AdminPaymentComplaintDetail {
  complaint: PaymentComplaint;
  payment: PaymentRecord;
  order_id: string;
  order_number: string;
  buyer_id: string;
  farmer_id: string;
  order?: {
    id: string;
    order_number: string;
    buyer_id: string;
    farmer_id: string;
  } | null;
}

// ---------------------------------------------------------------------------
// 6. Verification Review Queue & Actions
// ---------------------------------------------------------------------------

export interface AdminVerificationFilterParams {
  status?: string;
  role?: string;
  page?: number;
  page_size?: number;
}

export interface AdminVerificationListResponse {
  items: VerificationSubmission[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminVerificationApproveRequest {
  approval_notes?: string;
}

export interface AdminVerificationRejectRequest {
  rejection_reason: string;
}

// ---------------------------------------------------------------------------
// 7. Platform-Wide Analytics
// ---------------------------------------------------------------------------

export interface PlatformListedSupplyOverview {
  active_listings_count: number;
  total_active_quantity_by_unit: Record<string, string | number>;
  total_active_listed_value: string | number;
}

export interface PlatformBuyerDemandOverview {
  active_requirements_count: number;
  total_demanded_quantity_by_unit: Record<string, string | number>;
  total_approved_fulfilled_quantity_by_unit: Record<string, string | number>;
}

export interface PlatformPaymentVelocity {
  total_payments: number;
  acknowledged_payments: number;
  disputed_payments: number;
  pending_payments: number;
  average_settlement_delay_hours?: number | null;
  dispute_rate?: number | null;
}

export interface PlatformUserEngagement {
  total_users: number;
  verified_farmers: number;
  verified_buyers: number;
  unverified_users: number;
  admin_users: number;
}

export interface PlatformOrderOutcomeBreakdown {
  total_orders: number;
  pending_confirmation: number;
  in_progress: number;
  completed: number;
  cancelled: number;
  currently_disputed: number;
  completed_order_share?: number | null;
  in_progress_share?: number | null;
  pending_share?: number | null;
  dispute_frequency?: number | null;
  cancelled_order_share?: number | null;
  concluded_orders: number;
  concluded_completion_rate?: number | null;
  concluded_cancellation_rate?: number | null;
}

export interface PlatformAnalyticsResponse {
  generated_at: string;
  platform_gmv: string | number;
  pipeline_gmv: string | number;
  listed_supply_overview: PlatformListedSupplyOverview;
  buyer_demand_overview: PlatformBuyerDemandOverview;
  order_outcomes: PlatformOrderOutcomeBreakdown;
  payment_velocity: PlatformPaymentVelocity;
  user_engagement: PlatformUserEngagement;
}

