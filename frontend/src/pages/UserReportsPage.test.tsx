import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { UserReportsPage } from "./UserReportsPage";
import { reportsApi } from "../api/reports";
import type { ReportItem, ReportListResponse } from "../types/reports";

vi.mock("../api/reports", () => ({
  reportsApi: {
    listMyReports: vi.fn(),
    getReport: vi.fn(),
    createReport: vi.fn(),
  },
}));

describe("UserReportsPage", () => {
  const mockReports: ReportItem[] = [
    {
      id: "rep-001",
      reporter_id: "user-1",
      reported_user_id: "user-buyer-99",
      listing_id: "listing-500",
      category: "payment",
      description: "Buyer defaulted on payment terms agreed during negotiation.",
      status: "action_taken",
      admin_notes: "Platform moderator verified default and warned user account.",
      reviewed_by_admin_id: "admin-1",
      created_at: "2026-03-25T10:00:00Z",
      updated_at: "2026-03-26T12:00:00Z",
    },
    {
      id: "rep-002",
      reporter_id: "user-1",
      reported_user_id: "user-seller-22",
      listing_id: null,
      category: "harassment",
      description: "Unacceptable abusive messages sent in chat thread.",
      status: "open",
      admin_notes: null,
      reviewed_by_admin_id: null,
      created_at: "2026-03-28T09:30:00Z",
      updated_at: "2026-03-28T09:30:00Z",
    },
  ];

  const mockListResponse: ReportListResponse = {
    items: mockReports,
    total: 2,
    page: 1,
    page_size: 10,
    total_pages: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders page header and list of user reports", async () => {
    vi.mocked(reportsApi.listMyReports).mockResolvedValueOnce(mockListResponse);

    render(
      <MemoryRouter>
        <UserReportsPage />
      </MemoryRouter>
    );

    expect(screen.getByText("Safety & Incident Reports")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Payment Issue")).toBeInTheDocument();
      expect(screen.getByText("Harassment")).toBeInTheDocument();
      expect(screen.getAllByText("Action Taken").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Open Intake").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("filters reports by status tab", async () => {
    vi.mocked(reportsApi.listMyReports).mockResolvedValueOnce(mockListResponse);

    render(
      <MemoryRouter>
        <UserReportsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Payment Issue")).toBeInTheDocument();
    });

    // Click "Open Intake" tab
    fireEvent.click(screen.getByRole("button", { name: "Open Intake" }));

    expect(screen.getByText("Harassment")).toBeInTheDocument();
    expect(screen.queryByText("Payment Issue")).not.toBeInTheDocument();
  });

  it("opens ReportDetailModal and displays narrative and moderator notes", async () => {
    vi.mocked(reportsApi.listMyReports).mockResolvedValueOnce(mockListResponse);
    vi.mocked(reportsApi.getReport).mockResolvedValueOnce(mockReports[0]);

    render(
      <MemoryRouter>
        <UserReportsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("View report rep-001")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText("View report rep-001"));

    await waitFor(() => {
      expect(screen.getByText("Report Details")).toBeInTheDocument();
      expect(screen.getByText("Platform moderator verified default and warned user account.")).toBeInTheDocument();
    });
  });

  it("renders empty state when no reports exist", async () => {
    vi.mocked(reportsApi.listMyReports).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });

    render(
      <MemoryRouter>
        <UserReportsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("No Reports Found")).toBeInTheDocument();
    });
  });

  it("renders error state when API fails", async () => {
    vi.mocked(reportsApi.listMyReports).mockRejectedValueOnce(
      new Error("Database connection error")
    );

    render(
      <MemoryRouter>
        <UserReportsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Database connection error")).toBeInTheDocument();
    });
  });
});
