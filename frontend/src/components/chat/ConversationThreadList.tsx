import React from "react";
import { MessageSquare, Tractor, Store, Tag } from "lucide-react";
import type { ConversationItem } from "../../types/chat";

interface ConversationThreadListProps {
  conversations: ConversationItem[];
  selectedId: string | null;
  onSelect: (conversation: ConversationItem) => void;
  isLoading?: boolean;
}

export const ConversationThreadList: React.FC<ConversationThreadListProps> = ({
  conversations,
  selectedId,
  onSelect,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="divide-y divide-border animate-pulse p-3 space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="py-3 space-y-2">
            <div className="h-4 bg-secondary rounded w-1/2" />
            <div className="h-3 bg-secondary rounded w-3/4" />
          </div>
        ))}
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="py-12 px-4 text-center text-xs text-muted-foreground flex flex-col items-center justify-center gap-2">
        <MessageSquare className="w-8 h-8 opacity-40 text-muted-foreground" aria-hidden="true" />
        <p className="font-semibold text-foreground">No active conversations</p>
        <p className="text-[11px] max-w-xs">
          Conversations will appear here when you inquire about produce listings, requirements, or orders.
        </p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-border overflow-y-auto">
      {conversations.map((conv) => {
        const isSelected = conv.id === selectedId;
        const other = conv.other_participant;
        const isFarmer = other.role === "farmer";

        const formattedDate = new Date(conv.last_message_at).toLocaleDateString([], {
          month: "short",
          day: "numeric",
        });

        return (
          <button
            key={conv.id}
            type="button"
            onClick={() => onSelect(conv)}
            className={`w-full text-left p-3.5 transition-colors flex items-start gap-3 hover:bg-secondary/40 focus:outline-none ${
              isSelected ? "bg-primary-50/50 border-l-4 border-primary" : ""
            }`}
          >
            <div className="w-9 h-9 rounded-full bg-secondary flex items-center justify-center shrink-0 border border-border">
              {isFarmer ? (
                <Tractor className="w-4 h-4 text-primary" aria-hidden="true" />
              ) : (
                <Store className="w-4 h-4 text-blue-600" aria-hidden="true" />
              )}
            </div>

            <div className="flex-1 min-w-0 space-y-1">
              <div className="flex items-center justify-between gap-1">
                <span className="font-bold text-xs text-foreground truncate">
                  {other.name || other.entity_name || "Counterparty"}
                </span>
                <span className="text-[10px] text-muted-foreground shrink-0">{formattedDate}</span>
              </div>

              <div className="flex items-center gap-1.5">
                {conv.initial_context_type && (
                  <span className="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.2 rounded bg-secondary text-muted-foreground font-semibold uppercase tracking-wider shrink-0">
                    <Tag className="w-2.5 h-2.5" aria-hidden="true" />
                    {conv.initial_context_type}
                  </span>
                )}
                <span className="text-[10px] text-muted-foreground capitalize">
                  {other.role}
                </span>
              </div>

              <p className="text-xs text-muted-foreground truncate">
                {conv.last_message_preview || "No messages yet"}
              </p>
            </div>

            {conv.unread_count > 0 && (
              <span className="shrink-0 px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-primary text-primary-foreground">
                {conv.unread_count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};

