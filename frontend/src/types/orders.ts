/**
 * Domain types for AgriDirect Orders, Amendments, Inventory Ledger, and Fulfillment Approvals.
 * Aligned with backend Pydantic models in app.orders.schemas and app.requirements.schemas.
 */

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "payment_pending"
  | "payment_recorded"
  | "delivery_arranged"
  | "completed"
  | "cancelled"
  | "disputed";

export type DeliveryStatus =
  | "not_arranged"
  | "arranged"
  | "completion_marked"
  | "completed";

export type OrderItemStatus =
  | "confirmed"
  | "fulfilled"
  | "cancelled"
  | "disputed";

export type AmendmentType = "quantity" | "price" | "delivery_date" | "terms";

export type AmendmentStatus = "proposed" | "effective" | "rejected";

export type InventoryChangeType =
  | "order_fulfillment"
  | "order_cancellation_release"
  | "amendment_delta"
  | "manual_restock"
  | "manual_shrinkage";

export type FulfillmentApprovalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "not_applied"
  | "voided";

export interface OrderParticipant {
  id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  business_name?: string | null;
  farm_name?: string | null;
}

export interface OrderItem {
  id: string;
  order_id: string;
  listing_id?: string | null;
  buyer_requirement_id?: string | null;
  product_name: string;
  quantity: number | string;
  unit: string;
  unit_price: number | string;
  subtotal: number | string;
  quality_grade?: string | null;
  status: OrderItemStatus | string;
  created_at: string;
}

export interface OrderAmendment {
  id: string;
  order_id: string;
  proposed_by_user_id: string;
  amendment_type: AmendmentType;
  old_value: string;
  new_value: string;
  justification?: string | null;
  buyer_confirmed: boolean;
  farmer_confirmed: boolean;
  status: AmendmentStatus;
  effective_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderListItem {
  id: string;
  order_number: string;
  source_offer_id?: string | null;
  buyer_id: string;
  farmer_id: string;
  total_amount: number | string;
  currency: string;
  status: OrderStatus;
  delivery_status: DeliveryStatus;
  delivery_arranged_date?: string | null;
  items_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrderImage {
  id: string;
  order_id: string;
  image_url: string;
  mime_type: string;
  file_size_bytes: number;
  created_at: string;
}

export interface OrderCreatePayload {
  listing_id: string;
  quantity: number;
  delivery_destination_address?: string;
  delivery_arranged_date?: string;
  delivery_notes?: string;
  idempotency_key?: string;
}

export interface OrderDetail {
  id: string;
  order_number: string;
  source_offer_id?: string | null;
  buyer_id: string;
  farmer_id: string;
  total_amount: number | string;
  currency: string;
  status: OrderStatus;
  delivery_method?: string | null;
  delivery_destination_address?: string | null;
  delivery_arranged_date?: string | null;
  delivery_status: DeliveryStatus;
  delivery_completion_marked_by_user_id?: string | null;
  delivery_completion_marked_at?: string | null;
  delivery_acknowledged_by_user_id?: string | null;
  delivery_acknowledged_at?: string | null;
  delivery_notes?: string | null;
  cancellation_reason?: string | null;
  cancelled_by_user_id?: string | null;
  cancelled_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  buyer?: OrderParticipant | null;
  farmer?: OrderParticipant | null;
  amendments: OrderAmendment[];
  images?: OrderImage[];
}

export interface OrderListResponse {
  items: OrderListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface OrderAmendmentListResponse {
  items: OrderAmendment[];
  total: number;
}

export interface OrderCancelPayload {
  reason: string;
}

export interface OrderAmendmentCreatePayload {
  amendment_type: AmendmentType;
  order_item_id?: string | null;
  new_quantity?: number | null;
  new_price?: number | null;
  new_delivery_date?: string | null;
  new_terms?: string | null;
  justification: string;
}

export interface InventoryAdjustment {
  id: string;
  listing_id: string;
  order_id?: string | null;
  amendment_id?: string | null;
  change_type: InventoryChangeType | string;
  quantity_delta: number | string;
  recorded_by_user_id: string;
  notes?: string | null;
  created_at: string;
}

export interface InventoryAdjustmentListResponse {
  items: InventoryAdjustment[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FulfillmentApproval {
  id: string;
  requirement_id: string;
  order_id: string;
  order_item_id: string;
  proposed_quantity: number | string;
  approved_quantity?: number | string | null;
  status: FulfillmentApprovalStatus;
  reviewed_by_user_id?: string | null;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
  voided_by_user_id?: string | null;
  voided_at?: string | null;
  void_reason?: string | null;
  created_at: string;
  updated_at: string;
  requirement_title?: string | null;
  product_name?: string | null;
  unit?: string | null;
  requirement_remaining_quantity?: number | string | null;
  requirement_status?: string | null;
  order_number?: string | null;
}

export interface FulfillmentApprovalListResponse {
  items: FulfillmentApproval[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApproveFulfillmentPayload {
  approved_quantity?: number | null;
  close_requirement: boolean;
}

export interface RejectFulfillmentPayload {
  reason?: string | null;
}

export interface DeliveryArrangePayload {
  delivery_method: string;
  delivery_destination_address: string;
  delivery_arranged_date: string; // YYYY-MM-DD
  delivery_notes?: string | null;
}

export interface DeliveryAcknowledgePayload {
  notes?: string | null;
}

export interface OrderDeliveryAcknowledgement {
  id: string;
  order_id: string;
  user_id: string;
  acknowledged_at: string;
  notes?: string | null;
}

export interface OrderListFilterParams {
  role?: "buyer" | "farmer";
  status?: string;
  page?: number;
  page_size?: number;
}

