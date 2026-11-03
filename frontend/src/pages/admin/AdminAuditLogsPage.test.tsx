import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AdminAuditLogsPage } from "./AdminAuditLogsPage";
import { adminApi } from "../../api/admin";
import type { AdminAuditLog, AdminAuditLogListResponse } from "../../types/admin";

vi.mock("../../api/admin", () => ({
  adminApi: {
    listAuditLogs: vi.fn(),
    getAuditLog: vi.fn(),
  },
}));

describe("AdminAuditLogsPage", () => {
  const mockLogs: AdminAuditLog[] = [
    {
      id: "audit-entry-001",
      admin_user_id: "admin-uuid-1",
      action: "user_status_update",
      target_entity_type: "user",
      target_entity_id: "user-target-42",
      reason: "Account suspended due to counterfeit produce dispute findings.",
      ip_address: "192.168.1.100",
      created_at: "2026-04-12T14:30:00Z",
    },
    {
      id: "audit-entry-002",
      admin_user_id: "admin-uuid-1",
      action: "listing_moderation_close",
      target_entity_type: "listing",
      target_entity_id: "listing-target-88",
      reason: "Listing closed per commercial policy violation.",
      ip_address: "192.168.1.100",
      created_at: "2026-04-12T15:00:00Z",
    },
  ];

  const mockListResponse: AdminAuditLogListResponse = {
    items: mockLogs,
    total: 2,
    page: 1,
    page_size: 20,
    total_pages: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders audit log records and page header", async () => {
    vi.mocked(adminApi.listAuditLogs).mockResolvedValueOnce(mockListResponse);

    render(<AdminAuditLogsPage />);

    expect(screen.getByText("Platform Governance Audit Trail")).toBeInTheDocument();
    expect(screen.getByText("Strictly Read-Only Trail")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("user_status_update")).toBeInTheDocument();
      expect(screen.getByText("listing_moderation_close")).toBeInTheDocument();
    });
  });

  it("applies action and target entity filters", async () => {
    vi.mocked(adminApi.listAuditLogs).mockResolvedValue(mockListResponse);

    render(<AdminAuditLogsPage />);

    await waitFor(() => {
      expect(screen.getByText("user_status_update")).toBeInTheDocument();
    });

    const actionInput = screen.getByPlaceholderText(/e\.g\. user_status_update/i);
    fireEvent.change(actionInput, { target: { value: "user_status_update" } });

    const filterBtn = screen.getByRole("button", { name: "Filter" });
    fireEvent.click(filterBtn);

    expect(adminApi.listAuditLogs).toHaveBeenCalledWith(
      expect.objectContaining({
        action: "user_status_update",
      })
    );
  });

  it("opens AdminAuditLogDetailModal and displays immutable record details with no edit controls", async () => {
    vi.mocked(adminApi.listAuditLogs).mockResolvedValueOnce(mockListResponse);

    render(<AdminAuditLogsPage />);

    await waitFor(() => {
      expect(screen.getByLabelText("Inspect audit log audit-entry-001")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("Inspect audit log audit-entry-001"));

    await waitFor(() => {
      expect(screen.getByText("Audit Trail Record")).toBeInTheDocument();
      expect(screen.getByText("audit-entry-001")).toBeInTheDocument();
      expect(
        screen.getAllByText("Account suspended due to counterfeit produce dispute findings.")
          .length
      ).toBeGreaterThanOrEqual(1);
      expect(
        screen.getByText(/modifications and deletions are strictly disabled/i)
      ).toBeInTheDocument();
    });

    // Verify strictly read-only: no edit/delete/save buttons exist
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save/i })).not.toBeInTheDocument();
  });
});

