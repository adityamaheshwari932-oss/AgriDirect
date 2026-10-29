/**
 * User and Profile API endpoints.
 * Interacts with backend FastAPI endpoints defined in app.users.routes.
 */

import { apiClient, ApiClient } from "./client";
import type {
  BuyerProfileUpdate,
  FarmerProfileUpdate,
  User,
  UserProfileUpdate,
} from "../types";

export class UsersApi {
  private client: ApiClient;

  constructor(client: ApiClient = apiClient) {
    this.client = client;
  }

  /**
   * Fetch the current authenticated user's account details and attached profile.
   * Corresponds to GET /api/v1/users/me.
   */
  public async getUserProfile(): Promise<User> {
    return this.client.get<User>("/users/me");
  }

  /**
   * Update farmer-specific profile attributes.
   * Corresponds to PATCH /api/v1/users/me/farmer. Requires farmer role.
   */
  public async updateFarmerProfile(payload: FarmerProfileUpdate): Promise<User> {
    return this.client.patch<User>("/users/me/farmer", payload);
  }

  /**
   * Update buyer-specific profile attributes.
   * Corresponds to PATCH /api/v1/users/me/buyer. Requires buyer role.
   */
  public async updateBuyerProfile(payload: BuyerProfileUpdate): Promise<User> {
    return this.client.patch<User>("/users/me/buyer", payload);
  }

  /**
   * Update own profile using unified endpoint.
   * Corresponds to PATCH /api/v1/users/me.
   */
  public async updateProfile(payload: UserProfileUpdate): Promise<User> {
    return this.client.patch<User>("/users/me", payload);
  }
}

export const usersApi = new UsersApi();
