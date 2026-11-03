import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { FulfillmentApprovalModal } from "./FulfillmentApprovalModal";
import { ordersApi } from "../../api/orders";
import type { FulfillmentApproval } from "../../types/orders";

describe("FulfillmentApprovalModal", () => {
  const mockApproval: FulfillmentApproval = {
    id: "app-123",
    requirement_id: "req-456",
    order_id: "ord-789",
    order_item_id: "item-001",
    proposed_quantity: 100,
    approved_quantity: null,
    status: "pending",
    created_at: "2026-11-02T10:00:00Z",
    updated_at: "2026-11-02T10:00:00Z",
  };

  const onCloseMock = vi.fn();
  const onSuccessMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders modal with proposed quantity and order references", () => {
    render(
      <FulfillmentApprovalModal
        isOpen={true}
        approval={mockApproval}
        onClose={onCloseMock}
        onSuccess={onSuccessMock}
      />
    );

    expect(screen.getByText(/Review Demand Fulfillment/i)).toBeInTheDocument();
    expect(screen.getByText("100 units")).toBeInTheDocument();
    expect(screen.getByText("req-456")).toBeInTheDocument();
    expect(screen.getByText("ord-789")).toBeInTheDocument();
  });

  it("submits full quantity deduction approval", async () => {
    vi.spyOn(ordersApi, "approveFulfillment").mockResolvedValue({
      ...mockApproval,
      status: "approved",
      approved_quantity: 100,
    });

    render(
      <FulfillmentApprovalModal
        isOpen={true}
        approval={mockApproval}
        onClose={onCloseMock}
        onSuccess={onSuccessMock}
      />
    );

    const submitBtn = screen.getByRole("button", { name: /Confirm Approval/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(ordersApi.approveFulfillment).toHaveBeenCalledWith("app-123", {
        approved_quantity: undefined,
        close_requirement: false,
      });
      expect(onSuccessMock).toHaveBeenCalled();
      expect(onCloseMock).toHaveBeenCalled();
    });
  });

  it("submits custom partial quantity and closes requirement toggle", async () => {
    vi.spyOn(ordersApi, "approveFulfillment").mockResolvedValue({
      ...mockApproval,
      status: "approved",
      approved_quantity: 65,
    });

    render(
      <FulfillmentApprovalModal
        isOpen={true}
        approval={mockApproval}
        onClose={onCloseMock}
        onSuccess={onSuccessMock}
      />
    );

    // Select custom strategy
    const customRadio = screen.getByLabelText(/Custom Partial Deduction/i);
    fireEvent.click(customRadio);

    // Enter custom quantity
    const input = screen.getByPlaceholderText(/Enter amount/i);
    fireEvent.change(input, { target: { value: "65" } });

    // Check close requirement
    const closeCheckbox = screen.getByLabelText(/Close requirement upon approval/i);
    fireEvent.click(closeCheckbox);

    const submitBtn = screen.getByRole("button", { name: /Confirm Approval/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(ordersApi.approveFulfillment).toHaveBeenCalledWith("app-123", {
        approved_quantity: 65,
        close_requirement: true,
      });
      expect(onSuccessMock).toHaveBeenCalled();
    });
  });

  it("switches to reject tab and submits rejection with commercial explanation", async () => {
    vi.spyOn(ordersApi, "rejectFulfillment").mockResolvedValue({
      ...mockApproval,
      status: "rejected",
    });

    render(
      <FulfillmentApprovalModal
        isOpen={true}
        approval={mockApproval}
        onClose={onCloseMock}
        onSuccess={onSuccessMock}
      />
    );

    const rejectTab = screen.getByRole("button", { name: /Reject Deduction/i });
    fireEvent.click(rejectTab);

    const reasonInput = screen.getByPlaceholderText(/Explain why this order should not/i);
    fireEvent.change(reasonInput, { target: { value: "Quality mismatch with specification" } });

    const rejectBtn = screen.getByRole("button", { name: /Reject Demand Deduction/i });
    fireEvent.click(rejectBtn);

    await waitFor(() => {
      expect(ordersApi.rejectFulfillment).toHaveBeenCalledWith("app-123", {
        reason: "Quality mismatch with specification",
      });
      expect(onSuccessMock).toHaveBeenCalled();
      expect(onCloseMock).toHaveBeenCalled();
    });
  });
});
