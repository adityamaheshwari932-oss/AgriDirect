/**
 * Domain types for AgriDirect Produce Listings and Categories.
 * Aligned with backend Pydantic models in app.listings.schemas.
 */

export interface ProduceCategory {
  id: string;
  parent_id?: string | null;
  name: string;
  slug: string;
  is_active: boolean;
}

export interface ListingImage {
  id: string;
  listing_id: string;
  image_uri: string;
  is_primary: boolean;
  display_order: number;
  created_at: string;
}

export interface FarmerSummary {
  id: string;
  full_name: string;
  farm_name: string;
  city: string;
  state: string;
}

export type ListingStatus =
  | "draft"
  | "active"
  | "partially_fulfilled"
  | "closed"
  | "expired";

export interface ProduceListingDetail {
  id: string;
  farmer_id: string;
  category_id?: string | null;
  category?: ProduceCategory | null;
  product_name: string;
  title: string;
  description?: string | null;
  initial_quantity: number | string;
  available_quantity: number | string;
  unit: string;
  price_per_unit: number | string;
  quality_grade?: string | null;
  location_state: string;
  location_city: string;
  harvest_date?: string | null;
  available_from: string;
  expires_at: string;
  status: ListingStatus;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  images: ListingImage[];
  farmer?: FarmerSummary | null;
}

export interface ProduceListingPublicSummary {
  id: string;
  category_id?: string | null;
  category_name?: string | null;
  product_name: string;
  title: string;
  description?: string | null;
  available_quantity: number | string;
  unit: string;
  price_per_unit: number | string;
  quality_grade?: string | null;
  location_state: string;
  location_city: string;
  harvest_date?: string | null;
  available_from: string;
  expires_at: string;
  status: string;
  created_at: string;
  primary_image_uri?: string | null;
  farmer?: FarmerSummary | null;
}

export interface ProduceListingPublicListResponse {
  items: ProduceListingPublicSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FarmerListingListResponse {
  items: ProduceListingDetail[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ListingCreatePayload {
  product_name: string;
  title: string;
  description?: string | null;
  category_id?: string | null;
  initial_quantity: number;
  unit: string;
  price_per_unit: number;
  quality_grade?: string | null;
  location_state?: string | null;
  location_city?: string | null;
  harvest_date?: string | null;
  available_from?: string | null;
  expires_at?: string | null;
  status?: "active" | "draft";
}

export interface ListingUpdatePayload {
  product_name?: string;
  title?: string;
  description?: string | null;
  category_id?: string | null;
  initial_quantity?: number;
  unit?: string;
  price_per_unit?: number;
  quality_grade?: string | null;
  location_state?: string | null;
  location_city?: string | null;
  harvest_date?: string | null;
  available_from?: string | null;
  expires_at?: string | null;
  status?: string;
}

export interface ListingStatusUpdatePayload {
  status: "active" | "draft" | "closed";
}

export interface MarketplaceListingFilterParams {
  category_id?: string;
  category_slug?: string;
  q?: string;
  product_name?: string;
  state?: string;
  location_state?: string;
  city?: string;
  location_city?: string;
  min_price?: number;
  max_price?: number;
  unit?: string;
  quality_grade?: string;
  farmer_id?: string;
  sort_by?: "created_at" | "price_per_unit" | "available_quantity" | "product_name";
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

