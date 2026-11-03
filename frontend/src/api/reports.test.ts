import { describe, it, expect, vi, beforeEach } from "vitest";
import { reportsApi } from "./reports";
import { apiClient } from "./client";

describe("ReportsApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("submits a safety violation report", async () => {
    const payload = {
      reported_user_id: "user-2",
      category: "fraud",
      description: "Counterparty forged off-platform bank payment slip",
    };
    const mockReport = { id: "rep-1", status: "open", ...payload };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockReport);

    const res = await reportsApi.createReport(payload);
    expect(apiClient.post).toHaveBeenCalledWith("/reports", payload);
    expect(res).toEqual(mockReport);
  });

  it("lists reports submitted by caller", async () => {
    const mockList = { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockList);

    const res = await reportsApi.listMyReports(1, 20);
    expect(apiClient.get).toHaveBeenCalledWith("/reports/me?page=1&page_size=20");
    expect(res).toEqual(mockList);
  });

  it("gets details of a specific report", async () => {
    const mockReport = { id: "rep-1", status: "open", category: "quality_issue" };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockReport);

    const res = await reportsApi.getReport("rep-1");
    expect(apiClient.get).toHaveBeenCalledWith("/reports/rep-1");
    expect(res).toEqual(mockReport);
  });
});

