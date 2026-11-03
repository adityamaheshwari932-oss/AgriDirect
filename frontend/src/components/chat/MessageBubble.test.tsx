import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MessageBubble } from "./MessageBubble";
import { chatApi } from "../../api/chat";
import type { Message } from "../../types/chat";

vi.mock("../../api/chat", () => ({
  chatApi: {
    downloadAttachment: vi.fn(),
  },
}));

describe("MessageBubble", () => {
  const baseMessage: Message = {
    id: "msg-101",
    conversation_id: "conv-1",
    sender_id: "user-1",
    content: "Here is the batch document.",
    message_type: "text",
    delivery_status: "sent",
    is_read: false,
    created_at: "2026-03-30T10:00:00Z",
    attachments: [
      {
        id: "att-55",
        message_id: "msg-101",
        file_name: "quality_report.pdf",
        file_size_bytes: 2048,
        file_mime_type: "application/pdf",
        attachment_type: "document",
        created_at: "2026-03-30T10:00:00Z",
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders message content and attachment metadata", () => {
    render(<MessageBubble message={baseMessage} isCurrentUser={true} />);
    expect(screen.getByText("Here is the batch document.")).toBeInTheDocument();
    expect(screen.getByText("quality_report.pdf")).toBeInTheDocument();
    expect(screen.getByText("(2 KB)")).toBeInTheDocument();
    expect(screen.getByLabelText("Download quality_report.pdf")).toBeInTheDocument();
  });

  it("triggers authenticated download via chatApi when download button clicked", async () => {
    vi.mocked(chatApi.downloadAttachment).mockResolvedValueOnce();

    render(<MessageBubble message={baseMessage} isCurrentUser={false} />);
    const downloadBtn = screen.getByLabelText("Download quality_report.pdf");

    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(chatApi.downloadAttachment).toHaveBeenCalledWith("att-55", "quality_report.pdf");
    });
  });

  it("displays error message if download fails", async () => {
    vi.mocked(chatApi.downloadAttachment).mockRejectedValueOnce(
      new Error("Download failed: Network error")
    );

    render(<MessageBubble message={baseMessage} isCurrentUser={false} />);
    const downloadBtn = screen.getByLabelText("Download quality_report.pdf");

    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(screen.getByText("Download failed: Network error")).toBeInTheDocument();
    });
  });

  it("renders system message properly", () => {
    const sysMsg: Message = {
      ...baseMessage,
      id: "sys-1",
      message_type: "system",
      content: "Delivery marked as completed by seller",
      attachments: [],
    };
    render(<MessageBubble message={sysMsg} isCurrentUser={false} />);
    expect(screen.getByText("Delivery marked as completed by seller")).toBeInTheDocument();
  });
});