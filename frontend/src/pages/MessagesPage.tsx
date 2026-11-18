import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  MessageSquare,
  Search,
  RotateCw,
  ShieldCheck,
  AlertCircle,
} from "lucide-react";
import { chatApi } from "../api/chat";
import type { ConversationItem, ContextType } from "../types/chat";
import { ConversationThreadList } from "../components/chat/ConversationThreadList";
import { ChatConversationView } from "../components/chat/ChatConversationView";

export const MessagesPage: React.FC = () => {
  const { t } = useTranslation(["messaging", "common"]);
  const [searchParams, setSearchParams] = useSearchParams();
  const activeConversationId = searchParams.get("conversationId");

  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [contextFilter, setContextFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const loadConversations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const filterParam = contextFilter !== "all" ? (contextFilter as ContextType) : undefined;
      const data = await chatApi.listConversations({
        context_type: filterParam,
        limit: 50,
      });
      setConversations(data.items);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("messaging:load_error", "Failed to load conversations.");
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [contextFilter, t]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  const filteredConversations = useMemo(() => {
    return conversations.filter((c) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      const otherName = (c.other_participant.name || c.other_participant.entity_name || "").toLowerCase();
      const preview = (c.last_message_preview || "").toLowerCase();
      return otherName.includes(q) || preview.includes(q);
    });
  }, [conversations, searchQuery]);

  const handleSelectConversation = (conv: ConversationItem) => {
    setSearchParams({ conversationId: conv.id });
  };

  const handleBackToList = () => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("conversationId");
    setSearchParams(newParams);
  };

  const handleConversationUpdated = useCallback(() => {
    void loadConversations();
  }, [loadConversations]);

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <MessageSquare className="w-6 h-6 text-primary" aria-hidden="true" />
            <span>{t("messaging:page_title", "Direct Messages")}</span>
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {t("messaging:page_subtitle", "Contextual negotiation and deal coordination between verified participants.")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadConversations()}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-card text-foreground hover:bg-secondary/60 disabled:opacity-50 transition-colors shadow-sm"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-primary" : ""}`} />
            {t("common:actions.refresh", "Refresh")}
          </button>
        </div>
      </div>

      {/* Main Dual-Pane Window */}
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden min-h-[600px] grid grid-cols-1 md:grid-cols-12 divide-y md:divide-y-0 md:divide-x divide-border">
        {/* Left Pane: Conversation List */}
        <div
          className={`md:col-span-4 lg:col-span-4 flex flex-col bg-background/50 ${
            activeConversationId ? "hidden md:flex" : "flex"
          }`}
        >
          {/* Filter Bar & Search */}
          <div className="p-3 border-b border-border space-y-2.5">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute start-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder={t("messaging:search_placeholder", "Search conversations...")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full ps-8 pe-3 py-1.5 text-xs rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* Context type filter tabs */}
            <div className="flex items-center gap-1 overflow-x-auto pb-1 text-[11px]">
              {[
                { id: "all", label: t("common:filters.all", "All") },
                { id: "listing", label: t("messaging:tab_listings", "Listings") },
                { id: "requirement", label: t("messaging:tab_requirements", "Requirements") },
                { id: "order", label: t("messaging:tab_orders", "Orders") },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setContextFilter(tab.id)}
                  className={`px-2.5 py-1 rounded-md font-medium whitespace-nowrap transition-colors ${
                    contextFilter === tab.id
                      ? "bg-primary text-primary-foreground shadow-xs"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* List or Error */}
          {error ? (
            <div className="p-4 text-center space-y-2 my-auto">
              <AlertCircle className="w-6 h-6 text-destructive mx-auto" />
              <p className="text-xs text-destructive font-medium">{error}</p>
              <button
                type="button"
                onClick={() => void loadConversations()}
                className="text-xs text-primary underline"
              >
                {t("common:actions.retry", "Try again")}
              </button>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto max-h-[680px]">
              <ConversationThreadList
                conversations={filteredConversations}
                selectedId={activeConversationId}
                onSelect={handleSelectConversation}
                isLoading={isLoading}
              />
            </div>
          )}
        </div>

        {/* Right Pane: Selected Conversation or Empty State */}
        <div
          className={`md:col-span-8 lg:col-span-8 flex flex-col bg-background ${
            !activeConversationId ? "hidden md:flex" : "flex"
          }`}
        >
          {activeConversationId ? (
            <ChatConversationView
              conversationId={activeConversationId}
              onBack={handleBackToList}
              onConversationUpdated={handleConversationUpdated}
            />
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground space-y-3">
              <div className="w-14 h-14 rounded-full bg-secondary/80 flex items-center justify-center border border-border">
                <MessageSquare className="w-7 h-7 text-primary/70" />
              </div>
              <div className="space-y-1">
                <h3 className="font-semibold text-sm text-foreground">
                  {t("messaging:select_conversation_title", "Select a Conversation")}
                </h3>
                <p className="text-xs max-w-sm text-muted-foreground">
                  {t("messaging:select_conversation_desc", "Choose a conversation from the left thread list, or initiate a chat directly from a produce listing, requirement, or order.")}
                </p>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground/80 bg-secondary/40 px-3 py-1.5 rounded-full border border-border">
                <ShieldCheck className="w-3.5 h-3.5 text-primary" />
                {t("messaging:shield_note", "Contact information is shielded until mutual consent is exchanged")}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

