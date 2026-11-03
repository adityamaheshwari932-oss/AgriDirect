/**
 * Descriptive Market Analytics & Personal Trade Performance API service (Module 9).
 * Connects to FastAPI endpoints versioned under /api/v1/analytics.
 * Note: Purely descriptive; adheres to k-anonymity (k>=3) and dominance suppression.
 */

import { apiClient, ApiClient } from "./client";
import type {
  DemandSummaryResponse,
  MarketAnalyticsFilterParams,
  MarketSummaryResponse,
  MyPerformanceResponse,
} from "../types/analytics";

export class AnalyticsApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  /**
   * Retrieve privacy-preserving descriptive marketplace supply and realized trade metrics.
   * Public or authenticated.
   */
  public async getMarketSummary(
    params?: MarketAnalyticsFilterParams
  ): Promise<MarketSummaryResponse> {
    const query = new URLSearchParams();
    if (params?.product_name) query.set("product_name", params.product_name);
    if (params?.category_id) query.set("category_id", params.category_id);
    if (params?.state) query.set("state", params.state);
    if (params?.city) query.set("city", params.city);
    if (params?.unit) query.set("unit", params.unit);
    if (params?.start_date) query.set("start_date", params.start_date);
    if (params?.end_date) query.set("end_date", params.end_date);

    const qs = query.toString();
    const endpoint = qs ? `/analytics/market-summary?${qs}` : "/analytics/market-summary";
    return this.client.get<MarketSummaryResponse>(endpoint);
  }

  /**
   * Retrieve open buyer procurement demand and approved fulfillment ledger accounting.
   * Public or authenticated.
   */
  public async getDemandSummary(
    params?: MarketAnalyticsFilterParams
  ): Promise<DemandSummaryResponse> {
    const query = new URLSearchParams();
    if (params?.product_name) query.set("product_name", params.product_name);
    if (params?.category_id) query.set("category_id", params.category_id);
    if (params?.state) query.set("state", params.state);
    if (params?.city) query.set("city", params.city);
    if (params?.unit) query.set("unit", params.unit);
    if (params?.start_date) query.set("start_date", params.start_date);
    if (params?.end_date) query.set("end_date", params.end_date);

    const qs = query.toString();
    const endpoint = qs ? `/analytics/demand-summary?${qs}` : "/analytics/demand-summary";
    return this.client.get<DemandSummaryResponse>(endpoint);
  }

  /**
   * Retrieve role-specialized personal trade performance and settlement dashboard.
   * Authenticated verified farmer or buyer.
   */
  public async getMyPerformance(): Promise<MyPerformanceResponse> {
    return this.client.get<MyPerformanceResponse>("/analytics/my-performance");
  }
}

export const analyticsApi = new AnalyticsApi();

