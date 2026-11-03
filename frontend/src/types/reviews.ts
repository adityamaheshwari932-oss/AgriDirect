/**
 * Domain types for AgriDirect Ratings, Reviews & Reputation (Module 7).
 * Aligned with backend Pydantic models in app.reviews.schemas.
 */

export interface ReviewCreatePayload {
  order_id: string;
  overall_rating: number; // 1-5
  quality_rating?: number | null; // 1-5
  accuracy_rating?: number | null; // 1-5
  communication_rating?: number | null; // 1-5
  reliability_rating?: number | null; // 1-5
  review_text?: string | null; // max 2000 chars
}

export interface ReviewItem {
  id: string;
  order_id: string;
  reviewer_id: string;
  reviewed_user_id: string;
  overall_rating: number;
  quality_rating?: number | null;
  accuracy_rating?: number | null;
  communication_rating?: number | null;
  reliability_rating?: number | null;
  review_text?: string | null;
  created_at: string;
}

export interface ReviewListResponse {
  items: ReviewItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UserReputationSummary {
  user_id: string;
  total_reviews: number;
  average_rating: number;
  quality_rating_avg?: number | null;
  accuracy_rating_avg?: number | null;
  communication_rating_avg?: number | null;
  reliability_rating_avg?: number | null;
  rating_distribution: Record<string, number>; // "1", "2", "3", "4", "5"
}

