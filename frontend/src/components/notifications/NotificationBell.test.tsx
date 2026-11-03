import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { NotificationBell } from "./NotificationBell";
import { notificationsApi } from "../../api/notifications";

vi.mock("../../api/notifications", () => ({
  notificationsApi: {
    getUnreadCount: vi.fn(),
    listNotifications: vi.fn(),
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn(),
  },
}));

describe("NotificationBell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders notification bell and shows unread badge when unread > 0", async () => {
    vi.mocked(notificationsApi.getUnreadCount).mockResolvedValueOnce({ unread_count: 5 });

    render(
      <MemoryRouter>
        <NotificationBell />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("5")).toBeInTheDocument();
    });
  });

  it("opens notification dropdown when clicked", async () => {
    vi.mocked(notificationsApi.getUnreadCount).mockResolvedValueOnce({ unread_count: 2 });
    vi.mocked(notificationsApi.listNotifications).mockResolvedValueOnce({
      items: [
        {
          id: "n-1",
          user_id: "user-1",
          event_type: "order_created",
          title: "New Order Placed",
          body: "Buyer placed order #ORD-1234",
          reference_type: "order",
          reference_id: "ord-1",
          is_read: false,
          created_at: "2026-03-30T10:00:00Z",
        },
      ],
      total: 1,
      unread_count: 1,
      page: 1,
      page_size: 15,
      total_pages: 1,
    });

    render(
      <MemoryRouter>
        <NotificationBell />
      </MemoryRouter>
    );

    const bellButton = screen.getByRole("button", { name: /Notifications/i });
    fireEvent.click(bellButton);

    await waitFor(() => {
      expect(screen.getByText("New Order Placed")).toBeInTheDocument();
      expect(screen.getByText("Buyer placed order #ORD-1234")).toBeInTheDocument();
    });
  });
});

