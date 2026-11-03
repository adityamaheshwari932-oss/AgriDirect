import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AdminVerificationQueuePage } from "./AdminVerificationQueuePage";
import { ToastProvider } from "../../components/ui/toast";
import { adminApi } from "../../api/admin";
import type { VerificationSubmission } from "../../types/verification";

vi.mock("../../api/admin", () => ({
  adminApi: {
    listVerifications: vi.fn(),
    getVerification: vi.fn(),
    downloadVerificationDocument: vi.fn(),
    approveVerification: vi.fn(),
    rejectVerification: vi.fn(),
  },
}));

describe("AdminVerificationQueuePage", () => {
  const mockSubmission: VerificationSubmission = {
    id: "ver-sub-1",
    user_id: "user-farmer-100",
    user_email: "farmer.kisan@agri.test",
    user_role: "farmer",
    status: "pending",
    submission_notes: "Kisan Credit Card and 7/12 Land Record attached.",
    created_at: "2026-04-10T08:00:00Z",
    updated_at: "2026-04-10T08:00:00Z",
    documents: [
      {
        id: "doc-kcc-1",
        submission_id: "ver-sub-1",
        document_type: "kisan_credit_card",
        document_number: "KCC-54321",
        file_mime_type: "application/pdf",
        file_size_bytes: 204800,
        created_at: "2026-04-10T08:05:00Z",
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = () =>
    render(
      <ToastProvider>
        <AdminVerificationQueuePage />
      </ToastProvider>
    );

  it("renders verification queue and lists pending submissions", async () => {
    vi.mocked(adminApi.listVerifications).mockResolvedValueOnce({
      items: [mockSubmission],
      total: 1,
      page: 1,
      page_size: 15,
      total_pages: 1,
    });

    renderComponent();

    expect(screen.getByText("Administrative Identity Verification Queue")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("farmer.kisan@agri.test")).toBeInTheDocument();
      expect(screen.getByText("1 document(s)")).toBeInTheDocument();
      expect(screen.getAllByText("Pending Review").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("opens review modal and downloads evidence document", async () => {
    vi.mocked(adminApi.listVerifications).mockResolvedValueOnce({
      items: [mockSubmission],
      total: 1,
      page: 1,
      page_size: 15,
      total_pages: 1,
    });
    vi.mocked(adminApi.getVerification).mockResolvedValueOnce(mockSubmission);

    const mockBlob = new Blob(["sample pdf"], { type: "application/pdf" });
    vi.mocked(adminApi.downloadVerificationDocument).mockResolvedValueOnce({
      blob: mockBlob,
      filename: "kcc_doc.pdf",
      mimeType: "application/pdf",
    });

    // Mock createObjectURL & revokeObjectURL
    window.URL.createObjectURL = vi.fn().mockReturnValue("blob:http://localhost/sample-pdf");
    window.URL.revokeObjectURL = vi.fn();

    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /review verification application/i })
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /review verification application/i })
    );

    await waitFor(() => {
      expect(screen.getByText("Identity Verification Review")).toBeInTheDocument();
      expect(screen.getByText("kisan credit card")).toBeInTheDocument();
    });

    // Click download
    const downloadBtn = screen.getByRole("button", { name: /download evidence/i });
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(adminApi.downloadVerificationDocument).toHaveBeenCalledWith("ver-sub-1", "doc-kcc-1");
      expect(window.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
    });
  });

  it("approves verification application successfully", async () => {
    vi.mocked(adminApi.listVerifications).mockResolvedValueOnce({
      items: [mockSubmission],
      total: 1,
      page: 1,
      page_size: 15,
      total_pages: 1,
    });
    vi.mocked(adminApi.getVerification).mockResolvedValueOnce(mockSubmission);
    vi.mocked(adminApi.approveVerification).mockResolvedValueOnce({
      ...mockSubmission,
      status: "approved",
    });

    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /review verification application/i })
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /review verification application/i })
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /approve application/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /approve application/i }));

    await waitFor(() => {
      expect(screen.getByText("Approve Verification Application")).toBeInTheDocument();
    });

    const notesInput = screen.getByPlaceholderText(/optional notes to record/i);
    fireEvent.change(notesInput, { target: { value: "KCC document verified with registry." } });

    fireEvent.click(screen.getByRole("button", { name: /confirm approval/i }));

    await waitFor(() => {
      expect(adminApi.approveVerification).toHaveBeenCalledWith("ver-sub-1", {
        approval_notes: "KCC document verified with registry.",
      });
    });
  });

  it("rejects verification application with mandatory reason", async () => {
    vi.mocked(adminApi.listVerifications).mockResolvedValueOnce({
      items: [mockSubmission],
      total: 1,
      page: 1,
      page_size: 15,
      total_pages: 1,
    });
    vi.mocked(adminApi.getVerification).mockResolvedValueOnce(mockSubmission);
    vi.mocked(adminApi.rejectVerification).mockResolvedValueOnce({
      ...mockSubmission,
      status: "rejected",
      rejection_reason: "Document image is blurred and registration number is illegible.",
    });

    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /review verification application/i })
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /review verification application/i })
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /reject application/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /reject application/i }));

    await waitFor(() => {
      expect(screen.getByText("Reject Verification Application")).toBeInTheDocument();
    });

    const reasonInput = screen.getByPlaceholderText(/state clearly what information was missing/i);
    fireEvent.change(reasonInput, {
      target: { value: "Document image is blurred and registration number is illegible." },
    });

    fireEvent.click(screen.getByRole("button", { name: /confirm rejection/i }));

    await waitFor(() => {
      expect(adminApi.rejectVerification).toHaveBeenCalledWith("ver-sub-1", {
        rejection_reason: "Document image is blurred and registration number is illegible.",
      });
    });
  });
});

