/**
 * Ratings, Reviews & Counterparty Reputation API service (Module 7).
 * Connects to FastAPI endpoints versioned under /api/v1/reviews.
 */

import { apiClient, ApiClient } from "./client";
import type {
  ReviewCreatePayload,
  ReviewItem,
  ReviewListResponse,
  UserReputationSummary,
} from "../types/reviews";

export class ReviewsApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  /**
   * Submit a rating and review for an eligible completed order.
   * Verified order participant only. Order must be in completed status.
   */
  public async submitReview(payload: ReviewCreatePayload): Promise<ReviewItem> {
    return this.client.post<ReviewItem>("/reviews", payload);
  }

  /**
   * Retrieve an individual rating and review by ID.
   */
  public async getReview(reviewId: string): Promise<ReviewItem> {
    return this.client.get<ReviewItem>(`/reviews/${reviewId}`);
  }

  /**
   * List paginated reviews received by a target user (newest first).
   */
  public async listUserReviews(
    userId: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<ReviewListResponse> {
    return this.client.get<ReviewListResponse>(
      `/reviews/users/${userId}?page=${page}&page_size=${pageSize}`
    );
  }

  /**
   * Calculate aggregate reputation statistics, criterion breakdowns, and star distribution for a user.
   */
  public async getUserReputationSummary(
    userId: string
  ): Promise<UserReputationSummary> {
    return this.client.get<UserReputationSummary>(
      `/reviews/users/${userId}/summary`
    );
  }

  /**
   * Retrieve reviews attached to a specific completed order.
   * Restricted to order participants and administrators.
   */
  public async getOrderReviews(orderId: string): Promise<ReviewItem[]> {
    return this.client.get<ReviewItem[]>(`/reviews/orders/${orderId}`);
  }
}

export const reviewsApi = new ReviewsApi();

