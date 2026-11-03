import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AdminUsersPage } from "./AdminUsersPage";
import { ToastProvider } from "../../components/ui/toast";
import { adminApi } from "../../api/admin";
import { authStore } from "../../store/authStore";
import type { AdminUserDetail, AdminUserListResponse, AdminUserSummary } from "../../types/admin";
import type { User } from "../../types";

vi.mock("../../api/admin", () => ({
  adminApi: {
    listUsers: vi.fn(),
    getUserDetail: vi.fn(),
    updateUserStatus: vi.fn(),
  },
}));

describe("AdminUsersPage", () => {
  const currentAdminUser: User = {
    id: "admin-self-id",
    email: "superadmin@agridirect.gov",
    role: "admin",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };

  const mockUsers: AdminUserSummary[] = [
    {
      id: "admin-self-id",
      email: "superadmin@agridirect.gov",
      display_name: "Super Admin",
      phone_number: "+919999999999",
      role: "admin",
      verification_status: "verified",
      account_status: "active",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    {
      id: "farmer-user-2",
      email: "ramesh@farm.test",
      display_name: "Ramesh Farmer",
      phone_number: "+919876543210",
      role: "farmer",
      verification_status: "verified",
      account_status: "active",
      organization_name: "Ramesh Agro Farms",
      location_summary: "Nagpur, Maharashtra",
      created_at: "2026-02-15T00:00:00Z",
      updated_at: "2026-02-15T00:00:00Z",
    },
    {
      id: "buyer-user-3",
      email: "procure@bigcorp.test",
      display_name: "BigCorp Procurements",
      phone_number: "+919123456789",
      role: "buyer",
      verification_status: "pending",
      account_status: "restricted",
      organization_name: "BigCorp Foods Ltd",
      location_summary: "Mumbai, Maharashtra",
      created_at: "2026-03-01T00:00:00Z",
      updated_at: "2026-03-01T00:00:00Z",
    },
  ];

  const mockListResponse: AdminUserListResponse = {
    items: mockUsers,
    total: 3,
    page: 1,
    page_size: 15,
    total_pages: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    authStore.reset();
    authStore.setUser(currentAdminUser);
  });

  const renderComponent = () =>
    render(
      <ToastProvider>
        <AdminUsersPage />
      </ToastProvider>
    );

  it("renders page header and list of users", async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValueOnce(mockListResponse);

    renderComponent();

    expect(screen.getByText("User Directory & Moderation")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("superadmin@agridirect.gov")).toBeInTheDocument();
      expect(screen.getByText("ramesh@farm.test")).toBeInTheDocument();
      expect(screen.getByText("procure@bigcorp.test")).toBeInTheDocument();
    });
  });

  it("applies role and search filters", async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(mockListResponse);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("superadmin@agridirect.gov")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search by email/i);
    fireEvent.change(searchInput, { target: { value: "Ramesh" } });

    const searchBtn = screen.getByRole("button", { name: /search directory/i });
    fireEvent.click(searchBtn);

    expect(adminApi.listUsers).toHaveBeenCalledWith(
      expect.objectContaining({
        search: "Ramesh",
      })
    );
  });

  it("opens AdminUserDetailModal and renders full profile", async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValueOnce(mockListResponse);

    const mockDetail: AdminUserDetail = {
      id: "farmer-user-2",
      email: "ramesh@farm.test",
      role: "farmer",
      verification_status: "verified",
      account_status: "active",
      created_at: "2026-02-15T00:00:00Z",
      updated_at: "2026-02-15T00:00:00Z",
      farmer_profile: {
        id: "fp-1",
        full_name: "Ramesh Farmer",
        farm_name: "Ramesh Agro Farms",
        farm_location_address: "Plot 42, Green Valley",
        city: "Nagpur",
        state: "Maharashtra",
        postal_code: "440001",
        farm_size_acres: 25,
        primary_crops: "Soybean, Cotton",
        farming_practices: "Organic certified",
        created_at: "2026-02-15T00:00:00Z",
        updated_at: "2026-02-15T00:00:00Z",
      },
      activity_counts: {
        listings_count: 5,
        requirements_count: 0,
        completed_orders_count: 14,
        reports_filed_count: 0,
        reports_received_count: 0,
      },
      recent_audit_logs: [],
    };

    vi.mocked(adminApi.getUserDetail).mockResolvedValueOnce(mockDetail);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByLabelText("Inspect user ramesh@farm.test")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("Inspect user ramesh@farm.test"));

    await waitFor(() => {
      expect(screen.getByText("User Inspection Details")).toBeInTheDocument();
      expect(screen.getByText("Farmer Agricultural Profile")).toBeInTheDocument();
      expect(screen.getByText("Soybean, Cotton")).toBeInTheDocument();
    });
  });

  it("prevents self-modification: Status button is disabled for logged-in admin", async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValueOnce(mockListResponse);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("superadmin@agridirect.gov")).toBeInTheDocument();
    });

    const selfStatusBtn = screen.getByLabelText("Moderate status of user superadmin@agridirect.gov");
    expect(selfStatusBtn).toBeDisabled();
    expect(selfStatusBtn).toHaveAttribute(
      "title",
      "Self-modification forbidden: You cannot modify your own administrator account status."
    );
  });

  it("opens AdminUserStatusModal for another user and successfully updates account status", async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(mockListResponse);
    vi.mocked(adminApi.updateUserStatus).mockResolvedValueOnce({
      user: {
        ...mockUsers[1],
        account_status: "suspended",
      },
      previous_status: "active",
      new_status: "suspended",
      audit_log_id: "audit-999",
      reason: "Policy violation regarding quality misrepresentation",
      updated_at: "2026-11-04T00:00:00Z",
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByLabelText("Moderate status of user ramesh@farm.test")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("Moderate status of user ramesh@farm.test"));

    await waitFor(() => {
      expect(screen.getByText("Moderate User Account Status")).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText(/new account status/i);
    fireEvent.change(statusSelect, { target: { value: "suspended" } });

    const reasonInput = screen.getByPlaceholderText(/provide a factual administrative explanation/i);
    fireEvent.change(reasonInput, {
      target: { value: "Policy violation regarding quality misrepresentation" },
    });

    // Consequential status change requires confirm step
    const submitBtn = screen.getByRole("button", { name: /update account status/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Confirm Consequential Moderation")).toBeInTheDocument();
    });

    const confirmBtn = screen.getByRole("button", { name: /confirm & apply/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(adminApi.updateUserStatus).toHaveBeenCalledWith("farmer-user-2", {
        account_status: "suspended",
        reason: "Policy violation regarding quality misrepresentation",
      });
    });
  });

  it("handles last-active-admin 400/409 conflict error display", async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(mockListResponse);
    vi.mocked(adminApi.updateUserStatus).mockRejectedValueOnce(
      new Error("Cannot deactivate or block the last active administrator")
    );

    renderComponent();

    await waitFor(() => {
      expect(screen.getByLabelText("Moderate status of user ramesh@farm.test")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("Moderate status of user ramesh@farm.test"));

    await waitFor(() => {
      expect(screen.getByText("Moderate User Account Status")).toBeInTheDocument();
    });

    const reasonInput = screen.getByPlaceholderText(/provide a factual administrative explanation/i);
    fireEvent.change(reasonInput, {
      target: { value: "Attempting to change status of last admin" },
    });

    const submitBtn = screen.getByRole("button", { name: /update account status/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(
        screen.getAllByText("Cannot deactivate or block the last active administrator").length
      ).toBeGreaterThanOrEqual(1);
    });
  });

  it("validates mandatory reason length before allowing submission", async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(mockListResponse);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByLabelText("Moderate status of user ramesh@farm.test")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("Moderate status of user ramesh@farm.test"));

    await waitFor(() => {
      expect(screen.getByText("Moderate User Account Status")).toBeInTheDocument();
    });

    // Reason shorter than 10 characters disables the submit button
    const reasonInput = screen.getByPlaceholderText(/provide a factual administrative explanation/i);
    fireEvent.change(reasonInput, { target: { value: "Short" } });

    const submitBtn = screen.getByRole("button", { name: /update account status/i });
    expect(submitBtn).toBeDisabled();
  });
});
