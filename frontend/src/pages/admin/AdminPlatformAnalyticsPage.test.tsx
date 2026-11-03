import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AdminPlatformAnalyticsPage } from "./AdminPlatformAnalyticsPage";
import { adminApi } from "../../api/admin";
import type { PlatformAnalyticsResponse } from "../../types/admin";

vi.mock("../../api/admin", () => ({
  adminApi: {
    getPlatformAnalytics: vi.fn(),
  },
}));

describe("AdminPlatformAnalyticsPage", () => {
  const mockAnalytics: PlatformAnalyticsResponse = {
    generated_at: "2026-11-04T00:00:00Z",
    platform_gmv: "1850000.00",
    pipeline_gmv: "420000.00",
    listed_supply_overview: {
      active_listings_count: 55,
      total_active_quantity_by_unit: { kg: "18000", quintal: "250" },
      total_active_listed_value: "850000.00",
    },
    buyer_demand_overview: {
      active_requirements_count: 24,
      total_demanded_quantity_by_unit: { kg: "14000" },
      total_approved_fulfilled_quantity_by_unit: { kg: "32000" },
    },
    order_outcomes: {
      total_orders: 110,
      pending_confirmation: 8,
      in_progress: 12,
      completed: 82,
      cancelled: 6,
      currently_disputed: 2,
      concluded_orders: 88,
      concluded_completion_rate: 93.18,
      concluded_cancellation_rate: 6.82,
    },
    payment_velocity: {
      total_payments: 125,
      acknowledged_payments: 118,
      disputed_payments: 4,
      pending_payments: 3,
      average_settlement_delay_hours: 5.2,
      dispute_rate: 0.032,
    },
    user_engagement: {
      total_users: 150,
      verified_farmers: 70,
      verified_buyers: 60,
      unverified_users: 16,
      admin_users: 4,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    vi.mocked(adminApi.getPlatformAnalytics).mockReturnValue(new Promise(() => {}));

    render(<AdminPlatformAnalyticsPage />);

    expect(screen.getByText("Computing unsuppressed platform analytics...")).toBeInTheDocument();
  });

  it("renders platform analytics metrics upon successful fetch", async () => {
    vi.mocked(adminApi.getPlatformAnalytics).mockResolvedValueOnce(mockAnalytics);

    render(<AdminPlatformAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText("Platform Operational Analytics")).toBeInTheDocument();
      expect(screen.getByText("₹18,50,000.00")).toBeInTheDocument();
      expect(screen.getByText("₹4,20,000.00")).toBeInTheDocument();
      expect(screen.getByText("55 Active Listings")).toBeInTheDocument();
      expect(screen.getByText("24 Open Requirements")).toBeInTheDocument();
      expect(screen.getByText("Completion Rate: 93.2%")).toBeInTheDocument();
      expect(screen.getByText("Cancellation Rate: 6.8%")).toBeInTheDocument();
      expect(screen.getByText("150 Total Accounts")).toBeInTheDocument();
      expect(screen.getByText("5.2 hours")).toBeInTheDocument();
    });
  });

  it("renders error state with retry on failure", async () => {
    vi.mocked(adminApi.getPlatformAnalytics).mockRejectedValueOnce(
      new Error("Network connection error")
    );

    render(<AdminPlatformAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText("Network connection error")).toBeInTheDocument();
    });

    vi.mocked(adminApi.getPlatformAnalytics).mockResolvedValueOnce(mockAnalytics);

    const retryBtn = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByText("₹18,50,000.00")).toBeInTheDocument();
    });
  });

  it("allows refreshing analytics via header button", async () => {
    vi.mocked(adminApi.getPlatformAnalytics).mockResolvedValue(mockAnalytics);

    render(<AdminPlatformAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText("₹18,50,000.00")).toBeInTheDocument();
    });

    const refreshBtn = screen.getByRole("button", { name: /refresh analytics/i });
    fireEvent.click(refreshBtn);

    expect(adminApi.getPlatformAnalytics).toHaveBeenCalledTimes(2);
  });
});

