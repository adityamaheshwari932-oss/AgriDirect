/**
 * Authentication and current-user API endpoints.
 * Interacts with backend FastAPI endpoints defined in app.auth.routes and app.users.routes.
 */

import { apiClient, ApiClient } from "./client";
import type {
  BuyerRegisterRequest,
  FarmerRegisterRequest,
  LoginRequest,
  TokenResponse,
  TransporterRegisterRequest,
  User,
} from "../types";

export class AuthApi {
  private client: ApiClient;

  constructor(client: ApiClient = apiClient) {
    this.client = client;
  }

  /**
   * Authenticate with email and password to receive a JWT access token and user account details.
   */
  public async login(payload: LoginRequest): Promise<TokenResponse> {
    return this.client.post<TokenResponse>("/auth/login", payload, { skipAuth: true });
  }

  /**
   * Register a new verified farmer account and initial farm profile.
   * Note: Registration creates the user and profile, returning UserRead with HTTP 201.
   * It does not automatically issue a token or log the user in.
   */
  public async registerFarmer(payload: FarmerRegisterRequest): Promise<User> {
    return this.client.post<User>("/auth/register/farmer", payload, { skipAuth: true });
  }

  /**
   * Register a new commercial buyer account and initial business profile.
   * Note: Registration creates the user and profile, returning UserRead with HTTP 201.
   * It does not automatically issue a token or log the user in.
   */
  public async registerBuyer(payload: BuyerRegisterRequest): Promise<User> {
    return this.client.post<User>("/auth/register/buyer", payload, { skipAuth: true });
  }

  /**
   * Register a new transportation service provider account and initial fleet profile.
   * Note: Registration creates the user and profile, returning UserRead with HTTP 201.
   * It does not automatically issue a token or log the user in.
   */
  public async registerTransporter(payload: TransporterRegisterRequest): Promise<User> {
    return this.client.post<User>("/auth/register/transporter", payload, { skipAuth: true });
  }

  /**
   * Fetch the safe account details and profile for the currently authenticated active user.
   * Requires a valid Bearer token in the request header.
   */
  public async getCurrentUser(): Promise<User> {
    return this.client.get<User>("/users/me");
  }
}

export const authApi = new AuthApi();
