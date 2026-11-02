/**
 * Buyer Procurement Requirements API service.
 * Interacts with backend FastAPI endpoints defined in app.requirements.routes.
 */

import { apiClient, ApiClient } from "./client";
import type {
  BuyerRequirementDetail,
  BuyerRequirementListResponse,
  BuyerRequirementPublicListResponse,
  MarketplaceRequirementFilterParams,
  RequirementCreatePayload,
  RequirementStatusUpdatePayload,
  RequirementUpdatePayload,
} from "../types/requirements";

export class RequirementsApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  /**
   * Retrieve requirements owned by the authenticated verified commercial buyer.
   * Corresponds to GET /api/v1/requirements/me.
   */
  public async getMyRequirements(params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<BuyerRequirementListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    const endpoint = qs ? `/requirements/me?${qs}` : "/requirements/me";
    return this.client.get<BuyerRequirementListResponse>(endpoint);
  }

  /**
   * Search and filter public marketplace buyer procurement demands.
   * Publicly accessible without authentication.
   */
  public async searchMarketplace(
    params?: MarketplaceRequirementFilterParams
  ): Promise<BuyerRequirementPublicListResponse> {
    const query = new URLSearchParams();
    if (params?.category_id) query.set("category_id", params.category_id);
    if (params?.category_slug) query.set("category_slug", params.category_slug);
    if (params?.q) query.set("q", params.q);
    if (params?.product_name) query.set("product_name", params.product_name);
    if (params?.destination_state || params?.state) {
      query.set("state", params.destination_state || params.state || "");
    }
    if (params?.destination_city || params?.city) {
      query.set("city", params.destination_city || params.city || "");
    }
    if (params?.min_price !== undefined) query.set("min_price", String(params.min_price));
    if (params?.max_price !== undefined) query.set("max_price", String(params.max_price));
    if (params?.min_quantity !== undefined) {
      query.set("min_quantity", String(params.min_quantity));
    }
    if (params?.max_quantity !== undefined) {
      query.set("max_quantity", String(params.max_quantity));
    }
    if (params?.unit) query.set("unit", params.unit);
    if (params?.quality_grade) query.set("quality_grade", params.quality_grade);
    if (params?.price_condition) query.set("price_condition", params.price_condition);
    if (params?.buyer_id) query.set("buyer_id", params.buyer_id);
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.sort_order) query.set("sort_order", params.sort_order);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    const endpoint = qs ? `/requirements?${qs}` : "/requirements";
    return this.client.get<BuyerRequirementPublicListResponse>(endpoint);
  }

  /**
   * Retrieve requirement details by UUID.
   */
  public async getRequirement(id: string): Promise<BuyerRequirementDetail> {
    return this.client.get<BuyerRequirementDetail>(`/requirements/${id}`);
  }

  /**
   * Create a new procurement demand requirement.
   * Strictly restricted to authenticated verified commercial buyers.
   */
  public async createRequirement(
    payload: RequirementCreatePayload
  ): Promise<BuyerRequirementDetail> {
    return this.client.post<BuyerRequirementDetail>("/requirements", payload);
  }

  /**
   * Update permitted attributes of a buyer requirement.
   * Owner only. Server controls remaining_quantity, buyer_id, timestamps.
   */
  public async updateRequirement(
    id: string,
    payload: RequirementUpdatePayload
  ): Promise<BuyerRequirementDetail> {
    return this.client.patch<BuyerRequirementDetail>(`/requirements/${id}`, payload);
  }

  /**
   * Transition requirement lifecycle status (draft, active, closed).
   */
  public async updateStatus(
    id: string,
    payload: RequirementStatusUpdatePayload
  ): Promise<BuyerRequirementDetail> {
    return this.client.patch<BuyerRequirementDetail>(
      `/requirements/${id}/status`,
      payload
    );
  }

  /**
   * Soft-delete a buyer requirement.
   */
  public async deleteRequirement(id: string): Promise<void> {
    return this.client.delete<void>(`/requirements/${id}`);
  }
}

export const requirementsApi = new RequirementsApi();

