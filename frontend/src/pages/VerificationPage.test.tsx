import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VerificationPage } from "./VerificationPage";
import { authStore } from "../store/authStore";
import { verificationApi } from "../api/verification";
import { ApiError } from "../api/errors";
import { InMemoryTokenStorage, tokenStorage } from "../api/tokenStorage";
import type { User } from "../types";
import type {
  VerificationDocument,
  VerificationSubmission,
} from "../types/verification";

describe("VerificationPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    tokenStorage.setProvider(new InMemoryTokenStorage());
    authStore.reset();
    vi.spyOn(authStore, "refreshUser").mockResolvedValue(mockFarmerUser);
  });

  const mockFarmerUser: User = {
    id: "farmer-uuid-1",
    email: "farmer@greenacres.test",
    role: "farmer",
    verification_status: "unverified",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    farmer_profile: {
      id: "f-prof-1",
      full_name: "Sarah Jenkins",
      farm_name: "Green Acres Farm",
      farm_location_address: "123 Valley Road",
      city: "Salinas",
      state: "CA",
      postal_code: "93901",
      farm_size_acres: 50,
      farming_practices: "organic",
      primary_crops: "Tomatoes, Lettuce",
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
    },
  };

  const mockBuyerUser: User = {
    id: "buyer-uuid-2",
    email: "buyer@grandhotel.test",
    role: "buyer",
    verification_status: "pending",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    buyer_profile: {
      id: "b-prof-1",
      contact_person_name: "Rahul Verma",
      business_name: "Grand Hotel & Suites",
      business_type: "hotel",
      business_registration_number: "27AAAAA0000A1Z5",
      delivery_receiving_address: "Dock 3, Central Kitchen",
      city: "Mumbai",
      state: "Maharashtra",
      postal_code: "400001",
      procurement_summary: "Weekly bulk organic produce",
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
    },
  };

  const mockTransporterUser: User = {
    id: "transporter-uuid-3",
    email: "transporter@speedyhaul.test",
    role: "transporter",
    verification_status: "unverified",
    account_status: "active",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    transporter_profile: {
      id: "t-prof-1",
      business_name: "Speedy Haul Logistics",
      contact_name: "Vikram Patil",
      phone_number: "+919876543230",
      transport_type: "refrigerated",
      vehicle_capacity_kg: 6000,
      vehicle_registration_number: "MH-12-TC-9988",
      is_available: true,
      experience_years: 5,
      created_at: "2026-10-29T12:00:00Z",
      updated_at: "2026-10-29T12:00:00Z",
    },
  };

  const mockSubmission: VerificationSubmission = {
    id: "sub-98765432-1111-2222-3333-444455556666",
    user_id: "farmer-uuid-1",
    status: "pending",
    submission_notes: "Initial organic farm verification application",
    created_at: "2026-10-29T12:00:00Z",
    updated_at: "2026-10-29T12:00:00Z",
    documents: [
      {
        id: "doc-1111-2222",
        submission_id: "sub-98765432-1111-2222-3333-444455556666",
        document_type: "land_ownership",
        document_number: "TITLE-1234",
        file_mime_type: "application/pdf",
        file_size_bytes: 524288,
        created_at: "2026-10-29T12:05:00Z",
      },
    ],
  };

  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <VerificationPage />
      </MemoryRouter>
    );
  };

  it("renders page header and farmer-specific instructions", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(null);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([]);

    renderComponent();

    expect(screen.getByRole("heading", { name: /^account verification$/i })).toBeInTheDocument();
    expect(
      screen.getByText(/validate your agricultural producer credentials/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/producer verification requirements & accepted evidence/i)).toBeInTheDocument();
  });

  it("renders buyer-specific instructions for commercial buyer account", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockBuyerUser,
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(null);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([]);

    renderComponent();

    expect(
      screen.getByText(/validate your commercial business entity credentials/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/commercial buyer verification requirements & accepted evidence/i)
    ).toBeInTheDocument();
  });

  it("renders transporter-specific instructions for transportation provider account", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockTransporterUser,
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(null);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([]);

    renderComponent();

    expect(
      screen.getByText(/validate your commercial transport credentials/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/transportation provider verification requirements & accepted evidence/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/vehicle registration \(rc\)/i)).toBeInTheDocument();
  });

  it("displays unsupported role message for admin or non-trade accounts", () => {
    authStore["state"] = {
      status: "authenticated",
      user: {
        ...mockFarmerUser,
        role: "admin",
      },
      error: null,
    };

    renderComponent();

    expect(screen.getByText(/verification not applicable/i)).toBeInTheDocument();
    expect(
      screen.getByText(/designed exclusively for registered agricultural producers/i)
    ).toBeInTheDocument();
  });

  it("renders empty state when user has no current submission (404)", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(null);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([]);

    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByText(/no verification application submitted yet/i)
      ).toBeInTheDocument();
    });
  });

  it("renders active pending submission details, status badge, and attached documents", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: {
        ...mockFarmerUser,
        verification_status: "pending",
      },
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(mockSubmission);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([mockSubmission]);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/application submission #sub-9876/i)).toBeInTheDocument();
      expect(screen.getByText("TITLE-1234")).toBeInTheDocument();
      expect(screen.getByText(/land ownership record \/ title/i)).toBeInTheDocument();
      expect(screen.getByText(/initial organic farm verification application/i)).toBeInTheDocument();
    });
  });

  it("renders verified status state, displays verified notice, and hides upload tab", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: {
        ...mockFarmerUser,
        verification_status: "verified",
      },
      error: null,
    };

    const verifiedSubmission: VerificationSubmission = {
      ...mockSubmission,
      status: "approved",
      reviewed_at: "2026-10-29T14:00:00Z",
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(verifiedSubmission);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([verifiedSubmission]);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/account fully verified/i)).toBeInTheDocument();
      expect(screen.queryByRole("tab", { name: /upload evidence/i })).not.toBeInTheDocument();
    });
  });

  it("renders rejected state with administrative rejection reason alert", async () => {
    authStore["state"] = {
      status: "authenticated",
      user: {
        ...mockFarmerUser,
        verification_status: "rejected",
      },
      error: null,
    };

    const rejectedSubmission: VerificationSubmission = {
      ...mockSubmission,
      status: "rejected",
      reviewed_at: "2026-10-29T14:00:00Z",
      rejection_reason: "Land ownership title was illegible; please upload a clear scanned copy.",
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(rejectedSubmission);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([rejectedSubmission]);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/administrative rejection rationale:/i)).toBeInTheDocument();
      expect(
        screen.getByText(/land ownership title was illegible; please upload a clear scanned copy/i)
      ).toBeInTheDocument();
    });
  });

  it("validates file format on client and rejects unsupported file extensions", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(null);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([]);

    renderComponent();

    await user.click(screen.getByRole("tab", { name: /upload evidence/i }));

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();

    // Select unsupported .exe file
    const invalidFile = new File(["malicious payload"], "malware.exe", {
      type: "application/octet-stream",
    });

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    expect(
      screen.getByText(/unsupported file format. please select a pdf, jpeg, png, or webp document/i)
    ).toBeInTheDocument();
  });

  it("validates file size on client and rejects oversized files (> 10 MiB)", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(null);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([]);

    renderComponent();

    await user.click(screen.getByRole("tab", { name: /upload evidence/i }));

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

    // Create mock oversized file (> 10 MB)
    const oversizedFile = new File(["a".repeat(100)], "huge.pdf", {
      type: "application/pdf",
    });
    Object.defineProperty(oversizedFile, "size", { value: 11 * 1024 * 1024 });

    await user.upload(fileInput, oversizedFile);

    expect(
      screen.getByText(/exceeds the maximum permitted limit of 10 mib/i)
    ).toBeInTheDocument();
  });

  it("successfully uploads a document and updates submission view", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValue(null);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValue([]);

    const newDoc: VerificationDocument = {
      id: "doc-new-123",
      submission_id: "sub-123",
      document_type: "kisan_credit_card",
      document_number: "KCC-555",
      file_mime_type: "application/pdf",
      file_size_bytes: 10240,
      created_at: "2026-10-29T12:00:00Z",
    };

    const uploadSpy = vi
      .spyOn(verificationApi, "uploadVerificationDocument")
      .mockResolvedValueOnce(newDoc);

    renderComponent();

    await user.click(screen.getByRole("tab", { name: /upload evidence/i }));

    // Select document type
    const select = screen.getByLabelText(/document category/i);
    await user.selectOptions(select, "kisan_credit_card");

    // Enter document number
    const numInput = screen.getByLabelText(/document \/ certificate number/i);
    await user.type(numInput, "KCC-555");

    // Select valid PDF file
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(["%PDF-1.4 sample"], "kcc.pdf", { type: "application/pdf" });
    await user.upload(fileInput, validFile);

    // Verify preview
    expect(screen.getByText("kcc.pdf")).toBeInTheDocument();

    // Click submit upload
    const uploadBtn = screen.getByRole("button", { name: /upload document/i });
    await user.click(uploadBtn);

    expect(uploadSpy).toHaveBeenCalledWith(validFile, "kisan_credit_card", "KCC-555");

    await waitFor(() => {
      expect(
        screen.getByText(/document "kcc.pdf" was uploaded successfully/i)
      ).toBeInTheDocument();
    });
  });

  it("handles document upload failure with error alert", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValue(null);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValue([]);

    vi.spyOn(verificationApi, "uploadVerificationDocument").mockRejectedValueOnce(
      new ApiError(422, "Invalid file signature: content does not match PDF format")
    );

    renderComponent();

    await user.click(screen.getByRole("tab", { name: /upload evidence/i }));

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const fakeFile = new File(["not a real pdf"], "bad.pdf", { type: "application/pdf" });
    await user.upload(fileInput, fakeFile);

    const uploadBtn = screen.getByRole("button", { name: /upload document/i });
    await user.click(uploadBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/invalid file signature: content does not match pdf format/i)
      ).toBeInTheDocument();
    });
  });

  it("triggers binary download on document download button click", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(mockSubmission);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([mockSubmission]);

    const fakeBlob = new Blob(["%PDF-1.4 file content"], { type: "application/pdf" });
    const downloadSpy = vi
      .spyOn(verificationApi, "downloadVerificationDocument")
      .mockResolvedValueOnce({
        blob: fakeBlob,
        filename: "land_ownership-doc.pdf",
        mimeType: "application/pdf",
      });

    // Mock createObjectURL and revokeObjectURL
    const createObjectURLMock = vi.fn().mockReturnValue("blob:http://localhost/fake-blob");
    const revokeObjectURLMock = vi.fn();
    window.URL.createObjectURL = createObjectURLMock;
    window.URL.revokeObjectURL = revokeObjectURLMock;

    renderComponent();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /download land ownership record/i })).toBeInTheDocument();
    });

    const downloadBtn = screen.getByRole("button", { name: /download land ownership record/i });
    await user.click(downloadBtn);

    expect(downloadSpy).toHaveBeenCalledWith("doc-1111-2222");
    expect(createObjectURLMock).toHaveBeenCalledWith(fakeBlob);
  });

  it("switches to history tab and renders previous submission records", async () => {
    const user = userEvent.setup();
    authStore["state"] = {
      status: "authenticated",
      user: mockFarmerUser,
      error: null,
    };

    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(mockSubmission);
    vi.spyOn(verificationApi, "getMyVerificationHistory").mockResolvedValueOnce([
      mockSubmission,
      {
        ...mockSubmission,
        id: "sub-old-1111-2222",
        status: "rejected",
        rejection_reason: "Initial documents were expired",
        created_at: "2026-09-01T10:00:00Z",
      },
    ]);

    renderComponent();

    const historyTab = await screen.findByRole("tab", { name: /submission history \(2\)/i });
    await user.click(historyTab);

    expect(screen.getByText("Application #2")).toBeInTheDocument();
    expect(screen.getByText("Application #1")).toBeInTheDocument();
    expect(screen.getByText(/initial documents were expired/i)).toBeInTheDocument();
  });
});
