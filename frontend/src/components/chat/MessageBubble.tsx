import React, { useState } from "react";
import { Check, CheckCheck, FileText, Image, Download, Loader2, AlertCircle } from "lucide-react";
import { chatApi } from "../../api/chat";
import type { Message } from "../../types/chat";

interface MessageBubbleProps {
  message: Message;
  isCurrentUser: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isCurrentUser,
}) => {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleDownload = async (attachmentId: string, filename: string) => {
    setDownloadingId(attachmentId);
    setDownloadError(null);
    try {
      await chatApi.downloadAttachment(attachmentId, filename);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Download failed";
      setDownloadError(msg);
    } finally {
      setDownloadingId(null);
    }
  };

  // System messages are rendered centered
  if (message.message_type === "system") {
    return (
      <div className="flex justify-center my-2">
        <span className="px-3 py-1 rounded-full text-[11px] font-medium bg-secondary text-muted-foreground border border-border">
          {message.content}
        </span>
      </div>
    );
  }

  const formattedTime = new Date(message.created_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className={`flex flex-col mb-3 ${
        isCurrentUser ? "items-end" : "items-start"
      }`}
    >
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-xs shadow-xs space-y-1.5 ${
          isCurrentUser
            ? "bg-primary text-primary-foreground rounded-br-xs"
            : "bg-secondary text-foreground rounded-bl-xs border border-border"
        }`}
      >
        <p className="whitespace-pre-wrap break-words leading-relaxed">
          {message.content}
        </p>

        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="space-y-1 pt-1 border-t border-white/20">
            {message.attachments.map((att) => {
              const isImage = att.attachment_type === "image";

              return (
                <div
                  key={att.id}
                  className={`p-2 rounded-xl flex items-center justify-between gap-2 text-[11px] ${
                    isCurrentUser ? "bg-black/10" : "bg-card border border-border"
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    {isImage ? (
                      <Image className="w-4 h-4 shrink-0 text-primary" aria-hidden="true" />
                    ) : (
                      <FileText className="w-4 h-4 shrink-0 text-primary" aria-hidden="true" />
                    )}
                    <span className="truncate font-medium">{att.file_name}</span>
                    <span className="text-[10px] opacity-75 shrink-0">
                      ({(att.file_size_bytes / 1024).toFixed(0)} KB)
                    </span>
                  </div>

                  <button
                    type="button"
                    disabled={downloadingId === att.id}
                    onClick={() => void handleDownload(att.id, att.file_name)}
                    className="p-1 rounded-lg hover:bg-black/10 shrink-0 text-current disabled:opacity-50 transition-colors"
                    aria-label={`Download ${att.file_name}`}
                  >
                    {downloadingId === att.id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                    ) : (
                      <Download className="w-3.5 h-3.5" aria-hidden="true" />
                    )}
                  </button>
                </div>
              );
            })}
            {downloadError && (
              <p className="text-[10px] text-destructive bg-destructive/10 p-1 rounded flex items-center gap-1">
                <AlertCircle className="w-3 h-3 shrink-0" />
                <span>{downloadError}</span>
              </p>
            )}
          </div>
        )}

        {/* Footer: Time & Status */}
        <div
          className={`flex items-center justify-end gap-1 text-[10px] ${
            isCurrentUser ? "text-primary-foreground/75" : "text-muted-foreground"
          }`}
        >
          <span>{formattedTime}</span>
          {isCurrentUser && (
            <span>
              {message.delivery_status === "read" || message.is_read ? (
                <CheckCheck className="w-3.5 h-3.5 text-blue-300" aria-label="Read" />
              ) : message.delivery_status === "delivered" ? (
                <CheckCheck className="w-3.5 h-3.5 text-primary-foreground/80" aria-label="Delivered" />
              ) : (
                <Check className="w-3.5 h-3.5 text-primary-foreground/80" aria-label="Sent" />
              )}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

