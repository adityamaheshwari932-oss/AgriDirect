/**
 * Domain types for AgriDirect Contextual Messaging & Chat (Module 5).
 * Aligned with backend Pydantic models in app.chat.schemas.
 */

export type ContextType = "listing" | "requirement" | "offer" | "order" | "general";

export type MessageType = "text" | "system" | "contact_request";

export type MessageDeliveryStatus = "sent" | "delivered" | "read";

export type AttachmentType = "image" | "document";

export type ContactRequestStatus = "pending" | "approved" | "rejected" | "cancelled";

export interface ParticipantSummary {
  id: string;
  role: string;
  verification_status: string;
  name: string;
  entity_name?: string | null;
  email?: string | null;
  phone_number?: string | null;
}

export interface ConversationCreatePayload {
  target_user_id?: string | null;
  listing_id?: string | null;
  requirement_id?: string | null;
  order_id?: string | null;
  offer_id?: string | null;
}

export interface ConversationItem {
  id: string;
  farmer_id: string;
  buyer_id: string;
  initial_context_type?: string | null;
  initial_context_id?: string | null;
  order_id?: string | null;
  status: string;
  created_at: string;
  last_message_at: string;
  unread_count: number;
  other_participant: ParticipantSummary;
  last_message_preview?: string | null;
}

export interface ActiveContactRequestSummary {
  id: string;
  requester_id: string;
  status: ContactRequestStatus;
  requested_at: string;
}

export interface ConversationDetail extends ConversationItem {
  contact_sharing_consented: boolean;
  active_contact_request?: ActiveContactRequestSummary | null;
}

export interface ConversationListResponse {
  items: ConversationItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface MessageCreatePayload {
  content: string;
  order_id?: string | null;
}

export interface MessageAttachment {
  id: string;
  message_id: string;
  file_name: string;
  file_mime_type: string;
  file_size_bytes: number;
  attachment_type: AttachmentType;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  message_type: MessageType;
  delivery_status: MessageDeliveryStatus;
  is_read: boolean;
  delivered_at?: string | null;
  read_at?: string | null;
  order_id?: string | null;
  created_at: string;
  attachments: MessageAttachment[];
}

export interface MessageListResponse {
  items: Message[];
  total: number;
}

export interface ContactShareRequestCreatePayload {
  notes?: string | null;
}

export interface ContactShareRequest {
  id: string;
  conversation_id: string;
  requester_id: string;
  recipient_id: string;
  status: ContactRequestStatus;
  requested_at: string;
  responded_at?: string | null;
  notes?: string | null;
}

export interface ContactDetails {
  id: string;
  role: string;
  name: string;
  entity_name?: string | null;
  email?: string | null;
  phone_number?: string | null;
}

export interface ReadStatusResponse {
  conversation_id: string;
  marked_read_count: number;
}

export interface ChatUnreadCountResponse {
  conversation_id: string;
  unread_count: number;
}

