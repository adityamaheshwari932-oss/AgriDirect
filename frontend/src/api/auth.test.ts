import { describe, expect, it, vi } from "vitest";
import { AuthApi } from "./auth";
import type { ApiClient } from "./client";
import type {
  BuyerRegisterRequest,
  FarmerRegisterRequest,
  LoginRequest,
  TokenResponse,
  User,
} from "../types";

describe("AuthApi", () => {
  const mockUser: User = {
    id: "user-123",
    email: "farmer@example.com",
    role: "farmer",
    verification_status: "unverified",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    farmer_profile: {
      id: "profile-123",
      full_name: "Ramesh Patel",
      farm_name: "Patel Farms",
      farm_location_address: "Khed",
      city: "Pune",
      state: "Maharashtra",
      postal_code: "411001",
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
    },
  };

  it("calls POST /auth/login with credentials and skipAuth", async () => {
    const mockPost = vi.fn().mockResolvedValueOnce({
      access_token: "jwt-token-abc",
      token_type: "bearer",
      user: mockUser,
    } as TokenResponse);

    const mockClient = { post: mockPost, get: vi.fn() } as unknown as ApiClient;
    const api = new AuthApi(mockClient);

    const credentials: LoginRequest = { email: "farmer@example.com", password: "Password123!" };
    const response = await api.login(credentials);

    expect(mockPost).toHaveBeenCalledWith("/auth/login", credentials, { skipAuth: true });
    expect(response.access_token).toBe("jwt-token-abc");
    expect(response.user.email).toBe("farmer@example.com");
  });

  it("calls POST /auth/register/farmer with farmer payload and skipAuth", async () => {
    const mockPost = vi.fn().mockResolvedValueOnce(mockUser);
    const mockClient = { post: mockPost, get: vi.fn() } as unknown as ApiClient;
    const api = new AuthApi(mockClient);

    const payload: FarmerRegisterRequest = {
      email: "farmer@example.com",
      password: "Password123!",
      full_name: "Ramesh Patel",
      farm_name: "Patel Farms",
    };
    const response = await api.registerFarmer(payload);

    expect(mockPost).toHaveBeenCalledWith("/auth/register/farmer", payload, { skipAuth: true });
    expect(response.id).toBe("user-123");
    expect(response.role).toBe("farmer");
  });

  it("calls POST /auth/register/buyer with buyer payload and skipAuth", async () => {
    const mockBuyerUser: User = {
      id: "buyer-456",
      email: "buyer@restaurant.com",
      role: "buyer",
      verification_status: "unverified",
      account_status: "active",
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
      buyer_profile: {
        id: "bprofile-456",
        contact_person_name: "Sita Sharma",
        business_name: "Taj Caterers",
        business_type: "caterer",
        delivery_receiving_address: "Dock 4, Mumbai",
        city: "Mumbai",
        state: "Maharashtra",
        postal_code: "400001",
        created_at: "2026-10-29T12:00:00Z",
        updated_at: "2026-10-29T12:00:00Z",
      },
    };

    const mockPost = vi.fn().mockResolvedValueOnce(mockBuyerUser);
    const mockClient = { post: mockPost, get: vi.fn() } as unknown as ApiClient;
    const api = new AuthApi(mockClient);

    const payload: BuyerRegisterRequest = {
      email: "buyer@restaurant.com",
      password: "Password123!",
      contact_person_name: "Sita Sharma",
      business_name: "Taj Caterers",
      business_type: "caterer",
    };
    const response = await api.registerBuyer(payload);

    expect(mockPost).toHaveBeenCalledWith("/auth/register/buyer", payload, { skipAuth: true });
    expect(response.role).toBe("buyer");
    expect(response.buyer_profile?.business_name).toBe("Taj Caterers");
  });

  it("calls GET /users/me to fetch current user profile", async () => {
    const mockGet = vi.fn().mockResolvedValueOnce(mockUser);
    const mockClient = { get: mockGet, post: vi.fn() } as unknown as ApiClient;
    const api = new AuthApi(mockClient);

    const user = await api.getCurrentUser();

    expect(mockGet).toHaveBeenCalledWith("/users/me");
    expect(user.id).toBe("user-123");
  });
});
