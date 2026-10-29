/**
 * Verification API service.
 * Connects to backend endpoints for verification application submissions,
 * document uploads, status checking, history, and document downloads.
 */

import { ApiClient, apiClient } from "./client";
import { ApiError } from "./errors";
import type {
  VerificationDocument,
  VerificationSubmission,
  VerificationSubmissionCreate,
} from "../types/verification";

export class VerificationApi {
  constructor(private readonly client: ApiClient = apiClient) {}

  /**
   * Retrieves the applicant's current active pending submission or most recent submission.
   * Returns null if no submission exists yet (HTTP 404).
   */
  public async getMyVerification(): Promise<VerificationSubmission | null> {
    try {
      return await this.client.get<VerificationSubmission>("/users/me/verification");
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 404) {
        return null;
      }
      throw err;
    }
  }

  /**
   * Retrieves complete submission history for the authenticated user in reverse chronological order.
   */
  public async getMyVerificationHistory(): Promise<VerificationSubmission[]> {
    return this.client.get<VerificationSubmission[]>("/users/me/verification/history");
  }

  /**
   * Submits a new verification application with optional notes and role.
   */
  public async submitVerification(
    payload: VerificationSubmissionCreate = {}
  ): Promise<VerificationSubmission> {
    return this.client.post<VerificationSubmission>("/users/me/verification", payload);
  }

  /**
   * Uploads an evidence document attached to the applicant's pending submission.
   * Automatically streams via FormData multipart without overriding browser boundary.
   */
  public async uploadVerificationDocument(
    file: File,
    documentType: string,
    documentNumber?: string
  ): Promise<VerificationDocument> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", documentType);
    if (documentNumber && documentNumber.trim()) {
      formData.append("document_number", documentNumber.trim());
    }

    return this.client.post<VerificationDocument>("/users/me/verification/documents", formData);
  }

  /**
   * Downloads an evidence document belonging to the caller as a binary Blob.
   */
  public async downloadVerificationDocument(
    documentId: string
  ): Promise<{ blob: Blob; filename?: string; mimeType: string }> {
    return this.client.downloadBlob(`/users/me/verification/documents/${documentId}/download`);
  }
}

export const verificationApi = new VerificationApi();
