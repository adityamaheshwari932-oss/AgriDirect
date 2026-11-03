/**
 * Domain types for AgriDirect Notifications & Operational Alerts (Module 7).
 * Aligned with backend Pydantic models in app.notifications.schemas.
 */

export type NotificationReferenceType = "order" | "offer" | "listing" | "verification";

export interface NotificationItem {
  id: string;
  user_id: string;
  event_type: string;
  title: string;
  body: string;
  reference_type?: NotificationReferenceType | null;
  reference_id?: string | null;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface NotificationMarkReadResponse {
  id: string;
  is_read: boolean;
  read_at: string;
  message: string;
}

export interface NotificationMarkAllReadResponse {
  marked_count: number;
  message: string;
}

export interface NotificationUnreadCountResponse {
  unread_count: number;
}

