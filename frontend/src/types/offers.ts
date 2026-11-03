/**
 * Domain types for AgriDirect Structured Offers, Counter-Offers, and Negotiation.
 * Aligned with backend Pydantic models in app.offers.schemas and app.models.offer.
 */

export type OfferStatus =
  | "pending"
  | "countered"
  | "accepted"
  | "rejected"
  | "withdrawn"
  | "expired";

export type OfferItemStatus = "proposed" | "agreed" | "rejected" | "modified";

export interface OfferUserSummary {
  id: string;
  role: string;
  name: string;
  business_name?: string | null;
  city?: string | null;
  state?: string | null;
}

export interface OfferItem {
  id: string;
  offer_id: string;
  listing_id?: string | null;
  buyer_requirement_id?: string | null;
  product_name: string;
  quantity: number | string;
  unit: string;
  unit_price: number | string;
  subtotal: number | string;
  quality_grade?: string | null;
  status: OfferItemStatus | string;
  created_at: string;
}

export interface OfferSummary {
  id: string;
  offer_number: string;
  conversation_id: string;
  sender_id: string;
  recipient_id: string;
  parent_offer_id?: string | null;
  delivery_terms?: string | null;
  proposed_delivery_date?: string | null;
  total_amount: number | string;
  item_count: number;
  status: OfferStatus;
  expires_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OfferDetail {
  id: string;
  offer_number: string;
  conversation_id: string;
  sender_id: string;
  recipient_id: string;
  parent_offer_id?: string | null;
  delivery_terms?: string | null;
  proposed_delivery_date?: string | null;
  total_amount: number | string;
  status: OfferStatus;
  expires_at?: string | null;
  created_at: string;
  updated_at: string;
  sender?: OfferUserSummary | null;
  recipient?: OfferUserSummary | null;
  items: OfferItem[];
  order_id?: string | null;
  order_number?: string | null;
}

export interface OfferListResponse {
  items: OfferSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface OfferHistoryResponse {
  root_offer_id: string;
  current_offer_id: string;
  chain_length: number;
  history: OfferDetail[];
}

export interface OfferItemCreatePayload {
  listing_id: string;
  buyer_requirement_id?: string | null;
  product_name?: string | null;
  quantity: number;
  unit: string;
  unit_price: number;
  quality_grade?: string | null;
}

export interface OfferCreatePayload {
  recipient_id: string;
  delivery_terms?: string | null;
  proposed_delivery_date?: string | null;
  expires_at?: string | null;
  items: OfferItemCreatePayload[];
}

export interface CounterOfferCreatePayload {
  delivery_terms?: string | null;
  proposed_delivery_date?: string | null;
  expires_at?: string | null;
  items: OfferItemCreatePayload[];
}

export interface OfferRejectPayload {
  reason?: string | null;
}

export interface ItemFulfillmentDecision {
  offer_item_id: string;
  apply_to_requirement: boolean;
  approved_quantity?: number | null;
  close_requirement: boolean;
}

export interface OfferAcceptPayload {
  apply_to_requirement?: boolean;
  approved_quantity?: number | null;
  close_requirement?: boolean;
  item_fulfillments?: ItemFulfillmentDecision[] | null;
}

export interface OfferAcceptResponse {
  offer_id: string;
  offer_number: string;
  order_id: string;
  order_number: string;
  status: string;
  total_amount: number | string;
  message: string;
}

export interface OfferListFilterParams {
  role?: "sent" | "received";
  status?: string;
  conversation_id?: string;
  page?: number;
  page_size?: number;
}

