/**
 * TypeScript interfaces for Transporter role and operations.
 * Corresponds to backend app.transporters.schemas.
 */

export type TransportType =
  | "mini_truck"
  | "open_body"
  | "refrigerated"
  | "covered_truck"
  | "tempo"
  | "trailer"
  | "other";

export type CoverageType = "pickup_only" | "delivery_only" | "both";

export type TransportStatus =
  | "none"
  | "assigned"
  | "in_transit"
  | "delivered"
  | "cancelled";

export interface ServiceArea {
  id: string;
  transporter_profile_id: string;
  state: string;
  district: string;
  taluka_subdistrict?: string | null;
  village_town?: string | null;
  pincode?: string | null;
  coverage_type: CoverageType;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ServiceAreaCreate {
  state: string;
  district: string;
  taluka_subdistrict?: string;
  village_town?: string;
  pincode?: string;
  coverage_type?: CoverageType;
  is_active?: boolean;
}

export interface ServiceAreaUpdate {
  taluka_subdistrict?: string;
  village_town?: string;
  pincode?: string;
  coverage_type?: CoverageType;
  is_active?: boolean;
}

export interface TransporterRegisterRequest {
  email: string;
  password: string;
  phone_number: string;
  business_name: string;
  contact_name: string;
  transport_type: TransportType | string;
  vehicle_capacity_kg: number;
  vehicle_registration_number: string;
  experience_years?: number;
  operating_states?: string;
  bio?: string;
  initial_service_areas?: ServiceAreaCreate[];
}

export interface TransporterProfileUpdate {
  business_name?: string;
  contact_name?: string;
  phone_number?: string;
  transport_type?: string;
  vehicle_capacity_kg?: number;
  vehicle_registration_number?: string;
  is_available?: boolean;
  experience_years?: number;
  operating_states?: string;
  bio?: string;
}

export interface TransporterDetail {
  id: string;
  user_id: string;
  business_name: string;
  contact_name: string;
  phone_number: string;
  transport_type: string;
  vehicle_capacity_kg: number;
  vehicle_registration_number: string;
  is_available: boolean;
  experience_years: number;
  operating_states?: string | null;
  bio?: string | null;
  verification_status: string;
  created_at: string;
  updated_at: string;
  service_areas: ServiceArea[];
}

export interface TransporterSearchResult {
  id: string;
  user_id: string;
  business_name: string;
  contact_name: string;
  phone_number: string;
  transport_type: string;
  vehicle_capacity_kg: number;
  vehicle_registration_number: string;
  is_available: boolean;
  experience_years: number;
  operating_states?: string | null;
  bio?: string | null;
  verification_status: string;
  service_areas: ServiceArea[];
}

export interface TransporterSearchResponse {
  total: number;
  items: TransporterSearchResult[];
}

export interface TransporterSearchParams {
  pickup_state?: string;
  pickup_district?: string;
  delivery_state?: string;
  delivery_district?: string;
  transport_type?: string;
  min_capacity_kg?: number;
  only_available?: boolean;
  page?: number;
  page_size?: number;
}

export interface OrderTransportCoordinationRequest {
  transporter_user_id?: string;
  transport_status?: TransportStatus;
  delivery_notes?: string;
}

export interface OrderTransportCoordinationResponse {
  order_id: string;
  order_number: string;
  transporter_id?: string | null;
  transporter_business_name?: string | null;
  transporter_phone?: string | null;
  transport_status: string;
  delivery_notes?: string | null;
}

export type TransportRequestStatus =
  | "pending"
  | "transporter_accepted"
  | "counterparty_approved"
  | "counterparty_rejected"
  | "declined"
  | "cancelled"
  | "accepted";

export interface TransportConnectionRequestCreate {
  transporter_user_id: string;
  order_id?: string;
  offer_id?: string;
  pickup_state?: string;
  pickup_district?: string;
  pickup_address?: string;
  delivery_state?: string;
  delivery_district?: string;
  delivery_address?: string;
  cargo_description?: string;
  weight_kg?: number;
  required_delivery_date?: string;
  notes?: string;
}

export interface TransportConnectionRequestResponse {
  response_notes?: string;
  rejection_reason?: string;
}

export interface TransportConnectionApprovalPayload {
  approval_notes?: string;
}

export interface TransportConnectionRejectionPayload {
  counterparty_rejection_reason?: string;
}

export interface TransportConnectionRequest {
  id: string;
  requester_id: string;
  transporter_id: string;
  order_id?: string | null;
  offer_id?: string | null;
  order_number?: string | null;
  offer_number?: string | null;
  requester_name: string;
  requester_role: string;
  transporter_business_name: string;
  transporter_contact_name: string;
  transporter_phone: string;
  pickup_state?: string | null;
  pickup_district?: string | null;
  pickup_address?: string | null;
  delivery_state?: string | null;
  delivery_district?: string | null;
  delivery_address?: string | null;
  cargo_description?: string | null;
  weight_kg?: number | null;
  required_delivery_date?: string | null;
  notes?: string | null;
  status: TransportRequestStatus;
  rejection_reason?: string | null;
  response_notes?: string | null;
  transporter_accepted_at?: string | null;
  counterparty_approved_by_id?: string | null;
  counterparty_approved_at?: string | null;
  counterparty_rejected_by_id?: string | null;
  counterparty_rejected_at?: string | null;
  counterparty_rejection_reason?: string | null;
  counterparty_name?: string | null;
  can_current_user_approve?: boolean;
  can_current_user_reject?: boolean;
  created_at: string;
  updated_at: string;
}

export interface TransportConnectionRequestListResponse {
  total: number;
  items: TransportConnectionRequest[];
}
