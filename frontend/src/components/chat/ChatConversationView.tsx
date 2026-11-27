import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Send,
  Paperclip,
  ShieldCheck,
  ShieldAlert,
  Loader2,
  AlertCircle,
  ChevronLeft,
  Phone,
  Check,
  X,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { chatApi } from "../../api/chat";
import { useAuth } from "../../store/authStore";
import type { ConversationDetail, Message } from "../../types/chat";
import { MessageBubble } from "./MessageBubble";
import { AttachmentModal } from "./AttachmentModal";
import { ContactShareModal } from "./ContactShareModal";

interface ChatConversationViewProps {
  conversationId: string;
  onBack?: () => void;
  onConversationUpdated?: () => void;
}

export const ChatConversationView: React.FC<ChatConversationViewProps> = ({
  conversationId,
  onBack,
  onConversationUpdated,
}) => {
  const { t } = useTranslation(["messaging", "common"]);
  const { user } = useAuth();

  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [textInput, setTextInput] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isAttachmentModalOpen, setIsAttachmentModalOpen] = useState(false);
  const [isContactModalOpen, setIsContactModalOpen] = useState(false);

  // Processing contact request actions
  const [isRespondingContact, setIsRespondingContact] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const onConversationUpdatedRef = useRef(onConversationUpdated);
  const isPollingRef = useRef(false);
  const lastMsgIdRef = useRef<string | undefined>(undefined);
  const hasInitialScrolledRef = useRef(false);

  useEffect(() => {
    onConversationUpdatedRef.current = onConversationUpdated;
  }, [onConversationUpdated]);

  useEffect(() => {
    lastMsgIdRef.current = messages.length > 0 ? messages[messages.length - 1].id : undefined;
  }, [messages]);

  const scrollToBottom = (smooth = true) => {
    if (typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: smooth ? "smooth" : "auto" });
    }
  };

  // Load conversation detail & initial message history
  const loadConversationData = useCallback(async () => {
    hasInitialScrolledRef.current = false;
    setIsLoading(true);
    setError(null);
    try {
      const [detail, msgs] = await Promise.all([
        chatApi.getConversation(conversationId),
        chatApi.listMessages(conversationId, { limit: 50, order: "asc" }),
      ]);
      setConversation(detail);
      setMessages(msgs);

      // Mark read
      if (detail.unread_count > 0) {
        void chatApi.markConversationRead(conversationId).then(() => {
          onConversationUpdatedRef.current?.();
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("messaging:load_thread_error", "Failed to load conversation.");
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, t]);

  useEffect(() => {
    void loadConversationData();
  }, [loadConversationData]);

  // Scroll to bottom on initial load
  useEffect(() => {
    if (!isLoading && messages.length > 0 && !hasInitialScrolledRef.current) {
      hasInitialScrolledRef.current = true;
      scrollToBottom(false);
    }
  }, [isLoading, messages.length]);

  // REST polling for new incoming messages
  useEffect(() => {
    let isCancelled = false;

    const pollInterval = setInterval(async () => {
      if (document.hidden) return; // Skip background tabs
      if (isPollingRef.current) return; // Prevent concurrent polling requests

      const lastMsgId = lastMsgIdRef.current;
      if (!lastMsgId) return;

      isPollingRef.current = true;
      try {
        const newMsgs = await chatApi.listMessages(conversationId, {
          after_id: lastMsgId,
          order: "asc",
          limit: 20,
        });

        if (!isCancelled && newMsgs.length > 0) {
          setMessages((prev) => {
            const existingIds = new Set(prev.map((m) => m.id));
            const fresh = newMsgs.filter((m) => !existingIds.has(m.id));
            if (fresh.length === 0) return prev;
            return [...prev, ...fresh];
          });
          scrollToBottom(true);
          void chatApi.markConversationRead(conversationId).then(() => {
            onConversationUpdatedRef.current?.();
          });
        }
      } catch {
        // Silent poll catch to prevent UI disruptions
      } finally {
        isPollingRef.current = false;
      }
    }, 3500);

    return () => {
      isCancelled = true;
      clearInterval(pollInterval);
      isPollingRef.current = false;
    };
  }, [conversationId]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = textInput.trim();
    if (!trimmed || isSending) return;

    setIsSending(true);
    setError(null);
    try {
      const msg = await chatApi.sendMessage(conversationId, { content: trimmed });
      setMessages((prev) => [...prev, msg]);
      setTextInput("");
      scrollToBottom(true);
      if (onConversationUpdated) onConversationUpdated();
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : t("messaging:send_error", "Failed to send message.");
      setError(errorMsg);
    } finally {
      setIsSending(false);
    }
  };

  const handleSendAttachment = async (file: File, caption: string) => {
    setIsSending(true);
    setError(null);
    try {
      const msg = await chatApi.sendMessageWithAttachment(
        conversationId,
        caption.trim() ? caption.trim() : t("messaging:attached_file", "Attached file"),
        file
      );
      setMessages((prev) => [...prev, msg]);
      scrollToBottom(true);
      if (onConversationUpdated) onConversationUpdated();
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : t("messaging:attachment_upload_error", "Failed to upload attachment.");
      setError(errorMsg);
    } finally {
      setIsSending(false);
    }
  };

  const handleApproveContactRequest = async (requestId: string) => {
    setIsRespondingContact(true);
    try {
      await chatApi.approveContactSharing(requestId);
      await loadConversationData();
      if (onConversationUpdated) onConversationUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("messaging:approve_contact_error", "Failed to approve contact request.");
      setError(msg);
    } finally {
      setIsRespondingContact(false);
    }
  };

  const handleRejectContactRequest = async (requestId: string) => {
    setIsRespondingContact(true);
    try {
      await chatApi.rejectContactSharing(requestId);
      await loadConversationData();
      if (onConversationUpdated) onConversationUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("messaging:reject_contact_error", "Failed to reject contact request.");
      setError(msg);
    } finally {
      setIsRespondingContact(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-xs text-muted-foreground gap-2">
        <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden="true" />
        <span>{t("messaging:loading_thread", "Loading message thread...")}</span>
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-xs text-muted-foreground gap-2">
        <AlertCircle className="w-6 h-6 text-destructive" aria-hidden="true" />
        <span>{t("messaging:thread_not_found", "Unable to find conversation thread.")}</span>
      </div>
    );
  }

  const other = conversation.other_participant;
  const isRecipientOfContactRequest =
    Boolean(
      conversation.active_contact_request &&
      conversation.active_contact_request.status === "pending" &&
      conversation.active_contact_request.requester_id !== user?.id
    );

  return (
    <div className="flex-1 flex flex-col h-full bg-card overflow-hidden">
      {/* Top Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between gap-3 bg-secondary/30 shrink-0">
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="lg:hidden p-1.5 rounded-lg text-muted-foreground hover:bg-secondary focus:outline-none"
              aria-label={t("messaging:back_to_list", "Back to conversations list")}
            >
              <ChevronLeft className="w-5 h-5 rtl:rotate-180" />
            </button>
          )}

          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-xs text-foreground truncate">
                {other.name || other.entity_name || t("messaging:counterparty", "Counterparty")}
              </span>
              <span className="text-[10px] px-1.5 py-0.2 rounded font-semibold bg-secondary text-muted-foreground uppercase">
                {other.role}
              </span>
              {other.verification_status === "verified" ? (
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" aria-label={t("common:status.verified", "Verified user")} />
              ) : (
                <ShieldAlert className="w-3.5 h-3.5 text-amber-500" aria-label={t("common:status.unverified", "Unverified user")} />
              )}
            </div>
            <p className="text-[10px] text-muted-foreground truncate">
              {t("messaging:context_label", "Context: {{type}}", {
                type: conversation.initial_context_type || t("messaging:general_inquiry", "General Inquiry"),
              })}
            </p>
          </div>
        </div>

        {/* Contact info button */}
        <div>
          <button
            type="button"
            onClick={() => setIsContactModalOpen(true)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl border border-border bg-card hover:bg-secondary transition-colors text-foreground"
          >
            <Phone className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
            <span>
              {conversation.contact_sharing_consented
                ? t("messaging:view_contact_info", "View Contact Info")
                : t("messaging:request_contact_info", "Request Contact Info")}
            </span>
          </button>
        </div>
      </div>

      {/* Pending Contact Consent Request Banner (if recipient) */}
      {isRecipientOfContactRequest && conversation.active_contact_request && (
        <div className="bg-primary-50/70 border-b border-primary-200 px-4 py-2 text-xs flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2 text-primary-950 font-medium">
            <Phone className="w-4 h-4 text-primary shrink-0" aria-hidden="true" />
            <span>{t("messaging:contact_request_banner", "Counterparty requested mutual phone and email contact disclosure.")}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={isRespondingContact}
              onClick={() => handleRejectContactRequest(conversation.active_contact_request!.id)}
              className="px-2.5 py-1 rounded-lg border border-border text-foreground hover:bg-secondary text-[11px] font-semibold transition-colors disabled:opacity-50 flex items-center gap-1"
            >
              <X className="w-3 h-3" />
              <span>{t("common:decline", "Decline")}</span>
            </button>
            <button
              type="button"
              disabled={isRespondingContact}
              onClick={() => handleApproveContactRequest(conversation.active_contact_request!.id)}
              className="px-2.5 py-1 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-[11px] font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-1"
            >
              <Check className="w-3 h-3" />
              <span>{t("common:approve", "Approve")}</span>
            </button>
          </div>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-1">
        {error && (
          <div className="p-2.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-xs text-muted-foreground p-6">
            <p className="font-semibold text-foreground">{t("messaging:beginning_title", "Beginning of conversation")}</p>
            <p className="text-[11px] max-w-xs mt-1">
              {t("messaging:beginning_subtitle", "Send a message to inquire about delivery schedules, harvest grades, or trade agreements.")}
            </p>
          </div>
        ) : (
          messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              isCurrentUser={m.sender_id === user?.id}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Input Area */}
      <form onSubmit={handleSendMessage} className="p-3 border-t border-border bg-secondary/20 flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={() => setIsAttachmentModalOpen(true)}
          className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
          aria-label={t("messaging:attach_file", "Attach file")}
        >
          <Paperclip className="w-4 h-4" aria-hidden="true" />
        </button>

        <input
          type="text"
          dir="auto"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder={t("messaging:type_placeholder", "Type your message...")}
          maxLength={5000}
          className="flex-1 rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium text-start"
        />

        <button
          type="submit"
          disabled={!textInput.trim() || isSending}
          className="p-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-xs focus:outline-none focus:ring-2 focus:ring-primary"
          aria-label={t("messaging:send_button", "Send message")}
        >
          {isSending ? (
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="w-4 h-4 rtl:-scale-x-100" aria-hidden="true" />
          )}
        </button>
      </form>

      {/* Attachment Modal */}
      <AttachmentModal
        isOpen={isAttachmentModalOpen}
        onClose={() => setIsAttachmentModalOpen(false)}
        onAttach={handleSendAttachment}
      />

      {/* Contact Sharing Modal */}
      <ContactShareModal
        isOpen={isContactModalOpen}
        conversationId={conversation.id}
        hasConsent={conversation.contact_sharing_consented}
        onClose={() => setIsContactModalOpen(false)}
        onRequestSent={() => void loadConversationData()}
      />
    </div>
  );
};

