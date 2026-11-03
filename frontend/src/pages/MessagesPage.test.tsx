import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MessagesPage } from "./MessagesPage";
import { chatApi } from "../api/chat";
import type { ConversationItem, ConversationListResponse } from "../types/chat";

vi.mock("../api/chat", () => ({
  chatApi: {
    listConversations: vi.fn(),
    getConversation: vi.fn(),
    listMessages: vi.fn(),
    markConversationRead: vi.fn(),
    sendMessage: vi.fn(),
    createOrGetConversation: vi.fn(),
  },
}));

vi.mock("../store/authStore", () => ({
  useAuth: () => ({
    user: { id: "user-1", email: "farmer@test.com", role: "farmer", is_verified: true },
    isAuthenticated: true,
  }),
}));

const mockConversations: ConversationItem[] = [
  {
    id: "conv-1",
    farmer_id: "user-1",
    buyer_id: "buyer-1",
    status: "active",
    created_at: "2026-03-29T10:00:00Z",
    initial_context_type: "listing",
    initial_context_id: "list-100",
    other_participant: {
      id: "buyer-1",
      name: "Acme Supermarkets",
      role: "buyer",
      verification_status: "verified",
      entity_name: "Acme Corp",
    },
    last_message_at: "2026-03-30T10:00:00Z",
    last_message_preview: "Interested in the 500kg Alphonso mangoes",
    unread_count: 2,
  },
  {
    id: "conv-2",
    farmer_id: "user-1",
    buyer_id: "buyer-2",
    status: "active",
    created_at: "2026-03-28T10:00:00Z",
    initial_context_type: "order",
    initial_context_id: "order-200",
    other_participant: {
      id: "buyer-2",
      name: "Fresh Foods Ltd",
      role: "buyer",
      verification_status: "verified",
      entity_name: "Fresh Foods Ltd",
    },
    last_message_at: "2026-03-29T14:30:00Z",
    last_message_preview: "Delivery scheduled for tomorrow",
    unread_count: 0,
  },
];

const mockListResponse: ConversationListResponse = {
  items: mockConversations,
  total: mockConversations.length,
  limit: 50,
  offset: 0,
};

describe("MessagesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders messages page and displays conversation list", async () => {
    vi.mocked(chatApi.listConversations).mockResolvedValueOnce(mockListResponse);

    render(
      <MemoryRouter>
        <MessagesPage />
      </MemoryRouter>
    );

    expect(screen.getByText("Direct Messages")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Acme Supermarkets")).toBeInTheDocument();
      expect(screen.getByText("Fresh Foods Ltd")).toBeInTheDocument();
    });

    expect(screen.getByText("Interested in the 500kg Alphonso mangoes")).toBeInTheDocument();
  });

  it("filters conversations by search query", async () => {
    vi.mocked(chatApi.listConversations).mockResolvedValueOnce(mockListResponse);

    render(
      <MemoryRouter>
        <MessagesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Acme Supermarkets")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search conversations...");
    fireEvent.change(searchInput, { target: { value: "Fresh Foods" } });

    expect(screen.queryByText("Acme Supermarkets")).not.toBeInTheDocument();
    expect(screen.getByText("Fresh Foods Ltd")).toBeInTheDocument();
  });

  it("displays empty state when no conversation is selected", async () => {
    vi.mocked(chatApi.listConversations).mockResolvedValueOnce(mockListResponse);

    render(
      <MemoryRouter>
        <MessagesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Select a Conversation")).toBeInTheDocument();
    });
  });

  it("handles loading error gracefully", async () => {
    vi.mocked(chatApi.listConversations).mockRejectedValueOnce(new Error("Network Error"));

    render(
      <MemoryRouter>
        <MessagesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Network Error")).toBeInTheDocument();
    });
  });
});
