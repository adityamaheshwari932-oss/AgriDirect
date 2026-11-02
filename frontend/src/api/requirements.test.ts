import { beforeEach, describe, expect, it, vi } from "vitest";
import { requirementsApi } from "./requirements";
import { apiClient } from "./client";
import type {
  BuyerRequirementDetail,
  BuyerRequirementListResponse,
  BuyerRequirementPublicListResponse,
  RequirementCreatePayload,
} from "../types/requirements";

describe("RequirementsApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("retrieves buyer own requirements with status and pagination", async () => {
    const mockResponse: BuyerRequirementListResponse = {
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    };

    vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse);

    const result = await requirementsApi.getMyRequirements({
      status: "active",
      page: 1,
      page_size: 10,
    });

    expect(apiClient.get).toHaveBeenCalledWith("/requirements/me?status=active&page=1&page_size=10");
    expect(result.items).toEqual([]);
  });

  it("searches public marketplace buyer requirements with filters", async () => {
    const mockResponse: BuyerRequirementPublicListResponse = {
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      total_pages: 0,
    };

    vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse);

    await requirementsApi.searchMarketplace({
      q: "potatoes",
      category_id: "cat-456",
      state: "Punjab",
      city: "Jalandhar",
      min_price: 1500,
      max_price: 2500,
      min_quantity: 50,
      max_quantity: 200,
      unit: "quintal",
      price_condition: "negotiable",
      sort_by: "required_by_date",
      sort_order: "asc",
      page: 1,
      page_size: 12,
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining("/requirements?category_id=cat-456&q=potatoes&state=Punjab&city=Jalandhar&min_price=1500&max_price=2500&min_quantity=50&max_quantity=200&unit=quintal&price_condition=negotiable&sort_by=required_by_date&sort_order=asc&page=1&page_size=12")
    );
  });

  it("retrieves requirement detail by UUID", async () => {
    const mockDetail = { id: "req-1", title: "Bulk Potatoes" } as BuyerRequirementDetail;
    vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockDetail);

    const result = await requirementsApi.getRequirement("req-1");
    expect(apiClient.get).toHaveBeenCalledWith("/requirements/req-1");
    expect(result.id).toBe("req-1");
  });

  it("creates a new buyer procurement requirement", async () => {
    const payload: RequirementCreatePayload = {
      product_name: "Processing Potatoes",
      title: "Weekly Bulk Demand",
      required_quantity: 100,
      unit: "quintal",
      target_price_per_unit: 1900,
      price_condition: "negotiable",
      required_by_date: "2026-11-20",
      status: "active",
    };

    const mockCreated = { id: "new-req-1", ...payload } as unknown as BuyerRequirementDetail;
    vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockCreated);

    const result = await requirementsApi.createRequirement(payload);
    expect(apiClient.post).toHaveBeenCalledWith("/requirements", payload);
    expect(result.id).toBe("new-req-1");
  });

  it("updates permitted fields on requirement", async () => {
    vi.spyOn(apiClient, "patch").mockResolvedValueOnce({ id: "req-1", required_quantity: 150 });

    await requirementsApi.updateRequirement("req-1", { required_quantity: 150 });
    expect(apiClient.patch).toHaveBeenCalledWith("/requirements/req-1", { required_quantity: 150 });
  });

  it("transitions requirement status", async () => {
    vi.spyOn(apiClient, "patch").mockResolvedValueOnce({ id: "req-1", status: "closed" });

    await requirementsApi.updateStatus("req-1", { status: "closed" });
    expect(apiClient.patch).toHaveBeenCalledWith("/requirements/req-1/status", { status: "closed" });
  });

  it("soft-deletes a buyer requirement", async () => {
    vi.spyOn(apiClient, "delete").mockResolvedValueOnce(undefined);

    await requirementsApi.deleteRequirement("req-1");
    expect(apiClient.delete).toHaveBeenCalledWith("/requirements/req-1");
  });
});

