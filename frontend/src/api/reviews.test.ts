import { describe, it, expect, vi, beforeEach } from "vitest";
import { reviewsApi } from "./reviews";
import { apiClient } from "./client";

describe("ReviewsApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("submits a review on a completed order", async () => {
    const payload = {
      order_id: "order-1",
      overall_rating: 5,
      quality_rating: 5,
      communication_rating: 4,
      review_text: "Excellent organic produce",
    };
    const mockReview = { id: "rev-1", ...payload };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockReview);

    const res = await reviewsApi.submitReview(payload);
    expect(apiClient.post).toHaveBeenCalledWith("/reviews", payload);
    expect(res).toEqual(mockReview);
  });

  it("retrieves user reputation summary", async () => {
    const mockSummary = {
      user_id: "user-1",
      total_reviews: 12,
      average_rating: 4.75,
      rating_distribution: { "5": 9, "4": 3, "3": 0, "2": 0, "1": 0 },
    };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockSummary);

    const res = await reviewsApi.getUserReputationSummary("user-1");
    expect(apiClient.get).toHaveBeenCalledWith("/reviews/users/user-1/summary");
    expect(res).toEqual(mockSummary);
  });

  it("lists reviews received by a user with pagination", async () => {
    const mockList = { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockList);

    const res = await reviewsApi.listUserReviews("user-1", 1, 20);
    expect(apiClient.get).toHaveBeenCalledWith("/reviews/users/user-1?page=1&page_size=20");
    expect(res).toEqual(mockList);
  });

  it("retrieves order-specific reviews", async () => {
    const mockReviews = [{ id: "rev-1", overall_rating: 5 }];
    vi.spyOn(apiClient, "get").mockResolvedValue(mockReviews);

    const res = await reviewsApi.getOrderReviews("order-1");
    expect(apiClient.get).toHaveBeenCalledWith("/reviews/orders/order-1");
    expect(res).toEqual(mockReviews);
  });
});

