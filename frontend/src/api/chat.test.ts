import { describe, it, expect, vi, beforeEach } from "vitest";
import { chatApi } from "./chat";
import { apiClient } from "./client";

describe("ChatApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("creates or retrieves a conversation", async () => {
    const payload = { target_user_id: "user-2", listing_id: "listing-1" };
    const mockDetail = { id: "conv-1", unread_count: 0 };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockDetail);

    const res = await chatApi.createOrGetConversation(payload);
    expect(apiClient.post).toHaveBeenCalledWith("/conversations", payload);
    expect(res).toEqual(mockDetail);
  });

  it("lists user conversations with query parameters", async () => {
    const mockList = { items: [], total: 0, limit: 20, offset: 0 };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockList);

    const res = await chatApi.listConversations({ context_type: "listing", limit: 20 });
    expect(apiClient.get).toHaveBeenCalledWith("/conversations?context_type=listing&limit=20");
    expect(res).toEqual(mockList);
  });

  it("gets conversation details", async () => {
    const mockDetail = { id: "conv-1", contact_sharing_consented: false };
    vi.spyOn(apiClient, "get").mockResolvedValue(mockDetail);

    const res = await chatApi.getConversation("conv-1");
    expect(apiClient.get).toHaveBeenCalledWith("/conversations/conv-1");
    expect(res).toEqual(mockDetail);
  });

  it("sends a text message in thread", async () => {
    const payload = { content: "Is the grain dry?" };
    const mockMsg = { id: "msg-1", content: "Is the grain dry?", delivery_status: "sent" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockMsg);

    const res = await chatApi.sendMessage("conv-1", payload);
    expect(apiClient.post).toHaveBeenCalledWith("/conversations/conv-1/messages", payload);
    expect(res).toEqual(mockMsg);
  });

  it("lists messages with pagination cursors", async () => {
    const mockMsgs = [{ id: "msg-1", content: "Hello" }];
    vi.spyOn(apiClient, "get").mockResolvedValue(mockMsgs);

    const res = await chatApi.listMessages("conv-1", { limit: 10, order: "asc" });
    expect(apiClient.get).toHaveBeenCalledWith("/conversations/conv-1/messages?limit=10&order=asc");
    expect(res).toEqual(mockMsgs);
  });

  it("sends message with attachment via FormData", async () => {
    const file = new File(["test image content"], "photo.jpg", { type: "image/jpeg" });
    const mockMsg = { id: "msg-2", attachments: [{ id: "att-1" }] };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockMsg);

    const res = await chatApi.sendMessageWithAttachment("conv-1", "Here is crop photo", file, "ord-1");
    expect(apiClient.post).toHaveBeenCalledWith(
      "/conversations/conv-1/messages/with-attachment",
      expect.any(FormData)
    );
    expect(res).toEqual(mockMsg);
  });

  it("marks conversation as read", async () => {
    const mockRes = { conversation_id: "conv-1", marked_read_count: 3 };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockRes);

    const res = await chatApi.markConversationRead("conv-1");
    expect(apiClient.post).toHaveBeenCalledWith("/conversations/conv-1/read");
    expect(res).toEqual(mockRes);
  });

  it("manages contact sharing requests and consent", async () => {
    const mockReq = { id: "req-1", status: "pending" };
    vi.spyOn(apiClient, "post").mockResolvedValue(mockReq);

    const resReq = await chatApi.requestContactSharing("conv-1", { notes: "Call to coordinate truck" });
    expect(apiClient.post).toHaveBeenCalledWith("/conversations/conv-1/contact-requests", {
      notes: "Call to coordinate truck",
    });
    expect(resReq).toEqual(mockReq);

    const approvedReq = { id: "req-1", status: "approved" };
    vi.spyOn(apiClient, "post").mockResolvedValue(approvedReq);
    const resApprove = await chatApi.approveContactSharing("req-1");
    expect(apiClient.post).toHaveBeenCalledWith("/contact-requests/req-1/approve");
    expect(resApprove).toEqual(approvedReq);

    const contacts = { id: "u-2", role: "farmer", name: "Ramesh", phone_number: "+919876543210" };
    vi.spyOn(apiClient, "get").mockResolvedValue(contacts);
    const resContacts = await chatApi.getContactDetails("conv-1");
    expect(apiClient.get).toHaveBeenCalledWith("/conversations/conv-1/contacts");
    expect(resContacts).toEqual(contacts);
  });

  it("downloads an attachment with bearer auth via downloadBlob", async () => {
    const fakeBlob = new Blob(["sample content"], { type: "application/pdf" });
    vi.spyOn(apiClient, "downloadBlob").mockResolvedValue({
      blob: fakeBlob,
      filename: "invoice.pdf",
      mimeType: "application/pdf",
    });

    const createObjectURLSpy = vi.fn().mockReturnValue("blob:http://localhost/test-blob");
    const revokeObjectURLSpy = vi.fn();
    window.URL.createObjectURL = createObjectURLSpy;
    window.URL.revokeObjectURL = revokeObjectURLSpy;

    const clickSpy = vi.fn();
    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tagName: string) => {
      const el = originalCreateElement(tagName);
      if (tagName === "a") {
        el.click = clickSpy;
      }
      return el;
    });

    await chatApi.downloadAttachment("att-123", "fallback.pdf");

    expect(apiClient.downloadBlob).toHaveBeenCalledWith("/attachments/att-123");
    expect(createObjectURLSpy).toHaveBeenCalledWith(fakeBlob);
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURLSpy).toHaveBeenCalledWith("blob:http://localhost/test-blob");
  });
});

