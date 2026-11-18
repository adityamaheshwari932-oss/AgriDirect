import { render, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ChatConversationView } from "./ChatConversationView";
import { chatApi } from "../../api/chat";
import { authStore } from "../../store/authStore";
import type { ConversationDetail, Message } from "../../types/chat";
import type { User } from "../../types";

vi.mock("../../api/chat", () => ({
  chatApi: {
    getConversation: vi.fn(),
    listMessages: vi.fn(),
    markConversationRead: vi.fn(),
    sendMessage: vi.fn(),
    requestContactShare: vi.fn(),
    respondContactShare: vi.fn(),
    uploadAttachment: vi.fn(),
  },
}));

describe("ChatConversationView — D-5 Polling & Remount Regression Tests", () => {
  const currentUser: User = {
    id: "user-farmer-1",
    email: "farmer@agridirect.in",
    role: "farmer",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };

  const mockConversation: ConversationDetail = {
    id: "conv-100",
    farmer_id: "user-farmer-1",
    buyer_id: "user-buyer-1",
    status: "active",
    initial_context_type: "order",
    order_id: "ord-1",
    created_at: "2026-01-10T10:00:00Z",
    last_message_at: "2026-01-10T10:00:00Z",
    unread_count: 0,
    contact_sharing_consented: false,
    other_participant: {
      id: "user-buyer-1",
      name: "Sunil Sharma",
      entity_name: "Sharma Agro",
      role: "buyer",
      verification_status: "verified",
    },
  };

  const initialMessages: Message[] = [
    {
      id: "msg-1",
      conversation_id: "conv-100",
      sender_id: "user-buyer-1",
      content: "Hello, when can you dispatch the wheat?",
      message_type: "text",
      delivery_status: "delivered",
      is_read: true,
      attachments: [],
      created_at: "2026-01-10T10:00:00Z",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    authStore.reset();
    authStore.setUser(currentUser);

    vi.mocked(chatApi.getConversation).mockResolvedValue(mockConversation);
    vi.mocked(chatApi.listMessages).mockResolvedValue(initialMessages);
    vi.mocked(chatApi.markConversationRead).mockResolvedValue({ success: true } as any);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not re-trigger loadConversationData when onConversationUpdated changes reference", async () => {
    let updateFn1 = vi.fn();
    let updateFn2 = vi.fn();

    const { rerender } = render(
      <MemoryRouter>
        <ChatConversationView
          conversationId="conv-100"
          onConversationUpdated={updateFn1}
        />
      </MemoryRouter>
    );

    // Initial load
    await act(async () => {
      await Promise.resolve();
    });

    expect(chatApi.getConversation).toHaveBeenCalledTimes(1);
    expect(chatApi.listMessages).toHaveBeenCalledTimes(1);

    // Re-render with a NEW onConversationUpdated callback identity (simulating unmemoized parent)
    rerender(
      <MemoryRouter>
        <ChatConversationView
          conversationId="conv-100"
          onConversationUpdated={updateFn2}
        />
      </MemoryRouter>
    );

    await act(async () => {
      await Promise.resolve();
    });

    // Should NOT re-trigger loadConversationData
    expect(chatApi.getConversation).toHaveBeenCalledTimes(1);
    expect(chatApi.listMessages).toHaveBeenCalledTimes(1);
  });

  it("marks unread conversation as read and notifies onConversationUpdated without loop", async () => {
    const onUpdated = vi.fn();
    vi.mocked(chatApi.getConversation).mockResolvedValue({
      ...mockConversation,
      unread_count: 3,
    });

    render(
      <MemoryRouter>
        <ChatConversationView
          conversationId="conv-100"
          onConversationUpdated={onUpdated}
        />
      </MemoryRouter>
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(chatApi.markConversationRead).toHaveBeenCalledWith("conv-100");
    await act(async () => {
      await Promise.resolve();
    });
    expect(onUpdated).toHaveBeenCalledTimes(1);
  });

  it("polls for new messages at 3.5s interval without tearing down timer on state change", async () => {
    render(
      <MemoryRouter>
        <ChatConversationView conversationId="conv-100" />
      </MemoryRouter>
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(chatApi.listMessages).toHaveBeenCalledTimes(1);

    // Mock incoming poll message
    const incomingMsg: Message = {
      id: "msg-2",
      conversation_id: "conv-100",
      sender_id: "user-buyer-1",
      content: "Confirmed, we are ready to receive.",
      message_type: "text",
      delivery_status: "delivered",
      is_read: true,
      attachments: [],
      created_at: "2026-01-10T10:05:00Z",
    };

    vi.mocked(chatApi.listMessages).mockResolvedValueOnce([incomingMsg]);

    // Advance timer by 3500ms
    await act(async () => {
      vi.advanceTimersByTime(3500);
    });

    expect(chatApi.listMessages).toHaveBeenCalledWith("conv-100", {
      after_id: "msg-1",
      order: "asc",
      limit: 20,
    });

    // Now advance another 3500ms, should poll with after_id: msg-2
    vi.mocked(chatApi.listMessages).mockResolvedValueOnce([]);

    await act(async () => {
      vi.advanceTimersByTime(3500);
    });

    expect(chatApi.listMessages).toHaveBeenCalledWith("conv-100", {
      after_id: "msg-2",
      order: "asc",
      limit: 20,
    });
  });

  it("cleans up timer when unmounting and stops polling", async () => {
    const { unmount } = render(
      <MemoryRouter>
        <ChatConversationView conversationId="conv-100" />
      </MemoryRouter>
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(chatApi.listMessages).toHaveBeenCalledTimes(1);

    // Unmount
    unmount();

    // Advance timer
    await act(async () => {
      vi.advanceTimersByTime(7000);
    });

    // Should not have polled again
    expect(chatApi.listMessages).toHaveBeenCalledTimes(1);
  });
});
