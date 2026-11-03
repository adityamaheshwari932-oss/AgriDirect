/**
 * Platform Safety & User Conduct Reports API service (Module 8).
 * Connects to FastAPI endpoints versioned under /api/v1/reports.
 */

import { apiClient, ApiClient } from "./client";
import type {
  ReportCreatePayload,
  ReportItem,
  ReportListResponse,
} from "../types/reports";

export class ReportsApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  /**
   * Submit a safety, fraud, or marketplace misconduct report.
   */
  public async createReport(payload: ReportCreatePayload): Promise<ReportItem> {
    return this.client.post<ReportItem>("/reports", payload);
  }

  /**
   * List reports filed by the authenticated caller (newest first).
   */
  public async listMyReports(
    page: number = 1,
    pageSize: number = 20
  ): Promise<ReportListResponse> {
    return this.client.get<ReportListResponse>(
      `/reports/me?page=${page}&page_size=${pageSize}`
    );
  }

  /**
   * Retrieve details of a report filed by caller.
   */
  public async getReport(reportId: string): Promise<ReportItem> {
    return this.client.get<ReportItem>(`/reports/${reportId}`);
  }
}

export const reportsApi = new ReportsApi();

