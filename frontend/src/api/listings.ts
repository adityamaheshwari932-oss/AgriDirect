/**
 * Produce Listings and Categories API service.
 * Interacts with backend FastAPI endpoints defined in app.listings.routes.
 */

import { apiClient, ApiClient } from "./client";
import type {
  FarmerListingListResponse,
  ListingCreatePayload,
  ListingImage,
  ListingStatusUpdatePayload,
  ListingUpdatePayload,
  MarketplaceListingFilterParams,
  ProduceCategory,
  ProduceListingDetail,
  ProduceListingPublicListResponse,
} from "../types/listings";

export class ListingsApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  /**
   * Retrieve active produce taxonomy categories.
   * Publicly accessible.
   */
  public async getCategories(): Promise<ProduceCategory[]> {
    return this.client.get<ProduceCategory[]>("/listings/categories");
  }

  /**
   * Retrieve listings owned by the authenticated verified farmer.
   * Corresponds to GET /api/v1/listings/me.
   */
  public async getMyListings(params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<FarmerListingListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    const endpoint = qs ? `/listings/me?${qs}` : "/listings/me";
    return this.client.get<FarmerListingListResponse>(endpoint);
  }

  /**
   * Search and filter public marketplace produce listings.
   * Publicly accessible without authentication.
   */
  public async searchMarketplace(
    params?: MarketplaceListingFilterParams
  ): Promise<ProduceListingPublicListResponse> {
    const query = new URLSearchParams();
    if (params?.category_id) query.set("category_id", params.category_id);
    if (params?.category_slug) query.set("category_slug", params.category_slug);
    if (params?.q) query.set("q", params.q);
    if (params?.product_name) query.set("product_name", params.product_name);
    if (params?.state || params?.location_state) {
      query.set("state", params.state || params.location_state || "");
    }
    if (params?.city || params?.location_city) {
      query.set("city", params.city || params.location_city || "");
    }
    if (params?.min_price !== undefined) query.set("min_price", String(params.min_price));
    if (params?.max_price !== undefined) query.set("max_price", String(params.max_price));
    if (params?.unit) query.set("unit", params.unit);
    if (params?.quality_grade) query.set("quality_grade", params.quality_grade);
    if (params?.farmer_id) query.set("farmer_id", params.farmer_id);
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.sort_order) query.set("sort_order", params.sort_order);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    const endpoint = qs ? `/listings?${qs}` : "/listings";
    return this.client.get<ProduceListingPublicListResponse>(endpoint);
  }

  /**
   * Retrieve listing details by UUID.
   * Public for active listings; drafts/closed visible to owner.
   */
  public async getListing(id: string): Promise<ProduceListingDetail> {
    return this.client.get<ProduceListingDetail>(`/listings/${id}`);
  }

  /**
   * Create a new produce listing.
   * Strictly restricted to authenticated verified farmers.
   */
  public async createListing(
    payload: ListingCreatePayload
  ): Promise<ProduceListingDetail> {
    return this.client.post<ProduceListingDetail>("/listings", payload);
  }

  /**
   * Update permitted listing attributes.
   * Owner only. Server controls available_quantity, farmer_id, timestamps.
   */
  public async updateListing(
    id: string,
    payload: ListingUpdatePayload
  ): Promise<ProduceListingDetail> {
    return this.client.patch<ProduceListingDetail>(`/listings/${id}`, payload);
  }

  /**
   * Transition listing lifecycle status (draft, active, closed).
   */
  public async updateStatus(
    id: string,
    payload: ListingStatusUpdatePayload
  ): Promise<ProduceListingDetail> {
    return this.client.patch<ProduceListingDetail>(`/listings/${id}/status`, payload);
  }

  /**
   * Soft-delete a produce listing.
   */
  public async deleteListing(id: string): Promise<void> {
    return this.client.delete<void>(`/listings/${id}`);
  }

  /**
   * Upload photographic asset for produce listing.
   * Max 5 MB, JPEG, PNG, or WebP. Max 5 images per listing.
   */
  public async uploadImage(
    id: string,
    file: File,
    isPrimary: boolean = false,
    displayOrder: number = 0
  ): Promise<ListingImage> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("is_primary", String(isPrimary));
    formData.append("display_order", String(displayOrder));

    return this.client.post<ListingImage>(`/listings/${id}/images`, formData);
  }

  /**
   * Delete an attached image from storage and listing.
   */
  public async deleteImage(id: string, imageId: string): Promise<void> {
    return this.client.delete<void>(`/listings/${id}/images/${imageId}`);
  }

  /**
   * Designate image as primary thumbnail for catalog card views.
   */
  public async setPrimaryImage(
    id: string,
    imageId: string
  ): Promise<ListingImage> {
    return this.client.patch<ListingImage>(
      `/listings/${id}/images/${imageId}/primary`,
      {}
    );
  }

  /**
   * Generate canonical streaming URL for listing image.
   */
  public getImageUrl(id: string, imageId: string): string {
    return `/api/v1/listings/${id}/images/${imageId}`;
  }
}

export const listingsApi = new ListingsApi();

