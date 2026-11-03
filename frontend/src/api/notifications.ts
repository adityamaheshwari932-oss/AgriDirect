/**
 * Notifications & Operational Alerts API service (Module 7).
 * Connects to FastAPI endpoints versioned under /api/v1/notifications.
 */

import { apiClient, ApiClient } from "./client";
import type {
  NotificationItem,
  NotificationListResponse,
  NotificationMarkAllReadResponse,
  NotificationMarkReadResponse,
  NotificationUnreadCountResponse,
} from "../types/notifications";

export class NotificationsApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  /**
   * Retrieve paginated notifications inbox for the authenticated user.
   * Unread notifications appear first, followed by newest-first.
   */
  public async listNotifications(
    page: number = 1,
    pageSize: number = 20,
    unreadOnly: boolean = false
  ): Promise<NotificationListResponse> {
    const query = new URLSearchParams();
    query.set("page", String(page));
    query.set("page_size", String(pageSize));
    if (unreadOnly) {
      query.set("unread_only", "true");
    }

    return this.client.get<NotificationListResponse>(
      `/notifications?${query.toString()}`
    );
  }

  /**
   * Fast aggregate query of total unread notifications for badge rendering.
   */
  public async getUnreadCount(): Promise<NotificationUnreadCountResponse> {
    return this.client.get<NotificationUnreadCountResponse>(
      "/notifications/unread-count"
    );
  }

  /**
   * Mark a single notification as read.
   */
  public async markNotificationRead(
    id: string
  ): Promise<NotificationMarkReadResponse> {
    return this.client.post<NotificationMarkReadResponse>(
      `/notifications/${id}/read`
    );
  }

  /**
   * Bulk mark all notifications belonging to the authenticated user as read.
   */
  public async markAllRead(): Promise<NotificationMarkAllReadResponse> {
    return this.client.post<NotificationMarkAllReadResponse>(
      "/notifications/read-all"
    );
  }

  /**
   * Retrieve details of a single notification owned by caller.
   */
  public async getNotification(id: string): Promise<NotificationItem> {
    return this.client.get<NotificationItem>(`/notifications/${id}`);
  }
}

export const notificationsApi = new NotificationsApi();

