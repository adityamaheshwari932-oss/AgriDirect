import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TransporterDashboardPage } from "./TransporterDashboardPage";
import { authStore } from "../store/authStore";
import { transportersApi } from "../api/transporters";
import { verificationApi } from "../api/verification";
import type { TransporterDetail, User } from "../types";
import type { VerificationSubmission } from "../types/verification";

describe("TransporterDashboardPage", () => {
  const mockTransporterUser: User = {
    id: "user-transporter-1",
    email: "transporter@test.com",
    role: "transporter",
    verification_status: "verified",
    account_status: "active",
    created_at: "2026-11-18T10:00:00Z",
    updated_at: "2026-11-18T10:00:00Z",
  };

  const mockDetail: TransporterDetail = {
    id: "transporter-prof-1",
    user_id: "user-transporter-1",
    business_name: "Sahyadri Agro Haulage",
    contact_name: "Santosh Shinde",
    phone_number: "+919876500000",
    transport_type: "refrigerated",
    vehicle_capacity_kg: 5000,
    vehicle_registration_number: "MH-14-GH-1212",
    is_available: true,
    experience_years: 6,
    operating_states: "Maharashtra, Goa",
    bio: "Refrigerated transport for perishable vegetables.",
    verification_status: "verified",
    created_at: "2026-11-18T10:00:00Z",
    updated_at: "2026-11-18T10:00:00Z",
    service_areas: [
      {
        id: "area-1",
        transporter_profile_id: "transporter-prof-1",
        state: "Maharashtra",
        district: "Nashik",
        taluka_subdistrict: "Niphad",
        pincode: "422303",
        coverage_type: "both",
        is_active: true,
        created_at: "2026-11-18T10:00:00Z",
        updated_at: "2026-11-18T10:00:00Z",
      },
    ],
  };

    beforeEach(() => {
    authStore.reset();
    vi.restoreAllMocks();
    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValue(null);
  });

  it("renders restricted message when user is not a transporter", () => {
    authStore.setUser({ ...mockTransporterUser, role: "farmer" });
    render(
      <MemoryRouter>
        <TransporterDashboardPage />
      </MemoryRouter>
    );
    expect(screen.getByText(/Access restricted to registered transportation providers/i)).toBeInTheDocument();
  });

  it("loads and displays transporter profile and declared service areas", async () => {
    authStore.setUser(mockTransporterUser);
    vi.spyOn(transportersApi, "getMyProfile").mockResolvedValueOnce(mockDetail);

    render(
      <MemoryRouter>
        <TransporterDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Sahyadri Agro Haulage")).toBeInTheDocument();
      expect(screen.getByText(/Santosh Shinde/i)).toBeInTheDocument();
      expect(screen.getByText(/5,000 kg Payload/i)).toBeInTheDocument();
      expect(screen.getByText(/Available for Loads/i)).toBeInTheDocument();
      expect(screen.getByText(/Maharashtra • Nashik/i)).toBeInTheDocument();
    });
  });

  it("toggles fleet availability status", async () => {
    authStore.setUser(mockTransporterUser);
    vi.spyOn(transportersApi, "getMyProfile").mockResolvedValueOnce(mockDetail);
    vi.spyOn(transportersApi, "updateMyProfile").mockResolvedValueOnce({
      ...mockDetail,
      is_available: false,
    });

    render(
      <MemoryRouter>
        <TransporterDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Available for Loads/i)).toBeInTheDocument();
    });

    const toggleBtn = screen.getByText(/Available for Loads/i);
    fireEvent.click(toggleBtn);

    await waitFor(() => {
      expect(transportersApi.updateMyProfile).toHaveBeenCalledWith({ is_available: false });
    });
  });

  it("renders dedicated verification section with unverified status and submit button", async () => {
    const unverifiedUser: User = {
      ...mockTransporterUser,
      verification_status: "unverified",
    };
    authStore.setUser(unverifiedUser);
    vi.spyOn(transportersApi, "getMyProfile").mockResolvedValueOnce(mockDetail);
    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(null);

    render(
      <MemoryRouter>
        <TransporterDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Identity & Transport Compliance Verification")).toBeInTheDocument();
      expect(screen.getByText("Not Submitted")).toBeInTheDocument();
      expect(screen.getByText("Submit Verification Documents")).toBeInTheDocument();
      expect(screen.getByText(/Upload vehicle RC and commercial permit/i)).toBeInTheDocument();
    });
  });

  it("renders verification section with pending review state", async () => {
    const pendingUser: User = {
      ...mockTransporterUser,
      verification_status: "pending",
    };
    const mockPendingSub: VerificationSubmission = {
      id: "sub-pending-1",
      user_id: "user-transporter-1",
      status: "pending",
      submission_notes: "Fleet permits attached",
      created_at: "2026-11-18T10:00:00Z",
      updated_at: "2026-11-18T10:00:00Z",
      documents: [],
    };

    authStore.setUser(pendingUser);
    vi.spyOn(transportersApi, "getMyProfile").mockResolvedValueOnce(mockDetail);
    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(mockPendingSub);

    render(
      <MemoryRouter>
        <TransporterDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Under Review")).toBeInTheDocument();
      expect(screen.getByText(/Submitted credentials are currently under review/i)).toBeInTheDocument();
    });
  });

  it("renders rejected verification state with admin rejection feedback and resubmit link", async () => {
    const rejectedUser: User = {
      ...mockTransporterUser,
      verification_status: "rejected",
    };
    const mockRejectedSub: VerificationSubmission = {
      id: "sub-rej-1",
      user_id: "user-transporter-1",
      status: "rejected",
      rejection_reason: "Vehicle RC scan is unreadable. Please provide a clear colored copy.",
      created_at: "2026-11-18T10:00:00Z",
      updated_at: "2026-11-18T11:00:00Z",
      reviewed_at: "2026-11-18T11:00:00Z",
      documents: [],
    };

    authStore.setUser(rejectedUser);
    vi.spyOn(transportersApi, "getMyProfile").mockResolvedValueOnce(mockDetail);
    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(mockRejectedSub);

    render(
      <MemoryRouter>
        <TransporterDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Administrative Rejection Reason")).toBeInTheDocument();
      expect(screen.getByText(/Vehicle RC scan is unreadable/i)).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Resubmit Application/i })).toBeInTheDocument();
    });
  });

  it("renders approved verification state with submitted documents", async () => {
    const approvedUser: User = {
      ...mockTransporterUser,
      verification_status: "verified",
    };
    const mockApprovedSub: VerificationSubmission = {
      id: "sub-appr-1",
      user_id: "user-transporter-1",
      status: "approved",
      created_at: "2026-11-18T10:00:00Z",
      updated_at: "2026-11-18T11:00:00Z",
      reviewed_at: "2026-11-18T11:00:00Z",
      documents: [
        {
          id: "doc-rc-1",
          submission_id: "sub-appr-1",
          document_type: "vehicle_rc",
          document_number: "MH-14-GH-1212",
          file_mime_type: "application/pdf",
          file_size_bytes: 1048576,
          created_at: "2026-11-18T10:05:00Z",
        },
      ],
    };

    authStore.setUser(approvedUser);
    vi.spyOn(transportersApi, "getMyProfile").mockResolvedValueOnce(mockDetail);
    vi.spyOn(verificationApi, "getMyVerification").mockResolvedValueOnce(mockApprovedSub);

    render(
      <MemoryRouter>
        <TransporterDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Approved & Compliant")).toBeInTheDocument();
      expect(screen.getByText(/Full access to order transport coordination is active/i)).toBeInTheDocument();
      expect(screen.getByText(/Vehicle Registration Certificate \(RC\)/i)).toBeInTheDocument();
    });
  });
});
