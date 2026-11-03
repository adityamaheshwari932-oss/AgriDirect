import { describe, it, expect, vi, beforeEach } from "vitest";
import { analyticsApi } from "./analytics";
import { apiClient } from "./client";

describe("AnalyticsApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("retrieves market summary with filters", async () => {
    const mockSummary = {
      provenance: { generated_at: "2026-11-03T19:00:00Z" },
      privacy: { is_suppressed: false },
      active_supply: { total_listings_count: 8 },
      realized_trades: { total_orders_count: 5 },
    };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockSummary);

    const res = await analyticsApi.getMarketSummary({ product_name: "Wheat", state: "Punjab" });
    expect(apiClient.get).toHaveBeenCalledWith("/analytics/market-summary?product_name=Wheat&state=Punjab");
    expect(res).toEqual(mockSummary);
  });

  it("retrieves demand summary", async () => {
    const mockDemand = {
      provenance: { generated_at: "2026-11-03T19:00:00Z" },
      privacy: { is_suppressed: false },
      open_demand: { total_requirements_count: 4 },
      approved_fulfillment: { total_approvals_count: 2 },
    };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockDemand);

    const res = await analyticsApi.getDemandSummary();
    expect(apiClient.get).toHaveBeenCalledWith("/analytics/demand-summary");
    expect(res).toEqual(mockDemand);
  });

  it("retrieves personal performance report for authenticated user", async () => {
    const mockPerf = {
      user_id: "user-1",
      role: "farmer",
      total_listings_created: 10,
      total_realized_revenue: "150000.00",
    };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockPerf);

    const res = await analyticsApi.getMyPerformance();
    expect(apiClient.get).toHaveBeenCalledWith("/analytics/my-performance");
    expect(res).toEqual(mockPerf);
  });
});

