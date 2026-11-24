import { beforeEach, describe, expect, it, vi } from "vitest";
import { listingsApi } from "./listings";
import { apiClient } from "./client";
import type {
  FarmerListingListResponse,
  ListingCreatePayload,
  ListingImage,
  ProduceCategory,
  ProduceListingDetail,
  ProduceListingPublicListResponse,
} from "../types/listings";

describe("ListingsApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("retrieves active produce categories", async () => {
    const mockCategories: ProduceCategory[] = [
      { id: "cat-1", name: "Grains & Cereals", slug: "grains", is_active: true },
      { id: "cat-2", name: "Fruits & Berries", slug: "fruits", is_active: true },
    ];

    vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockCategories);

    const result = await listingsApi.getCategories();
    expect(apiClient.get).toHaveBeenCalledWith("/listings/categories");
    expect(result).toEqual(mockCategories);
  });

  it("retrieves farmer own listings with status and pagination query params", async () => {
    const mockResponse: FarmerListingListResponse = {
      items: [],
      total: 0,
      page: 2,
      page_size: 10,
      total_pages: 0,
    };

    vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse);

    const result = await listingsApi.getMyListings({
      status: "active",
      page: 2,
      page_size: 10,
    });

    expect(apiClient.get).toHaveBeenCalledWith("/listings/me?status=active&page=2&page_size=10");
    expect(result.page).toBe(2);
  });

  it("searches public marketplace with multiple filter query parameters", async () => {
    const mockPublicResponse: ProduceListingPublicListResponse = {
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      total_pages: 0,
    };

    vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockPublicResponse);

    await listingsApi.searchMarketplace({
      q: "wheat",
      category_id: "cat-123",
      state: "Maharashtra",
      city: "Nashik",
      min_price: 2000,
      max_price: 3000,
      unit: "quintal",
      quality_grade: "Grade A",
      sort_by: "price_per_unit",
      sort_order: "asc",
      page: 1,
      page_size: 12,
    });

    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining("/listings?category_id=cat-123&q=wheat&state=Maharashtra&city=Nashik&min_price=2000&max_price=3000&unit=quintal&quality_grade=Grade+A&sort_by=price_per_unit&sort_order=asc&page=1&page_size=12")
    );
  });

  it("retrieves listing detail by UUID", async () => {
    const mockDetail = { id: "list-1", title: "Premium Lot" } as ProduceListingDetail;
    vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockDetail);

    const result = await listingsApi.getListing("list-1");
    expect(apiClient.get).toHaveBeenCalledWith("/listings/list-1");
    expect(result.id).toBe("list-1");
  });

  it("creates a new produce listing", async () => {
    const payload: ListingCreatePayload = {
      product_name: "Sharbati Wheat",
      title: "Farm Fresh Wheat",
      initial_quantity: 50,
      unit: "quintal",
      price_per_unit: 2800,
      status: "active",
    };

    const mockCreated = { id: "new-list-1", ...payload } as unknown as ProduceListingDetail;
    vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockCreated);

    const result = await listingsApi.createListing(payload);
    expect(apiClient.post).toHaveBeenCalledWith("/listings", payload);
    expect(result.id).toBe("new-list-1");
  });

  it("updates permitted fields on produce listing", async () => {
    vi.spyOn(apiClient, "patch").mockResolvedValueOnce({ id: "list-1", price_per_unit: 2900 });

    await listingsApi.updateListing("list-1", { price_per_unit: 2900 });
    expect(apiClient.patch).toHaveBeenCalledWith("/listings/list-1", { price_per_unit: 2900 });
  });

  it("transitions listing status", async () => {
    vi.spyOn(apiClient, "patch").mockResolvedValueOnce({ id: "list-1", status: "closed" });

    await listingsApi.updateStatus("list-1", { status: "closed" });
    expect(apiClient.patch).toHaveBeenCalledWith("/listings/list-1/status", { status: "closed" });
  });

  it("soft-deletes a produce listing", async () => {
    vi.spyOn(apiClient, "delete").mockResolvedValueOnce(undefined);

    await listingsApi.deleteListing("list-1");
    expect(apiClient.delete).toHaveBeenCalledWith("/listings/list-1");
  });

  it("uploads an image asset via FormData", async () => {
    const mockImage: ListingImage = {
      id: "img-1",
      listing_id: "list-1",
      image_uri: "/uploads/img.jpg",
      is_primary: true,
      display_order: 0,
      created_at: "2026-10-30T10:00:00Z",
    };

    vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockImage);

    const file = new File(["dummy content"], "photo.jpg", { type: "image/jpeg" });
    const result = await listingsApi.uploadImage("list-1", file, true, 0);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/listings/list-1/images",
      expect.any(FormData)
    );
    expect(result.id).toBe("img-1");
  });

  it("uploads multiple image assets via FormData", async () => {
    const mockImages: ListingImage[] = [
      {
        id: "img-1",
        listing_id: "list-1",
        image_uri: "/uploads/img1.jpg",
        is_primary: true,
        display_order: 0,
        created_at: "2026-10-30T10:00:00Z",
      },
      {
        id: "img-2",
        listing_id: "list-1",
        image_uri: "/uploads/img2.jpg",
        is_primary: false,
        display_order: 1,
        created_at: "2026-10-30T10:00:01Z",
      },
    ];

    vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockImages);

    const files = [
      new File(["content1"], "photo1.jpg", { type: "image/jpeg" }),
      new File(["content2"], "photo2.png", { type: "image/png" }),
    ];
    const result = await listingsApi.uploadImages("list-1", files);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/listings/list-1/images",
      expect.any(FormData)
    );
    expect(result).toHaveLength(2);
  });

  it("retrieves all images attached to a listing", async () => {
    const mockImages: ListingImage[] = [
      {
        id: "img-1",
        listing_id: "list-1",
        image_uri: "/uploads/img1.jpg",
        is_primary: true,
        display_order: 0,
        created_at: "2026-10-30T10:00:00Z",
      },
    ];

    vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockImages);

    const result = await listingsApi.getImages("list-1");
    expect(apiClient.get).toHaveBeenCalledWith("/listings/list-1/images");
    expect(result).toEqual(mockImages);
  });

  it("reorders listing images", async () => {
    const mockImages: ListingImage[] = [
      {
        id: "img-2",
        listing_id: "list-1",
        image_uri: "/uploads/img2.jpg",
        is_primary: true,
        display_order: 0,
        created_at: "2026-10-30T10:00:01Z",
      },
      {
        id: "img-1",
        listing_id: "list-1",
        image_uri: "/uploads/img1.jpg",
        is_primary: false,
        display_order: 1,
        created_at: "2026-10-30T10:00:00Z",
      },
    ];

    vi.spyOn(apiClient, "patch").mockResolvedValueOnce(mockImages);

    const result = await listingsApi.reorderImages("list-1", ["img-2", "img-1"]);
    expect(apiClient.patch).toHaveBeenCalledWith("/listings/list-1/images/reorder", {
      image_ids: ["img-2", "img-1"],
    });
    expect(result[0].id).toBe("img-2");
  });

  it("deletes a listing image and sets primary image", async () => {
    vi.spyOn(apiClient, "delete").mockResolvedValueOnce(undefined);
    vi.spyOn(apiClient, "patch").mockResolvedValueOnce({ id: "img-2", is_primary: true });

    await listingsApi.deleteImage("list-1", "img-1");
    expect(apiClient.delete).toHaveBeenCalledWith("/listings/list-1/images/img-1");

    await listingsApi.setPrimaryImage("list-1", "img-2");
    expect(apiClient.patch).toHaveBeenCalledWith("/listings/list-1/images/img-2/primary", {});
  });

  it("generates correct streaming URL", () => {
    const url = listingsApi.getImageUrl("list-123", "img-456");
    expect(url).toBe("/api/v1/listings/list-123/images/img-456");
  });
});

