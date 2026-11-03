import { beforeEach, describe, expect, it, vi } from "vitest";
import { adminApi, AdminApi } from "./admin";
import { apiClient } from "./client";
import { ApiError } from "./errors";
import type {
  AdminAuditLog,
  AdminAuditLogListResponse,
  AdminListingListResponse,
  AdminListingModerateResponse,
  AdminPaymentComplaintDetail,
  AdminRequirementListResponse,
  AdminRequirementModerateResponse,
  AdminUserDetail,
  AdminUserListResponse,
  AdminUserStatusUpdateResponse,
  AdminVerificationListResponse,
  PlatformAnalyticsResponse,
} from "../types/admin";
import type { PaymentComplaint, PaymentComplaintListResponse } from "../types/payments";
import type { ReportItem, ReportListResponse } from "../types/reports";
import type { VerificationSubmission } from "../types/verification";

describe("AdminApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // 1. Platform Analytics
  // ===========================================================================

  describe("Platform Analytics", () => {
    it("getPlatformAnalytics requests /analytics/admin/platform and returns data", async () => {
      const mockAnalytics: PlatformAnalyticsResponse = {
        generated_at: "2026-11-03T23:00:00Z",
        platform_gmv: "1500000.00",
        pipeline_gmv: "350000.00",
        listed_supply_overview: {
          active_listings_count: 42,
          total_active_quantity_by_unit: { kg: "12500.000" },
          total_active_listed_value: "625000.00",
        },
        buyer_demand_overview: {
          active_requirements_count: 18,
          total_demanded_quantity_by_unit: { kg: "9800.000" },
          total_approved_fulfilled_quantity_by_unit: { kg: "24000.000" },
        },
        order_outcomes: {
          total_orders: 85,
          pending_confirmation: 5,
          in_progress: 10,
          completed: 65,
          cancelled: 5,
          currently_disputed: 2,
          concluded_orders: 70,
          concluded_completion_rate: 92.86,
          concluded_cancellation_rate: 7.14,
        },
        payment_velocity: {
          total_payments: 95,
          acknowledged_payments: 88,
          disputed_payments: 3,
          pending_payments: 4,
          average_settlement_delay_hours: 6.5,
          dispute_rate: 0.031,
        },
        user_engagement: {
          total_users: 120,
          verified_farmers: 55,
          verified_buyers: 45,
          unverified_users: 15,
          admin_users: 5,
        },
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockAnalytics);

      const result = await adminApi.getPlatformAnalytics();
      expect(apiClient.get).toHaveBeenCalledWith("/analytics/admin/platform");
      expect(result).toEqual(mockAnalytics);
    });

    it("propagates errors on platform analytics failure", async () => {
      vi.spyOn(apiClient, "get").mockRejectedValueOnce(new ApiError(403, "Administrator access required"));

      await expect(adminApi.getPlatformAnalytics()).rejects.toThrow("Administrator access required");
    });
  });

  // ===========================================================================
  // 2. User Directory & Moderation
  // ===========================================================================

  describe("User Management", () => {
    it("listUsers calls /admin/users without query params when none provided", async () => {
      const mockUsersResponse: AdminUserListResponse = {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockUsersResponse);

      const result = await adminApi.listUsers();
      expect(apiClient.get).toHaveBeenCalledWith("/admin/users");
      expect(result).toEqual(mockUsersResponse);
    });

    it("listUsers formats all query parameters correctly", async () => {
      const mockUsersResponse: AdminUserListResponse = {
        items: [
          {
            id: "user-1",
            email: "farmer@example.com",
            phone_number: "+919876543210",
            role: "farmer",
            verification_status: "verified",
            account_status: "active",
            display_name: "Ramesh Kumar",
            created_at: "2026-10-01T00:00:00Z",
            updated_at: "2026-10-01T00:00:00Z",
          },
        ],
        total: 1,
        page: 2,
        page_size: 10,
        total_pages: 1,
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockUsersResponse);

      const result = await adminApi.listUsers({
        search: "Ramesh",
        role: "farmer",
        account_status: "active",
        verification_status: "verified",
        registered_from: "2026-10-01",
        registered_to: "2026-10-31",
        page: 2,
        page_size: 10,
        sort_by: "email",
        sort_order: "asc",
      });

      expect(apiClient.get).toHaveBeenCalledWith(
        "/admin/users?search=Ramesh&role=farmer&account_status=active&verification_status=verified&registered_from=2026-10-01&registered_to=2026-10-31&page=2&page_size=10&sort_by=email&sort_order=asc"
      );
      expect(result).toEqual(mockUsersResponse);
    });

    it("getUserDetail fetches /admin/users/:id", async () => {
      const mockDetail: AdminUserDetail = {
        id: "user-123",
        email: "buyer@example.com",
        role: "buyer",
        verification_status: "verified",
        account_status: "active",
        created_at: "2026-10-01T00:00:00Z",
        updated_at: "2026-10-01T00:00:00Z",
        activity_counts: {
          listings_count: 0,
          requirements_count: 12,
          completed_orders_count: 8,
          reports_filed_count: 0,
          reports_received_count: 0,
        },
        recent_audit_logs: [],
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockDetail);

      const result = await adminApi.getUserDetail("user-123");
      expect(apiClient.get).toHaveBeenCalledWith("/admin/users/user-123");
      expect(result).toEqual(mockDetail);
    });

    it("updateUserStatus sends PATCH to /admin/users/:id/status", async () => {
      const mockUpdateResponse: AdminUserStatusUpdateResponse = {
        user: {
          id: "user-123",
          email: "buyer@example.com",
          role: "buyer",
          verification_status: "verified",
          account_status: "suspended",
          display_name: "Buyer Entity",
          created_at: "2026-10-01T00:00:00Z",
          updated_at: "2026-11-03T00:00:00Z",
        },
        previous_status: "active",
        new_status: "suspended",
        audit_log_id: "audit-999",
        reason: "Administrative suspension pending investigation",
        updated_at: "2026-11-03T00:00:00Z",
      };

      vi.spyOn(apiClient, "patch").mockResolvedValueOnce(mockUpdateResponse);

      const payload = {
        account_status: "suspended",
        reason: "Administrative suspension pending investigation",
      };

      const result = await adminApi.updateUserStatus("user-123", payload);
      expect(apiClient.patch).toHaveBeenCalledWith("/admin/users/user-123/status", payload);
      expect(result).toEqual(mockUpdateResponse);
    });
  });

  // ===========================================================================
  // 3. Catalog Moderation (Produce Listings)
  // ===========================================================================

  describe("Produce Listing Moderation", () => {
    it("listListings calls /admin/listings with filters", async () => {
      const mockListingsResponse: AdminListingListResponse = {
        items: [
          {
            id: "listing-1",
            farmer_id: "farmer-1",
            farmer_email: "farmer@example.com",
            farmer_name: "Farmer John",
            product_name: "Organic Wheat",
            title: "Premium Sharbati Wheat",
            initial_quantity: 500,
            available_quantity: 250,
            unit: "kg",
            price_per_unit: 45,
            status: "active",
            is_deleted: false,
            expires_at: "2026-12-31T00:00:00Z",
            reports_count: 1,
            created_at: "2026-10-15T00:00:00Z",
            updated_at: "2026-10-15T00:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockListingsResponse);

      const result = await adminApi.listListings({
        search: "Wheat",
        status: "active",
        has_reports: true,
      });

      expect(apiClient.get).toHaveBeenCalledWith("/admin/listings?search=Wheat&status=active&has_reports=true");
      expect(result).toEqual(mockListingsResponse);
    });

    it("moderateListing sends POST to /admin/listings/:id/moderate", async () => {
      const mockModerateResponse: AdminListingModerateResponse = {
        listing: {
          id: "listing-1",
          farmer_id: "farmer-1",
          farmer_email: "farmer@example.com",
          farmer_name: "Farmer John",
          product_name: "Organic Wheat",
          title: "Premium Sharbati Wheat",
          initial_quantity: 500,
          available_quantity: 250,
          unit: "kg",
          price_per_unit: 45,
          status: "closed",
          is_deleted: false,
          expires_at: "2026-12-31T00:00:00Z",
          reports_count: 1,
          created_at: "2026-10-15T00:00:00Z",
          updated_at: "2026-11-03T00:00:00Z",
        },
        action: "close",
        previous_status: "active",
        new_status: "closed",
        is_deleted: false,
        audit_log_id: "audit-123",
        reason: "Listing closed due to multiple user complaints",
        updated_at: "2026-11-03T00:00:00Z",
      };

      vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockModerateResponse);

      const payload = {
        action: "close",
        reason: "Listing closed due to multiple user complaints",
      };

      const result = await adminApi.moderateListing("listing-1", payload);
      expect(apiClient.post).toHaveBeenCalledWith("/admin/listings/listing-1/moderate", payload);
      expect(result).toEqual(mockModerateResponse);
    });
  });

  // ===========================================================================
  // 4. Catalog Moderation (Buyer Requirements)
  // ===========================================================================

  describe("Buyer Requirement Moderation", () => {
    it("listRequirements calls /admin/requirements with filters", async () => {
      const mockRequirementsResponse: AdminRequirementListResponse = {
        items: [
          {
            id: "req-1",
            buyer_id: "buyer-1",
            buyer_email: "buyer@example.com",
            buyer_name: "AgriCorp Procurements",
            product_name: "Basmati Rice",
            title: "Basmati Rice 1121 Wanted",
            required_quantity: 2000,
            remaining_quantity: 1500,
            unit: "kg",
            price_condition: "negotiable",
            required_by_date: "2026-12-01",
            status: "active",
            is_deleted: false,
            reports_count: 0,
            created_at: "2026-10-20T00:00:00Z",
            updated_at: "2026-10-20T00:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockRequirementsResponse);

      const result = await adminApi.listRequirements({
        status: "active",
        buyer_id: "buyer-1",
      });

      expect(apiClient.get).toHaveBeenCalledWith("/admin/requirements?status=active&buyer_id=buyer-1");
      expect(result).toEqual(mockRequirementsResponse);
    });

    it("moderateRequirement sends POST to /admin/requirements/:id/moderate", async () => {
      const mockModerateResponse: AdminRequirementModerateResponse = {
        requirement: {
          id: "req-1",
          buyer_id: "buyer-1",
          buyer_email: "buyer@example.com",
          buyer_name: "AgriCorp Procurements",
          product_name: "Basmati Rice",
          title: "Basmati Rice 1121 Wanted",
          required_quantity: 2000,
          remaining_quantity: 1500,
          unit: "kg",
          price_condition: "negotiable",
          required_by_date: "2026-12-01",
          status: "closed",
          is_deleted: true,
          reports_count: 0,
          created_at: "2026-10-20T00:00:00Z",
          updated_at: "2026-11-03T00:00:00Z",
        },
        action: "remove",
        previous_status: "active",
        new_status: "closed",
        is_deleted: true,
        audit_log_id: "audit-456",
        reason: "Administrative removal per buyer request",
        updated_at: "2026-11-03T00:00:00Z",
      };

      vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockModerateResponse);

      const payload = {
        action: "remove",
        reason: "Administrative removal per buyer request",
      };

      const result = await adminApi.moderateRequirement("req-1", payload);
      expect(apiClient.post).toHaveBeenCalledWith("/admin/requirements/req-1/moderate", payload);
      expect(result).toEqual(mockModerateResponse);
    });
  });

  // ===========================================================================
  // 5. Safety Reports Moderation
  // ===========================================================================

  describe("Safety Reports Moderation", () => {
    it("listReports calls /admin/reports with query params", async () => {
      const mockReportsResponse: ReportListResponse = {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockReportsResponse);

      const result = await adminApi.listReports({ status: "open", category: "fraud" });
      expect(apiClient.get).toHaveBeenCalledWith("/admin/reports?status=open&category=fraud");
      expect(result).toEqual(mockReportsResponse);
    });

    it("getReport calls /admin/reports/:id", async () => {
      const mockReport: ReportItem = {
        id: "rep-123",
        reporter_id: "user-1",
        category: "fraud",
        description: "Payment slip manipulation suspected",
        status: "open",
        created_at: "2026-10-25T00:00:00Z",
        updated_at: "2026-10-25T00:00:00Z",
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockReport);

      const result = await adminApi.getReport("rep-123");
      expect(apiClient.get).toHaveBeenCalledWith("/admin/reports/rep-123");
      expect(result).toEqual(mockReport);
    });

    it("moderateReport sends POST to /admin/reports/:id/moderate", async () => {
      const mockUpdatedReport: ReportItem = {
        id: "rep-123",
        reporter_id: "user-1",
        category: "fraud",
        description: "Payment slip manipulation suspected",
        status: "action_taken",
        admin_notes: "Investigation completed and user suspended",
        created_at: "2026-10-25T00:00:00Z",
        updated_at: "2026-11-03T00:00:00Z",
      };

      vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockUpdatedReport);

      const payload = {
        status: "action_taken",
        admin_notes: "Investigation completed and user suspended",
      };

      const result = await adminApi.moderateReport("rep-123", payload);
      expect(apiClient.post).toHaveBeenCalledWith("/admin/reports/rep-123/moderate", payload);
      expect(result).toEqual(mockUpdatedReport);
    });
  });

  // ===========================================================================
  // 6. Payment Dispute Complaints Moderation
  // ===========================================================================

  describe("Payment Dispute Complaints Moderation", () => {
    it("listPaymentComplaints calls /admin/payment-complaints with pagination and status", async () => {
      const mockComplaintsResponse: PaymentComplaintListResponse = {
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockComplaintsResponse);

      const result = await adminApi.listPaymentComplaints({ status: "under_review", limit: 25, offset: 50 });
      expect(apiClient.get).toHaveBeenCalledWith("/admin/payment-complaints?status=under_review&limit=25&offset=50");
      expect(result).toEqual(mockComplaintsResponse);
    });

    it("getPaymentComplaintDetail calls /admin/payment-complaints/:id", async () => {
      const mockDetail: AdminPaymentComplaintDetail = {
        complaint: {
          id: "comp-1",
          payment_record_id: "pay-1",
          complainant_user_id: "user-farmer",
          complaint_reason: "Amount not credited to account",
          has_evidence: true,
          status: "open",
          created_at: "2026-10-26T00:00:00Z",
          updated_at: "2026-10-26T00:00:00Z",
        },
        payment: {
          id: "pay-1",
          order_id: "ord-1",
          recorded_by_user_id: "user-buyer",
          amount: "50000.00",
          payment_method: "bank_transfer",
          has_proof: true,
          status: "disputed",
          payment_date: "2026-10-25",
          has_historical_acknowledgement: false,
          created_at: "2026-10-25T00:00:00Z",
          updated_at: "2026-10-26T00:00:00Z",
        },
        order_id: "ord-1",
        order_number: "ORD-2026-0001",
        buyer_id: "user-buyer",
        farmer_id: "user-farmer",
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockDetail);

      const result = await adminApi.getPaymentComplaintDetail("comp-1");
      expect(apiClient.get).toHaveBeenCalledWith("/admin/payment-complaints/comp-1");
      expect(result).toEqual(mockDetail);
    });

    it("resolvePaymentComplaint sends POST to /admin/payment-complaints/:id/resolve", async () => {
      const mockResolved: PaymentComplaint = {
        id: "comp-1",
        payment_record_id: "pay-1",
        complainant_user_id: "user-farmer",
        complaint_reason: "Amount not credited to account",
        has_evidence: true,
        status: "resolved",
        admin_resolution_notes: "Bank confirmed settlement delayed due to clearing cycle",
        created_at: "2026-10-26T00:00:00Z",
        updated_at: "2026-11-03T00:00:00Z",
      };

      vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockResolved);

      const payload = {
        status: "resolved",
        admin_resolution_notes: "Bank confirmed settlement delayed due to clearing cycle",
      };

      const result = await adminApi.resolvePaymentComplaint("comp-1", payload);
      expect(apiClient.post).toHaveBeenCalledWith("/admin/payment-complaints/comp-1/resolve", payload);
      expect(result).toEqual(mockResolved);
    });
  });

  // ===========================================================================
  // 7. Identity Verification Queue & Decisions
  // ===========================================================================

  describe("Identity Verification Review", () => {
    it("listVerifications calls /admin/verifications with filters", async () => {
      const mockVerificationsResponse: AdminVerificationListResponse = {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockVerificationsResponse);

      const result = await adminApi.listVerifications({ status: "pending", role: "farmer" });
      expect(apiClient.get).toHaveBeenCalledWith("/admin/verifications?status=pending&role=farmer");
      expect(result).toEqual(mockVerificationsResponse);
    });

    it("getVerification calls /admin/verifications/:id", async () => {
      const mockSubmission: VerificationSubmission = {
        id: "ver-1",
        user_id: "user-farmer",
        status: "pending",
        created_at: "2026-10-27T00:00:00Z",
        updated_at: "2026-10-27T00:00:00Z",
        documents: [],
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockSubmission);

      const result = await adminApi.getVerification("ver-1");
      expect(apiClient.get).toHaveBeenCalledWith("/admin/verifications/ver-1");
      expect(result).toEqual(mockSubmission);
    });

    it("downloadVerificationDocument calls downloadBlob with document endpoint", async () => {
      const mockBlob = new Blob(["fake-pdf"], { type: "application/pdf" });
      vi.spyOn(apiClient, "downloadBlob").mockResolvedValueOnce({
        blob: mockBlob,
        filename: "aadhaar.pdf",
        mimeType: "application/pdf",
      });

      const result = await adminApi.downloadVerificationDocument("ver-1", "doc-1");
      expect(apiClient.downloadBlob).toHaveBeenCalledWith(
        "/admin/verifications/ver-1/documents/doc-1/download"
      );
      expect(result.blob).toBe(mockBlob);
      expect(result.filename).toBe("aadhaar.pdf");
    });

    it("approveVerification sends POST to /admin/verifications/:id/approve", async () => {
      const mockApproved: VerificationSubmission = {
        id: "ver-1",
        user_id: "user-farmer",
        status: "approved",
        created_at: "2026-10-27T00:00:00Z",
        updated_at: "2026-11-03T00:00:00Z",
        documents: [],
      };

      vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockApproved);

      const payload = { approval_notes: "Identity documents verified successfully" };
      const result = await adminApi.approveVerification("ver-1", payload);

      expect(apiClient.post).toHaveBeenCalledWith("/admin/verifications/ver-1/approve", payload);
      expect(result).toEqual(mockApproved);
    });

    it("approveVerification defaults to empty body when payload omitted", async () => {
      const mockApproved: VerificationSubmission = {
        id: "ver-1",
        user_id: "user-farmer",
        status: "approved",
        created_at: "2026-10-27T00:00:00Z",
        updated_at: "2026-11-03T00:00:00Z",
        documents: [],
      };

      vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockApproved);

      const result = await adminApi.approveVerification("ver-1");
      expect(apiClient.post).toHaveBeenCalledWith("/admin/verifications/ver-1/approve", {});
      expect(result).toEqual(mockApproved);
    });

    it("rejectVerification sends POST to /admin/verifications/:id/reject with reason", async () => {
      const mockRejected: VerificationSubmission = {
        id: "ver-1",
        user_id: "user-farmer",
        status: "rejected",
        rejection_reason: "Document image is blurred and unreadable",
        created_at: "2026-10-27T00:00:00Z",
        updated_at: "2026-11-03T00:00:00Z",
        documents: [],
      };

      vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockRejected);

      const payload = { rejection_reason: "Document image is blurred and unreadable" };
      const result = await adminApi.rejectVerification("ver-1", payload);

      expect(apiClient.post).toHaveBeenCalledWith("/admin/verifications/ver-1/reject", payload);
      expect(result).toEqual(mockRejected);
    });
  });

  // ===========================================================================
  // 8. Governance Audit Trail
  // ===========================================================================

  describe("Governance Audit Trail", () => {
    it("listAuditLogs calls /admin/audit-logs with query params", async () => {
      const mockAuditLogsResponse: AdminAuditLogListResponse = {
        items: [
          {
            id: "audit-1",
            admin_user_id: "admin-1",
            action: "user_status_update",
            target_entity_type: "user",
            target_entity_id: "user-2",
            reason: "Account suspended for misconduct",
            ip_address: "127.0.0.1",
            created_at: "2026-11-03T10:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockAuditLogsResponse);

      const result = await adminApi.listAuditLogs({
        action: "user_status_update",
        target_entity_type: "user",
      });

      expect(apiClient.get).toHaveBeenCalledWith("/admin/audit-logs?action=user_status_update&target_entity_type=user");
      expect(result).toEqual(mockAuditLogsResponse);
    });

    it("getAuditLog calls /admin/audit-logs/:id", async () => {
      const mockLog: AdminAuditLog = {
        id: "audit-1",
        admin_user_id: "admin-1",
        action: "user_status_update",
        target_entity_type: "user",
        target_entity_id: "user-2",
        reason: "Account suspended for misconduct",
        ip_address: "127.0.0.1",
        created_at: "2026-11-03T10:00:00Z",
      };

      vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockLog);

      const result = await adminApi.getAuditLog("audit-1");
      expect(apiClient.get).toHaveBeenCalledWith("/admin/audit-logs/audit-1");
      expect(result).toEqual(mockLog);
    });
  });

  // ===========================================================================
  // Custom ApiClient Injection
  // ===========================================================================

  describe("Custom ApiClient Injection", () => {
    it("allows custom ApiClient to be passed to constructor", async () => {
      const customClient = {
        get: vi.fn().mockResolvedValue({ id: "log-xyz" }),
        post: vi.fn(),
        patch: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
        downloadBlob: vi.fn(),
      } as unknown as typeof apiClient;

      const customApi = new AdminApi(customClient);
      const res = await customApi.getAuditLog("log-xyz");

      expect(customClient.get).toHaveBeenCalledWith("/admin/audit-logs/log-xyz");
      expect(res).toEqual({ id: "log-xyz" });
    });
  });
});

