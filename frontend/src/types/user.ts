/**
 * Domain types for AgriDirect users and role-specific profiles.
 * Aligned with backend Pydantic models in app.auth.schemas and app.models.user.
 */

export type UserRole = "farmer" | "buyer" | "admin" | "transporter";

export type VerificationStatus = "unverified" | "pending" | "verified" | "rejected";

export type AccountStatus = "active" | "restricted" | "suspended" | "blocked" | "inactive";

export interface FarmerProfile {
  id: string;
  full_name: string;
  farm_name: string;
  farm_location_address: string;
  city: string;
  state: string;
  postal_code: string;
  latitude?: number | null;
  longitude?: number | null;
  farm_size_acres?: number | null;
  farming_practices?: string | null;
  primary_crops?: string | null;
  bio?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BuyerProfile {
  id: string;
  contact_person_name: string;
  business_name: string;
  business_type: string;
  business_registration_number?: string | null;
  delivery_receiving_address: string;
  city: string;
  state: string;
  postal_code: string;
  latitude?: number | null;
  longitude?: number | null;
  procurement_summary?: string | null;
  bio?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransporterProfile {
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
}

export interface User {
  id: string;
  email: string;
  phone_number?: string | null;
  role: UserRole;
  verification_status: VerificationStatus;
  account_status: AccountStatus;
  created_at: string;
  updated_at: string;
  farmer_profile?: FarmerProfile | null;
  buyer_profile?: BuyerProfile | null;
  transporter_profile?: TransporterProfile | null;
}

export interface FarmerProfileUpdate {
  full_name?: string;
  farm_name?: string;
  farm_location_address?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  latitude?: number | null;
  longitude?: number | null;
  farm_size_acres?: number | null;
  farming_practices?: string;
  primary_crops?: string;
  bio?: string;
  phone_number?: string;
}

export interface BuyerProfileUpdate {
  contact_person_name?: string;
  business_name?: string;
  business_type?: string;
  business_registration_number?: string;
  delivery_receiving_address?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  latitude?: number | null;
  longitude?: number | null;
  procurement_summary?: string;
  bio?: string;
  phone_number?: string;
}

export interface UserProfileUpdate {
  phone_number?: string;
  full_name?: string;
  farm_name?: string;
  farm_location_address?: string;
  farm_size_acres?: number | null;
  farming_practices?: string;
  primary_crops?: string;
  contact_person_name?: string;
  business_name?: string;
  business_type?: string;
  business_registration_number?: string;
  delivery_receiving_address?: string;
  procurement_summary?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  latitude?: number | null;
  longitude?: number | null;
  bio?: string;
}
