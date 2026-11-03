/**
 * Contextual Messaging, Chat Threads, Attachments & Contact Sharing API service (Module 5).
 * Connects to FastAPI endpoints versioned under /api/v1.
 */

import { apiClient, ApiClient } from "./client";
import type {
  ChatUnreadCountResponse,
  ContactDetails,
  ContactShareRequest,
  ContactShareRequestCreatePayload,
  ConversationCreatePayload,
  ConversationDetail,
  ConversationListResponse,
  Message,
  MessageAttachment,
  MessageCreatePayload,
  ReadStatusResponse,
} from "../types/chat";

export class ChatApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  /**
   * Initiate a new conversation or retrieve an existing canonical thread.
   */
  public async createOrGetConversation(
    payload: ConversationCreatePayload
  ): Promise<ConversationDetail> {
    return this.client.post<ConversationDetail>("/conversations", payload);
  }

  /**
   * List conversations for the authenticated user with unread counts.
   */
  public async listConversations(params?: {
    context_type?: string;
    order_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<ConversationListResponse> {
    const query = new URLSearchParams();
    if (params?.context_type) query.set("context_type", params.context_type);
    if (params?.order_id) query.set("order_id", params.order_id);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset !== undefined) query.set("offset", String(params.offset));

    const qs = query.toString();
    const endpoint = qs ? `/conversations?${qs}` : "/conversations";
    return this.client.get<ConversationListResponse>(endpoint);
  }

  /**
   * Retrieve full conversation details, participant info, and contact consent state.
   */
  public async getConversation(conversationId: string): Promise<ConversationDetail> {
    return this.client.get<ConversationDetail>(`/conversations/${conversationId}`);
  }

  /**
   * Send a text message in an authorized conversation thread.
   */
  public async sendMessage(
    conversationId: string,
    payload: MessageCreatePayload
  ): Promise<Message> {
    return this.client.post<Message>(
      `/conversations/${conversationId}/messages`,
      payload
    );
  }

  /**
   * Retrieve ordered message history with cursor-based pagination.
   * Calling this marks counterparty messages as delivered on the backend.
   */
  public async listMessages(
    conversationId: string,
    params?: {
      limit?: number;
      before_id?: string;
      after_id?: string;
      order?: "asc" | "desc";
    }
  ): Promise<Message[]> {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.before_id) query.set("before_id", params.before_id);
    if (params?.after_id) query.set("after_id", params.after_id);
    if (params?.order) query.set("order", params.order);

    const qs = query.toString();
    const endpoint = qs
      ? `/conversations/${conversationId}/messages?${qs}`
      : `/conversations/${conversationId}/messages`;
    return this.client.get<Message[]>(endpoint);
  }

  /**
   * Send a message and upload an attachment atomically in a single request (multipart/form-data).
   */
  public async sendMessageWithAttachment(
    conversationId: string,
    content: string,
    file: File,
    orderId?: string | null
  ): Promise<Message> {
    const formData = new FormData();
    formData.append("content", content);
    formData.append("file", file);
    if (orderId) {
      formData.append("order_id", orderId);
    }

    return this.client.post<Message>(
      `/conversations/${conversationId}/messages/with-attachment`,
      formData
    );
  }

  /**
   * Upload an attachment to an existing message (multipart/form-data).
   */
  public async uploadAttachment(
    conversationId: string,
    messageId: string,
    file: File
  ): Promise<MessageAttachment> {
    const formData = new FormData();
    formData.append("file", file);

    return this.client.post<MessageAttachment>(
      `/conversations/${conversationId}/messages/${messageId}/attachments`,
      formData
    );
  }

  /**
   * Get direct streaming path for an attachment.
   */
  public getAttachmentUrl(attachmentId: string): string {
    return `${this.client.getBaseUrl()}/attachments/${attachmentId}`;
  }

  /**
   * Securely download a chat attachment using Bearer authentication and trigger browser download.
   */
  public async downloadAttachment(attachmentId: string, fallbackFilename?: string): Promise<void> {
    const { blob, filename } = await this.client.downloadBlob(`/attachments/${attachmentId}`);
    const resolvedFilename = filename || fallbackFilename || `attachment-${attachmentId}`;
    const objectUrl = URL.createObjectURL(blob);
    try {
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = resolvedFilename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } finally {
      URL.revokeObjectURL(objectUrl);
    }
  }

  /**
   * Mark all unread counterparty messages in the conversation as read.
   */
  public async markConversationRead(
    conversationId: string
  ): Promise<ReadStatusResponse> {
    return this.client.post<ReadStatusResponse>(
      `/conversations/${conversationId}/read`
    );
  }

  /**
   * Retrieve total unread messages in a thread for the authenticated user.
   */
  public async getUnreadCount(
    conversationId: string
  ): Promise<ChatUnreadCountResponse> {
    return this.client.get<ChatUnreadCountResponse>(
      `/conversations/${conversationId}/unread-count`
    );
  }

  /**
   * Initiate a bilateral contact sharing consent request.
   */
  public async requestContactSharing(
    conversationId: string,
    payload?: ContactShareRequestCreatePayload
  ): Promise<ContactShareRequest> {
    return this.client.post<ContactShareRequest>(
      `/conversations/${conversationId}/contact-requests`,
      payload || {}
    );
  }

  /**
   * List contact sharing requests in a conversation.
   */
  public async listContactRequests(
    conversationId: string
  ): Promise<ContactShareRequest[]> {
    return this.client.get<ContactShareRequest[]>(
      `/conversations/${conversationId}/contact-requests`
    );
  }

  /**
   * Approve a received contact sharing request.
   */
  public async approveContactSharing(
    requestId: string
  ): Promise<ContactShareRequest> {
    return this.client.post<ContactShareRequest>(
      `/contact-requests/${requestId}/approve`
    );
  }

  /**
   * Reject a received contact sharing request.
   */
  public async rejectContactSharing(
    requestId: string
  ): Promise<ContactShareRequest> {
    return this.client.post<ContactShareRequest>(
      `/contact-requests/${requestId}/reject`
    );
  }

  /**
   * Disclose counterparty phone and email after mutual consent is established.
   */
  public async getContactDetails(
    conversationId: string
  ): Promise<ContactDetails> {
    return this.client.get<ContactDetails>(
      `/conversations/${conversationId}/contacts`
    );
  }
}

export const chatApi = new ChatApi();

