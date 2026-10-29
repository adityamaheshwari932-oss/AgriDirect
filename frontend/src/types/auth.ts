/**
 * Authentication and registration payloads and responses.
 * Aligned with backend Pydantic models in app.auth.schemas.
 */

import type { User } from "./user";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface FarmerRegisterRequest {
  email: string;
  password: string;
  password_confirm?: string;
  full_name: string;
  phone_number?: string;
  farm_name?: string;
  farm_location_address?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  latitude?: number;
  longitude?: number;
  farm_size_acres?: number;
  farming_practices?: string;
  primary_crops?: string;
  bio?: string;
}

export interface BuyerRegisterRequest {
  email: string;
  password: string;
  password_confirm?: string;
  contact_person_name?: string;
  full_name?: string;
  business_name?: string;
  business_type?: string;
  business_registration_number?: string;
  phone_number?: string;
  delivery_receiving_address?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  latitude?: number;
  longitude?: number;
  procurement_summary?: string;
  bio?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}
