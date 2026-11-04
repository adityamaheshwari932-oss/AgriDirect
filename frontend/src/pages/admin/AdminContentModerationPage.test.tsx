import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AdminContentModerationPage } from "./AdminContentModerationPage";
import { ToastProvider } from "../../components/ui/toast";
import { adminApi } from "../../api/admin";
import type { PaymentComplaint, PaymentComplaintStatus } from "../../types/payments";
import type { ReportItem } from "../../types/reports";

vi.mock("../../api/admin", () => ({
  adminApi: {
    listListings: vi.fn(),
    moderateListing: vi.fn(),
    listRequirements: vi.fn(),
    moderateRequirement: vi.fn(),
    listReports: vi.fn(),
    moderateReport: vi.fn(),
    listPaymentComplaints: vi.fn(),
    getPaymentComplaintDetail: vi.fn(),
    resolvePaymentComplaint: vi.fn(),
  },
}));

describe("AdminContentModerationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = () =>
    render(
      <ToastProvider>
        <AdminContentModerationPage />
      </ToastProvider>
    );

  const mockListings = [
    {
      id: "listing-1",
      farmer_id: "farmer-1",
      farmer_email: "farmer@farm.test",
      farmer_name: "Farmer John",
      product_name: "Alphonso Mango",
      title: "Devgad Alphonso Grade A",
      initial_quantity: 1000,
      available_quantity: 800,
      unit: "dozen",
      price_per_unit: 800,
      status: "active",
      is_deleted: false,
      expires_at: "2026-12-31T00:00:00Z",
      reports_count: 0,
      created_at: "2026-04-01T00:00:00Z",
      updated_at: "2026-04-01T00:00:00Z",
    },
  ];

  const mockRequirements = [
    {
      id: "req-1",
      buyer_id: "buyer-1",
      buyer_email: "procure@foods.test",
      buyer_name: "Global Foods",
      product_name: "Basmati Rice",
      title: "Export Quality Basmati",
      required_quantity: 5000,
      remaining_quantity: 3500,
      unit: "kg",
      price_condition: "negotiable",
      required_by_date: "2026-11-30",
      status: "active",
      is_deleted: false,
      reports_count: 0,
      created_at: "2026-04-02T00:00:00Z",
      updated_at: "2026-04-02T00:00:00Z",
    },
  ];

  const mockReports: ReportItem[] = [
    {
      id: "rep-1",
      reporter_id: "user-1",
      category: "quality_issue",
      description: "Produce delivered had rot and was not Grade A as represented.",
      status: "open",
      created_at: "2026-04-05T00:00:00Z",
      updated_at: "2026-04-05T00:00:00Z",
    },
  ];

  const mockComplaints: PaymentComplaint[] = [
    {
      id: "comp-1",
      payment_record_id: "pay-1",
      complainant_user_id: "farmer-1",
      complaint_reason: "NEFT transaction not reflected in bank account after 5 business days.",
      has_evidence: true,
      status: "open",
      created_at: "2026-04-06T00:00:00Z",
      updated_at: "2026-04-06T00:00:00Z",
    },
  ];

  it("renders listings tab by default and allows moderation", async () => {
    vi.mocked(adminApi.listListings).mockResolvedValueOnce({
      items: mockListings,
      total: 1,
      page: 1,
      page_size: 15,
      total_pages: 1,
    });
    vi.mocked(adminApi.moderateListing).mockResolvedValueOnce({
      listing: { ...mockListings[0], status: "closed" },
      action: "close",
      previous_status: "active",
      new_status: "closed",
      is_deleted: false,
      audit_log_id: "audit-1",
      reason: "Listing closed by admin due to pricing discrepancy",
      updated_at: "2026-11-04T00:00:00Z",
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Alphonso Mango")).toBeInTheDocument();
      expect(screen.getByText("Farmer John")).toBeInTheDocument();
    });

    // Click Moderate button
    fireEvent.click(screen.getByRole("button", { name: /moderate/i }));

    await waitFor(() => {
      expect(screen.getByText("Moderate Produce Listing")).toBeInTheDocument();
    });

    const reasonInput = screen.getByPlaceholderText(/provide a mandatory administrative reason/i);
    fireEvent.change(reasonInput, {
      target: { value: "Listing closed by admin due to pricing discrepancy" },
    });

    // Close action requires confirmation
    const submitBtn = screen.getByRole("button", { name: /apply moderation/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Confirm Listing Moderation")).toBeInTheDocument();
    });

    const confirmBtn = screen.getByRole("button", { name: /confirm & apply/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(adminApi.moderateListing).toHaveBeenCalledWith("listing-1", {
        action: "close",
        reason: "Listing closed by admin due to pricing discrepancy",
      });
    });
  });

  it("switches to Buyer Requirements tab and moderates requirement", async () => {
    vi.mocked(adminApi.listListings).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 15,
      total_pages: 0,
    });
    vi.mocked(adminApi.listRequirements).mockResolvedValueOnce({
      items: mockRequirements,
      total: 1,
      page: 1,
      page_size: 15,
      total_pages: 1,
    });
    vi.mocked(adminApi.moderateRequirement).mockResolvedValueOnce({
      requirement: { ...mockRequirements[0], status: "closed", is_deleted: true },
      action: "remove",
      previous_status: "active",
      new_status: "closed",
      is_deleted: true,
      audit_log_id: "audit-2",
      reason: "Soft-deleted due to spam content in requirement title",
      updated_at: "2026-11-04T00:00:00Z",
    });

    renderComponent();

    // Switch to Requirements tab
    fireEvent.click(screen.getByRole("button", { name: /buyer requirements/i }));

    await waitFor(() => {
      expect(screen.getByText("Basmati Rice")).toBeInTheDocument();
      expect(screen.getByText("Global Foods")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /moderate/i }));

    await waitFor(() => {
      expect(screen.getByText("Moderate Buyer Requirement")).toBeInTheDocument();
    });

    const actionSelect = screen.getByLabelText(/moderation action/i);
    fireEvent.change(actionSelect, { target: { value: "remove" } });

    const reasonInput = screen.getByPlaceholderText(/provide a mandatory administrative reason/i);
    fireEvent.change(reasonInput, {
      target: { value: "Soft-deleted due to spam content in requirement title" },
    });

    const submitBtn = screen.getByRole("button", { name: /apply moderation/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Confirm Requirement Moderation")).toBeInTheDocument();
    });

    const confirmBtn = screen.getByRole("button", { name: /confirm & apply/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(adminApi.moderateRequirement).toHaveBeenCalledWith("req-1", {
        action: "remove",
        reason: "Soft-deleted due to spam content in requirement title",
      });
    });
  });

  it("switches to Safety Reports tab and records moderation resolution", async () => {
    vi.mocked(adminApi.listListings).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 15,
      total_pages: 0,
    });
    vi.mocked(adminApi.listReports).mockResolvedValueOnce({
      items: mockReports,
      total: 1,
      page: 1,
      page_size: 15,
      total_pages: 1,
    });
    vi.mocked(adminApi.moderateReport).mockResolvedValueOnce({
      ...mockReports[0],
      status: "action_taken",
      admin_notes: "Investigation verified rot and merchant issued warning.",
    });

    renderComponent();

    // Switch to Safety Reports tab
    fireEvent.click(screen.getByRole("button", { name: /safety reports/i }));

    await waitFor(() => {
      expect(screen.getByText("quality issue")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /review & moderate/i }));

    await waitFor(() => {
      expect(screen.getByText("Moderate Safety Report")).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText(/moderation status/i);
    fireEvent.change(statusSelect, { target: { value: "action_taken" } });

    const notesInput = screen.getByPlaceholderText(/record investigation findings/i);
    fireEvent.change(notesInput, {
      target: { value: "Investigation verified rot and merchant issued warning." },
    });

    const saveBtn = screen.getByRole("button", { name: /save resolution/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(adminApi.moderateReport).toHaveBeenCalledWith("rep-1", {
        status: "action_taken",
        admin_notes: "Investigation verified rot and merchant issued warning.",
      });
    });
  });

  it("switches to Payment Complaints tab and resolves dispute without payment acknowledgement", async () => {
    vi.mocked(adminApi.listListings).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 15,
      total_pages: 0,
    });
    vi.mocked(adminApi.listPaymentComplaints).mockResolvedValueOnce({
      items: mockComplaints,
      total: 1,
      limit: 15,
      offset: 0,
    });
    vi.mocked(adminApi.getPaymentComplaintDetail).mockResolvedValueOnce({
      complaint: mockComplaints[0],
      payment: {
        id: "pay-1",
        order_id: "ord-1",
        recorded_by_user_id: "buyer-1",
        amount: "75000.00",
        payment_method: "bank_transfer",
        has_proof: true,
        status: "disputed",
        payment_date: "2026-04-01",
        has_historical_acknowledgement: false,
        created_at: "2026-04-01T00:00:00Z",
        updated_at: "2026-04-06T00:00:00Z",
      },
      order_id: "ord-1",
      order_number: "ORD-2026-4001",
      buyer_id: "buyer-1",
      farmer_id: "farmer-1",
    });
    vi.mocked(adminApi.resolvePaymentComplaint).mockResolvedValueOnce({
      ...mockComplaints[0],
      status: "resolved",
      admin_resolution_notes: "Bank confirmed UTR settlement cleared.",
    });

    renderComponent();

    // Switch to Payment Complaints tab
    fireEvent.click(screen.getByRole("button", { name: /payment complaints/i }));

    await waitFor(() => {
      expect(screen.getByText("farmer-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /inspect & resolve/i }));

    await waitFor(() => {
      expect(screen.getByText("Payment Dispute Moderation")).toBeInTheDocument();
      expect(screen.getByText("ORD-2026-4001")).toBeInTheDocument();
      expect(screen.getByText("75000.00")).toBeInTheDocument();
      // Crucial policy check: verifies notice is shown that admin cannot acknowledge payments
      expect(
        screen.getByText(/administrators do not acknowledge payment receipt on behalf of farmers/i)
      ).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText(/dispute resolution status/i);
    fireEvent.change(statusSelect, { target: { value: "resolved" } });

    const notesInput = screen.getByLabelText(
      /administrative mediation & resolution notes/i
    );
    fireEvent.change(notesInput, {
      target: { value: "Bank confirmed UTR settlement cleared." },
    });

    const saveBtn = screen.getByRole("button", { name: /save dispute resolution/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(adminApi.resolvePaymentComplaint).toHaveBeenCalledWith("comp-1", {
        status: "resolved",
        admin_resolution_notes: "Bank confirmed UTR settlement cleared.",
      });
    });
  });

  it("filters payment complaints by open status and sends status=open", async () => {
    vi.mocked(adminApi.listListings).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 15,
      total_pages: 0,
    });
    vi.mocked(adminApi.listPaymentComplaints).mockResolvedValue({
      items: mockComplaints,
      total: 1,
      limit: 15,
      offset: 0,
    });

    renderComponent();

    // Switch to Payment Complaints tab
    fireEvent.click(screen.getByRole("button", { name: /payment complaints/i }));

    await waitFor(() => {
      expect(screen.getByText("farmer-1")).toBeInTheDocument();
    });

    const statusFilter = screen.getByRole("combobox");
    fireEvent.change(statusFilter, { target: { value: "open" } });

    await waitFor(() => {
      expect(adminApi.listPaymentComplaints).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "open",
        })
      );
    });
  });

  it("rejects terminal resolution when notes are shorter than 5 characters and allows submission with valid notes", async () => {
    vi.mocked(adminApi.listListings).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 15,
      total_pages: 0,
    });
    vi.mocked(adminApi.listPaymentComplaints).mockResolvedValueOnce({
      items: mockComplaints,
      total: 1,
      limit: 15,
      offset: 0,
    });
    vi.mocked(adminApi.getPaymentComplaintDetail).mockResolvedValueOnce({
      complaint: mockComplaints[0],
      payment: {
        id: "pay-1",
        order_id: "ord-1",
        recorded_by_user_id: "buyer-1",
        amount: "75000.00",
        payment_method: "bank_transfer",
        has_proof: true,
        status: "disputed",
        payment_date: "2026-04-01",
        has_historical_acknowledgement: false,
        created_at: "2026-04-01T00:00:00Z",
        updated_at: "2026-04-06T00:00:00Z",
      },
      order_id: "ord-1",
      order_number: "ORD-2026-4001",
      buyer_id: "buyer-1",
      farmer_id: "farmer-1",
    });
    vi.mocked(adminApi.resolvePaymentComplaint).mockResolvedValueOnce({
      ...mockComplaints[0],
      status: "resolved",
      admin_resolution_notes: "Settlement verified with buyer and farmer bank receipts.",
    });

    renderComponent();

    // Switch to Payment Complaints tab
    fireEvent.click(screen.getByRole("button", { name: /payment complaints/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /inspect & resolve/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /inspect & resolve/i }));

    await waitFor(() => {
      expect(screen.getByText("Payment Dispute Moderation")).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText(/dispute resolution status/i);
    fireEvent.change(statusSelect, { target: { value: "resolved" } });

    // Attempt submission with notes shorter than 5 characters
    const notesInput = screen.getByLabelText(
      /administrative mediation & resolution notes/i
    );
    fireEvent.change(notesInput, { target: { value: "abc" } });

    const saveBtn = screen.getByRole("button", { name: /save dispute resolution/i });
    fireEvent.click(saveBtn);

    // Validation error must be displayed and API must NOT be called
    await waitFor(() => {
      expect(
        screen.getByText(/administrative resolution notes must contain at least 5 characters/i)
      ).toBeInTheDocument();
    });
    expect(adminApi.resolvePaymentComplaint).not.toHaveBeenCalled();

    // Now provide valid notes (>= 5 characters) and submit
    fireEvent.change(notesInput, {
      target: { value: "Settlement verified with buyer and farmer bank receipts." },
    });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(adminApi.resolvePaymentComplaint).toHaveBeenCalledWith("comp-1", {
        status: "resolved",
        admin_resolution_notes: "Settlement verified with buyer and farmer bank receipts.",
      });
    });
  });

  it("enforces that payment complaint status uses open instead of submitted", async () => {
    // Type-level validation: valid status is 'open'
    const validStatus: PaymentComplaintStatus = "open";
    expect(validStatus).toBe("open");

    vi.mocked(adminApi.listListings).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 15,
      total_pages: 0,
    });
    vi.mocked(adminApi.listPaymentComplaints).mockResolvedValueOnce({
      items: mockComplaints,
      total: 1,
      limit: 15,
      offset: 0,
    });

    renderComponent();
    fireEvent.click(screen.getByRole("button", { name: /payment complaints/i }));

    await waitFor(() => {
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    const select = screen.getByRole("combobox");
    const options = Array.from(select.querySelectorAll("option")).map((o) => o.value);
    expect(options).toContain("open");
    expect(options).not.toContain("submitted");
  });
});
