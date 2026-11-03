import { describe, it, expect, vi, beforeEach } from "vitest";
import { notificationsApi } from "./notifications";
import { apiClient } from "./client";

describe("NotificationsApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("lists notifications with unread filter and pagination", async () => {
    const mockList = { items: [], total: 0, unread_count: 0, page: 1, page_size: 20, total_pages: 0 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockList);

    const res = await notificationsApi.listNotifications(1, 20, true);
    expect(apiClient.get).toHaveBeenCalledWith("/notifications?page=1&page_size=20&unread_only=true");
    expect(res).toEqual(mockList);
  });

  it("gets unread notification count", async () => {
    const mockCount = { unread_count: 5 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockCount);

    const res = await notificationsApi.getUnreadCount();
    expect(apiClient.get).toHaveBeenCalledWith("/notifications/unread-count");
    expect(res).toEqual(mockCount);
  });

  it("marks single notification as read", async () => {
    const mockResponse = { id: "notif-1", is_read: true, read_at: "2026-11-03T19:30:00Z", message: "Success" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const res = await notificationsApi.markNotificationRead("notif-1");
    expect(apiClient.post).toHaveBeenCalledWith("/notifications/notif-1/read");
    expect(res).toEqual(mockResponse);
  });

  it("marks all notifications as read", async () => {
    const mockResponse = { marked_count: 4, message: "All notifications marked read" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockResponse);

    const res = await notificationsApi.markAllRead();
    expect(apiClient.post).toHaveBeenCalledWith("/notifications/read-all");
    expect(res).toEqual(mockResponse);
  });
});

