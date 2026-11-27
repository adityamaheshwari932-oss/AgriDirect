import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AdminUserDetailModal } from "./AdminUserDetailModal";
import { adminApi } from "../../api/admin";
import type { AdminUserDetail } from "../../types/admin";

vi.mock("../../api/admin", () => ({
  adminApi: {
    getUserDetail: vi.fn(),
  },
}));

describe("AdminUserDetailModal — D-3 Safe Audit Logs Regression Tests", () => {
  const baseDetail: AdminUserDetail = {
    id: "usr-farmer-01",
    email: "farmer@agridirect.in",
    phone_number: "+91 98765 43210",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-01-15T10:00:00Z",
    updated_at: "2026-01-15T10:00:00Z",
    farmer_profile: {
      id: "fp-1",
      full_name: "Ramesh Patel",
      farm_name: "Patel Farms",
      farm_location_address: "Village Narsinghpur",
      city: "Narsinghpur",
      state: "Madhya Pradesh",
      postal_code: "487001",
      farm_size_acres: 25,
      farming_practices: "Organic",
      primary_crops: "Wheat, Soybean",
      created_at: "2026-01-15T10:00:00Z",
      updated_at: "2026-01-15T10:00:00Z",
    },
    buyer_profile: null,
    verification_summary: null,
    activity_counts: {
      listings_count: 5,
      requirements_count: 0,
      completed_orders_count: 8,
      reports_filed_count: 0,
      reports_received_count: 0,
    },
    recent_audit_logs: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders non-empty audit logs correctly", async () => {
    const detailWithLogs: AdminUserDetail = {
      ...baseDetail,
      recent_audit_logs: [
        {
          id: "log-1",
          admin_user_id: "adm-101",
          action: "VERIFICATION_APPROVED",
          target_entity_type: "user",
          target_entity_id: "usr-farmer-01",
          reason: "All government land records audited and verified",
          ip_address: "192.168.1.1",
          created_at: "2026-02-01T12:00:00Z",
        },
      ],
    };

    vi.mocked(adminApi.getUserDetail).mockResolvedValue(detailWithLogs);

    render(
      <AdminUserDetailModal
        userId="usr-farmer-01"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("farmer@agridirect.in")).toBeInTheDocument();
    });

    expect(screen.getByText("Recent Governance Audit Trail")).toBeInTheDocument();
    expect(screen.getByText("VERIFICATION_APPROVED")).toBeInTheDocument();
    expect(
      screen.getByText('"All government land records audited and verified"')
    ).toBeInTheDocument();
    expect(screen.getByText(/adm-101/)).toBeInTheDocument();
    expect(screen.getByText(/192.168.1.1/)).toBeInTheDocument();
  });

  it("renders empty-state gracefully when recent_audit_logs is an empty array", async () => {
    vi.mocked(adminApi.getUserDetail).mockResolvedValue({
      ...baseDetail,
      recent_audit_logs: [],
    });

    render(
      <AdminUserDetailModal
        userId="usr-farmer-01"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("farmer@agridirect.in")).toBeInTheDocument();
    });

    expect(screen.getByText("Recent Governance Audit Trail")).toBeInTheDocument();
    expect(screen.getByText("No audit logs found")).toBeInTheDocument();
  });

  it("renders empty-state safely without runtime crash when recent_audit_logs is null", async () => {
    vi.mocked(adminApi.getUserDetail).mockResolvedValue({
      ...baseDetail,
      recent_audit_logs: null as unknown as AdminUserDetail["recent_audit_logs"],
    });

    render(
      <AdminUserDetailModal
        userId="usr-farmer-01"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("farmer@agridirect.in")).toBeInTheDocument();
    });

    expect(screen.getByText("Recent Governance Audit Trail")).toBeInTheDocument();
    expect(screen.getByText("No audit logs found")).toBeInTheDocument();
  });

  it("renders empty-state safely without runtime crash when recent_audit_logs is undefined/omitted", async () => {
    const { recent_audit_logs: _omittedAuditLogs, ...detailWithoutLogs } = baseDetail;

    vi.mocked(adminApi.getUserDetail).mockResolvedValue(
      detailWithoutLogs as unknown as AdminUserDetail
    );

    render(
      <AdminUserDetailModal
        userId="usr-farmer-01"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("farmer@agridirect.in")).toBeInTheDocument();
    });

    expect(screen.getByText("Recent Governance Audit Trail")).toBeInTheDocument();
    expect(screen.getByText("No audit logs found")).toBeInTheDocument();
  });

  it("renders empty-state safely without runtime crash when recent_audit_logs is an unexpected non-array", async () => {
    vi.mocked(adminApi.getUserDetail).mockResolvedValue({
      ...baseDetail,
      recent_audit_logs: "invalid-string" as unknown as AdminUserDetail["recent_audit_logs"],
    });

    render(
      <AdminUserDetailModal
        userId="usr-farmer-01"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("farmer@agridirect.in")).toBeInTheDocument();
    });

    expect(screen.getByText("Recent Governance Audit Trail")).toBeInTheDocument();
    expect(screen.getByText("No audit logs found")).toBeInTheDocument();
  });
});
