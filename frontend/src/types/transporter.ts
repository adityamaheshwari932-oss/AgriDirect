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
