/**
 * Domain types for AgriDirect Buyer Procurement Requirements.
 * Aligned with backend Pydantic models in app.requirements.schemas.
 */

import type { ProduceCategory } from "./listings";

export interface BuyerSummary {
  id: string;
  contact_person_name: string;
  business_name: string;
  business_type: string;
  city: string;
  state: string;
}

export type RequirementStatus =
  | "draft"
  | "active"
  | "partially_fulfilled"
  | "fulfilled"
  | "closed"
  | "expired";

export type PriceCondition = "exact" | "range" | "negotiable";

export interface BuyerRequirementDetail {
  id: string;
  buyer_id: string;
  category_id?: string | null;
  category?: ProduceCategory | null;
  product_name: string;
  title: string;
  description?: string | null;
  required_quantity: number | string;
  remaining_quantity: number | string;
  unit: string;
  target_price_per_unit?: number | string | null;
  price_condition: string;
  quality_grade?: string | null;
  destination_state: string;
  destination_city: string;
  required_by_date: string;
  status: RequirementStatus;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  buyer?: BuyerSummary | null;
}

export interface BuyerRequirementPublicSummary {
  id: string;
  category_id?: string | null;
  category_name?: string | null;
  product_name: string;
  title: string;
  description?: string | null;
  required_quantity: number | string;
  remaining_quantity: number | string;
  unit: string;
  target_price_per_unit?: number | string | null;
  price_condition: string;
  quality_grade?: string | null;
  destination_state: string;
  destination_city: string;
  required_by_date: string;
  status: string;
  created_at: string;
  buyer?: BuyerSummary | null;
}

export interface BuyerRequirementPublicListResponse {
  items: BuyerRequirementPublicSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface BuyerRequirementListResponse {
  items: BuyerRequirementDetail[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RequirementCreatePayload {
  product_name: string;
  title: string;
  description?: string | null;
  category_id?: string | null;
  required_quantity: number;
  unit: string;
  target_price_per_unit?: number | null;
  price_condition: PriceCondition;
  quality_grade?: string | null;
  destination_state?: string | null;
  destination_city?: string | null;
  required_by_date: string; // YYYY-MM-DD
  status?: "active" | "draft";
}

export interface RequirementUpdatePayload {
  product_name?: string;
  title?: string;
  description?: string | null;
  category_id?: string | null;
  required_quantity?: number;
  unit?: string;
  target_price_per_unit?: number | null;
  price_condition?: PriceCondition;
  quality_grade?: string | null;
  destination_state?: string | null;
  destination_city?: string | null;
  required_by_date?: string;
  status?: string;
}

export interface RequirementStatusUpdatePayload {
  status: "active" | "draft" | "closed";
}

export interface MarketplaceRequirementFilterParams {
  category_id?: string;
  category_slug?: string;
  q?: string;
  product_name?: string;
  destination_state?: string;
  state?: string;
  destination_city?: string;
  city?: string;
  min_price?: number;
  max_price?: number;
  min_quantity?: number;
  max_quantity?: number;
  unit?: string;
  quality_grade?: string;
  price_condition?: string;
  buyer_id?: string;
  sort_by?:
    | "created_at"
    | "required_by_date"
    | "required_quantity"
    | "target_price_per_unit"
    | "product_name";
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

