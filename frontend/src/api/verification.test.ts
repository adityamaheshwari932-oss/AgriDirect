import { beforeEach, describe, expect, it, vi } from "vitest";
import { verificationApi } from "./verification";
import { apiClient } from "./client";
import { ApiError } from "./errors";
import type {
  VerificationDocument,
  VerificationSubmission,
} from "../types/verification";

describe("VerificationApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockSubmission: VerificationSubmission = {
    id: "sub-12345678-uuid",
    user_id: "user-123",
    status: "pending",
    submission_notes: "Organic farm documentation",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    documents: [],
  };

  const mockDocument: VerificationDocument = {
    id: "doc-uuid-1",
    submission_id: "sub-12345678-uuid",
    document_type: "kisan_credit_card",
    document_number: "KCC-987654",
    file_mime_type: "application/pdf",
    file_size_bytes: 102400,
    created_at: "2026-10-29T12:05:00Z",
  };

  it("getMyVerification returns submission on 200 OK", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockSubmission);

    const result = await verificationApi.getMyVerification();
    expect(apiClient.get).toHaveBeenCalledWith("/users/me/verification");
    expect(result).toEqual(mockSubmission);
  });

  it("getMyVerification returns null on HTTP 404 Not Found", async () => {
    vi.spyOn(apiClient, "get").mockRejectedValueOnce(
      new ApiError(404, "No verification submission found for this user")
    );

    const result = await verificationApi.getMyVerification();
    expect(result).toBeNull();
  });

  it("getMyVerification rethrows non-404 ApiErrors", async () => {
    vi.spyOn(apiClient, "get").mockRejectedValueOnce(
      new ApiError(500, "Internal Server Error")
    );

    await expect(verificationApi.getMyVerification()).rejects.toThrow("Internal Server Error");
  });

  it("getMyVerificationHistory returns submission array", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValueOnce([mockSubmission]);

    const result = await verificationApi.getMyVerificationHistory();
    expect(apiClient.get).toHaveBeenCalledWith("/users/me/verification/history");
    expect(result).toEqual([mockSubmission]);
  });

  it("submitVerification sends payload to /users/me/verification", async () => {
    vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockSubmission);

    const payload = { submission_notes: "New application", role: "farmer" };
    const result = await verificationApi.submitVerification(payload);

    expect(apiClient.post).toHaveBeenCalledWith("/users/me/verification", payload);
    expect(result).toEqual(mockSubmission);
  });

  it("uploadVerificationDocument packages FormData and posts to /users/me/verification/documents", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockDocument);

    const fakeFile = new File(["%PDF-1.4 sample content"], "land_title.pdf", {
      type: "application/pdf",
    });

    const result = await verificationApi.uploadVerificationDocument(
      fakeFile,
      "land_ownership",
      "DEED-456"
    );

    expect(postSpy).toHaveBeenCalledTimes(1);
    const [path, body] = postSpy.mock.calls[0];
    expect(path).toBe("/users/me/verification/documents");
    expect(body).toBeInstanceOf(FormData);

    const formData = body as FormData;
    expect(formData.get("document_type")).toBe("land_ownership");
    expect(formData.get("document_number")).toBe("DEED-456");
    expect(formData.get("file")).toBe(fakeFile);
    expect(result).toEqual(mockDocument);
  });

  it("downloadVerificationDocument calls downloadBlob with the expected path", async () => {
    const mockBlob = new Blob(["sample content"], { type: "application/pdf" });
    const downloadSpy = vi.spyOn(apiClient, "downloadBlob").mockResolvedValueOnce({
      blob: mockBlob,
      filename: "land_title.pdf",
      mimeType: "application/pdf",
    });

    const result = await verificationApi.downloadVerificationDocument("doc-uuid-1");

    expect(downloadSpy).toHaveBeenCalledWith(
      "/users/me/verification/documents/doc-uuid-1/download"
    );
    expect(result.blob).toBe(mockBlob);
    expect(result.filename).toBe("land_title.pdf");
  });
});
