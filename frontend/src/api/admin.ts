/**
 * Administrative API service for platform governance, user moderation,
 * catalog management, dispute facilitation, and identity reviews (Module 10 & Stage 6).
 *
 * Connects to FastAPI endpoints under /api/v1/admin, /api/v1/analytics/admin/platform,
 * /api/v1/admin/reports, /api/v1/admin/payment-complaints, and /api/v1/admin/verifications.
 */

import { ApiClient, apiClient } from "./client";
import type {
  AdminAuditLog,
  AdminAuditLogFilterParams,
  AdminAuditLogListResponse,
  AdminComplaintResolveRequest,
  AdminListingFilterParams,
  AdminListingListResponse,
  AdminListingModerateRequest,
  AdminListingModerateResponse,
  AdminPaymentComplaintDetail,
  AdminPaymentComplaintFilterParams,
  AdminReportFilterParams,
  AdminReportModerateRequest,
  AdminRequirementFilterParams,
  AdminRequirementListResponse,
  AdminRequirementModerateRequest,
  AdminRequirementModerateResponse,
  AdminUserDetail,
  AdminUserFilterParams,
  AdminUserListResponse,
  AdminUserStatusUpdateRequest,
  AdminUserStatusUpdateResponse,
  AdminVerificationApproveRequest,
  AdminVerificationFilterParams,
  AdminVerificationListResponse,
  AdminVerificationRejectRequest,
  PlatformAnalyticsResponse,
} from "../types/admin";
import type { PaymentComplaint, PaymentComplaintListResponse } from "../types/payments";
import type { ReportItem, ReportListResponse } from "../types/reports";
import type { VerificationSubmission } from "../types/verification";

function buildQueryString(params?: Record<string, unknown>): string {
  if (!params) return "";
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export class AdminApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  // ===========================================================================
  // 1. Platform Analytics
  // ===========================================================================

  /**
   * Retrieve platform-wide operational, GMV, supply, demand, and user engagement analytics.
   */
  public async getPlatformAnalytics(): Promise<PlatformAnalyticsResponse> {
    return this.client.get<PlatformAnalyticsResponse>("/analytics/admin/platform");
  }

  // ===========================================================================
  // 2. User Directory & Status Moderation
  // ===========================================================================

  /**
   * List platform users with administrative filters, search, and pagination.
   */
  public async listUsers(params?: AdminUserFilterParams): Promise<AdminUserListResponse> {
    const qs = buildQueryString(params as Record<string, unknown>);
    return this.client.get<AdminUserListResponse>(`/admin/users${qs}`);
  }

  /**
   * Retrieve detailed inspection profile for a specific user.
   */
  public async getUserDetail(userId: string): Promise<AdminUserDetail> {
    return this.client.get<AdminUserDetail>(`/admin/users/${userId}`);
  }

  /**
   * Update a user's account status (active, restricted, suspended, blocked) with rationale.
   */
  public async updateUserStatus(
    userId: string,
    payload: AdminUserStatusUpdateRequest
  ): Promise<AdminUserStatusUpdateResponse> {
    return this.client.patch<AdminUserStatusUpdateResponse>(`/admin/users/${userId}/status`, payload);
  }

  // ===========================================================================
  // 3. Catalog Moderation (Produce Listings)
  // ===========================================================================

  /**
   * List produce listings for administrative moderation queue.
   */
  public async listListings(params?: AdminListingFilterParams): Promise<AdminListingListResponse> {
    const qs = buildQueryString(params as Record<string, unknown>);
    return this.client.get<AdminListingListResponse>(`/admin/listings${qs}`);
  }

  /**
   * Apply moderation action (close, remove, restore) to a produce listing.
   */
  public async moderateListing(
    listingId: string,
    payload: AdminListingModerateRequest
  ): Promise<AdminListingModerateResponse> {
    return this.client.post<AdminListingModerateResponse>(`/admin/listings/${listingId}/moderate`, payload);
  }

  // ===========================================================================
  // 4. Catalog Moderation (Buyer Requirements)
  // ===========================================================================

  /**
   * List buyer requirements for administrative moderation queue.
   */
  public async listRequirements(params?: AdminRequirementFilterParams): Promise<AdminRequirementListResponse> {
    const qs = buildQueryString(params as Record<string, unknown>);
    return this.client.get<AdminRequirementListResponse>(`/admin/requirements${qs}`);
  }

  /**
   * Apply moderation action (close, remove, restore) to a buyer requirement.
   */
  public async moderateRequirement(
    requirementId: string,
    payload: AdminRequirementModerateRequest
  ): Promise<AdminRequirementModerateResponse> {
    return this.client.post<AdminRequirementModerateResponse>(`/admin/requirements/${requirementId}/moderate`, payload);
  }

  // ===========================================================================
  // 5. Safety Reports Moderation
  // ===========================================================================

  /**
   * List user safety, fraud, or conduct reports for moderation.
   */
  public async listReports(params?: AdminReportFilterParams): Promise<ReportListResponse> {
    const qs = buildQueryString(params as Record<string, unknown>);
    return this.client.get<ReportListResponse>(`/admin/reports${qs}`);
  }

  /**
   * Inspect single safety report details as administrator.
   */
  public async getReport(reportId: string): Promise<ReportItem> {
    return this.client.get<ReportItem>(`/admin/reports/${reportId}`);
  }

  /**
   * Moderate safety report with status transition and administrative findings.
   */
  public async moderateReport(
    reportId: string,
    payload: AdminReportModerateRequest
  ): Promise<ReportItem> {
    return this.client.post<ReportItem>(`/admin/reports/${reportId}/moderate`, payload);
  }

  // ===========================================================================
  // 6. Payment Dispute Complaints Moderation
  // ===========================================================================

  /**
   * List off-platform payment dispute complaints in administrative moderation queue.
   */
  public async listPaymentComplaints(
    params?: AdminPaymentComplaintFilterParams
  ): Promise<PaymentComplaintListResponse> {
    const qs = buildQueryString(params as Record<string, unknown>);
    return this.client.get<PaymentComplaintListResponse>(`/admin/payment-complaints${qs}`);
  }

  /**
   * Inspect detailed payment complaint with associated payment claim and counterparty order.
   */
  public async getPaymentComplaintDetail(
    complaintId: string
  ): Promise<AdminPaymentComplaintDetail> {
    return this.client.get<AdminPaymentComplaintDetail>(`/admin/payment-complaints/${complaintId}`);
  }

  /**
   * Resolve or update payment complaint dispute status with facilitation remarks.
   */
  public async resolvePaymentComplaint(
    complaintId: string,
    payload: AdminComplaintResolveRequest
  ): Promise<PaymentComplaint> {
    return this.client.post<PaymentComplaint>(
      `/admin/payment-complaints/${complaintId}/resolve`,
      payload
    );
  }

  // ===========================================================================
  // 7. Identity Verification Queue & Decisions
  // ===========================================================================

  /**
   * List pending and historical identity verification submissions for review.
   */
  public async listVerifications(
    params?: AdminVerificationFilterParams
  ): Promise<AdminVerificationListResponse> {
    const qs = buildQueryString(params as Record<string, unknown>);
    return this.client.get<AdminVerificationListResponse>(`/admin/verifications${qs}`);
  }

  /**
   * Inspect verification application with applicant profile and attached evidence documents.
   */
  public async getVerification(verificationId: string): Promise<VerificationSubmission> {
    return this.client.get<VerificationSubmission>(`/admin/verifications/${verificationId}`);
  }

  /**
   * Download an applicant's evidence document for administrative inspection.
   */
  public async downloadVerificationDocument(
    submissionId: string,
    documentId: string
  ): Promise<{ blob: Blob; filename?: string; mimeType: string }> {
    return this.client.downloadBlob(
      `/admin/verifications/${submissionId}/documents/${documentId}/download`
    );
  }

  /**
   * Approve a pending verification submission.
   */
  public async approveVerification(
    submissionId: string,
    payload?: AdminVerificationApproveRequest
  ): Promise<VerificationSubmission> {
    return this.client.post<VerificationSubmission>(
      `/admin/verifications/${submissionId}/approve`,
      payload || {}
    );
  }

  /**
   * Reject a pending verification submission with a mandatory reason.
   */
  public async rejectVerification(
    submissionId: string,
    payload: AdminVerificationRejectRequest
  ): Promise<VerificationSubmission> {
    return this.client.post<VerificationSubmission>(
      `/admin/verifications/${submissionId}/reject`,
      payload
    );
  }

  // ===========================================================================
  // 8. Governance Audit Trail
  // ===========================================================================

  /**
   * List immutable administrative audit log records with filtering and pagination.
   */
  public async listAuditLogs(
    params?: AdminAuditLogFilterParams
  ): Promise<AdminAuditLogListResponse> {
    const qs = buildQueryString(params as Record<string, unknown>);
    return this.client.get<AdminAuditLogListResponse>(`/admin/audit-logs${qs}`);
  }

  /**
   * Retrieve a single administrative audit log entry by its primary key.
   */
  public async getAuditLog(logId: string): Promise<AdminAuditLog> {
    return this.client.get<AdminAuditLog>(`/admin/audit-logs/${logId}`);
  }
}

export const adminApi = new AdminApi();

