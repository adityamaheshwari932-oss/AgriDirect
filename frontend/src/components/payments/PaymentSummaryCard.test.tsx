import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PaymentSummaryCard } from "./PaymentSummaryCard";
import type { PaymentSummary } from "../../types/payments";

const mockSummary: PaymentSummary = {
  order_id: "order-123",
  order_total: "10000.00",
  total_recorded: "8000.00",
  total_acknowledged: "6000.00",
  unacknowledged_amount: "2000.00",
  remaining_acknowledged_balance: "4000.00",
  remaining_payable_amount: "2000.00",
  max_available_for_new_payment: "2000.00",
  total_disputed: "0.00",
  settlement_status: "partially_settled",
  records_count: 2,
};

describe("PaymentSummaryCard", () => {
  it("renders payment reconciliation card with acknowledged and balance amounts", () => {
    render(<PaymentSummaryCard summary={mockSummary} />);

    expect(screen.getByText("Off-Platform Payment Reconciliation")).toBeInTheDocument();
    expect(screen.getByText("Partially Settled")).toBeInTheDocument();
    expect(screen.getByText("₹6,000.00")).toBeInTheDocument(); // Acknowledged
    expect(screen.getByText("₹4,000.00")).toBeInTheDocument(); // Remaining balance
  });

  it("renders loading pulse when isLoading is true", () => {
    const { container } = render(<PaymentSummaryCard summary={null} isLoading={true} />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });
});
