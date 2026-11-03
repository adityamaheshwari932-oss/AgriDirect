import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { AnalyticsDashboardPage } from "./AnalyticsDashboardPage";
import { analyticsApi } from "../api/analytics";
import type {
  FarmerPerformanceResponse,
  MarketSummaryResponse,
  DemandSummaryResponse,
} from "../types/analytics";

vi.mock("../api/analytics", () => ({
  analyticsApi: {
    getMyPerformance: vi.fn(),
    getMarketSummary: vi.fn(),
    getDemandSummary: vi.fn(),
  },
}));

vi.mock("../store/authStore", () => ({
  useAuth: () => ({
    user: { id: "farmer-1", role: "farmer", email: "farmer@test.com", is_verified: true },
    isAuthenticated: true,
  }),
}));

const mockFarmerPerformance: FarmerPerformanceResponse = {
  user_id: "farmer-1",
  role: "farmer",
  total_listings_created: 10,
  active_listings_count: 4,
  realized_sales_volume_by_unit: { kg: "85000" },
  total_realized_revenue: "750000.00",
  top_commodities: [],
  average_rating: 4.8,
  total_reviews_received: 12,
  order_outcomes: {
    active_in_progress: 2,
    pending_farmer_confirmation: 1,
    completed: 15,
    cancelled: 1,
    disputed: 0,
    total_orders: 19,
    non_pending_orders: 18,
    completion_rate: 0.83,
    cancellation_rate: 0.05,
    concluded_orders: 16,
    concluded_completion_rate: 0.94,
    concluded_cancellation_rate: 0.06,
  },
  payment_settlement: {
    total_payments_count: 15,
    total_amount_recorded: "750000.00",
    acknowledged_count: 14,
    acknowledged_amount: "700000.00",
    disputed_count: 0,
    disputed_amount: "0.00",
    pending_acknowledgement_count: 1,
    pending_acknowledgement_amount: "50000.00",
    average_acknowledgement_delay_hours: 4.2,
  },
};

const mockMarketSummary: MarketSummaryResponse = {
  provenance: {
    generated_at: "2026-03-30T10:00:00Z",
    query_filters: {},
    geographic_level_applied: "national",
    geographic_fallback_triggered: false,
    category_attribution_source: "database",
    is_historical_snapshot: false,
  },
  privacy: {
    is_suppressed: false,
    suppression_reason: null,
    distinct_farmers_band: "11+",
    distinct_buyers_band: "11+",
    observations_count_band: "11+",
    quantity_suppressed: false,
    gross_value_suppressed: false,
    vwap_suppressed: false,
    arithmetic_mean_suppressed: false,
    median_suppressed: false,
    min_price_suppressed: false,
  },
  active_supply: {
    total_listings_count: 45,
    total_available_quantity: "125000",
    measurement_unit: "kg",
  },
  realized_trades: {
    total_orders_count: 32,
    total_quantity_traded: "85000",
    measurement_unit: "kg",
    vwap: "65.50",
    arithmetic_mean: "64.00",
  },
};

const mockDemandSummary: DemandSummaryResponse = {
  provenance: {
    generated_at: "2026-03-30T10:00:00Z",
    query_filters: {},
    geographic_level_applied: "national",
    geographic_fallback_triggered: false,
    category_attribution_source: "database",
    is_historical_snapshot: false,
  },
  privacy: {
    is_suppressed: false,
    suppression_reason: null,
    distinct_farmers_band: null,
    distinct_buyers_band: null,
    observations_count_band: null,
    quantity_suppressed: false,
    gross_value_suppressed: false,
    vwap_suppressed: false,
    arithmetic_mean_suppressed: false,
    median_suppressed: false,
    min_price_suppressed: false,
  },
  open_demand: {
    total_requirements_count: 18,
    total_demanded_quantity: "95000",
    measurement_unit: "kg",
  },
  approved_fulfillment: {
    total_approvals_count: 12,
    total_approved_quantity: "60000",
    measurement_unit: "kg",
  },
};

describe("AnalyticsDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders performance tab by default and displays KPIs", async () => {
    vi.mocked(analyticsApi.getMyPerformance).mockResolvedValueOnce(mockFarmerPerformance);

    render(<AnalyticsDashboardPage />);

    expect(screen.getByText("Market & Operational Analytics")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Total Orders")).toBeInTheDocument();
      expect(screen.getByText("19")).toBeInTheDocument();
      expect(screen.getByText("94%")).toBeInTheDocument(); // 0.94 concluded completion rate
    });
  });

  it("switches to market summary tab and loads market data", async () => {
    vi.mocked(analyticsApi.getMyPerformance).mockResolvedValueOnce(mockFarmerPerformance);
    vi.mocked(analyticsApi.getMarketSummary).mockResolvedValueOnce(mockMarketSummary);

    render(<AnalyticsDashboardPage />);

    const marketTab = screen.getByText("Market Supply & Price Index");
    fireEvent.click(marketTab);

    await waitFor(() => {
      expect(analyticsApi.getMarketSummary).toHaveBeenCalled();
      expect(screen.getByText("Active Supply")).toBeInTheDocument();
      expect(screen.getByText("45")).toBeInTheDocument();
    });
  });

  it("switches to demand trends tab and loads demand data", async () => {
    vi.mocked(analyticsApi.getMyPerformance).mockResolvedValueOnce(mockFarmerPerformance);
    vi.mocked(analyticsApi.getDemandSummary).mockResolvedValueOnce(mockDemandSummary);

    render(<AnalyticsDashboardPage />);

    const demandTab = screen.getByText("Commercial Demand Trends");
    fireEvent.click(demandTab);

    await waitFor(() => {
      expect(analyticsApi.getDemandSummary).toHaveBeenCalled();
      expect(screen.getByText("Commercial Demand Summary")).toBeInTheDocument();
      expect(screen.getByText("18")).toBeInTheDocument();
    });
  });
});

